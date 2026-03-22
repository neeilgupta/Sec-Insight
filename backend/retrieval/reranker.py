"""
Cross-encoder reranker — scores each (query, child_chunk) pair and swaps in
the parent chunk text for small-to-big retrieval.

Takes the List[dict] output of hybrid_search() directly as input.

Public API
----------
rerank(query, candidates, collection_name, top_k=5) -> List[dict]
    Each dict: chunk_id, text (parent), metadata, rrf_score, rerank_score

Schema note
-----------
The indexer stores parent_text inline in each chunk's Chroma metadata, so
parent lookup is a dict access rather than a second Chroma query.
collection_name is kept in the signature for forward-compatibility with
schemas that use a separate parent_id lookup.
"""

from __future__ import annotations

from sentence_transformers import CrossEncoder

from backend.retrieval.hybrid_search import hybrid_search

# ---------------------------------------------------------------------------
# Module-level singleton — model is downloaded once, then cached
# ---------------------------------------------------------------------------

_cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def rerank(
    query: str,
    candidates: list[dict],
    collection_name: str,
    top_k: int = 5,
) -> list[dict]:
    """Cross-encode candidates and swap in parent text for the top results.

    Args:
        query: Natural-language question.
        candidates: Output of ``hybrid_search()`` — list of dicts with keys
            ``chunk_id``, ``text``, ``metadata``, ``rrf_score``.
        collection_name: Chroma collection name (kept for forward-compat).
        top_k: Number of reranked results to return (default 5).

    Returns:
        List of dicts with keys: ``chunk_id``, ``text`` (parent text if
        available, else child text), ``metadata``, ``rrf_score``,
        ``rerank_score``.  Sorted by ``rerank_score`` descending.
    """
    if not candidates:
        return []

    # ------------------------------------------------------------------
    # 1. Score every (query, child_text) pair in one batch call
    # ------------------------------------------------------------------
    pairs = [(query, c["text"]) for c in candidates]
    scores = _cross_encoder.predict(pairs)  # np.ndarray, can be negative

    # ------------------------------------------------------------------
    # 2. Sort by score descending, deduplicate on child text, take top_k
    # ------------------------------------------------------------------
    ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
    seen_texts: set[str] = set()
    deduped = []
    for score, c in ranked:
        if c["text"] not in seen_texts:
            seen_texts.add(c["text"])
            deduped.append((score, c))
    top = deduped[:top_k]

    # ------------------------------------------------------------------
    # 3. Swap in parent text (small-to-big retrieval)
    #    parent_text is stored inline in metadata by the indexer
    # ------------------------------------------------------------------
    results = []
    for score, c in top:
        parent_text = c["metadata"].get("parent_text") or c["text"]
        results.append(
            {
                "chunk_id": c["chunk_id"],
                "text": parent_text,
                "metadata": c["metadata"],
                "rrf_score": c["rrf_score"],
                "rerank_score": float(score),
            }
        )

    return results


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
        print(f"\n{'='*70}")
        print(f"Query: {q}")
        candidates = hybrid_search(q, COLLECTION, top_k=20)
        results = rerank(q, candidates, COLLECTION)

        print(f"\n  {'rank':<5} {'rerank_score':<14} {'rrf_score':<12} text[:200]")
        print(f"  {'-'*5} {'-'*14} {'-'*12} {'-'*40}")
        for i, r in enumerate(results[:3], 1):
            print(
                f"\n  #{i}  score={r['rerank_score']:>8.4f}  "
                f"rrf={r['rrf_score']:.6f}"
            )
            print(f"  chunk_id: {r['chunk_id']}")
            print(f"  text: {r['text'][:200]}")
