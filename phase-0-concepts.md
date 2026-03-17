# Phase 0 — Foundation Concepts

No code in this phase. Every concept here should be explainable out loud
before Phase 1 starts.

---

## 1. RAG pipeline end to end

**What it is:** Retrieval-Augmented Generation. Gives an LLM a custom memory
system by retrieving relevant document chunks before generating an answer.

**The four steps:**
1. **Chunking** — split documents into overlapping pieces
2. **Embedding** — convert each chunk to a vector (list of numbers representing meaning)
3. **Retrieval** — embed the user query, find closest chunks by cosine similarity
4. **Generation** — pass retrieved chunks + query to LLM, get grounded answer

**Key insight:** Indexing (chunking + embedding) happens once. Querying happens
every request. The vector DB bridges them.

**Critical rule:** The embedding model used during indexing and querying MUST be
the same. Vectors only have meaning relative to each other within the same space.

**Notes from learning session:**
[ Add your own notes here after discussing with Claude ]

---

## 2. Vector embeddings + vector databases

**What an embedding is:** A list of numbers (e.g. 1,536 for OpenAI's model)
that represents the *meaning* of text in high-dimensional space. Similar meaning
= nearby vectors.

**What a vector DB does:** Stores vectors and lets you search by similarity
(cosine similarity) rather than exact keyword match.

**Chroma:** The vector DB used in this project. Runs locally, easy setup,
good for prototyping.

**Notes from learning session:**
[ Add your own notes here ]

---

## 3. SEC EDGAR structure

**What SEC filings are:**
- **10-K** — annual report, ~100-300 pages, covers revenue, risks, strategy, debt
- **10-Q** — quarterly version, shorter, filed 3x/year
- All publicly available for free on EDGAR (SEC's government database)

**EDGAR API:** Free, no auth required for basic fetching. Can retrieve filings
by ticker symbol (e.g. AAPL) and filing type (10-K, 10-Q).

**Why this matters for parsing:** SEC filings are dense with tables (balance sheets,
income statements) that naive text splitters mangle. This is why Unstructured is
needed.

**Notes from learning session:**
[ Add your own notes here ]

---

## 4. Hybrid search — BM25 + vector (DIFFERENTIATOR)

**Why pure vector search isn't enough:**
- Vector search finds semantically similar chunks but can miss exact keyword matches
- BM25 is a classic keyword-based ranking algorithm — great for specific terms,
  financial figures, company names
- Hybrid = best of both

**How they're combined:** Reciprocal Rank Fusion (RRF) — each result gets a score
based on its rank in both lists, then scores are merged.

**Interview talking point:** "Pure vector search missed specific financial figures
because the embeddings smoothed out the numeric precision. BM25 catches those exactly."

**Notes from learning session:**
[ Add your own notes here ]

---

## 5. Cross-encoder rerankers (DIFFERENTIATOR)

**What they are:** A second-pass model that scores each (query, chunk) pair
directly — more accurate than embedding similarity but slower.

**The two-stage retrieval pattern:**
1. Fast retrieval: get top-50 candidates via hybrid search
2. Accurate reranking: cross-encoder scores all 50, return top-5

**Why this matters:** The embedding similarity is an approximation. The
cross-encoder actually reads both the query and the chunk together — much
more accurate for finding the truly relevant passage.

**Library:** sentence-transformers — `cross-encoder/ms-marco-MiniLM-L-6-v2`
is a good starting model.

**Notes from learning session:**
[ Add your own notes here ]

---

## 6. Small-to-big retrieval (DIFFERENTIATOR)

**The problem with standard chunking:** Small chunks = better search precision.
Large chunks = better context for the LLM. You can't have both with one chunk size.

**The solution:** Index small chunks for retrieval, but when a small chunk matches,
fetch its larger "parent" chunk to send to the LLM.

**Example:**
- Index: 100-word chunks (good for precise embedding similarity)
- Feed to LLM: the 400-word parent paragraph containing that chunk (good for context)

**Also called:** Parent document retrieval.

**Notes from learning session:**
[ Add your own notes here ]

---

## Check-in questions (answer these before Phase 1)

1. If I change my embedding model halfway through the project, what breaks and why?
2. Why would BM25 outperform vector search for the query "What was Apple's R&D spend in Q3?"
3. What's the tradeoff between retrieving more chunks (higher k) vs fewer?
4. Why does a cross-encoder need to see both the query and the chunk at the same time?
5. What happens if you make chunks too small? Too large?
