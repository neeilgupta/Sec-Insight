"""
SEC EDGAR fetcher — resolves a ticker to a CIK and returns the URL of the
primary document for the most recent 10-K or 10-Q filing.
"""

from typing import Literal

import httpx

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVES_URL = (
    "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}"
)

FormType = Literal["10-K", "10-Q"]


async def get_filing_url(
    ticker: str,
    form_type: FormType,
    user_agent: str,
) -> str:
    """Return the URL of the primary document for the most recent filing.

    Args:
        ticker: Stock ticker symbol, e.g. "AAPL".
        form_type: SEC form type — "10-K" (annual) or "10-Q" (quarterly).
        user_agent: Value for the SEC-required User-Agent header,
                    e.g. "Jane Doe jane@example.com".

    Returns:
        Absolute URL to the primary .htm document on SEC EDGAR.

    Raises:
        ValueError: If the ticker is not found or no matching filings exist.
        httpx.HTTPStatusError: On non-2xx responses from the SEC API.
    """
    headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}

    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30.0) as client:
        cik = await _get_cik(ticker.upper(), client)
        cik_padded = str(cik).zfill(10)

        submissions_url = SEC_SUBMISSIONS_URL.format(cik=cik_padded)
        resp = await client.get(submissions_url)
        resp.raise_for_status()
        data = resp.json()

        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        for form, accession, doc in zip(forms, accessions, primary_docs):
            if form == form_type:
                accession_clean = accession.replace("-", "")
                return SEC_ARCHIVES_URL.format(
                    cik=cik_padded,
                    accession=accession_clean,
                    doc=doc,
                )

        raise ValueError(
            f"No {form_type} filings found for '{ticker}' in EDGAR submissions."
        )


async def get_filing_info(
    ticker: str,
    form_type: FormType,
    user_agent: str,
) -> tuple[str, str]:
    """Return (url, filing_date) for the most recent filing of form_type.

    Like get_filing_url() but also returns the ISO filing date
    (e.g. "2024-09-28") required by chunk_elements() and index_chunks().

    Args:
        ticker: Stock ticker symbol, e.g. "AAPL".
        form_type: SEC form type — "10-K" or "10-Q".
        user_agent: Value for the SEC-required User-Agent header.

    Returns:
        Tuple of (absolute_url, filing_date) where filing_date is ISO "YYYY-MM-DD".

    Raises:
        ValueError: If the ticker is not found or no matching filings exist.
        httpx.HTTPStatusError: On non-2xx responses from the SEC API.
    """
    headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}

    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30.0) as client:
        cik = await _get_cik(ticker.upper(), client)
        cik_padded = str(cik).zfill(10)

        submissions_url = SEC_SUBMISSIONS_URL.format(cik=cik_padded)
        resp = await client.get(submissions_url)
        resp.raise_for_status()
        data = resp.json()

        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        filing_dates = recent.get("filingDate", [])

        for form, accession, doc, date in zip(forms, accessions, primary_docs, filing_dates):
            if form == form_type:
                accession_clean = accession.replace("-", "")
                url = SEC_ARCHIVES_URL.format(
                    cik=cik_padded,
                    accession=accession_clean,
                    doc=doc,
                )
                return url, date

        raise ValueError(
            f"No {form_type} filings found for '{ticker}' in EDGAR submissions."
        )


async def _get_cik(ticker: str, client: httpx.AsyncClient) -> int:
    """Resolve a ticker symbol to its SEC CIK number.

    Args:
        ticker: Uppercase ticker symbol.
        client: Shared httpx async client.

    Returns:
        Integer CIK.

    Raises:
        ValueError: If the ticker is not present in the SEC tickers map.
        httpx.HTTPStatusError: On non-2xx response.
    """
    resp = await client.get(SEC_TICKERS_URL)
    resp.raise_for_status()
    tickers_data = resp.json()

    # tickers_data is { "0": {"cik_str": 320193, "ticker": "AAPL", ...}, ... }
    ticker_to_cik: dict[str, int] = {
        entry["ticker"].upper(): entry["cik_str"]
        for entry in tickers_data.values()
    }

    if ticker not in ticker_to_cik:
        raise ValueError(
            f"Ticker '{ticker}' not found in SEC EDGAR. "
            "Check the symbol is correct and listed on a US exchange."
        )

    return ticker_to_cik[ticker]
