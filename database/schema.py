from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import Sequence


def create_table_schema_registry(conn: sqlite3.Connection) -> None:
    """Create the schema registry table used to track sheet columns over time."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS table_schema_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_id INTEGER NOT NULL,
            sheet_name TEXT NOT NULL,
            table_name TEXT NOT NULL,
            column_names TEXT NOT NULL,
            column_count INTEGER NOT NULL,
            schema_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def build_schema_hash(columns: Sequence[str]) -> str:
    """Create a deterministic schema fingerprint for a sheet."""
    joined = "|".join(columns)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def record_table_schema(
    conn: sqlite3.Connection,
    import_id: int,
    sheet_name: str,
    table_name: str,
    columns: Sequence[str],
) -> None:
    """Persist a sheet's schema details for later comparison."""
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    conn.execute(
        """
        INSERT INTO table_schema_registry (
            import_id,
            sheet_name,
            table_name,
            column_names,
            column_count,
            schema_hash,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            import_id,
            sheet_name,
            table_name,
            "|".join(columns),
            len(columns),
            build_schema_hash(columns),
            created_at,
        ),
    )
    conn.commit()
