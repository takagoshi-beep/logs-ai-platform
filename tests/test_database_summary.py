from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.main import app
from business.query import get_database_summary, get_table_columns, get_table_count
from storage.sqlite import SQLiteRepository


def _prepare_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "sqlite" / "logsys.db"
    repository = SQLiteRepository(db_path)
    repository.execute_query("CREATE TABLE sales (id INTEGER PRIMARY KEY, customer TEXT, amount REAL)")
    repository.execute_query("CREATE TABLE customer (id INTEGER PRIMARY KEY, name TEXT)")
    repository.execute_query("INSERT INTO sales (customer, amount) VALUES (?, ?)", ("Acme", 100.0))
    repository.close()
    return db_path


def test_get_database_summary(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    result = get_database_summary(db_path)
    assert result["table_count"] >= 2
    assert "sales" in result["tables"]


def test_get_table_count(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    result = get_table_count("sales", db_path)
    assert result["row_count"] == 1


def test_get_table_columns(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    result = get_table_columns("customer", db_path)
    assert "name" in result["columns"]


def test_database_summary_api_returns_200(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    main.DEFAULT_DB_PATH = db_path
    client = TestClient(app)
    response = client.get("/business/database/summary")
    assert response.status_code == 200
    assert "table_count" in response.json()


def test_table_count_api_returns_200(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    main.DEFAULT_DB_PATH = db_path
    client = TestClient(app)
    response = client.get("/business/table/sales/count")
    assert response.status_code == 200
    assert response.json()["table_name"] == "sales"


def test_table_columns_api_returns_200(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    main.DEFAULT_DB_PATH = db_path
    client = TestClient(app)
    response = client.get("/business/table/customer/columns")
    assert response.status_code == 200
    assert "columns" in response.json()
