# Phase 2 — Retrieval Engine

**Timeline:** Days 10-16  
**Goal:** A FastAPI backend that takes a user question and returns a streamed,
grounded answer using hybrid search + reranking.

---

## Learn before building

- [ ] How cosine similarity search works mathematically
- [ ] What Reciprocal Rank Fusion (RRF) does to merge ranked lists
- [ ] How contextual compression handles multi-turn conversation memory
- [ ] What streaming SSE looks like from a FastAPI endpoint

---

## Build tasks

### 1. Hybrid search (DIFFERENTIATOR)
**File:** `backend/retrieval/hybrid_search.py`

Combine BM25 (keyword) + vector (semantic) search, merge with RRF.

```bash
pip install rank-bm25
```

Steps:
1. Build BM25 index from all child chunks at ingestion time
2. At query time: run BM25 search → top-50 results
3. At query time: run vector similarity search → top-50 results
4. Merge both lists with Reciprocal Rank Fusion
5. Return top-20 merged candidates for reranking

RRF formula: `score(d) = Σ 1 / (k + rank(d))` where k=60 is standard.

**Validation:** Run the same 5 queries with pure vector vs hybrid. For queries
containing specific financial figures, hybrid should rank the right chunk higher.

---

### 2. Cross-encoder reranker (DIFFERENTIATOR)
**File:** `backend/retrieval/reranker.py`

```bash
pip install sentence-transformers
```

Model: `cross-encoder/ms-marco-MiniLM-L-6-v2` (fast, good quality)

Steps:
1. Take top-20 from hybrid search
2. Score each (query, child_chunk) pair with cross-encoder
3. Sort by score, take top-5
4. Look up parent chunks for each of the top-5
5. Return parent chunks as context to LLM

**Validation:** Compare reranked results vs pre-rerank results on 10 test queries.
Document where reranker helped and where it didn't.

---

### 3. FastAPI RAG endpoint (streaming)
**File:** `backend/api/query.py`

```python
@app.post("/query")
async def query(request: QueryRequest):
    # 1. Hybrid search
    # 2. Rerank
    # 3. Fetch parent chunks
    # 4. Build prompt
    # 5. Stream LLM response via SSE
```

Streaming: use `StreamingResponse` with Server-Sent Events format.

System prompt template:
```
You are a financial analyst assistant. Answer the user's question using ONLY
the provided excerpts from the SEC filing. If the answer is not in the excerpts,
say so explicitly. Always cite which section your answer comes from.

Filing: {company} {filing_type} {year}
Excerpts:
{context}
```

Return in each SSE event:
- The streamed token
- Source chunk metadata (for frontend highlighting)

---

### 4. Multi-turn conversation memory
**File:** `backend/api/session.py`

The "goldfish memory" problem: naively passing all history bloats the context window.

Solution — contextual compression:
1. Store full conversation history server-side (keyed by session ID)
2. Before each new query, compress old turns: summarize exchanges older than N turns
3. Pass: compressed history + last 3 full turns + new query

Simple implementation to start:
```python
history = []  # list of {role, content}
# Keep last 6 messages (3 turns), summarize the rest
```

---

## Validation checklist before Phase 3

- [ ] Hybrid search returns better results than pure vector on financial figure queries
- [ ] Reranker measurably improves top-5 precision on 10 test queries (document this)
- [ ] FastAPI endpoint streams tokens correctly
- [ ] Source chunk metadata included in SSE response
- [ ] Multi-turn: third question in a conversation still has context from first question
- [ ] Latency measured: vector search time, reranker time, LLM time (log these)

---

## Check-in with Claude chat after this phase

Explain out loud:
1. Why RRF works better than just averaging scores from BM25 and vector search
2. One specific query where the reranker changed the top result and why
3. How your contextual compression decides what to summarize vs keep
4. End-to-end latency breakdown (where is the bottleneck?)

---

## Resume bullet (fill in your actual numbers)
"Engineered hybrid retrieval pipeline combining BM25 and vector search with
Reciprocal Rank Fusion and cross-encoder reranking; measured [X]% precision
improvement over naive vector search on held-out financial queries."
