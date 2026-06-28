from __future__ import annotations

from validation.checks import (
    check_business_table_candidates,
    check_excel_files,
    check_sqlite_database,
    check_table_columns,
    check_table_row_counts,
    check_tables,
)
from validation.runner import run_validation


def test_raw_data_validation_runs_via_validation_layer() -> None:
    report = run_validation()

    assert report["status"] in {"ok", "warning", "error"}
    assert report["summary"]["check_count"] >= 6


def test_raw_data_validation_checks_excel_and_sqlite() -> None:
    excel_result = check_excel_files()
    sqlite_result = check_sqlite_database()

    assert excel_result["excel_file_count"] >= 1
    assert sqlite_result["db_exists"] is True


def test_raw_data_validation_checks_schema_tables_and_rows() -> None:
    table_result = check_tables()
    column_result = check_table_columns()
    row_result = check_table_row_counts()

    assert table_result["table_count"] >= 1
    assert column_result["table_columns"]
    assert row_result["row_counts"]


def test_raw_data_validation_checks_business_candidates() -> None:
    result = check_business_table_candidates()

    assert result["business_tables"]
    assert result["system_tables"]
    assert isinstance(result["candidates"], dict)
