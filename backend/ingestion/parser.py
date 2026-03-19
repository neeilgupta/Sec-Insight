"""
SEC filing parser — downloads an HTML filing and extracts structured elements
using the Unstructured library, preserving table structure.
"""

import asyncio
import collections

import httpx
from unstructured.documents.elements import Element
from unstructured.partition.html import partition_html


async def parse_filing(source: str, user_agent: str) -> list[Element]:
    """Parse an SEC filing into structured elements.

    Args:
        source: URL (https://...) or local file path to an HTML filing.
        user_agent: SEC-required User-Agent header, e.g. "Jane Doe jane@example.com".

    Returns:
        List of Unstructured Element objects (Title, NarrativeText, Table, etc.).

    Raises:
        httpx.HTTPStatusError: On non-2xx response when fetching a URL.
        FileNotFoundError: If a local path does not exist.
    """
    if source.startswith("http"):
        headers = {
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate",
        }
        async with httpx.AsyncClient(
            headers=headers, follow_redirects=True, timeout=30.0
        ) as client:
            resp = await client.get(source)
            resp.raise_for_status()
            html_text = resp.text

        elements = partition_html(text=html_text)
    else:
        elements = partition_html(filename=source)

    return elements


def _summarize(elements: list[Element]) -> None:
    """Print a summary of element type counts, sorted by frequency."""
    counts = collections.Counter(type(el).__name__ for el in elements)
    print(f"\nParsed {len(elements)} total elements:\n")
    for name, count in counts.most_common():
        print(f"  {name}: {count}")
    print()


if __name__ == "__main__":
    TEST_URL = (
        "https://www.sec.gov/Archives/edgar/data/0000320193"
        "/000032019325000079/aapl-20250927.htm"
    )
    USER_AGENT = "Sec-Insight dev@example.com"

    print(f"Fetching and parsing: {TEST_URL}")
    elements = asyncio.run(parse_filing(TEST_URL, USER_AGENT))
    _summarize(elements)
