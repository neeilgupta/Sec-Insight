"""
SEC EDGAR fetcher — resolves a ticker to a CIK and returns filing metadata
for a 10-K or 10-Q filing at a given recency index (0 = most recent).
"""

from dataclasses import dataclass
from typing import Literal

import httpx

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_SUBMISSIONS_SHARD_URL = "https://data.sec.gov/submissions/{name}"
SEC_ARCHIVES_URL = (
    "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}"
)

FormType = Literal["10-K", "10-Q"]


@dataclass(frozen=True)
class FilingRef:
    url: str           # absolute archive URL of the primary document
    filing_date: str   # ISO, when it was filed with the SEC   ("2024-11-01")
    report_date: str   # ISO, fiscal period end                ("2024-09-28"); "" if absent
    accession: str     # "0000320193-24-000123", hyphens intact
    form_type: str
    index: int         # position this came from, echoed back for logging


def _matches_from_block(block: dict, form_type: str) -> list[tuple[str, str, str, str]]:
    """Return (accession, primary_doc, filing_date, report_date) for each matching form,
    preserving the block's newest-first order."""
    forms = block.get("form", [])
    accessions = block.get("accessionNumber", [])
    primary_docs = block.get("primaryDocument", [])
    filing_dates = block.get("filingDate", [])
    report_dates = block.get("reportDate", [])

    matches = []
    for i, form in enumerate(forms):
        if form != form_type:
            continue
        report_date = report_dates[i] if i < len(report_dates) else ""
        matches.append((
            accessions[i],
            primary_docs[i],
            filing_dates[i],
            report_date or "",
        ))
    return matches


async def get_filing_info(
    ticker: str,
    form_type: FormType,
    user_agent: str,
    index: int = 0,
) -> FilingRef:
    """Return filing metadata for form_type at the given recency index.

    Args:
        ticker: Stock ticker symbol, e.g. "AAPL".
        form_type: SEC form type — "10-K" or "10-Q".
        user_agent: Value for the SEC-required User-Agent header.
        index: 0 = most recent, 1 = next most recent, etc.

    Returns:
        A FilingRef for the requested filing.

    Raises:
        ValueError: If index is negative, the ticker is not found, or fewer
            than index + 1 matching filings exist across all submission shards.
        httpx.HTTPStatusError: On non-2xx responses from the SEC API.
    """
    if index < 0:
        raise ValueError(f"index must be >= 0 (0 = most recent), got {index}.")

    headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}

    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30.0) as client:
        cik = await _get_cik(ticker.upper(), client)
        cik_padded = str(cik).zfill(10)

        submissions_url = SEC_SUBMISSIONS_URL.format(cik=cik_padded)
        resp = await client.get(submissions_url)
        resp.raise_for_status()
        data = resp.json()

        recent = data.get("filings", {}).get("recent", {})
        matches = _matches_from_block(recent, form_type)

        if len(matches) <= index:
            shards = sorted(
                data.get("filings", {}).get("files", []),
                key=lambda s: s["filingTo"],
                reverse=True,
            )
            for shard in shards:
                if len(matches) > index:
                    break
                shard_url = SEC_SUBMISSIONS_SHARD_URL.format(name=shard["name"])
                shard_resp = await client.get(shard_url)
                shard_resp.raise_for_status()
                matches.extend(_matches_from_block(shard_resp.json(), form_type))

        if len(matches) <= index:
            valid = f"valid: 0-{len(matches) - 1}" if matches else "none available"
            raise ValueError(
                f"Only {len(matches)} {form_type} filings found for '{ticker}' "
                f"across all submission shards; index {index} is out of range "
                f"({valid})."
            )

        accession, doc, filing_date, report_date = matches[index]
        accession_clean = accession.replace("-", "")
        url = SEC_ARCHIVES_URL.format(cik=cik_padded, accession=accession_clean, doc=doc)
        return FilingRef(
            url=url,
            filing_date=filing_date,
            report_date=report_date,
            accession=accession,
            form_type=form_type,
            index=index,
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
