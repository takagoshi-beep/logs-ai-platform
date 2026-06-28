from __future__ import annotations

from pathlib import Path

import pandas as pd

from business.router import route_business_query
from database.importer import import_latest_excel_to_sqlite


def _create_sample_business_db(tmp_path: Path) -> Path:
    excel_dir = tmp_path / "excel"
    excel_dir.mkdir(parents=True)
    db_path = tmp_path / "sqlite" / "logsys.db"
    workbook = excel_dir / "sample.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame(
            {
                "customer_code": ["C001", "C002"],
                "customer_name": ["Acme", "Zenith"],
                "sales": [100.0, 150.0],
            }
        ).to_excel(writer, sheet_name="Customers", index=False)
        pd.DataFrame(
            {
                "product_code": ["P001", "P002"],
                "product_name": ["LOGS Alpha", "LOGS Beta"],
            }
        ).to_excel(writer, sheet_name="Products", index=False)
    import_latest_excel_to_sqlite(excel_dir, db_path)
    return db_path


def test_route_business_query_handles_sales_ranking(tmp_path: Path) -> None:
    db_path = _create_sample_business_db(tmp_path)

    result = route_business_query("売上ランキングを見せて", db_path)

    assert result["success"] is True
    assert result["intent"]["domain"] == "sales"
    assert result["intent"]["action"] == "ranking"
    assert result["result"]["success"] is True


def test_route_business_query_handles_product_search(tmp_path: Path) -> None:
    db_path = _create_sample_business_db(tmp_path)

    result = route_business_query("商品を探して", db_path)

    assert result["success"] is True
    assert result["intent"]["domain"] == "product"
    assert result["intent"]["action"] == "search"
    assert result["result"]["success"] is True


def test_route_business_query_returns_unknown_for_unsupported_query(tmp_path: Path) -> None:
    db_path = _create_sample_business_db(tmp_path)

    result = route_business_query("天気を教えて", db_path)

    assert result["success"] is False
    assert result["intent"]["domain"] == "unknown"
    assert result["intent"]["action"] == "unknown"


def test_route_business_query_preserves_intent_metadata(tmp_path: Path) -> None:
    db_path = _create_sample_business_db(tmp_path)

    result = route_business_query("今月の帽子のトップ5を見せて", db_path)

    assert result["success"] is True
    assert result["intent"]["period"] == "this_month"
    assert result["intent"]["count"] == 5
    assert result["intent"]["category"] == "hat"
