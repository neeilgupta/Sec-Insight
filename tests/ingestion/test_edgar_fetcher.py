import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.ingestion.edgar_fetcher import get_filing_info


TICKERS_JSON = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
}

# Three 10-Ks interleaved with 10-Qs, newest first.
SUBMISSIONS_JSON = {
    "filings": {
        "recent": {
            "form":            ["10-K",              "10-Q",              "10-K",              "10-Q",              "10-K"],
            "accessionNumber": ["0000320193-24-000123", "0000320193-24-000100", "0000320193-23-000150", "0000320193-23-000090", "0000320193-22-000110"],
            "primaryDocument": ["aapl-20241101.htm",  "aapl-20240802.htm", "aapl-20231103.htm", "aapl-20230803.htm", "aapl-20221028.htm"],
            "filingDate":      ["2024-11-01",         "2024-08-02",        "2023-11-03",        "2023-08-03",        "2022-10-28"],
            "reportDate":      ["2024-09-28",         "2024-06-29",        "2023-09-30",        "2023-07-01",        "2022-09-24"],
        },
        "files": [],
    }
}


def _make_mock_client(json_bodies):
    def make_resp(json_data):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=json_data)
        return resp

    client = AsyncMock()
    client.get = AsyncMock(side_effect=[make_resp(j) for j in json_bodies])
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.mark.asyncio
async def test_get_filing_info_index_0_returns_newest():
    mock_client = _make_mock_client([TICKERS_JSON, SUBMISSIONS_JSON])
    with patch("backend.ingestion.edgar_fetcher.httpx.AsyncClient", return_value=mock_client):
        filing = await get_filing_info("AAPL", "10-K", "Test test@example.com")

    assert "0000320193" in filing.url
    assert "aapl-20241101.htm" in filing.url
    assert filing.filing_date == "2024-11-01"


@pytest.mark.asyncio
async def test_get_filing_info_index_1_and_2_skip_interleaved_10q():
    mock_client = _make_mock_client([TICKERS_JSON, SUBMISSIONS_JSON])
    with patch("backend.ingestion.edgar_fetcher.httpx.AsyncClient", return_value=mock_client):
        filing1 = await get_filing_info("AAPL", "10-K", "Test test@example.com", index=1)

    mock_client2 = _make_mock_client([TICKERS_JSON, SUBMISSIONS_JSON])
    with patch("backend.ingestion.edgar_fetcher.httpx.AsyncClient", return_value=mock_client2):
        filing2 = await get_filing_info("AAPL", "10-K", "Test test@example.com", index=2)

    assert filing1.filing_date == "2023-11-03"
    assert filing2.filing_date == "2022-10-28"


@pytest.mark.asyncio
async def test_get_filing_info_filing_ref_fields_populated():
    mock_client = _make_mock_client([TICKERS_JSON, SUBMISSIONS_JSON])
    with patch("backend.ingestion.edgar_fetcher.httpx.AsyncClient", return_value=mock_client):
        filing = await get_filing_info("AAPL", "10-K", "Test test@example.com", index=1)

    assert filing.report_date == "2023-09-30"
    assert filing.accession == "0000320193-23-000150"
    assert filing.index == 1
    assert filing.form_type == "10-K"


@pytest.mark.asyncio
async def test_get_filing_info_raises_out_of_range():
    mock_client = _make_mock_client([TICKERS_JSON, SUBMISSIONS_JSON])
    with patch("backend.ingestion.edgar_fetcher.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ValueError, match="valid: 0-2"):
            await get_filing_info("AAPL", "10-K", "Test test@example.com", index=3)


@pytest.mark.asyncio
async def test_get_filing_info_negative_index_raises_without_network_call():
    mock_client = _make_mock_client([TICKERS_JSON, SUBMISSIONS_JSON])
    with patch("backend.ingestion.edgar_fetcher.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ValueError, match="index must be >= 0"):
            await get_filing_info("AAPL", "10-K", "Test test@example.com", index=-1)

    mock_client.get.assert_not_called()


@pytest.mark.asyncio
async def test_get_filing_info_falls_through_to_shard_when_recent_exhausted():
    recent_no_10k = {
        "filings": {
            "recent": {
                "form": ["10-Q"],
                "accessionNumber": ["0000320193-24-000456"],
                "primaryDocument": ["aapl-20240629.htm"],
                "filingDate": ["2024-08-02"],
                "reportDate": ["2024-06-29"],
            },
            "files": [
                {"name": "CIK0000320193-submissions-001.json", "filingCount": 500,
                 "filingFrom": "2010-01-01", "filingTo": "2015-01-01"},
            ],
        }
    }
    shard_json = {
        "form": ["10-K"],
        "accessionNumber": ["0000320193-12-000001"],
        "primaryDocument": ["aapl-20120101.htm"],
        "filingDate": ["2012-01-03"],
        "reportDate": ["2011-09-30"],
    }
    mock_client = _make_mock_client([TICKERS_JSON, recent_no_10k, shard_json])
    with patch("backend.ingestion.edgar_fetcher.httpx.AsyncClient", return_value=mock_client):
        filing = await get_filing_info("AAPL", "10-K", "Test test@example.com", index=0)

    assert filing.filing_date == "2012-01-03"
    assert filing.report_date == "2011-09-30"


@pytest.mark.asyncio
async def test_get_filing_info_shards_fetched_by_filing_to_descending():
    recent_no_10k = {
        "filings": {
            "recent": {
                "form": ["10-Q"],
                "accessionNumber": ["0000320193-21-000900"],
                "primaryDocument": ["x.htm"],
                "filingDate": ["2021-01-01"],
                "reportDate": ["2020-09-30"],
            },
            # Deliberately listed oldest-first, to prove the code sorts by
            # filingTo rather than trusting array order.
            "files": [
                {"name": "shard-001.json", "filingFrom": "1994-01-01", "filingTo": "2010-01-01"},
                {"name": "shard-002.json", "filingFrom": "2010-01-02", "filingTo": "2020-01-01"},
            ],
        }
    }
    shard_002_json = {
        "form": ["10-K"],
        "accessionNumber": ["0000320193-15-000001"],
        "primaryDocument": ["aapl-20150101.htm"],
        "filingDate": ["2015-01-05"],
        "reportDate": ["2014-09-30"],
    }
    # Only one shard response provided — if the code fetched shard-001
    # first (wrong order) it would find no match there and try a second
    # shard fetch, which would raise StopIteration since side_effect is
    # exhausted.
    mock_client = _make_mock_client([TICKERS_JSON, recent_no_10k, shard_002_json])
    with patch("backend.ingestion.edgar_fetcher.httpx.AsyncClient", return_value=mock_client):
        filing = await get_filing_info("AAPL", "10-K", "Test test@example.com", index=0)

    assert filing.filing_date == "2015-01-05"
    third_call_url = mock_client.get.call_args_list[2].args[0]
    assert "shard-002.json" in third_call_url


@pytest.mark.asyncio
async def test_get_filing_info_exhausted_after_shards_raises():
    recent_no_10k = {
        "filings": {
            "recent": {
                "form": ["10-Q"],
                "accessionNumber": ["0000320193-21-000900"],
                "primaryDocument": ["x.htm"],
                "filingDate": ["2021-01-01"],
                "reportDate": ["2020-09-30"],
            },
            "files": [
                {"name": "shard-001.json", "filingFrom": "1994-01-01", "filingTo": "2010-01-01"},
            ],
        }
    }
    shard_no_10k = {
        "form": ["10-Q"],
        "accessionNumber": ["0000320193-05-000001"],
        "primaryDocument": ["aapl-20050101.htm"],
        "filingDate": ["2005-01-03"],
        "reportDate": ["2004-09-30"],
    }
    mock_client = _make_mock_client([TICKERS_JSON, recent_no_10k, shard_no_10k])
    with patch("backend.ingestion.edgar_fetcher.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ValueError, match="Only 0 10-K filings found"):
            await get_filing_info("AAPL", "10-K", "Test test@example.com", index=0)


@pytest.mark.asyncio
async def test_get_filing_info_raises_for_unknown_ticker():
    mock_client = _make_mock_client([TICKERS_JSON, SUBMISSIONS_JSON])
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
                "reportDate": ["2024-06-29"],
            }
        }
    }
    mock_client = _make_mock_client([TICKERS_JSON, no_10k])
    with patch("backend.ingestion.edgar_fetcher.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ValueError, match="10-K"):
            await get_filing_info("AAPL", "10-K", "Test test@example.com")
