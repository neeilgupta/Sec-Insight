from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.api.query import app

client = TestClient(app)


def _make_col(name: str) -> MagicMock:
    col = MagicMock()
    col.name = name
    return col


def test_collections_returns_sorted_list():
    cols = [_make_col("MSFT_10-K_2025-01-29"), _make_col("AAPL_10-K_2024-09-28")]
    with patch("backend.api.query.chromadb.PersistentClient") as mock_cls:
        mock_cls.return_value.list_collections.return_value = cols
        resp = client.get("/collections")

    assert resp.status_code == 200
    assert resp.json() == {
        "collections": ["AAPL_10-K_2024-09-28", "MSFT_10-K_2025-01-29"]
    }


def test_collections_returns_empty_list():
    with patch("backend.api.query.chromadb.PersistentClient") as mock_cls:
        mock_cls.return_value.list_collections.return_value = []
        resp = client.get("/collections")

    assert resp.status_code == 200
    assert resp.json() == {"collections": []}
