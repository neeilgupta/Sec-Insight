from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from backend.api.query import app
from backend.api.structured import KeyFigure, _LLMExtraction

client = TestClient(app)

_FAKE_RANKED = [
    {
        "chunk_id": "c1",
        "text": "Apple's total net sales were $391.0 billion in fiscal 2024.",
        "metadata": {"heading": "Consolidated Statements of Operations"},
        "rerank_score": 0.95,
    }
]

_FAKE_EXTRACTION = _LLMExtraction(
    answer="Apple's total net sales were $391.0 billion in fiscal year 2024.",
    key_figures=[
        KeyFigure(
            label="Total Net Sales",
            value="$391.0 billion",
            section="Consolidated Statements of Operations",
        )
    ],
    confidence=1.0,
)


def test_structured_query_returns_json():
    with (
        patch("backend.api.structured.hybrid_search", return_value=_FAKE_RANKED),
        patch("backend.api.structured.rerank", return_value=_FAKE_RANKED),
        patch("backend.api.structured._openai") as mock_client,
    ):
        mock_client.chat.completions.create = AsyncMock(return_value=_FAKE_EXTRACTION)
        resp = client.post("/structured_query", json={
            "query": "What was Apple's total net sales in fiscal 2024?",
            "collection_name": "AAPL_10-K_2024-09-28",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "key_figures" in data
    assert isinstance(data["key_figures"], list)
    assert data["ticker"] == "AAPL"
    assert data["filing_type"] == "10-K"
    assert data["year"] == "2024"


def test_structured_query_key_figures_have_required_fields():
    with (
        patch("backend.api.structured.hybrid_search", return_value=_FAKE_RANKED),
        patch("backend.api.structured.rerank", return_value=_FAKE_RANKED),
        patch("backend.api.structured._openai") as mock_client,
    ):
        mock_client.chat.completions.create = AsyncMock(return_value=_FAKE_EXTRACTION)
        resp = client.post("/structured_query", json={
            "query": "What was Apple's revenue breakdown by segment?",
            "collection_name": "AAPL_10-K_2024-09-28",
        })

    assert resp.status_code == 200
    figures = resp.json()["key_figures"]
    assert len(figures) > 0
    assert "label" in figures[0]
    assert "value" in figures[0]
    assert "section" in figures[0]


def test_structured_query_populates_metadata_from_collection_name():
    with (
        patch("backend.api.structured.hybrid_search", return_value=_FAKE_RANKED),
        patch("backend.api.structured.rerank", return_value=_FAKE_RANKED),
        patch("backend.api.structured._openai") as mock_client,
    ):
        mock_client.chat.completions.create = AsyncMock(return_value=_FAKE_EXTRACTION)
        resp = client.post("/structured_query", json={
            "query": "Revenue?",
            "collection_name": "MSFT_10-K_2024-06-30",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "MSFT"
    assert data["filing_type"] == "10-K"
    assert data["year"] == "2024"
    assert data["question"] == "Revenue?"
