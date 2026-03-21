"""
SEC filing indexer — embeds child chunks via OpenAI and persists them to a
local Chroma collection.

Write path only. The read/query path lives in vector_store.py.
Each Chroma record stores the child_text as the document, its embedding, and
all chunk metadata including parent_text — so retrieval can return full context
without a second lookup.
"""

import time

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

from backend.ingestion.chunker import Chunk, chunk_elements

# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_openai = OpenAI()  # reads OPENAI_API_KEY from environment
_chroma = chromadb.PersistentClient(path="./chroma_db")

EMBED_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALLOWED_TYPES = (str, int, float, bool)


def _safe_metadata(metadata: dict) -> dict:
    """Convert any non-Chroma-safe values to str."""
    return {
        k: v if isinstance(v, _ALLOWED_TYPES) else str(v)
        for k, v in metadata.items()
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def index_chunks(
    chunks: list[Chunk],
    ticker: str,
    filing_type: str,
    filing_date: str,
) -> str:
    """Embed and upsert chunks into a Chroma collection.

    Args:
        chunks: Output of ``chunk_elements()``.
        ticker: Stock ticker, e.g. ``"AAPL"``.
        filing_type: ``"10-K"`` or ``"10-Q"``.
        filing_date: ISO date string, e.g. ``"2024-09-28"``.

    Returns:
        The Chroma collection name, e.g. ``"AAPL_10K_2024-09-28"``.
    """
    collection_name = f"{ticker}_{filing_type}_{filing_date}"
    collection = _chroma.get_or_create_collection(name=collection_name)

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        texts = [c.child_text for c in batch]

        resp = _openai.embeddings.create(model=EMBED_MODEL, input=texts)
        embeddings = [d.embedding for d in resp.data]

        collection.upsert(
            ids=[c.chunk_id for c in batch],
            embeddings=embeddings,
            documents=texts,
            metadatas=[
                _safe_metadata({**c.metadata, "parent_text": c.parent_text})
                for c in batch
            ],
        )

        if i + BATCH_SIZE < len(chunks):
            time.sleep(1)

    return collection_name


def get_parent(collection_name: str, chunk_id: str) -> str:
    """Return the parent_text for a given chunk_id.

    Args:
        collection_name: Chroma collection to query.
        chunk_id: The ``chunk_id`` field from a :class:`Chunk`.

    Returns:
        The ``parent_text`` stored in that chunk's metadata.

    Raises:
        IndexError: If ``chunk_id`` is not found in the collection.
    """
    collection = _chroma.get_or_create_collection(name=collection_name)
    result = collection.get(ids=[chunk_id], include=["metadatas"])
    return result["metadatas"][0]["parent_text"]


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    FIXTURE = [
        {
            "type": "Title",
            "text": "Item 8. Financial Statements",
            "metadata": {"page_number": 42, "filename": "test.htm"},
        },
        {
            "type": "NarrativeText",
            "text": (
                "Apple Inc. reported total net sales of $391.0 billion for fiscal 2024, "
                "representing a modest increase compared to the prior year. "
                "The growth was primarily driven by strength in the Services segment, "
                "which reached an all-time high revenue of $96.2 billion. "
            ) * 40,
            "metadata": {"page_number": 42, "filename": "test.htm"},
        },
        {
            "type": "NarrativeText",
            "text": "The following table summarizes revenue by geographic segment.",
            "metadata": {"page_number": 43, "filename": "test.htm"},
        },
        {
            "type": "Table",
            "text": (
                "Segment | 2024 | 2023\n"
                "Americas | 167.0 | 162.1\n"
                "Europe | 101.3 | 94.3\n"
                "Greater China | 66.9 | 72.6\n"
                "Japan | 25.0 | 24.3\n"
                "Rest of Asia Pacific | 30.7 | 29.6\n"
                "Total Net Sales | 391.0 | 383.0"
            ),
            "metadata": {"page_number": 43, "filename": "test.htm"},
        },
        {
            "type": "NarrativeText",
            "text": (
                "Management's discussion continues with an analysis of gross margin trends. "
                "Gross margin was 46.2% for fiscal 2024, up from 44.1% in fiscal 2023, "
                "reflecting favorable mix shift toward higher-margin Services revenue."
            ),
            "metadata": {"page_number": 44, "filename": "test.htm"},
        },
    ]

    chunks = chunk_elements(FIXTURE, ticker="AAPL", filing_type="10-K", filing_date="2024-09-28")

    print(f"Chunked into {len(chunks)} chunks. Indexing...")
    collection_name = index_chunks(chunks, "AAPL", "10-K", "2024-09-28")
    print(f"Indexed {len(chunks)} chunks into collection '{collection_name}'")

    parent = get_parent(collection_name, chunks[0].chunk_id)
    print(f"\nParent text (first 200 chars):\n{parent[:200]}")

    assert parent == chunks[0].parent_text, "Roundtrip mismatch!"
    print("\nRoundtrip OK")
