from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from database.connection import get_db_connection

FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|pragma|attach|detach)\b",
    re.IGNORECASE,
)


def validate_select_sql(sql: str) -> None:
    normalized = (sql or "").strip()
    if not normalized:
        raise ValueError("SQL query is required")

    lowered = normalized.lower()
    if not lowered.startswith("select"):
        raise ValueError("Only SELECT statements are allowed")

    if FORBIDDEN_SQL_PATTERN.search(normalized):
        raise ValueError("Only SELECT statements are allowed")


def execute_sql(db_path: Path, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
    validate_select_sql(sql)
    with get_db_connection(db_path) as conn:
        cursor = conn.execute(sql, params or ())
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
