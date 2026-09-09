from backend.ingestion.chunker import (
    PARENT_MAX_TOKENS,
    TABLE_MIN_TOKENS,
    _count,
    _find_section_markers,
    chunk_elements,
)


def _el(el_type: str, text: str, page: int = 1) -> dict:
    return {"type": el_type, "text": text, "metadata": {"page_number": page, "filename": "test.htm"}}


def _prose(text: str, page: int = 1) -> dict:
    return _el("NarrativeText", text, page)


def _table(text: str, page: int = 1) -> dict:
    return _el("Table", text, page)


# ---------------------------------------------------------------------------
# section_item detection
# ---------------------------------------------------------------------------

def test_item_marker_forms_normalize_to_canonical_section():
    elements = [
        _prose("ITEM 1A. RISK FACTORS"),
        _prose("Item 1a. Risk Factors Lowercase"),
        _prose("ITEM 13.CERTAIN RELATIONSHIPS AND RELATED TRANSACTIONS"),
        _prose("ITEM 7.MANAGEMENT'S DISCUSSION AND ANALYSIS. Please read the"),
    ]
    markers = _find_section_markers(elements)

    assert markers[0][0] == "1A"
    assert markers[1][0] == "1A"
    assert markers[2][0] == "13"
    assert markers[3][0] == "7"


def test_marker_with_trailing_body_keeps_body_text():
    marker_text = (
        "ITEM 7.MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION. "
        "Results were strong across all segments this year."
    )
    chunks = chunk_elements([_prose(marker_text)], ticker="AAPL", filing_type="10-K", filing_date="2024-09-28")

    assert len(chunks) == 1
    assert chunks[0].metadata["section_item"] == "7"
    assert "Results were strong across all segments this year." in chunks[0].parent_text


def test_toc_suppression_ignores_dense_marker_run_then_body_sets_section():
    toc = [_prose(f"Item {n}. Heading {n}") for n in range(1, 21)]  # 20 markers, 1 apart
    filler = [
        _prose("This filing is organized according to the index above."),
        _prose("All amounts are presented in millions of U.S. dollars."),
    ]
    body = [_prose("Item 1. The Company designs, manufactures, and markets consumer electronics.")]

    chunks = chunk_elements(toc + filler + body, ticker="AAPL", filing_type="10-K", filing_date="2024-09-28")

    sections = {c.metadata["section_item"] for c in chunks}
    assert sections == {"", "1"}


def test_front_matter_before_first_marker_gets_empty_section_item():
    elements = [
        _prose("Apple Inc. Annual Report on Form 10-K for fiscal year 2024."),
        _prose("Item 1. Business. The Company designs consumer electronics."),
    ]
    chunks = chunk_elements(elements, ticker="AAPL", filing_type="10-K", filing_date="2024-09-28")

    front_matter = [c for c in chunks if "Annual Report" in c.parent_text]
    assert front_matter
    for c in front_matter:
        assert c.metadata["section_item"] == ""
        assert c.metadata["section_item"] is not None
        assert c.metadata["section_item"] != "None"


def test_table_carries_through_enclosing_section_item():
    real_table_text = "\n".join(f"Segment {n} | {100 + n}.0 | {90 + n}.0" for n in range(30))
    elements = [
        _prose("Item 7. Management's Discussion and Analysis of Financial Condition."),
        _prose("Revenue grew due to strong demand across all geographic segments this year."),
        _table(real_table_text),
        _prose("Gross margin expanded due to a favorable shift toward higher-margin revenue."),
    ]
    chunks = chunk_elements(elements, ticker="AAPL", filing_type="10-K", filing_date="2024-09-28")

    table_chunks = [c for c in chunks if c.metadata["is_table"]]
    assert table_chunks
    assert all(c.metadata["section_item"] == "7" for c in table_chunks)


# ---------------------------------------------------------------------------
# parent_id
# ---------------------------------------------------------------------------

def test_parent_id_shared_within_flush_and_differs_across_flushes():
    long_paragraph = "Apple Inc. reported strong results across all segments this quarter. " * 60
    real_table_text = "\n".join(f"Row {n} | {100 + n}.0 | {90 + n}.0" for n in range(30))
    elements = [_prose(long_paragraph), _table(real_table_text)]

    chunks = chunk_elements(elements, ticker="AAPL", filing_type="10-K", filing_date="2024-09-28")

    prose_chunks = [c for c in chunks if not c.metadata["is_table"]]
    table_chunks = [c for c in chunks if c.metadata["is_table"]]

    assert len(prose_chunks) > 1  # long paragraph split into multiple children
    assert len({c.parent_id for c in prose_chunks}) == 1
    assert len({c.parent_id for c in table_chunks}) == 1
    assert prose_chunks[0].parent_id != table_chunks[0].parent_id
    # parent_id in the dataclass field matches what's stored in metadata
    assert prose_chunks[0].parent_id == prose_chunks[0].metadata["parent_id"]


# ---------------------------------------------------------------------------
# Min-size table filter
# ---------------------------------------------------------------------------

def test_min_size_table_filter_drops_layout_tables_keeps_real_ones():
    layout_table = _table("Page 1 of 10")
    real_table_text = " | ".join(str(n) for n in range(400))
    real_table = _table(real_table_text)

    assert _count(layout_table["text"]) < TABLE_MIN_TOKENS
    assert _count(real_table_text) >= 200

    chunks = chunk_elements([layout_table, real_table], ticker="AAPL", filing_type="10-K", filing_date="2024-09-28")

    assert len(chunks) > 0
    assert all(c.metadata["is_table"] for c in chunks)
    assert all(_count(c.parent_text) >= TABLE_MIN_TOKENS for c in chunks)


# ---------------------------------------------------------------------------
# Table captions
# ---------------------------------------------------------------------------

def test_caption_prepended_to_table_but_long_paragraph_is_not():
    caption = "The following table presents segment revenue for the year."
    real_table_text = " | ".join(str(n) for n in range(400))

    with_caption = [_prose(caption), _table(real_table_text)]
    chunks = chunk_elements(with_caption, ticker="AAPL", filing_type="10-K", filing_date="2024-09-28")
    assert any(caption in c.parent_text for c in chunks if c.metadata["is_table"])

    long_paragraph = "This paragraph provides extensive narrative context and analysis. " * 60
    assert _count(long_paragraph) > 50

    with_long_paragraph = [_prose(long_paragraph), _table(real_table_text)]
    chunks2 = chunk_elements(with_long_paragraph, ticker="AAPL", filing_type="10-K", filing_date="2024-09-28")
    assert not any(long_paragraph.strip() in c.parent_text for c in chunks2 if c.metadata["is_table"])


# ---------------------------------------------------------------------------
# No truncation loss
# ---------------------------------------------------------------------------

def test_no_truncation_loss_for_oversized_buffer():
    sentence = "Apple Inc. continues to invest heavily in research and development. "
    marker_sentence = "UNIQUE_MARKER_SENTENCE_XYZ. "
    big_text = sentence * 200 + marker_sentence + sentence * 200
    assert _count(big_text) > PARENT_MAX_TOKENS

    chunks = chunk_elements([_prose(big_text)], ticker="AAPL", filing_type="10-K", filing_date="2024-09-28")

    parent_texts = {c.parent_id: c.parent_text for c in chunks}
    assert len(parent_texts) > 1  # split into multiple parents, not truncated to one

    marker_parents = [t for t in parent_texts.values() if "UNIQUE_MARKER_SENTENCE_XYZ" in t]
    assert len(marker_parents) == 1  # present exactly once — not lost, not duplicated

    for c in chunks:
        assert c.child_text in c.parent_text


# ---------------------------------------------------------------------------
# Existing behavior (no regression)
# ---------------------------------------------------------------------------

def test_existing_prose_overlap_and_number_guard_still_hold():
    text = (
        "Apple Inc. reported total net sales of $391.0 billion for fiscal 2024, "
        "representing a modest increase compared to the prior year. "
        "The growth was primarily driven by strength in the Services segment, "
        "which reached an all-time high revenue of $96.2 billion. "
    ) * 40
    chunks = chunk_elements([_prose(text)], ticker="AAPL", filing_type="10-K", filing_date="2024-09-28")

    children = [c.child_text for c in chunks]
    assert len(children) > 1  # split occurred

    for child in children:
        assert "$391.0" not in child or "$391.0 billion" in child
        assert "$96.2" not in child or "$96.2 billion" in child

    # Overlap: at least one sentence appears in two consecutive children
    sentences = [s.strip() for s in text.split(". ") if s.strip()]
    overlap_found = any(
        any(sentence in children[i] and sentence in children[i + 1] for sentence in sentences)
        for i in range(len(children) - 1)
    )
    assert overlap_found


def test_part_iii_cross_reference_run_is_not_mistaken_for_toc():
    # Items 10-14 are often one-line pointers to the proxy statement, so they
    # land <3 elements apart in the body — a dense run that is NOT a TOC.
    elements = []
    for n in range(10, 15):
        elements.append(_prose(f"ITEM {n}. HEADING {n}"))
        elements.append(_prose("Incorporated by reference to the Proxy Statement."))
    markers = _find_section_markers(elements)

    assert [markers[i][0] for i in sorted(markers)] == ["10", "11", "12", "13", "14"]


def test_toc_run_starting_at_item_1_is_still_suppressed():
    toc = [_prose(f"Item {n}. Heading {n}") for n in range(1, 21)]
    assert _find_section_markers(toc) == {}
