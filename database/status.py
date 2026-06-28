from __future__ import annotations

from pathlib import Path
from typing import Any

from database.repository import SYSTEM_TABLE_NAMES, get_repository


def list_database_tables(db_path: Path) -> list[dict[str, Any]]:
    return get_repository(db_path).get_database_status().get("tables", [])


def get_last_imported_at(db_path: Path) -> str | None:
    return get_repository(db_path).get_database_status().get("last_imported_at")


def get_database_status(db_path: Path) -> dict[str, Any]:
    return get_repository(db_path).get_database_status()
