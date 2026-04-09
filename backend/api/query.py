"""
FastAPI RAG endpoint — POST /query

Pipeline
--------
session history → hybrid_search → rerank → build prompt → stream GPT-4o

SSE event types
---------------
sources  {"type":"sources","chunks":[{chunk_id, text (≤300 chars), metadata, rerank_score}]}
token    {"type":"token","content":"..."}
done     {"type":"done"}
"""

from __future__ import annotations

import json
import logging
import time
from typing import AsyncGenerator

import chromadb

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel

from backend.retrieval.hybrid_search import hybrid_search
from backend.retrieval.reranker import rerank

load_dotenv()

from backend.api.session import session_manager  # noqa: E402

# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

_openai = AsyncOpenAI()

LLM_MODEL = "gpt-4o"
CHROMA_PATH = "./chroma_db"

# ---------------------------------------------------------------------------
# FastAPI app + CORS
# ---------------------------------------------------------------------------

app = FastAPI(title="SEC Insight API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    query: str
    collection_name: str  # e.g. "AAPL_10-K_2024-09-28"
    session_id: str = ""


class CompareRequest(BaseModel):
    query: str
    collection_a: str
    collection_b: str
    answer_a: str
    answer_b: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_collection(collection_name: str) -> tuple[str, str, str]:
    """Return (company, filing_type, year) from a collection name string.

    Expected format: "{TICKER}_{FILING_TYPE}_{DATE}"
    Example: "AAPL_10-K_2024-09-28" → ("AAPL", "10-K", "2024")
    """
    parts = collection_name.split("_", 2)
    if len(parts) < 3:
        return collection_name, "", ""
    company = parts[0]
    filing_type = parts[1]
    year = parts[2][:4]
    return company, filing_type, year


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


# ---------------------------------------------------------------------------
# Streaming generator
# ---------------------------------------------------------------------------


async def _stream(
    query: str,
    collection_name: str,
    session_id: str,
) -> AsyncGenerator[str, None]:
    # ------------------------------------------------------------------
    # 1. Hybrid search
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    candidates = hybrid_search(query, collection_name, top_k=20)
    logger.info("[LATENCY] hybrid_search: %.0fms | results=%d", (time.perf_counter() - t0) * 1000, len(candidates))

    if not candidates:
        yield _sse({"type": "error", "message": f"No indexed data found for collection: {collection_name}"})
        yield _sse({"type": "done"})
        return

    # ------------------------------------------------------------------
    # 2. Rerank
    # ------------------------------------------------------------------
    t1 = time.perf_counter()
    ranked = rerank(query, candidates, collection_name, top_k=8)
    logger.info("[LATENCY] rerank: %.0fms | results=%d", (time.perf_counter() - t1) * 1000, len(ranked))

    # ------------------------------------------------------------------
    # 3. Emit sources event (text truncated to 300 chars)
    # ------------------------------------------------------------------
    source_chunks = [
        {
            "chunk_id": r["chunk_id"],
            "text": r["text"][:300],
            "metadata": r["metadata"],
            "rerank_score": r["rerank_score"],
        }
        for r in ranked
    ]
    yield _sse({"type": "sources", "chunks": source_chunks})

    # ------------------------------------------------------------------
    # 4. Build prompt
    # ------------------------------------------------------------------
    company, filing_type, year = _parse_collection(collection_name)
    context = "\n\n---\n\n".join(
        f"[{r['metadata'].get('heading', 'Unknown Section')}]\n{r['text']}"
        for r in ranked
    )

    system_prompt = (
        "You are a financial analyst assistant. Answer the user's question using ONLY\n"
        "the provided excerpts from the SEC filing. Always cite which section your answer\n"
        "comes from. If the relevant information is only partially present, summarize what\n"
        "is available and briefly note what is missing. Use markdown formatting: bold key\n"
        "numbers, use bullet points for lists, and use tables for structured comparisons.\n\n"
        f"Filing: {company} {filing_type} {year}\n"
        f"Excerpts:\n{context}"
    )

    history = session_manager.get_history(session_id)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": query})

    # ------------------------------------------------------------------
    # 5. Stream GPT-4o
    # ------------------------------------------------------------------
    t_llm = time.perf_counter()
    first_token = True
    full_reply: list[str] = []

    stream = await _openai.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        stream=True,
    )

    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content is None:
            continue
        if first_token:
            logger.info(
                "[LATENCY] LLM first token: %.0fms",
                (time.perf_counter() - t_llm) * 1000,
            )
            first_token = False
        full_reply.append(content)
        yield _sse({"type": "token", "content": content})

    # ------------------------------------------------------------------
    # 6. Update session history
    # ------------------------------------------------------------------
    if session_id:
        await session_manager.add_message(session_id, "user", query)
        await session_manager.add_message(session_id, "assistant", "".join(full_reply))

    # ------------------------------------------------------------------
    # 7. Done
    # ------------------------------------------------------------------
    yield _sse({"type": "done"})


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@app.get("/collections")
def collections_endpoint() -> dict:
    """Return sorted list of all indexed Chroma collection names."""
    db = chromadb.PersistentClient(path=CHROMA_PATH)
    names = sorted(col.name for col in db.list_collections())
    return {"collections": names}


@app.post("/query")
async def query_endpoint(request: QueryRequest) -> StreamingResponse:
    return StreamingResponse(
        _stream(request.query, request.collection_name, request.session_id),
        media_type="text/event-stream",
    )


async def _stream_synthesis(req: CompareRequest) -> AsyncGenerator[str, None]:
    company_a = _parse_collection(req.collection_a)[0]
    company_b = _parse_collection(req.collection_b)[0]

    system_prompt = (
        "You are a financial analyst. Given the same question asked of two companies and "
        "their answers extracted from SEC filings, write a concise 2-3 sentence comparative "
        "analysis highlighting key similarities and differences. Use specific numbers when "
        "available. Be direct. Use markdown bold for key figures."
    )
    user_msg = (
        f"Question: {req.query}\n\n"
        f"**{company_a}:**\n{req.answer_a}\n\n"
        f"**{company_b}:**\n{req.answer_b}"
    )

    stream = await _openai.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        stream=True,
    )

    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content is None:
            continue
        yield _sse({"type": "token", "content": content})

    yield _sse({"type": "done"})


@app.post("/compare")
async def compare_endpoint(req: CompareRequest) -> StreamingResponse:
    return StreamingResponse(
        _stream_synthesis(req),
        media_type="text/event-stream",
    )


# ---------------------------------------------------------------------------
# Manual verification — python -m backend.api.query
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    COLLECTION = "AAPL_10-K_2024-09-28"
    SESSION = "test-session"
    QUERIES = [
        "What were Apple's total net sales in fiscal 2024?",
        "What is the gross margin percentage for fiscal 2024?",
        "How did revenue from Services compare to prior year?",
        "What were the main risk factors Apple highlighted in the filing?",
    ]

    async def _run_query(query: str) -> None:
        print(f"\n{'='*70}")
        print(f"Query: {query}")
        print("=" * 70)

        token_count = 0
        sources: list[dict] = []
        reply_parts: list[str] = []

        async for raw_event in _stream(query, COLLECTION, SESSION):
            print(raw_event, end="")  # print raw SSE line as it arrives
            # strip "data: " prefix and parse
            line = raw_event.strip()
            if not line.startswith("data: "):
                continue
            event = json.loads(line[len("data: "):])

            if event["type"] == "sources":
                sources = event["chunks"]
            elif event["type"] == "token":
                token_count += 1
                reply_parts.append(event["content"])
            # "done" needs no extra handling

        full_answer = "".join(reply_parts)

        print(f"\n--- SUMMARY ---")
        print(f"Token events : {token_count}")
        print(f"Sources ({len(sources)}):")
        for i, s in enumerate(sources, 1):
            print(f"  #{i}  score={s['rerank_score']:>7.4f}  chunk_id={s['chunk_id']}")
        print(f"\nFull answer:\n{full_answer}")

    async def _main() -> None:
        for q in QUERIES:
            await _run_query(q)

    asyncio.run(_main())
