from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.main import app


def _prepare_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "sqlite" / "logsys.db"
    main.DEFAULT_DB_PATH = db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    from storage.sqlite import SQLiteRepository

    repository = SQLiteRepository(db_path)
    repository.execute_query("CREATE TABLE sales (id INTEGER PRIMARY KEY, customer TEXT, amount REAL)")
    repository.execute_query("INSERT INTO sales (customer, amount) VALUES (?, ?)", ("Acme", 100.0))
    repository.execute_query("INSERT INTO sales (customer, amount) VALUES (?, ?)", ("Beta", 250.0))
    repository.close()
    return db_path


def test_api_explain_returns_question_path(tmp_path: Path) -> None:
    _prepare_db(tmp_path)
    client = TestClient(app)
    response = client.post("/api/explain", json={"question": "売上トップ10は？"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["question"] == "売上トップ10は？"
    assert payload["parsed_question"]["operation"] == "ranking"
    assert payload["semantic_result"]["metric"] in {"sales", "sales_amount"}
    assert payload["selected_business_tool"]["selected_tool"] == "business.sales_top"
    assert payload["authorization_result"]["allowed"] is True
    assert payload["final_answer_preview"]
    assert "source_information" in payload