from __future__ import annotations

import instructor
from fastapi import APIRouter
from openai import AsyncOpenAI
from pydantic import BaseModel

from backend.retrieval.hybrid_search import hybrid_search
from backend.retrieval.reranker import rerank

router = APIRouter()

_openai = instructor.from_openai(AsyncOpenAI())


def _parse_collection(collection_name: str) -> tuple[str, str, str]:
    """Return (ticker, filing_type, year) from e.g. 'AAPL_10-K_2024-09-28'."""
    parts = collection_name.split("_", 2)
    if len(parts) < 3:
        return collection_name, "", ""
    return parts[0], parts[1], parts[2][:4]


class KeyFigure(BaseModel):
    label: str    # e.g. "Total Net Sales"
    value: str    # e.g. "$391.0 billion"
    section: str  # e.g. "Consolidated Statements of Operations"


class _LLMExtraction(BaseModel):
    """Fields the LLM fills in — known fields are set by Python after the call."""
    answer: str
    key_figures: list[KeyFigure]
    confidence: float  # 1.0=directly stated, 0.5=inferred, 0.1=not found


class StructuredAnswer(BaseModel):
    ticker: str
    filing_type: str
    year: str
    question: str
    answer: str
    key_figures: list[KeyFigure]
    confidence: float


class StructuredQueryRequest(BaseModel):
    query: str
    collection_name: str


@router.post("/structured_query", response_model=StructuredAnswer)
async def structured_query(request: StructuredQueryRequest) -> StructuredAnswer:
    candidates = hybrid_search(request.query, request.collection_name, top_k=20)
    ranked = rerank(request.query, candidates, request.collection_name, top_k=8)

    ticker, filing_type, year = _parse_collection(request.collection_name)
    context = "\n\n---\n\n".join(
        f"[{r['metadata'].get('heading', 'Unknown Section')}]\n{r['text']}"
        for r in ranked
    )

    system_prompt = (
        "You are a financial analyst. Extract a structured answer from the provided "
        "SEC filing excerpts. Populate key_figures with every specific number, "
        "percentage, or dollar amount you reference. Set confidence to 1.0 if the "
        "answer is directly stated, 0.5 if inferred, 0.1 if not found.\n\n"
        f"Filing: {ticker} {filing_type} {year}\nExcerpts:\n{context}"
    )

    extracted: _LLMExtraction = await _openai.chat.completions.create(
        model="gpt-4o",
        response_model=_LLMExtraction,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.query},
        ],
    )

    return StructuredAnswer(
        ticker=ticker,
        filing_type=filing_type,
        year=year,
        question=request.query,
        answer=extracted.answer,
        key_figures=extracted.key_figures,
        confidence=extracted.confidence,
    )
