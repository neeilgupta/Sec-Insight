import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.ingestion.edgar_fetcher import get_filing_info


TICKERS_JSON = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
}

SUBMISSIONS_JSON = {
    "filings": {
        "recent": {
            "form": ["10-K", "10-Q"],
            "accessionNumber": ["0000320193-24-000123", "0000320193-24-000456"],
            "primaryDocument": ["aapl-20240928.htm", "aapl-20240629.htm"],
            "filingDate": ["2024-11-01", "2024-08-02"],
        }
    }
}


def _make_mock_client(tickers_json, submissions_json):
    def make_resp(json_data):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=json_data)
        return resp

    client = AsyncMock()
    client.get = AsyncMock(
        side_effect=[make_resp(tickers_json), make_resp(submissions_json)]
    )
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.mark.asyncio
async def test_get_filing_info_returns_url_and_date():
    mock_client = _make_mock_client(TICKERS_JSON, SUBMISSIONS_JSON)
    with patch("backend.ingestion.edgar_fetcher.httpx.AsyncClient", return_value=mock_client):
        url, date = await get_filing_info("AAPL", "10-K", "Test test@example.com")

    assert "0000320193" in url
    assert "aapl-20240928.htm" in url
    assert date == "2024-11-01"


@pytest.mark.asyncio
async def test_get_filing_info_picks_first_matching_form():
    mock_client = _make_mock_client(TICKERS_JSON, SUBMISSIONS_JSON)
    with patch("backend.ingestion.edgar_fetcher.httpx.AsyncClient", return_value=mock_client):
        url, date = await get_filing_info("AAPL", "10-Q", "Test test@example.com")

    assert "aapl-20240629.htm" in url
    assert date == "2024-08-02"


@pytest.mark.asyncio
async def test_get_filing_info_raises_for_unknown_ticker():
    mock_client = _make_mock_client(TICKERS_JSON, SUBMISSIONS_JSON)
    with patch("backend.ingestion.edgar_fetcher.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ValueError, match="TSLA"):
            await get_filing_info("TSLA", "10-K", "Test test@example.com")


@pytest.mark.asyncio
async def test_get_filing_info_raises_when_no_matching_form():
    no_10k = {
        "filings": {
            "recent": {
                "form": ["10-Q"],
                "accessionNumber": ["0000320193-24-000456"],
                "primaryDocument": ["aapl-20240629.htm"],
                "filingDate": ["2024-08-02"],
            }
        }
    }
    mock_client = _make_mock_client(TICKERS_JSON, no_10k)
    with patch("backend.ingestion.edgar_fetcher.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ValueError, match="10-K"):
            await get_filing_info("AAPL", "10-K", "Test test@example.com")
