from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.main import app
from business.query import (
    find_customer_tables,
    find_product_tables,
    find_sales_tables,
    get_business_tables,
    get_sales_summary,
    get_table_overview,
    get_top_sales,
)
from storage.sqlite import SQLiteRepository


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


def test_get_business_tables_returns_tables(tmp_path: Path) -> None:
    db_path = _prepare_sample_db(tmp_path)
    result = get_business_tables(db_path)
    assert result["success"] is True
    assert "sales_data" in result["tables"]


def test_get_table_overview_returns_payload(tmp_path: Path) -> None:
    db_path = _prepare_sample_db(tmp_path)
    result = get_table_overview("sales_data", db_path)
    assert result["success"] is True
    assert result["table_name"] == "sales_data"
    assert result["row_count"] >= 1


def test_find_sales_tables_returns_candidates(tmp_path: Path) -> None:
    db_path = _prepare_sample_db(tmp_path)
    result = find_sales_tables(db_path)
    assert result["success"] is True
    assert "sales_data" in result["tables"]


def test_find_customer_tables_runs_without_exception(tmp_path: Path) -> None:
    db_path = _prepare_sample_db(tmp_path)
    result = find_customer_tables(db_path)
    assert "success" in result


def test_find_product_tables_runs_without_exception(tmp_path: Path) -> None:
    db_path = _prepare_sample_db(tmp_path)
    result = find_product_tables(db_path)
    assert "success" in result


def test_get_sales_summary_runs_without_exception(tmp_path: Path) -> None:
    db_path = _prepare_sample_db(tmp_path)
    result = get_sales_summary(db_path)
    assert "success" in result
    assert "warnings" in result


def test_get_top_sales_runs_without_exception(tmp_path: Path) -> None:
    db_path = _prepare_sample_db(tmp_path)
    result = get_top_sales(limit=10, db_path=db_path)
    assert "success" in result
    assert "warnings" in result


def test_business_tables_endpoint_returns_200(tmp_path: Path) -> None:
    db_path = _prepare_sample_db(tmp_path)
    main.DEFAULT_DB_PATH = db_path

    client = TestClient(app)
    response = client.get("/business/tables")
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_business_sales_top_endpoint_returns_200(tmp_path: Path) -> None:
    db_path = _prepare_sample_db(tmp_path)
    main.DEFAULT_DB_PATH = db_path

    client = TestClient(app)
    response = client.get("/business/sales/top?limit=10")
    assert response.status_code == 200
    payload = response.json()
    assert "success" in payload
