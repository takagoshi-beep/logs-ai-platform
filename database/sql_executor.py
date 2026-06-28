from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from database.repository import get_repository

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
    return get_repository(db_path).execute_select(sql, params=params)
