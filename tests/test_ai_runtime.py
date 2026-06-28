from __future__ import annotations

from fastapi.testclient import TestClient

import ai.runtime as runtime
from app.main import app


class _StubGateway:
    def __init__(self) -> None:
        self.called = False

    def generate_answer(self, **_: object) -> str:
        self.called = True
        return "gateway response"


def test_run_chat_succeeds() -> None:
    result = runtime.run_chat("OEMとは？")

    assert result["success"] is True
    assert result["plan"]
    assert result["workflow"]
    assert isinstance(result["results"], list)


def test_ai_chat_returns_200() -> None:
    client = TestClient(app)
    response = client.post("/ai/chat", json={"message": "OEMとは？"})

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_run_chat_returns_log_id() -> None:
    result = runtime.run_chat("OEMとは？")

    assert result["log_id"]


def test_run_chat_returns_answer() -> None:
    result = runtime.run_chat("OEMとは？")

    assert result["answer"]


def test_run_chat_uses_gateway(monkeypatch) -> None:
    stub_gateway = _StubGateway()
    monkeypatch.setattr(runtime.LLMGateway, "from_env", classmethod(lambda cls: stub_gateway))

    result = runtime.run_chat("OEMとは？")

    assert stub_gateway.called is True
    assert result["answer"] == "gateway response"


def test_run_chat_failure_returns_success_false(monkeypatch) -> None:
    def raise_error(_message: str, _context: dict | None = None) -> dict:
        raise RuntimeError("planner failure")

    monkeypatch.setattr(runtime, "create_plan", raise_error)

    result = runtime.run_chat("OEMとは？")

    assert result["success"] is False
    assert result["stage"] == "planner"
    assert "planner failure" in result["error"]
