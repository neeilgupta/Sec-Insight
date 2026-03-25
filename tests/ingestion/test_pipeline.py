import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.ingestion.pipeline import ingest, _to_dicts


# ---------------------------------------------------------------------------
# _to_dicts tests
# ---------------------------------------------------------------------------

def _make_element(type_name: str, text: str, page: int = 1, filename: str = "test.htm"):
    el = MagicMock()
    el.text = text
    el.metadata.page_number = page
    el.metadata.filename = filename
    type(el).__name__ = type_name
    return el


def test_to_dicts_converts_elements():
    elements = [
        _make_element("Title", "Item 7. Net Sales", page=30),
        _make_element("NarrativeText", "Revenue was $391B.", page=30),
        _make_element("Table", "Col1 | Col2\nA | B", page=31),
    ]
    result = _to_dicts(elements)

    assert len(result) == 3
    assert result[0] == {
        "type": "Title",
        "text": "Item 7. Net Sales",
        "metadata": {"page_number": 30, "filename": "test.htm"},
    }
    assert result[2]["type"] == "Table"
    assert result[2]["metadata"]["page_number"] == 31


def test_to_dicts_handles_missing_metadata():
    el = MagicMock(spec=[])  # spec=[] means no attributes allowed by default
    el.text = "Some text"
    # metadata is a separate mock with no page_number or filename
    el.metadata = MagicMock(spec=[])
    type(el).__name__ = "NarrativeText"

    result = _to_dicts([el])
    assert result[0]["metadata"]["page_number"] is None
    assert result[0]["metadata"]["filename"] is None


# ---------------------------------------------------------------------------
# ingest() tests (all stages mocked)
# ---------------------------------------------------------------------------

MOCK_URL = "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm"
MOCK_DATE = "2024-09-28"


@pytest.mark.asyncio
async def test_ingest_returns_collection_name():
    mock_element = _make_element("NarrativeText", "Apple revenue $391B")
    mock_chunks = [MagicMock()]

    with patch("backend.ingestion.pipeline.get_filing_info", new_callable=AsyncMock) as mock_fetch, \
         patch("backend.ingestion.pipeline.parse_filing", new_callable=AsyncMock) as mock_parse, \
         patch("backend.ingestion.pipeline.chunk_elements") as mock_chunk, \
         patch("backend.ingestion.pipeline.index_chunks") as mock_index:

        mock_fetch.return_value = (MOCK_URL, MOCK_DATE)
        mock_parse.return_value = [mock_element]
        mock_chunk.return_value = mock_chunks
        mock_index.return_value = "AAPL_10-K_2024-09-28"

        result = await ingest("AAPL", "10-K")

    assert result == "AAPL_10-K_2024-09-28"


@pytest.mark.asyncio
async def test_ingest_passes_correct_args_between_stages():
    mock_element = _make_element("NarrativeText", "Apple revenue $391B")
    mock_chunks = [MagicMock()]

    with patch("backend.ingestion.pipeline.get_filing_info", new_callable=AsyncMock) as mock_fetch, \
         patch("backend.ingestion.pipeline.parse_filing", new_callable=AsyncMock) as mock_parse, \
         patch("backend.ingestion.pipeline.chunk_elements") as mock_chunk, \
         patch("backend.ingestion.pipeline.index_chunks") as mock_index:

        mock_fetch.return_value = (MOCK_URL, MOCK_DATE)
        mock_parse.return_value = [mock_element]
        mock_chunk.return_value = mock_chunks
        mock_index.return_value = "AAPL_10-K_2024-09-28"

        await ingest("AAPL", "10-K")

    assert mock_parse.call_args[0][0] == MOCK_URL

    _, chunk_kwargs = mock_chunk.call_args
    assert chunk_kwargs["ticker"] == "AAPL"
    assert chunk_kwargs["filing_type"] == "10-K"
    assert chunk_kwargs["filing_date"] == MOCK_DATE

    assert mock_index.call_args[0][0] == mock_chunks
    assert mock_index.call_args[0][1] == "AAPL"
    assert mock_index.call_args[0][3] == MOCK_DATE


@pytest.mark.asyncio
async def test_ingest_propagates_fetch_error():
    with patch("backend.ingestion.pipeline.get_filing_info", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = ValueError("No 10-K filings found for 'FAKE'")
        with pytest.raises(ValueError, match="FAKE"):
            await ingest("FAKE", "10-K")
