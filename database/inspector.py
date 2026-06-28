from __future__ import annotations

from pathlib import Path
from typing import Any

from database.repository import get_repository


def list_tables(db_path: Path) -> list[dict[str, Any]]:
    """Return all user tables and their row counts."""
    return get_repository(db_path).list_tables()


def get_table_sample(db_path: Path, table_name: str, limit: int = 10) -> list[dict[str, Any]]:
    """Return the first N rows from a table as JSON-friendly dictionaries."""
    return get_repository(db_path).get_table_sample(table_name, limit=limit)


def get_table_row_count(db_path: Path, table_name: str) -> int:
    """Return the total number of rows in a table."""
    return get_repository(db_path).get_table_row_count(table_name)
