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

ITEM_RE = re.compile(r"^\s*ITEM\s+(\d{1,2})\s*([A-C])?\s*[.:—-]", re.IGNORECASE)
TABLE_MIN_TOKENS = 30
CAPTION_MAX_TOKENS = 50


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
    parent_id: str = field(default_factory=lambda: str(uuid4()))


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


def _atomize(text: str, chunk_size: int) -> list[str]:
    """Recursively split text into atomic pieces no larger than chunk_size
    tokens, preferring paragraph, then sentence, then word boundaries."""
    if _count(text) <= chunk_size:
        return [text]

    # 1. Split on paragraphs
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(parts) > 1:
        atoms: list[str] = []
        for part in parts:
            atoms.extend(_atomize(part, chunk_size))
        return atoms

    # 2. Split on sentence endings
    parts = [s.strip() for s in re.split(r'(?<=[.!?]) +', text) if s.strip()]
    if len(parts) > 1:
        atoms = []
        for part in parts:
            atoms.extend(_atomize(part, chunk_size))
        return atoms

    # 3. Split on words
    words = text.split(" ")
    if len(words) > 1:
        atoms = []
        for word in words:
            atoms.extend(_atomize(word, chunk_size))
        return atoms

    # 4. Hard token cut — single token or unsplittable
    return [_truncate(text, chunk_size)]


def _split_prose(text: str, chunk_size: int = PROSE_CHUNK_SIZE, overlap: int = PROSE_OVERLAP) -> list[str]:
    """Recursively split prose text into atomic pieces, then merge with overlap."""
    atoms = _atomize(text, chunk_size)
    return _merge_pieces(atoms, chunk_size, overlap)


def _split_into_parents(text: str, max_tokens: int = PARENT_MAX_TOKENS) -> list[str]:
    """Split text into as many <=max_tokens parents as needed, with zero
    overlap, so the parents partition the text instead of truncating it."""
    if not text:
        return []
    atoms = _atomize(text, max_tokens)
    return _merge_pieces(atoms, max_tokens, overlap=0)


def _split_table(text: str, chunk_size: int = TABLE_CHUNK_SIZE, overlap: int = TABLE_OVERLAP) -> list[str]:
    """Split a table by rows, then merge with overlap, preserving row boundaries."""
    rows = [r.strip() for r in text.split("\n") if r.strip()]
    return _merge_pieces(rows, chunk_size, overlap, sep="\n")


# ---------------------------------------------------------------------------
# Section-item detection
# ---------------------------------------------------------------------------

def _find_section_markers(elements: list[dict]) -> dict[int, tuple[str, str]]:
    """First pass over elements: find ITEM section markers, then drop
    table-of-contents runs.

    A TOC lists every item heading a few elements apart near the start of a
    filing; a body marker is usually hundreds of elements from the next one.
    A contiguous run of >= 5 markers spaced <3 elements apart is discarded as
    a TOC, but only when the run starts at Item 1 — a real TOC always
    enumerates from the top, whereas Part III (Items 10-14) is a run of
    one-line cross-references to the proxy statement and must be kept.
    Returns {element_index: (section_item, section_title)} for markers that
    survive.
    """

    markers: list[tuple[int, str, str]] = []
    for idx, element in enumerate(elements):
        text = element.get("text") or ""
        match = ITEM_RE.match(text)
        if not match:
            continue
        number, suffix = match.group(1), match.group(2) or ""
        item = f"{int(number)}{suffix.upper()}"
        markers.append((idx, item, text.strip()))

    surviving: list[tuple[int, str, str]] = []
    i = 0
    while i < len(markers):
        j = i
        while j + 1 < len(markers) and markers[j + 1][0] - markers[j][0] < 3:
            j += 1
        is_toc = j - i + 1 >= 5 and markers[i][1] == "1"
        if not is_toc:
            surviving.extend(markers[i:j + 1])
        i = j + 1

    return {idx: (item, text) for idx, item, text in surviving}


def _extract_caption(element: dict | None) -> str:
    """Return the preceding element's text as a table caption or "" if it
    doesn't look like a short introductory sentence."""
    if element is None:
        return ""
    text = (element.get("text") or "").strip()
    if not text or _count(text) > CAPTION_MAX_TOKENS:
        return ""
    if not text.endswith((".", ":")):
        return ""
    if text.count("|") > 1: # looks like a table row,  not a sentence
        return ""
    return text

# ---------------------------------------------------------------------------
# Flush helpers
# ---------------------------------------------------------------------------

def _flush_prose(
    buffer: list[dict],
    heading: str,
    section_item: str,
    section_title: str,
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

    full_text = " ".join(el["text"] for el in buffer if el.get("text"))
    parent_texts = _split_into_parents(full_text, PARENT_MAX_TOKENS)
    chunks: list[Chunk] = []

    for parent_text in parent_texts:
        parent_id = str(uuid4())
        children = _split_prose(parent_text)

        for i, child_text in enumerate(children):
            chunks.append(Chunk(
                child_text=child_text,
                parent_text=parent_text,
                parent_id=parent_id,
                metadata={
                    "ticker": ticker,
                    "filing_type": filing_type,
                    "filing_date": filing_date,
                    "heading": heading,
                    "section_item": section_item,
                    "section_title": section_title,
                    "page_number": page_number,
                    "filename": filename,
                    "element_type": "prose",
                    "is_table": False,
                    "chunk_index": i,
                    "parent_id": parent_id,
                },
            ))
            chunk_index += 1

    return chunks, chunk_index


def _flush_table(
    element: dict,
    heading: str,
    section_item: str,
    section_title: str,
    caption: str,
    ticker: str,
    filing_type: str,
    filing_date: str,
    chunk_index: int,
) -> tuple[list[Chunk], int]:
    meta = element.get("metadata", {})
    page_number = meta.get("page_number", "unknown")
    filename = meta.get("filename", "unknown")

    table_text = element.get("text", "")
    # The caption also survives as its own prose chunk (flushed just before
    # this table) — duplicated on purpose, so the table has a linguistic
    # hook even if the prose chunk isn't the one retrieved.
    raw_parent_text = f"{caption} {table_text}" if caption else table_text
    parent_text = _truncate(raw_parent_text, PARENT_MAX_TOKENS)

    if _count(parent_text) < TABLE_MIN_TOKENS:
        return [], chunk_index

    children = _split_table(parent_text)
    parent_id = str(uuid4())
    chunks: list[Chunk] = []

    for i, child_text in enumerate(children):
        chunks.append(Chunk(
            child_text=child_text,
            parent_text=parent_text,
            parent_id=parent_id,
            metadata={
                "ticker": ticker,
                "filing_type": filing_type,
                "filing_date": filing_date,
                "heading": heading,
                "section_item": section_item,
                "section_title": section_title,
                "page_number": page_number,
                "filename": filename,
                "element_type": element.get("type", "Table"),
                "is_table": True,
                "chunk_index": i,
                "parent_id": parent_id,
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
    current_item: str = ""
    current_title: str = ""
    chunk_index: int = 0

    section_markers = _find_section_markers(elements)

    for idx, element in enumerate(elements):
        el_type = element.get("type", "")

        if el_type in TABLE_TYPES:
            # Grab the caption before the flush empties prose_buffer
            caption = _extract_caption(prose_buffer[-1] if prose_buffer else None)

            # Flush accumulated prose first
            new_chunks, chunk_index = _flush_prose(
                prose_buffer, current_heading, current_item, current_title,
                ticker, filing_type, filing_date, chunk_index
            )
            all_chunks.extend(new_chunks)
            prose_buffer = []

            # Isolate table into its own parent
            new_chunks, chunk_index = _flush_table(
                element, current_heading, current_item, current_title, caption,
                ticker, filing_type, filing_date, chunk_index
            )
            all_chunks.extend(new_chunks)
            continue

        marker = section_markers.get(idx)
        is_heading = el_type in HEADING_TYPES

        if is_heading or marker is not None:
            # Flush current prose section before starting new one
            new_chunks, chunk_index = _flush_prose(
                prose_buffer, current_heading, current_item, current_title,
                ticker, filing_type, filing_date, chunk_index
            )
            all_chunks.extend(new_chunks)
            prose_buffer = []

            if is_heading:
                current_heading = element.get("text", "")
            if marker is not None:
                current_item, current_title = marker

            if not is_heading:
                # Marker carries body text on the same element — keep it.
                prose_buffer.append(element)
            continue

        prose_buffer.append(element)
        # Auto-flush when buffer exceeds parent size to prevent truncation
        buffer_tokens = sum(_count(el.get("text", "")) for el in prose_buffer)
        if buffer_tokens >= PARENT_MAX_TOKENS:
            new_chunks, chunk_index = _flush_prose(
                prose_buffer, current_heading, current_item, current_title,
                ticker, filing_type, filing_date, chunk_index
            )
            all_chunks.extend(new_chunks)
            prose_buffer = []

    # Flush any remaining prose
    new_chunks, chunk_index = _flush_prose(
        prose_buffer, current_heading, current_item, current_title,
        ticker, filing_type, filing_date, chunk_index
    )
    all_chunks.extend(new_chunks)

    return all_chunks


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    FIXTURE = [
        # --- Table of contents: dense marker run, must be suppressed ---
        {
            "type": "NarrativeText",
            "text": "Item 1. Business",
            "metadata": {"page_number": 1, "filename": "test.htm"},
        },
        {
            "type": "NarrativeText",
            "text": "Item 1A. Risk Factors",
            "metadata": {"page_number": 1, "filename": "test.htm"},
        },
        {
            "type": "NarrativeText",
            "text": "Item 2. Properties",
            "metadata": {"page_number": 1, "filename": "test.htm"},
        },
        {
            "type": "NarrativeText",
            "text": "Item 3. Legal Proceedings",
            "metadata": {"page_number": 1, "filename": "test.htm"},
        },
        {
            "type": "NarrativeText",
            "text": "Item 7. Management's Discussion and Analysis",
            "metadata": {"page_number": 1, "filename": "test.htm"},
        },
        # --- Front matter: prose before the first surviving marker ---
        {
            "type": "NarrativeText",
            "text": "This annual report on Form 10-K is organized by the items listed above.",
            "metadata": {"page_number": 2, "filename": "test.htm"},
        },
        {
            "type": "NarrativeText",
            "text": "Apple Inc. was incorporated in California and reincorporated in Delaware in 1977.",
            "metadata": {"page_number": 2, "filename": "test.htm"},
        },
        # --- Real body marker, far enough from the TOC run to survive ---
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
        # --- Layout table: below TABLE_MIN_TOKENS, must be dropped ---
        {
            "type": "Table",
            "text": "Page 44",
            "metadata": {"page_number": 44, "filename": "test.htm"},
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
        section = chunk.metadata["section_item"] or "-"
        preview = chunk.child_text[:80].replace("\n", " ")
        print(f"  [{chunk.metadata['chunk_index']}] {kind} | item {section:>2} | {tokens} tokens | {preview}...")

    table_elements = sum(1 for el in FIXTURE if el["type"] in TABLE_TYPES)
    tables_kept = len({c.parent_id for c in chunks if c.metadata["is_table"]})
    print(f"\ntables: {table_elements} elements -> {tables_kept} kept (layout tables dropped)")
