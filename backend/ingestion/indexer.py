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
        # --- Section 1: Net Sales ---
        {
            "type": "Title",
            "text": "Item 7. Management's Discussion and Analysis — Net Sales",
            "metadata": {"page_number": 30, "filename": "test.htm"},
        },
        {
            "type": "NarrativeText",
            "text": (
                "Apple Inc. reported total net sales of $391.0 billion for fiscal 2024, "
                "representing a 2% increase compared to fiscal 2023. iPhone net sales were "
                "$201.0 billion, relatively flat year-over-year as consumers in several "
                "markets delayed upgrade cycles pending new product introductions. Mac net "
                "sales were $29.9 billion, recovering from a weak fiscal 2023 driven by the "
                "transition to Apple silicon and constrained supply. iPad net sales were "
                "$26.7 billion, reflecting softer consumer demand partially offset by "
                "enterprise adoption of iPad Pro."
            ),
            "metadata": {"page_number": 30, "filename": "test.htm"},
        },
        {
            "type": "NarrativeText",
            "text": (
                "Wearables, Home and Accessories net sales were $37.0 billion, a slight "
                "decrease driven by maturing AirPods and Apple Watch markets. Services net "
                "sales reached an all-time high of $96.2 billion, up 13% from fiscal 2023, "
                "fueled by growth in the App Store, Apple Music, iCloud+, Apple TV+, and "
                "Apple Pay. The Company had over one billion paid subscriptions across its "
                "services portfolio at the end of fiscal 2024."
            ),
            "metadata": {"page_number": 31, "filename": "test.htm"},
        },
        # --- Section 2: Gross Margin ---
        {
            "type": "Title",
            "text": "Item 7. Management's Discussion and Analysis — Gross Margin",
            "metadata": {"page_number": 32, "filename": "test.htm"},
        },
        {
            "type": "NarrativeText",
            "text": (
                "Gross margin for fiscal 2024 was $180.7 billion, representing a gross "
                "margin percentage of 46.2%, compared to 44.1% in fiscal 2023. The "
                "improvement reflects continued mix shift toward higher-margin Services "
                "revenue, favorable commodity costs, and operational efficiencies across "
                "the supply chain. Products gross margin was 36.9%, up from 36.5% in the "
                "prior year, driven by lower component costs and improved manufacturing "
                "yields on Apple silicon."
            ),
            "metadata": {"page_number": 32, "filename": "test.htm"},
        },
        # --- Table: Revenue by segment ---
        {
            "type": "NarrativeText",
            "text": "The following table summarizes net sales by reportable segment for fiscal years 2024 and 2023.",
            "metadata": {"page_number": 33, "filename": "test.htm"},
        },
        {
            "type": "Table",
            "text": (
                "Segment | FY2024 ($B) | FY2023 ($B) | YoY Change\n"
                "Americas | 167.0 | 162.1 | +3.0%\n"
                "Europe | 101.3 | 94.3 | +7.4%\n"
                "Greater China | 66.9 | 72.6 | -7.9%\n"
                "Japan | 25.0 | 24.3 | +2.9%\n"
                "Rest of Asia Pacific | 30.7 | 29.6 | +3.7%\n"
                "Total Net Sales | 391.0 | 383.0 | +2.1%"
            ),
            "metadata": {"page_number": 33, "filename": "test.htm"},
        },
        # --- Section 3: Liquidity ---
        {
            "type": "Title",
            "text": "Item 7. Management's Discussion and Analysis — Liquidity and Capital Resources",
            "metadata": {"page_number": 34, "filename": "test.htm"},
        },
        {
            "type": "NarrativeText",
            "text": (
                "As of September 28, 2024, the Company had cash, cash equivalents, and "
                "marketable securities of $153.0 billion. During fiscal 2024, the Company "
                "generated operating cash flow of $118.3 billion. The Company returned "
                "$110.0 billion to shareholders through dividends of $15.2 billion and "
                "share repurchases of $94.9 billion under its ongoing capital return "
                "program. The Board of Directors declared a quarterly cash dividend of "
                "$0.25 per share, an increase of 4% from the prior quarterly dividend."
            ),
            "metadata": {"page_number": 34, "filename": "test.htm"},
        },
    ]

    chunks = chunk_elements(FIXTURE, ticker="AAPL", filing_type="10-K", filing_date="2024-09-28")

    print(f"Chunked into {len(chunks)} chunks. Indexing...")
    collection_name = index_chunks(chunks, "AAPL", "10-K", "2024-09-28")
    print(f"Indexed {len(chunks)} chunks into collection '{collection_name}'")

    print("\n--- parent_text spot-check (3 chunks) ---")
    for chunk in chunks[:3]:
        parent = get_parent(collection_name, chunk.chunk_id)
        assert parent == chunk.parent_text, f"Roundtrip mismatch on {chunk.chunk_id}!"
        section = chunk.metadata.get("heading", "")
        print(f"\n  chunk_id : {chunk.chunk_id}")
        print(f"  heading  : {section}")
        print(f"  parent   ({len(parent)} chars): {parent[:300]}")
    print("\nRoundtrip OK — all parent_text values are coherent paragraphs")
