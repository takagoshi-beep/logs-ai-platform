from __future__ import annotations

from pathlib import Path

import pandas as pd

from business.product import get_product, get_product_schema, get_products, search_products
from database.importer import import_latest_excel_to_sqlite


def _create_sample_product_db(tmp_path: Path) -> Path:
    excel_dir = tmp_path / "excel"
    excel_dir.mkdir(parents=True)
    db_path = tmp_path / "sqlite" / "logsys.db"
    workbook = excel_dir / "sample.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame(
            {
                "product_code": ["P001", "P002", "P003"],
                "name": ["Widget", "Gadget", "Thingamajig"],
                "price": [10.0, 20.0, 30.0],
            }
        ).to_excel(writer, sheet_name="Products", index=False)
    import_latest_excel_to_sqlite(excel_dir, db_path)
    return db_path


def test_get_product_schema_returns_product_columns(tmp_path: Path) -> None:
    db_path = _create_sample_product_db(tmp_path)

    result = get_product_schema(db_path)

    assert result["success"] is True
    assert result["table_name"].lower() == "products"
    assert any(col["name"] == "product_code" for col in result["columns"])
    assert any(col["name"] == "name" for col in result["columns"])


def test_get_products_returns_product_list(tmp_path: Path) -> None:
    db_path = _create_sample_product_db(tmp_path)

    result = get_products(db_path, limit=2)

    assert result["success"] is True
    assert result["table_name"].lower() == "products"
    assert len(result["products"]) == 2
    assert result["products"][0]["product_code"] == "P001"


def test_get_product_returns_single_product_by_code(tmp_path: Path) -> None:
    db_path = _create_sample_product_db(tmp_path)

    result = get_product(db_path, "P002")

    assert result["success"] is True
    assert result["product"]["name"] == "Gadget"


def test_search_products_returns_matching_items(tmp_path: Path) -> None:
    db_path = _create_sample_product_db(tmp_path)

    result = search_products(db_path, keyword="widget")

    assert result["success"] is True
    assert len(result["products"]) == 1
    assert result["products"][0]["product_code"] == "P001"
