from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def create_import_registry(conn: sqlite3.Connection) -> None:
    """Create the import registry table for tracking imported workbooks."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS import_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            excel_filename TEXT NOT NULL,
            excel_updated_at TEXT,
            imported_at TEXT NOT NULL,
            sheet_count INTEGER NOT NULL,
            total_rows INTEGER NOT NULL
        )
        """
    )
    conn.commit()


def record_import(conn: sqlite3.Connection, excel_path: Path, sheet_count: int, total_rows: int) -> int:
    """Persist the import metadata for the current workbook."""
    imported_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    excel_updated_at = datetime.fromtimestamp(
        excel_path.stat().st_mtime,
        tz=timezone.utc,
    ).replace(microsecond=0).isoformat()

    cursor = conn.execute(
        """
        INSERT INTO import_registry (
            excel_filename,
            excel_updated_at,
            imported_at,
            sheet_count,
            total_rows
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (excel_path.name, excel_updated_at, imported_at, sheet_count, total_rows),
    )
    conn.commit()
    return int(cursor.lastrowid)
