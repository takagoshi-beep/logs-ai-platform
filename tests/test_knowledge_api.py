from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_knowledge_index_endpoint_returns_categories() -> None:
    client = TestClient(app)

    response = client.get("/knowledge")

    assert response.status_code == 200
    payload = response.json()
    assert "glossary" in payload
    assert "companies" in payload
    assert "brands" in payload


def test_knowledge_category_endpoint_returns_requested_category() -> None:
    client = TestClient(app)

    response = client.get("/knowledge/glossary")

    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert payload[0]["category"] == "glossary"


def test_knowledge_search_endpoint_returns_matching_terms() -> None:
    client = TestClient(app)

    response = client.get("/knowledge/search", params={"q": "OEM"})

    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert any(item["term"] == "OEM" for item in payload)
