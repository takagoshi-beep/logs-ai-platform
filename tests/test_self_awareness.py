from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from self_awareness.capabilities import get_capabilities, get_limitations, get_next_recommendations
from self_awareness.status import get_ai_status


def test_capabilities_can_be_fetched() -> None:
    result = get_capabilities()

    assert result["business"]
    assert result["knowledge"]
    assert result["system"]


def test_limitations_can_be_fetched() -> None:
    result = get_limitations()

    assert result


def test_recommendations_can_be_fetched() -> None:
    result = get_next_recommendations()

    assert result


def test_status_can_be_fetched() -> None:
    result = get_ai_status()

    assert result["test_count"] >= 0
    assert result["layers"]


def test_answer_can_refer_to_self_awareness_for_capabilities() -> None:
    client = TestClient(app)
    response = client.post("/answer", json={"message": "何ができますか？"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"]
