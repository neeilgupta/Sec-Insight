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
**Phase:** 1 → 2 transition
**Last completed:** Phase 1 — Ingestion pipeline ✓

Completed files:
- `edgar_fetcher.py` — async ticker → CIK → filing URL lookup ✓
- `parser.py` — table-aware HTML parsing via Unstructured ✓
- `chunker.py` — recursive prose + table chunker, small-to-big, tiktoken ✓
- `indexer.py` — OpenAI embeddings + Chroma upsert, idempotent write path ✓
- `vector_store.py` — skipped; indexer.py covers the full Phase 1 spec

Next: learn Phase 2 concepts (cosine similarity, RRF, cross-encoder reranking,
SSE streaming) before building retrieval engine.

## Repo
https://github.com/[your-username]/sec-insight
