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
**Phase:** 3 — Frontend in progress (Task 1 Vue chat UI ✓, pipeline.py ✓, /collections endpoint ✓)
**Last completed:** Phase 1 ✓, Phase 2 ✓, Phase 3 Task 1 ✓

### Phase 1 — Ingestion pipeline ✓
- `backend/ingestion/edgar_fetcher.py` — async ticker → CIK → filing URL lookup; `get_filing_url()` returns URL; `get_filing_info()` returns `(url, filing_date)` tuple ✓
- `backend/ingestion/parser.py` — table-aware HTML parsing via Unstructured
- `backend/ingestion/chunker.py` — recursive prose + table chunker, small-to-big, tiktoken (50-token overlap)
- `backend/ingestion/indexer.py` — OpenAI embeddings + Chroma upsert, idempotent write path; stores `parent_text` inline in Chroma metadata
- `backend/ingestion/pipeline.py` — orchestrates: `get_filing_info → parse_filing → _to_dicts → chunk_elements → index_chunks`; CLI: `python -m backend.ingestion.pipeline AAPL 10-K` ✓

### Phase 3 — Frontend + source highlighting (in progress)
- `frontend/` — Vue 3 + Vite + TypeScript scaffold ✓
- `frontend/src/composables/useSSE.ts` — `fetch` + `ReadableStream` SSE reader (NOT EventSource — endpoint is POST); parses `sources`/`token`/`done` events; buffers incomplete lines across reads ✓
- `frontend/src/components/TickerInput.vue` — fetches `GET /api/collections` on mount; shows `<select>` dropdown of indexed filings (format: `AAPL · 10-K · 2024-09-28`); emits `submit(query, collectionName)` with selected collection name ✓
- `frontend/src/components/ChatWindow.vue` — scrollable message list; auto-scrolls on new content ✓
- `frontend/src/components/MessageBubble.vue` — user/assistant bubbles; numbered citation badges; badge click emits `highlightSource(index)` ✓
- `frontend/src/components/StreamingResponse.vue` — live token display with blinking CSS cursor ✓
- `frontend/src/components/SourcePanel.vue` — right panel 40% width; source cards with section heading + rerank score; highlighted card gets indigo left border ✓
- `frontend/src/App.vue` — root layout; session ID via `crypto.randomUUID()`; all state lives here ✓
- `frontend/src/components/ComparisonView.vue` — **blank stub** (Phase 3 Task 3)
- `backend/api/structured.py` — **blank stub** (Phase 3 Task 4)

### Phase 2 — Retrieval engine ✓
- `backend/retrieval/hybrid_search.py` — BM25 + Chroma vector search merged with RRF (k=60); fetches all child chunks for BM25 at query time; returns top-20 as `List[dict]` with keys `chunk_id, text, metadata, rrf_score` ✓
- `backend/retrieval/reranker.py` — cross-encoder reranking (`cross-encoder/ms-marco-MiniLM-L-6-v2`); deduplicates on child text before slicing top-5; swaps in `parent_text` from metadata for small-to-big retrieval; returns `List[dict]` with keys `chunk_id, text, metadata, rrf_score, rerank_score` ✓
- `backend/api/query.py` — FastAPI POST `/query` with SSE streaming; `GET /collections` returns sorted Chroma collection names; pipeline: hybrid search → rerank → build prompt → stream GPT-4o; emits `sources`, `token`, `done` events; CORS enabled ✓
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
- `python -m backend.ingestion.pipeline TICKER 10-K` indexes any real SEC filing; Chroma collection named `TICKER_FILING-TYPE_DATE`; UI dropdown auto-populates from `GET /collections`
- Frontend vite dev proxy: `/api/*` → `http://localhost:8000/*` (strips `/api` prefix); frontend never hardcodes backend URL
- `SEC_USER_AGENT` env var required for EDGAR requests (format: `"Name email@domain.com"`); already in `.env.example`

## Repo
https://github.com/[your-username]/sec-insight
