from __future__ import annotations

from pathlib import Path

import ai.runtime as runtime
from app import main
from observability.tracer import get_trace_session
from storage.sqlite import SQLiteRepository


def _prepare_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "sqlite" / "logsys.db"
    repository = SQLiteRepository(db_path)
    repository.execute_query("CREATE TABLE sales (id INTEGER PRIMARY KEY, customer TEXT, amount REAL)")
    repository.execute_query("INSERT INTO sales (customer, amount) VALUES (?, ?)", ("Acme", 100.0))
    repository.close()
    return db_path


def test_chat_top_sales_uses_business_tool_selection(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    main.DEFAULT_DB_PATH = db_path

    result = runtime.run_chat("売上トップ10")
    business_steps = [item for item in result.get("workflow", {}).get("steps", []) if item.get("name") == "business.execute_tool"]
    assert business_steps
    assert business_steps[0].get("input", {}).get("tool_name") == "business.sales_top"


def test_chat_table_list_uses_database_summary_tool(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    main.DEFAULT_DB_PATH = db_path

    result = runtime.run_chat("どんなテーブルがありますか？")
    business_steps = [item for item in result.get("workflow", {}).get("steps", []) if item.get("name") == "business.execute_tool"]
    assert business_steps
    assert business_steps[0].get("input", {}).get("tool_name") == "business.database_summary"


def test_trace_contains_business_tool_selected_fields(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    main.DEFAULT_DB_PATH = db_path

    result = runtime.run_chat("売上トップ10")
    trace = get_trace_session(result["trace_id"])
    assert trace is not None
    records = [item for item in trace["records"] if item["layer"] == "BusinessToolSelection"]
    assert records
    output = records[0]["output"]
    assert "business_tool_selected" in output
    assert "business_tool_confidence" in output


def test_business_answer_does_not_call_llm(tmp_path: Path, monkeypatch) -> None:
    db_path = _prepare_db(tmp_path)
    main.DEFAULT_DB_PATH = db_path

    def _raise_gateway(*_args, **_kwargs):
        raise RuntimeError("LLM should not be called")

    monkeypatch.setattr(runtime.LLMGateway, "from_env", classmethod(_raise_gateway))
    result = runtime.run_chat("売上トップ10")
    assert result["success"] is True
