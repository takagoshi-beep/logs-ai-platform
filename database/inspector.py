from __future__ import annotations

from pathlib import Path
from typing import Any

from database.connection import get_db_connection


def list_tables(db_path: Path) -> list[dict[str, Any]]:
    """Return all user tables and their row counts."""
    with get_db_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        result = []
        for row in rows:
            table_name = row["name"]
            count_row = conn.execute(f'SELECT COUNT(*) AS count FROM "{table_name}"').fetchone()
            result.append({"table_name": table_name, "row_count": int(count_row["count"])})
        return result


def get_table_sample(db_path: Path, table_name: str, limit: int = 10) -> list[dict[str, Any]]:
    """Return the first N rows from a table as JSON-friendly dictionaries."""
    with get_db_connection(db_path) as conn:
        rows = conn.execute(f'SELECT * FROM "{table_name}" LIMIT {limit}').fetchall()
        return [dict(row) for row in rows]


def get_table_row_count(db_path: Path, table_name: str) -> int:
    """Return the total number of rows in a table."""
    with get_db_connection(db_path) as conn:
        row = conn.execute(f'SELECT COUNT(*) AS count FROM "{table_name}"').fetchone()
        return int(row["count"])
