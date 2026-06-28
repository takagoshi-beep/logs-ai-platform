from __future__ import annotations

from pathlib import Path
from typing import Any

from database.repository import get_repository

SYSTEM_TABLE_NAMES = {
    "import_registry",
    "table_schema_registry",
    "validation_report",
    "view_import_summary",
}


def quote_identifier(identifier: str) -> str:
    return f'"{identifier.replace("\"", "\"\"")}"'


def list_schema_objects(db_path: Path) -> list[str]:
    return get_repository(db_path).list_schema_objects()


def get_table_columns(db_path: Path, table_name: str) -> list[dict[str, Any]]:
    return get_repository(db_path).get_table_columns(table_name)


def get_column_sample_values(db_path: Path, table_name: str, column_name: str, limit: int = 3) -> list[Any]:
    return get_repository(db_path).get_column_sample_values(table_name, column_name, limit=limit)


def is_system_table(table_name: str) -> bool:
    return table_name in SYSTEM_TABLE_NAMES


def get_table_schema(db_path: Path, table_name: str) -> dict[str, Any]:
    return get_repository(db_path).get_table_schema(table_name)


def list_database_schema(db_path: Path) -> list[dict[str, Any]]:
    return get_repository(db_path).list_database_schema()


def get_table_row_count(db_path: Path, table_name: str) -> int:
    return get_repository(db_path).get_table_row_count(table_name)
