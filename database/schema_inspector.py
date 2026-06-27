from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from database.connection import get_db_connection

SYSTEM_TABLE_NAMES = {
    "import_registry",
    "table_schema_registry",
    "validation_report",
    "view_import_summary",
}


def quote_identifier(identifier: str) -> str:
    return f'"{identifier.replace("\"", "\"\"")}"'


def list_schema_objects(db_path: Path) -> list[str]:
    if not db_path.exists():
        return []

    with get_db_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        return [row["name"] for row in rows]


def get_table_columns(db_path: Path, table_name: str) -> list[dict[str, Any]]:
    with get_db_connection(db_path) as conn:
        rows = conn.execute(f'PRAGMA table_info({quote_identifier(table_name)})').fetchall()
        return [
            {"name": row["name"], "type": row["type"] or ""}
            for row in rows
        ]


def get_column_sample_values(db_path: Path, table_name: str, column_name: str, limit: int = 3) -> list[Any]:
    with get_db_connection(db_path) as conn:
        quoted_table = quote_identifier(table_name)
        quoted_column = quote_identifier(column_name)
        rows = conn.execute(
            f"SELECT {quoted_column} FROM {quoted_table} WHERE {quoted_column} IS NOT NULL LIMIT ?",
            (limit,),
        ).fetchall()
        return [row[0] for row in rows]


def is_system_table(table_name: str) -> bool:
    return table_name in SYSTEM_TABLE_NAMES


def get_table_schema(db_path: Path, table_name: str) -> dict[str, Any]:
    if table_name not in list_schema_objects(db_path):
        raise ValueError("Table not found")

    columns = get_table_columns(db_path, table_name)
    for column in columns:
        column["sample_values"] = get_column_sample_values(
            db_path, table_name, column["name"], limit=3
        )

    return {
        "table_name": table_name,
        "table_type": "system" if is_system_table(table_name) else "business",
        "row_count": get_table_row_count(db_path, table_name),
        "column_count": len(columns),
        "columns": columns,
    }


def list_database_schema(db_path: Path) -> list[dict[str, Any]]:
    return [get_table_schema(db_path, table_name) for table_name in list_schema_objects(db_path)]


def get_table_row_count(db_path: Path, table_name: str) -> int:
    with get_db_connection(db_path) as conn:
        row = conn.execute(f'SELECT COUNT(*) AS count FROM {quote_identifier(table_name)}').fetchone()
        return int(row["count"])
