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
**Phase:** 2 — Retrieval Engine ✓ complete, moving to Phase 3
**Last completed:** Phase 1 ✓, Phase 2 ✓ (all components done)

### Phase 1 — Ingestion pipeline ✓
- `backend/ingestion/edgar_fetcher.py` — async ticker → CIK → filing URL lookup
- `backend/ingestion/parser.py` — table-aware HTML parsing via Unstructured
- `backend/ingestion/chunker.py` — recursive prose + table chunker, small-to-big, tiktoken (50-token overlap)
- `backend/ingestion/indexer.py` — OpenAI embeddings + Chroma upsert, idempotent write path; stores `parent_text` inline in Chroma metadata

### Phase 2 — Retrieval engine ✓
- `backend/retrieval/hybrid_search.py` — BM25 + Chroma vector search merged with RRF (k=60); fetches all child chunks for BM25 at query time; returns top-20 as `List[dict]` with keys `chunk_id, text, metadata, rrf_score` ✓
- `backend/retrieval/reranker.py` — cross-encoder reranking (`cross-encoder/ms-marco-MiniLM-L-6-v2`); deduplicates on child text before slicing top-5; swaps in `parent_text` from metadata for small-to-big retrieval; returns `List[dict]` with keys `chunk_id, text, metadata, rrf_score, rerank_score` ✓
- `backend/api/query.py` — FastAPI POST `/query` with SSE streaming; pipeline: hybrid search → rerank → build prompt → stream GPT-4o; emits `sources`, `token`, `done` events; latency logged via `time.perf_counter` for each stage; CORS enabled; context blocks prefixed with `[heading]` for LLM citation; delegates session history to `SessionManager` ✓
- `backend/api/session.py` — `SessionManager` class with contextual compression; keeps last 6 messages (3 turns) verbatim; older turns summarised via GPT-4o into a rolling summary string injected as `{"role":"system"}` at position 0 of history; incremental compression (each call extends existing summary, not rewrite); preserves financial figures/tickers/filing refs in summary prompt; module-level `session_manager` singleton imported by `query.py` ✓

### Key implementation notes
- Chroma collection name format: `"{TICKER}_{FILING_TYPE}_{DATE}"` e.g. `"AAPL_10-K_2024-09-28"` (hyphen in filing type)
- `parent_text` is stored inline in each child chunk's Chroma metadata — no separate parent document or `parent_id` field
- BM25 index is built at query time from all docs fetched via `collection.get()` (not at ingestion time); known scaling risk — cache the index per collection at first-query time before going to real filings
- Cross-encoder scores can be negative; dedup happens after sort, before top-k slice
- Context passed to LLM is formatted as `[{heading}]\n{text}` so the model can cite real section names
- `parent_text` repetition bug: was caused by fixture using `* 40` on a single NarrativeText element — `_flush_prose` joins all buffer elements, so the repeated string became the parent. Fixed by updating the fixture to use realistic, distinct text. When re-indexing, delete the collection first (`client.delete_collection(...)`) — Chroma upserts by ID, so stale chunks survive a plain re-run.
- SSE format: each event is `data: {json}\n\n`; `sources` event fires before LLM stream starts; `done` event fires after session history is written
- Session compression fires inside `add_message` after appending (not lazily at read time), keeping `get_history` synchronous; Turn 4 onward triggers two GPT-4o compression calls per turn (one for user msg, one for assistant msg) but both happen after `done` is yielded so they don't block the stream
- Latency profile (observed): hybrid_search ~150ms warm (1100ms cold start from CrossEncoder load), rerank ~75ms, LLM first token ~400–1200ms (dominant bottleneck, network-bound)

## Repo
https://github.com/[your-username]/sec-insight
