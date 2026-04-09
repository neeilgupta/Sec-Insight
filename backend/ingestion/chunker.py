"""
SEC filing chunker — converts Unstructured element dicts into Chunk objects
for embedding and retrieval.

Implements small-to-big chunking: child chunks (small) are embedded and used
for similarity search; parent chunks (large) are stored in metadata and fed
to the LLM at retrieval time.

Tables are always isolated into their own parent — never merged with prose.
Prose is accumulated by section (bounded by headings), then split recursively.
"""

import re
from dataclasses import dataclass, field
from uuid import uuid4

import tiktoken

# ---------------------------------------------------------------------------
# Token utilities
# ---------------------------------------------------------------------------

_enc = tiktoken.get_encoding("cl100k_base")

PARENT_MAX_TOKENS = 2048
PROSE_CHUNK_SIZE = 512
PROSE_OVERLAP = 50
TABLE_CHUNK_SIZE = 128
TABLE_OVERLAP = 20

TABLE_TYPES = {"Table", "TableChunk"}
HEADING_TYPES = {"Title", "Header"}


def _count(text: str) -> int:
    return len(_enc.encode(text))


def _truncate(text: str, max_tokens: int) -> str:
    tokens = _enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return _enc.decode(tokens[:max_tokens])


# ---------------------------------------------------------------------------
# Chunk dataclass
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    child_text: str
    parent_text: str
    metadata: dict
    chunk_id: str = field(default_factory=lambda: str(uuid4()))


# ---------------------------------------------------------------------------
# Splitting helpers
# ---------------------------------------------------------------------------

def _merge_pieces(pieces: list[str], chunk_size: int, overlap: int, sep: str = " ") -> list[str]:
    """Greedily merge atomic text pieces into windows of up to chunk_size tokens
    with a sliding overlap."""
    window: list[str] = []
    window_tokens = 0
    results: list[str] = []

    for piece in pieces:
        piece_tokens = _count(piece)
        if window and window_tokens + piece_tokens > chunk_size:
            results.append(sep.join(window))
            # Drop pieces from front until remaining tokens <= overlap
            while window and window_tokens > overlap:
                removed = window.pop(0)
                window_tokens -= _count(removed)
        window.append(piece)
        window_tokens += piece_tokens

    if window:
        results.append(sep.join(window))

    return results


def _split_prose(text: str, chunk_size: int = PROSE_CHUNK_SIZE, overlap: int = PROSE_OVERLAP) -> list[str]:
    """Recursively split prose text into atomic pieces, then merge with overlap."""

    def _atomize(text: str) -> list[str]:
        if _count(text) <= chunk_size:
            return [text]

        # 1. Split on paragraphs
        parts = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(parts) > 1:
            atoms: list[str] = []
            for part in parts:
                atoms.extend(_atomize(part))
            return atoms

        # 2. Split on sentence endings
        parts = [s.strip() for s in re.split(r'(?<=[.!?]) +', text) if s.strip()]
        if len(parts) > 1:
            atoms = []
            for part in parts:
                atoms.extend(_atomize(part))
            return atoms

        # 3. Split on words
        words = text.split(" ")
        if len(words) > 1:
            atoms = []
            for word in words:
                atoms.extend(_atomize(word))
            return atoms

        # 4. Hard token cut — single token or unsplittable
        return [_truncate(text, chunk_size)]

    atoms = _atomize(text)
    return _merge_pieces(atoms, chunk_size, overlap)


def _split_table(text: str, chunk_size: int = TABLE_CHUNK_SIZE, overlap: int = TABLE_OVERLAP) -> list[str]:
    """Split a table by rows, then merge with overlap, preserving row boundaries."""
    rows = [r.strip() for r in text.split("\n") if r.strip()]
    return _merge_pieces(rows, chunk_size, overlap, sep="\n")


# ---------------------------------------------------------------------------
# Flush helpers
# ---------------------------------------------------------------------------

def _flush_prose(
    buffer: list[dict],
    heading: str,
    ticker: str,
    filing_type: str,
    filing_date: str,
    chunk_index: int,
) -> tuple[list[Chunk], int]:
    if not buffer:
        return [], chunk_index

    first_meta = buffer[0].get("metadata", {})
    page_number = first_meta.get("page_number", "unknown")
    filename = first_meta.get("filename", "unknown")

    parent_text = _truncate(
        " ".join(el["text"] for el in buffer if el.get("text")),
        PARENT_MAX_TOKENS,
    )
    children = _split_prose(parent_text)
    chunks: list[Chunk] = []

    for i, child_text in enumerate(children):
        chunks.append(Chunk(
            child_text=child_text,
            parent_text=parent_text,
            metadata={
                "ticker": ticker,
                "filing_type": filing_type,
                "filing_date": filing_date,
                "heading": heading,
                "page_number": page_number,
                "filename": filename,
                "element_type": "prose",
                "is_table": False,
                "chunk_index": i,
            },
        ))
        chunk_index += 1

    return chunks, chunk_index


def _flush_table(
    element: dict,
    heading: str,
    ticker: str,
    filing_type: str,
    filing_date: str,
    chunk_index: int,
) -> tuple[list[Chunk], int]:
    meta = element.get("metadata", {})
    page_number = meta.get("page_number", "unknown")
    filename = meta.get("filename", "unknown")

    parent_text = _truncate(element.get("text", ""), PARENT_MAX_TOKENS)
    children = _split_table(parent_text)
    chunks: list[Chunk] = []

    for i, child_text in enumerate(children):
        chunks.append(Chunk(
            child_text=child_text,
            parent_text=parent_text,
            metadata={
                "ticker": ticker,
                "filing_type": filing_type,
                "filing_date": filing_date,
                "heading": heading,
                "page_number": page_number,
                "filename": filename,
                "element_type": element.get("type", "Table"),
                "is_table": True,
                "chunk_index": i,
            },
        ))
        chunk_index += 1

    return chunks, chunk_index


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chunk_elements(
    elements: list[dict],
    ticker: str,
    filing_type: str,
    filing_date: str,
) -> list[Chunk]:
    """Convert a list of Unstructured element dicts into Chunk objects.

    Args:
        elements: Dicts with keys ``type``, ``text``, and ``metadata``
                  (metadata contains ``page_number`` and ``filename``).
        ticker: Stock ticker, e.g. ``"AAPL"``.
        filing_type: ``"10-K"`` or ``"10-Q"``.
        filing_date: ISO date string, e.g. ``"2024-09-28"``.

    Returns:
        List of :class:`Chunk` objects ready for embedding.
    """
    all_chunks: list[Chunk] = []
    prose_buffer: list[dict] = []
    current_heading: str = ""
    chunk_index: int = 0

    for element in elements:
        el_type = element.get("type", "")

        if el_type in TABLE_TYPES:
            # Flush accumulated prose first
            new_chunks, chunk_index = _flush_prose(
                prose_buffer, current_heading, ticker, filing_type, filing_date, chunk_index
            )
            all_chunks.extend(new_chunks)
            prose_buffer = []

            # Isolate table into its own parent
            new_chunks, chunk_index = _flush_table(
                element, current_heading, ticker, filing_type, filing_date, chunk_index
            )
            all_chunks.extend(new_chunks)

        elif el_type in HEADING_TYPES:
            # Flush current prose section before starting new one
            new_chunks, chunk_index = _flush_prose(
                prose_buffer, current_heading, ticker, filing_type, filing_date, chunk_index
            )
            all_chunks.extend(new_chunks)
            prose_buffer = []
            current_heading = element.get("text", "")

        else:
            prose_buffer.append(element)
            # Auto-flush when buffer exceeds parent size to prevent truncation
            buffer_tokens = sum(_count(el.get("text", "")) for el in prose_buffer)
            if buffer_tokens >= PARENT_MAX_TOKENS:
                new_chunks, chunk_index = _flush_prose(
                    prose_buffer, current_heading, ticker, filing_type, filing_date, chunk_index
                )
                all_chunks.extend(new_chunks)
                prose_buffer = []

    # Flush any remaining prose
    new_chunks, chunk_index = _flush_prose(
        prose_buffer, current_heading, ticker, filing_type, filing_date, chunk_index
    )
    all_chunks.extend(new_chunks)

    return all_chunks


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
                # Repeated ~40x to exceed 512 tokens and force splitting + overlap
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

    print(f"\n{len(chunks)} chunks produced:\n")
    for chunk in chunks:
        kind = "TABLE" if chunk.metadata["is_table"] else "PROSE"
        tokens = _count(chunk.child_text)
        preview = chunk.child_text[:80].replace("\n", " ")
        print(f"  [{chunk.metadata['chunk_index']}] {kind} | {tokens} tokens | {preview}...")

    print()
