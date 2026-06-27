from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

SYSTEM_TABLE_NAMES = {
    "import_registry",
    "table_schema_registry",
    "validation_report",
}


def list_database_tables(db_path: Path) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        tables = []
        for (name,) in rows:
            count = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            tables.append({"table": name, "rows": int(count)})
    return tables


def get_last_imported_at(db_path: Path) -> str | None:
    if not db_path.exists():
        return None

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT imported_at FROM import_registry ORDER BY imported_at DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else None


def get_database_status(db_path: Path) -> dict[str, Any]:
    if not db_path.exists():
        return {
            "status": "not_found",
            "db_exists": False,
            "db_path": str(db_path),
            "total_table_count": 0,
            "business_table_count": 0,
            "system_table_count": 0,
            "tables": [],
            "last_imported_at": None,
        }

    tables = list_database_tables(db_path)
    system_tables = [table for table in tables if table["table"] in SYSTEM_TABLE_NAMES]
    business_tables = [table for table in tables if table["table"] not in SYSTEM_TABLE_NAMES]
    return {
        "status": "ok",
        "db_exists": True,
        "db_path": str(db_path),
        "total_table_count": len(tables),
        "business_table_count": len(business_tables),
        "system_table_count": len(system_tables),
        "table_count": len(tables),
        "tables": tables,
        "last_imported_at": get_last_imported_at(db_path),
    }
