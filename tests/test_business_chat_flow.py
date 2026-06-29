from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import ai.runtime as runtime
from app import main
from app.main import app
from observability.tracer import get_trace_session
from storage.sqlite import SQLiteRepository


class _StubGateway:
    def generate_answer(self, **_: object) -> str:
        return "stubbed business answer"


def _prepare_sample_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "sqlite" / "logsys.db"
    repository = SQLiteRepository(db_path)
    repository.execute_query(
        "CREATE TABLE sales_data (id INTEGER PRIMARY KEY, customer_name TEXT, product_name TEXT, sales_amount REAL)"
    )
    repository.execute_query(
        "INSERT INTO sales_data (customer_name, product_name, sales_amount) VALUES (?, ?, ?)",
        ("Acme", "Item-A", 1200.0),
    )
    repository.execute_query(
        "INSERT INTO sales_data (customer_name, product_name, sales_amount) VALUES (?, ?, ?)",
        ("Bravo", "Item-B", 950.0),
    )
    repository.close()
    return db_path


def test_table_question_selects_business_tool() -> None:
    result = runtime.run_chat("どんなテーブルがありますか？")
    tools = [step.get("name") for step in result.get("workflow", {}).get("steps", [])]
    assert "business.execute_tool" in tools
    business_steps = [step for step in result.get("workflow", {}).get("steps", []) if step.get("name") == "business.execute_tool"]
    assert business_steps
    assert business_steps[0].get("input", {}).get("tool_name") == "business.database_summary"


def test_top_sales_question_calls_business_query(tmp_path: Path, monkeypatch) -> None:
    db_path = _prepare_sample_db(tmp_path)
    main.DEFAULT_DB_PATH = db_path
    monkeypatch.setattr(runtime.LLMGateway, "from_env", classmethod(lambda cls: _StubGateway()))

    result = runtime.run_chat("売上トップ10")
    assert result["success"] is True
    assert any(item.get("type") == "business" for item in result.get("results", []))


def test_chat_endpoint_returns_business_query_answer(tmp_path: Path, monkeypatch) -> None:
    db_path = _prepare_sample_db(tmp_path)
    main.DEFAULT_DB_PATH = db_path
    monkeypatch.setattr(runtime.LLMGateway, "from_env", classmethod(lambda cls: _StubGateway()))

    client = TestClient(app)
    response = client.post("/chat", json={"message": "売上トップ10"})
    assert response.status_code == 200
    payload = response.json()
    assert "answer" in payload
    assert payload["success"] is True


def test_trace_contains_business_execution(tmp_path: Path, monkeypatch) -> None:
    db_path = _prepare_sample_db(tmp_path)
    main.DEFAULT_DB_PATH = db_path
    monkeypatch.setattr(runtime.LLMGateway, "from_env", classmethod(lambda cls: _StubGateway()))

    result = runtime.run_chat("売上トップ10")
    trace = get_trace_session(result["trace_id"])

    assert trace is not None
    layers = [record["layer"] for record in trace["records"]]
    assert "Business" in layers
