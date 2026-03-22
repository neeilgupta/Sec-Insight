"""
Hybrid search — BM25 (keyword) + Chroma vector search, merged with
Reciprocal Rank Fusion (RRF, k=60).

Query path only. Ingestion / embedding lives in backend/ingestion/indexer.py.

Public API
----------
hybrid_search(query, collection_name, top_k=20) -> List[dict]
    Each dict: chunk_id, text, metadata, rrf_score
"""

from __future__ import annotations

import numpy as np
from rank_bm25 import BM25Okapi

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ---------------------------------------------------------------------------
# Module-level singletons — match indexer.py exactly
# ---------------------------------------------------------------------------

_chroma = chromadb.PersistentClient(path="./chroma_db")
_openai = OpenAI()  # reads OPENAI_API_KEY from environment

EMBED_MODEL = "text-embedding-3-small"
BM25_CANDIDATES = 50
VECTOR_CANDIDATES = 50
RRF_K = 60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def _embed(query: str) -> list[float]:
    resp = _openai.embeddings.create(model=EMBED_MODEL, input=[query])
    return resp.data[0].embedding


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def hybrid_search(
    query: str,
    collection_name: str,
    top_k: int = 20,
) -> list[dict]:
    """Hybrid BM25 + vector search merged with Reciprocal Rank Fusion.

    Args:
        query: Natural-language question.
        collection_name: Chroma collection (e.g. ``"AAPL_10K_2024-09-28"``).
        top_k: Number of merged results to return (default 20).

    Returns:
        List of dicts with keys: ``chunk_id``, ``text``, ``metadata``,
        ``rrf_score``.  Sorted by ``rrf_score`` descending.
    """
    collection = _chroma.get_or_create_collection(name=collection_name)

    # ------------------------------------------------------------------
    # 1. Fetch all child chunks for BM25 index
    # ------------------------------------------------------------------
    all_data = collection.get(include=["documents", "metadatas"])
    all_ids: list[str] = all_data["ids"]
    all_docs: list[str] = all_data["documents"]
    all_metas: list[dict] = all_data["metadatas"]

    if not all_ids:
        return []

    # Build a lookup so we can reconstruct results by chunk_id
    id_to_doc = {id_: doc for id_, doc in zip(all_ids, all_docs)}
    id_to_meta = {id_: meta for id_, meta in zip(all_ids, all_metas)}

    # ------------------------------------------------------------------
    # 2. BM25 search — top-50
    # ------------------------------------------------------------------
    corpus = [_tokenize(doc) for doc in all_docs]
    bm25 = BM25Okapi(corpus)
    query_tokens = _tokenize(query)
    bm25_scores = bm25.get_scores(query_tokens)

    n_bm25 = min(BM25_CANDIDATES, len(all_ids))
    bm25_top_indices = np.argsort(bm25_scores)[::-1][:n_bm25]
    bm25_ids = [all_ids[i] for i in bm25_top_indices]

    # ------------------------------------------------------------------
    # 3. Vector search — top-50
    # ------------------------------------------------------------------
    query_embedding = _embed(query)
    n_vector = min(VECTOR_CANDIDATES, len(all_ids))
    vector_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_vector,
        include=["documents", "metadatas"],
    )
    vector_ids: list[str] = vector_results["ids"][0]

    # ------------------------------------------------------------------
    # 4. Reciprocal Rank Fusion (k=60)
    # ------------------------------------------------------------------
    rrf_scores: dict[str, float] = {}
    for rank, id_ in enumerate(bm25_ids):
        rrf_scores[id_] = rrf_scores.get(id_, 0.0) + 1.0 / (RRF_K + rank + 1)
    for rank, id_ in enumerate(vector_ids):
        rrf_scores[id_] = rrf_scores.get(id_, 0.0) + 1.0 / (RRF_K + rank + 1)

    sorted_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)
    top_ids = sorted_ids[:top_k]

    # ------------------------------------------------------------------
    # 5. Build result list
    # ------------------------------------------------------------------
    return [
        {
            "chunk_id": id_,
            "text": id_to_doc[id_],
            "metadata": id_to_meta[id_],
            "rrf_score": rrf_scores[id_],
        }
        for id_ in top_ids
    ]


# ---------------------------------------------------------------------------
# Manual verification
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    COLLECTION = "AAPL_10-K_2024-09-28"
    QUERIES = [
        "What were Apple's total net sales in fiscal 2024?",
        "What is the gross margin percentage for fiscal 2024?",
        "How did Services revenue perform compared to prior year?",
    ]

    for q in QUERIES:
        print(f"\nQuery: {q}")
        results = hybrid_search(q, COLLECTION, top_k=20)
        print(f"  {'chunk_id':<45} rrf_score")
        print(f"  {'-'*45} ---------")
        for r in results[:5]:
            print(f"  {r['chunk_id']:<45} {r['rrf_score']:.6f}")
