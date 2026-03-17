# SEC Insight — Full Roadmap

## Overview
A deployed full-stack RAG system where users enter a stock ticker, the app fetches
the latest 10-K/10-Q from SEC EDGAR, and enables multi-turn conversational querying
with a comparison mode for two companies side by side.

**Target:** 5-7 weeks  
**Goal:** Impressive for FAANG + AI lab (Anthropic, OpenAI, Waymo) 2027 internship recruiting

---

## Phase 0 — Foundation concepts (Days 1-3)
No code. Learn before building.

### Learn
- [ ] RAG pipeline end to end (retrieval, chunking, embedding, generation)
- [ ] Vector embeddings + vector databases
- [ ] SEC EDGAR structure and API
- [ ] Hybrid search — BM25 vs vector search, why combine them
- [ ] Cross-encoder rerankers — what they are and when they help
- [ ] Small-to-big retrieval — parent document retrieval concept

### Check-in
Discuss each concept in Claude chat. You should be able to explain all six out loud
before writing any code.

---

## Phase 1 — Ingestion pipeline (Days 4-9)

### Build
- [ ] SEC EDGAR fetcher — fetch 10-K/10-Q by ticker symbol
- [ ] Table-aware PDF parsing with Unstructured (DIFFERENTIATOR)
- [ ] Recursive chunker with overlap
- [ ] Small-to-big chunk indexing (DIFFERENTIATOR)
- [ ] Chroma vector store setup + OpenAI embedding integration

### Learn first
- Chunking strategy tradeoffs (fixed-size vs recursive vs semantic)
- Why overlap prevents losing context at chunk boundaries
- What Unstructured does differently from naive text extraction

### Rules
- Write the chunker yourself first, no Claude Code. Then refactor.
- Manually inspect parsed tables from a real 10-K before moving on.

### Resume bullet
"Built ingestion pipeline with table-aware PDF parsing (Unstructured), small-to-big
chunk indexing, and OpenAI embeddings stored in Chroma vector store."

---

## Phase 2 — Retrieval engine (Days 10-16)

### Build
- [ ] Hybrid search — BM25 + vector search merged with Reciprocal Rank Fusion (DIFFERENTIATOR)
- [ ] Cross-encoder reranker via sentence-transformers (DIFFERENTIATOR)
- [ ] FastAPI RAG endpoint with streaming (SSE)
- [ ] Multi-turn conversation memory with contextual compression

### Learn first
- How cosine similarity search works
- What Reciprocal Rank Fusion does
- How contextual compression handles the "goldfish memory" problem

### Rules
- After building retrieval, run 10 manual test queries and inspect raw chunks.
- Verify hybrid + reranker beats plain vector search before moving on.

### Resume bullet
"Engineered hybrid retrieval pipeline combining BM25 and vector search with
cross-encoder reranking, achieving measurably higher precision on tabular
financial queries."

---

## Phase 3 — Frontend + source highlighting (Days 17-24)

### Build
- [ ] Vue 3 chat UI — ticker input, streaming response display
- [ ] Source highlighting + citations panel (DIFFERENTIATOR)
- [ ] Two-company side-by-side comparison mode
- [ ] Structured JSON output mode with Instructor/Pydantic

### Learn first
- How Server-Sent Events (SSE) work for streaming in Vue
- How to pass source chunk metadata back from the API for highlighting

### Notes
- Source highlighting is the interpretability story — critical for Anthropic.
- You already know Vue from J&J and LyftLogic. Focus learning time on SSE.

---

## Phase 4 — Eval harness (Days 25-31)

### Build
- [ ] RAGAS eval framework setup (faithfulness, answer relevancy, context precision)
- [ ] 20+ ground-truth Q&A pairs from real SEC filings
- [ ] LLM-as-a-judge automated scoring with GPT-4o (DIFFERENTIATOR)
- [ ] Benchmark: naive RAG vs hybrid RAG vs long-context stuffing (DIFFERENTIATOR)
- [ ] README comparison table: chunking strategy A vs B, embedding model A vs B (DIFFERENTIATOR)

### Why this matters
This phase is what separates the project from every other RAG demo on GitHub.
The README comparison table is the single most impressive thing to show an
Anthropic or OpenAI interviewer.

### Resume bullet
"Designed RAGAS eval harness with 20+ ground-truth pairs and LLM-as-a-judge
scoring; published benchmark comparing retrieval strategies and embedding models
by faithfulness and answer relevancy."

---

## Phase 5 — Deploy + ship (Days 32-40)

### Build
- [ ] Dockerize FastAPI backend
- [ ] Deploy backend to Railway
- [ ] Deploy Vue frontend to Vercel
- [ ] Connect frontend to Railway backend
- [ ] Write README with architecture diagram + benchmark table + live demo link

### Resume bullet
"Deployed production RAG system (Railway + Vercel, Dockerized) serving live users;
GitHub README includes architecture diagram and retrieval benchmark results."

---

## Interview narrative (draft)
"I built a financial RAG system that ingests SEC 10-K filings and lets users query
them conversationally. The interesting engineering problems were: (1) table-aware
parsing — standard text splitters mangle balance sheets, so I used Unstructured to
preserve table structure; (2) retrieval quality — I implemented hybrid search with
BM25 + vector and a cross-encoder reranker, and measured the improvement with a
RAGAS eval harness; (3) interpretability — the UI highlights the exact source
passage the answer came from."
