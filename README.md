# Sec-Insight
I'm building SEC Insight — a financial RAG system for querying SEC 10-K/10-Q filings. Stack: FastAPI + Python backend, Vue 3 frontend, Chroma vector DB, OpenAI embeddings, deployed on Railway + Vercel. Differentiators: table-aware parsing with Unstructured, hybrid search (BM25 + vector + cross-encoder reranker), small-to-big retrieval, RAGAS eval
