from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from intent.classifier import classify_intent
from intent.registry import get_intent_types


def test_intent_explain_for_oem_question() -> None:
    result = classify_intent("OEMとは？")

    assert result.intent_type == "explain"
    assert result.requires_memory is False


def test_intent_ranking_for_sales_question() -> None:
    result = classify_intent("売上ランキング")

    assert result.intent_type == "ranking"
    assert result.requires_business_logic is True


def test_intent_continue_requires_memory() -> None:
    result = classify_intent("前回の続き")

    assert result.intent_type == "continue"
    assert result.requires_memory is True


def test_intent_search_for_product_question() -> None:
    result = classify_intent("商品を探して")

    assert result.intent_type == "search"


def test_intent_status_for_capability_question() -> None:
    result = classify_intent("何ができますか？")

    assert result.intent_type == "status"


def test_intent_unknown_for_unmatched_question() -> None:
    result = classify_intent("これは何ですか")

    assert result.intent_type == "unknown"


def test_intent_api_returns_result() -> None:
    client = TestClient(app)
    response = client.post("/intent/classify", json={"message": "OEMとは？", "user_id": "takagoshi"})

    assert response.status_code == 200
    assert response.json()["intent_type"] == "explain"


def test_intent_types_api_returns_known_types() -> None:
    client = TestClient(app)
    response = client.get("/intent/types")

    assert response.status_code == 200
    payload = response.json()
    assert any(item["name"] == "explain" for item in payload["types"])
    assert any(item["name"] == "unknown" for item in get_intent_types())
