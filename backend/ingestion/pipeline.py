"""
End-to-end ingestion pipeline: ticker + form type → Chroma collection.

Orchestrates:
    edgar_fetcher.get_filing_info  →  parser.parse_filing
    →  _to_dicts  →  chunker.chunk_elements  →  indexer.index_chunks

Usage (CLI):
    python -m backend.ingestion.pipeline AAPL 10-K
    python -m backend.ingestion.pipeline MSFT 10-K
    python -m backend.ingestion.pipeline TSLA 10-Q
    python -m backend.ingestion.pipeline AAPL 10-K --index 1
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import time

from dotenv import load_dotenv

load_dotenv()

from backend.ingestion.chunker import chunk_elements
from backend.ingestion.edgar_fetcher import FormType, get_filing_info
from backend.ingestion.indexer import index_chunks
from backend.ingestion.parser import parse_filing

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _to_dicts(elements: list) -> list[dict]:
    """Convert Unstructured Element objects to plain dicts expected by chunk_elements().

    chunk_elements() expects: [{"type": str, "text": str, "metadata": {"page_number": ..., "filename": ...}}]
    Unstructured elements expose: type(el).__name__, el.text, el.metadata.page_number, el.metadata.filename
    """
    return [
        {
            "type": type(el).__name__,
            "text": el.text,
            "metadata": {
                "page_number": getattr(el.metadata, "page_number", None),
                "filename": getattr(el.metadata, "filename", None),
            },
        }
        for el in elements
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def ingest(ticker: str, form_type: FormType, index: int = 0) -> str:
    """Fetch, parse, chunk, and index a filing into Chroma.

    Args:
        ticker: Stock ticker symbol, e.g. "AAPL". Case-insensitive.
        form_type: "10-K" (annual) or "10-Q" (quarterly).
        index: 0 = most recent filing, 1 = next most recent, etc.

    Returns:
        Chroma collection name, e.g. "AAPL_10-K_2024-09-28".

    Raises:
        ValueError: If ticker not found or no matching filings on EDGAR.
        httpx.HTTPStatusError: On non-2xx SEC API response.
        KeyError: If SECuser_agent env var is missing from .env.
    """
    ticker = ticker.upper()
    user_agent = os.environ["SEC_USER_AGENT"]

    # Stage 1 — Fetch filing URL + date from EDGAR
    t0 = time.perf_counter()
    logger.info("[1/4] Fetching %s %s from EDGAR...", ticker, form_type)
    filing = await get_filing_info(ticker, form_type, user_agent, index=index)
    logger.info(
        "      ✓  url=%s  filed=%s period=%s  (%.1fs)",
        filing.url, filing.filing_date, filing.report_date or "?", time.perf_counter() - t0,
    )

    # Stage 2 — Download and parse HTML filing
    t0 = time.perf_counter()
    logger.info("[2/4] Parsing filing HTML (this may take ~30s for large filings)...")
    elements = await parse_filing(filing.url, user_agent)
    element_dicts = _to_dicts(elements)
    logger.info("      ✓  %d elements parsed  (%.1fs)", len(element_dicts), time.perf_counter() - t0)

    # Stage 3 — Chunk elements into child+parent pairs
    t0 = time.perf_counter()
    logger.info("[3/4] Chunking...")
    chunks = chunk_elements(
        element_dicts,
        ticker=ticker,
        filing_type=form_type,
        filing_date=filing.filing_date,
    )
    logger.info("      ✓  %d chunks  (%.1fs)", len(chunks), time.perf_counter() - t0)

    # Stage 4 — Embed and upsert to Chroma
    t0 = time.perf_counter()
    logger.info("[4/4] Indexing to Chroma (OpenAI embeddings, ~1s per 100 chunks)...")
    collection_name = index_chunks(chunks, ticker, form_type, filing.filing_date)
    logger.info("      ✓  collection=%s  (%.1fs)", collection_name, time.perf_counter() - t0)

    return collection_name


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _parser = argparse.ArgumentParser(description="Ingest a SEC filing into Chroma.")
    _parser.add_argument("ticker", help="Stock ticker symbol, e.g. AAPL")
    _parser.add_argument(
        "form_type", nargs="?", default="10-K", choices=["10-K", "10-Q"],
        help="SEC form type (default: 10-K)",
    )
    _parser.add_argument(
        "--index", type=int, default=0,
        help="Recency index: 0 = most recent filing, 1 = next most recent, etc (default: 0)",
    )
    _args = _parser.parse_args()

    collection = asyncio.run(ingest(_args.ticker, _args.form_type, index=_args.index))

    print(f"\nDone. Collection: {collection}")
    print(f"Now query it in the UI: ticker={_args.ticker.upper()}, filing={_args.form_type}")
