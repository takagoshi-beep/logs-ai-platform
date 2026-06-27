from __future__ import annotations

from pathlib import Path

import pandas as pd

from business.customer import (
    get_customer,
    get_customer_schema,
    get_customers,
    get_top_customers_by_sales,
    search_customers,
)
from database.importer import import_latest_excel_to_sqlite


def _create_sample_customer_db(tmp_path: Path) -> Path:
    excel_dir = tmp_path / "excel"
    excel_dir.mkdir(parents=True)
    db_path = tmp_path / "sqlite" / "logsys.db"
    workbook = excel_dir / "sample.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame(
            {
                "customer_code": ["C001", "C002", "C003"],
                "customer_name": ["Acme", "Zenith", "Orbit"],
                "sales": [100.0, 150.0, 50.0],
            }
        ).to_excel(writer, sheet_name="Customers", index=False)
    import_latest_excel_to_sqlite(excel_dir, db_path)
    return db_path


def test_get_customer_schema_returns_customer_columns(tmp_path: Path) -> None:
    db_path = _create_sample_customer_db(tmp_path)

    result = get_customer_schema(db_path)

    assert result["success"] is True
    assert result["table_name"].lower() == "customers"
    assert any(col["name"] == "customer_code" for col in result["columns"])
    assert any(col["name"] == "customer_name" for col in result["columns"])


def test_get_customers_returns_customer_list(tmp_path: Path) -> None:
    db_path = _create_sample_customer_db(tmp_path)

    result = get_customers(db_path, limit=2)

    assert result["success"] is True
    assert result["table_name"].lower() == "customers"
    assert len(result["customers"]) == 2
    assert result["customers"][0]["customer_code"] == "C001"


def test_get_customer_returns_single_customer_by_code(tmp_path: Path) -> None:
    db_path = _create_sample_customer_db(tmp_path)

    result = get_customer(db_path, "C002")

    assert result["success"] is True
    assert result["customer"]["customer_name"] == "Zenith"


def test_search_customers_returns_matching_items(tmp_path: Path) -> None:
    db_path = _create_sample_customer_db(tmp_path)

    result = search_customers(db_path, keyword="orb")

    assert result["success"] is True
    assert len(result["customers"]) == 1
    assert result["customers"][0]["customer_code"] == "C003"


def test_get_top_customers_by_sales_reuses_sales_module(tmp_path: Path) -> None:
    db_path = _create_sample_customer_db(tmp_path)

    result = get_top_customers_by_sales(db_path, limit=2)

    assert result["success"] is True
    assert result["table_name"] == "customers"
    assert result["top_customers"]
