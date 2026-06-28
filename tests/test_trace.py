from __future__ import annotations

from fastapi.testclient import TestClient

from ai.runtime import run_chat
from app.main import app
from observability.tracer import get_trace_session


def test_run_chat_returns_trace_id() -> None:
    result = run_chat("OEMとは？")

    assert result["success"] is True
    assert result["trace_id"]


def test_trace_endpoint_returns_session() -> None:
    client = TestClient(app)

    result = run_chat("OEMとは？")
    response = client.get(f"/trace/{result['trace_id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trace_id"] == result["trace_id"]
    assert payload["records"]
    assert payload["records"][0]["layer"] == "Validation"


def test_trace_records_core_layers() -> None:
    result = run_chat("OEMとは？")
    trace = get_trace_session(result["trace_id"])

    assert trace is not None
    layers = [record["layer"] for record in trace["records"]]
    assert "Runtime" in layers
    assert "Context" in layers
    assert "Intent" in layers
    assert "Planner" in layers
    assert "Workflow" in layers
    assert "Answer" in layers