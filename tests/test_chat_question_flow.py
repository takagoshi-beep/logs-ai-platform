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


def test_chat_response_contains_question_understanding(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    main.DEFAULT_DB_PATH = db_path

    result = runtime.run_chat("売上トップ5を教えて")
    question = result.get("question_understanding")

    assert result["success"] is True
    assert isinstance(question, dict)
    assert question.get("operation") == "ranking"
    assert question.get("metric") == "sales"
    assert question.get("limit") == 5


def test_trace_contains_question_layer_fields(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    main.DEFAULT_DB_PATH = db_path

    result = runtime.run_chat("売上トップ5を教えて")
    trace = get_trace_session(result["trace_id"])
    assert trace is not None

    question_records = [item for item in trace["records"] if item["layer"] == "Question"]
    assert question_records
    output = question_records[0]["output"]
    assert output["question_metric"] == "sales"
    assert output["question_operation"] == "ranking"
    assert output["question_limit"] == 5
