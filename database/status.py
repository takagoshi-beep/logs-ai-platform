from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def get_database_status(db_path: Path) -> dict[str, Any]:
    if not db_path.exists():
        return {
            "status": "not_found",
            "db_path": str(db_path),
            "tables": [],
            "last_imported_at": None,
        }

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        tables = []
        for (name,) in rows:
            count = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            tables.append({"table": name, "rows": int(count)})

        last_imported_at = None
        last_row = conn.execute(
            "SELECT imported_at FROM import_registry ORDER BY imported_at DESC LIMIT 1"
        ).fetchone()
        if last_row:
            last_imported_at = last_row[0]

    return {
        "status": "ok",
        "db_path": str(db_path),
        "tables": tables,
        "last_imported_at": last_imported_at,
    }
