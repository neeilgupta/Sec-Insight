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
**Phase:** 1 — Ingestion pipeline
**Last completed:** Tasks 1 + 2 — `edgar_fetcher.py` and `parser.py`
**Working on:** Task 3 — `chunker.py` (recursive chunker with overlap)

Completed so far:
- `edgar_fetcher.py` — async ticker → CIK → filing URL lookup, smoke-tested against AAPL 10-K ✓
- `parser.py` — `partition_html` parsing with SEC-compliant httpx download, element type summary ✓

Next: write `chunker.py` from scratch (512 token chunks, 50 token overlap, recursive split on paragraphs → sentences → words) before using Claude Code on it.

## Repo
https://github.com/[your-username]/sec-insight
