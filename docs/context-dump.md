# SEC Insight — Claude Context Dump

Paste this at the top of any new Claude or Claude Code conversation.

---

I'm building **SEC Insight** — a full-stack financial RAG system that lets users query SEC 10-K/10-Q filings conversationally by entering a stock ticker.

## Stack
- **Backend:** FastAPI + Python
- **Frontend:** Vue 3 + Vite
- **Vector DB:** Chroma
- **Embeddings:** OpenAI text-embedding-3-small
- **LLM:** GPT-4o (streaming)
- **Deploy:** Railway (backend) + Vercel (frontend)
- **Containerization:** Docker

## Differentiators (what makes this not a generic RAG demo)
1. **Table-aware PDF parsing** via Unstructured — can query specific balance sheet cells
2. **Hybrid search** — BM25 + vector search merged with Reciprocal Rank Fusion
3. **Cross-encoder reranker** — sentence-transformers reranker on top of hybrid results
4. **Small-to-big retrieval** — embed small chunks, feed parent chunks to LLM
5. **RAGAS eval harness** — faithfulness + answer relevancy scoring with LLM-as-a-judge
6. **Source highlighting** — UI shows exact paragraph/table the answer came from
7. **README benchmark table** — comparison of chunking strategies + embedding models by eval metrics

## Phases
- Phase 0 — Foundation concepts (no code)
- Phase 1 — Ingestion pipeline
- Phase 2 — Retrieval engine
- Phase 3 — Frontend + source highlighting
- Phase 4 — Eval harness
- Phase 5 — Deploy + ship

## Current status
**Phase:** 2 — Retrieval Engine (in progress)
**Last completed:** Phase 1 — Ingestion pipeline ✓, Phase 2 retrieval core ✓

### Phase 1 — Ingestion pipeline ✓
- `backend/ingestion/edgar_fetcher.py` — async ticker → CIK → filing URL lookup
- `backend/ingestion/parser.py` — table-aware HTML parsing via Unstructured
- `backend/ingestion/chunker.py` — recursive prose + table chunker, small-to-big, tiktoken (50-token overlap)
- `backend/ingestion/indexer.py` — OpenAI embeddings + Chroma upsert, idempotent write path; stores `parent_text` inline in Chroma metadata
- `vector_store.py` — skipped; indexer.py covers the full Phase 1 spec

### Phase 2 — Retrieval engine (in progress)
Completed:
- `backend/retrieval/hybrid_search.py` — BM25 + Chroma vector search merged with RRF (k=60); fetches all child chunks for BM25 at query time; returns top-20 as `List[dict]` with keys `chunk_id, text, metadata, rrf_score` ✓
- `backend/retrieval/reranker.py` — cross-encoder reranking (`cross-encoder/ms-marco-MiniLM-L-6-v2`); deduplicates on child text before slicing top-5; swaps in `parent_text` from metadata for small-to-big retrieval; returns `List[dict]` with keys `chunk_id, text, metadata, rrf_score, rerank_score` ✓

Next:
- `backend/api/query.py` — FastAPI `/query` POST endpoint, SSE streaming: hybrid search → rerank → build prompt → stream GPT-4o response with source metadata
- `backend/api/session.py` — multi-turn conversation memory with contextual compression (keep last 6 messages, summarize older turns)

### Key implementation notes
- Chroma collection name format: `"{TICKER}_{FILING_TYPE}_{DATE}"` e.g. `"AAPL_10-K_2024-09-28"` (hyphen in filing type)
- `parent_text` is stored inline in each child chunk's Chroma metadata — no separate parent document or `parent_id` field
- BM25 index is built at query time from all docs fetched via `collection.get()` (not at ingestion time)
- Cross-encoder scores can be negative; dedup happens after sort, before top-k slice

## Repo
https://github.com/[your-username]/sec-insight
