from __future__ import annotations

from business.formatter import (
    format_business_result,
    format_database_summary,
    format_table_columns,
    format_table_count,
)


def test_format_database_summary() -> None:
    text = format_database_summary({"table_count": 18, "tables": ["sales", "customer"]})
    assert "18" in text
    assert "sales" in text


def test_format_table_count() -> None:
    text = format_table_count({"table_name": "sales", "row_count": 52341, "warning": None})
    assert "sales" in text
    assert "52341" in text


def test_format_table_columns() -> None:
    text = format_table_columns({"table_name": "customer", "columns": ["id", "name"], "warning": None})
    assert "customer" in text
    assert "id" in text


def test_format_business_result_uses_table_candidates() -> None:
    text = format_business_result("business.find_sales_tables", {"tables": ["sales_data"], "warnings": []})
    assert "売上" in text
    assert "sales_data" in text
