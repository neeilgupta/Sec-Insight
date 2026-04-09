"""
Bulk re-ingestion script — re-indexes all SEC filing collections with the
current chunker (fixed auto-flush logic).

Run from the project root:
    python scripts/reingest_all.py

Each ticker's collection is deleted then recreated cleanly (handled by
indexer.py's delete-then-create logic). The pipeline always fetches the
latest available 10-K from EDGAR.

Skip META — it was already re-ingested with the fixed chunker.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Ensure project root is on the path when running as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# Tickers to re-ingest (all except META which was already fixed)
TICKERS = [
    "AAPL",
    "AMZN",
    "GOOGL",
    "JPM",
    "LLY",
    "MA",
    "MSFT",
    "NFLX",
    "NVDA",
    "TSLA",
    "V",
    "WMT",
    "XOM",
]

CHROMA_PATH = "./chroma_db"

# Legacy collection created during early testing (missing hyphen in "10K")
LEGACY_COLLECTIONS_TO_DELETE = ["AAPL_10K_2024-09-28"]


def _delete_legacy_collections() -> None:
    db = chromadb.PersistentClient(path=CHROMA_PATH)
    for name in LEGACY_COLLECTIONS_TO_DELETE:
        try:
            db.delete_collection(name=name)
            logger.info("Deleted legacy collection: %r", name)
        except Exception:
            logger.info("Legacy collection not found (already gone): %r", name)


async def _reingest_all() -> None:
    from backend.ingestion.pipeline import ingest

    _delete_legacy_collections()

    total = len(TICKERS)
    for i, ticker in enumerate(TICKERS, 1):
        logger.info("=" * 60)
        logger.info("[%d/%d] Re-ingesting %s 10-K …", i, total, ticker)
        try:
            collection_name = await ingest(ticker, "10-K")
            logger.info("[%d/%d] Done: %s → collection=%r", i, total, ticker, collection_name)
        except Exception as exc:
            logger.error("[%d/%d] FAILED for %s: %s", i, total, ticker, exc)

    logger.info("=" * 60)
    logger.info("Re-ingestion complete. Final collections:")
    db = chromadb.PersistentClient(path=CHROMA_PATH)
    for col in sorted(db.list_collections(), key=lambda c: c.name):
        count = db.get_collection(col.name).count()
        logger.info("  %-35s %d chunks", col.name, count)


if __name__ == "__main__":
    asyncio.run(_reingest_all())
