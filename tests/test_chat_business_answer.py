from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import ai.runtime as runtime
from app import main
from app.main import app
from observability.tracer import get_trace_session
from storage.sqlite import SQLiteRepository


def _prepare_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "sqlite" / "logsys.db"
    repository = SQLiteRepository(db_path)
    repository.execute_query("CREATE TABLE sales (id INTEGER PRIMARY KEY, customer TEXT, amount REAL)")
    repository.execute_query("CREATE TABLE customer (id INTEGER PRIMARY KEY, name TEXT)")
    repository.execute_query("INSERT INTO sales (customer, amount) VALUES (?, ?)", ("Acme", 100.0))
    repository.close()
    return db_path


def test_chat_tables_question_uses_business_answer_without_llm(tmp_path: Path, monkeypatch) -> None:
    db_path = _prepare_db(tmp_path)
    main.DEFAULT_DB_PATH = db_path

    def _raise_gateway(*_args, **_kwargs):
        raise RuntimeError("LLM should not be called")

    monkeypatch.setattr(runtime.LLMGateway, "from_env", classmethod(_raise_gateway))

    result = runtime.run_chat("どんなテーブルがありますか？")
    assert result["success"] is True
    assert "テーブル" in result["answer"]


def test_chat_table_count_question_uses_business_answer(tmp_path: Path, monkeypatch) -> None:
    db_path = _prepare_db(tmp_path)
    main.DEFAULT_DB_PATH = db_path
    monkeypatch.setattr(runtime.LLMGateway, "from_env", classmethod(lambda cls: (_ for _ in ()).throw(RuntimeError("no llm"))))

    result = runtime.run_chat("salesは何件ありますか？")
    assert result["success"] is True
    assert "sales" in result["answer"]


def test_chat_table_columns_question_uses_business_answer(tmp_path: Path, monkeypatch) -> None:
    db_path = _prepare_db(tmp_path)
    main.DEFAULT_DB_PATH = db_path
    monkeypatch.setattr(runtime.LLMGateway, "from_env", classmethod(lambda cls: (_ for _ in ()).throw(RuntimeError("no llm"))))

    result = runtime.run_chat("customerの列を教えて")
    assert result["success"] is True
    assert "列" in result["answer"]


def test_chat_endpoint_business_flow_returns_200(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    main.DEFAULT_DB_PATH = db_path

    client = TestClient(app)
    response = client.post("/chat", json={"message": "どんなテーブルがありますか？"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert "source_information" in payload


def test_trace_includes_business_source_layers(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    main.DEFAULT_DB_PATH = db_path

    result = runtime.run_chat("どんなテーブルがありますか？")
    trace = get_trace_session(result["trace_id"])
    assert trace is not None
    layers = [item["layer"] for item in trace["records"]]
    assert "Semantic" in layers
    assert "Authorization" in layers
    assert "BusinessQuery" in layers
    assert "RepositoryQuery" in layers
    assert "Formatter" in layers
    assert "AnswerSource" in layers
    assert "Storage" in layers
