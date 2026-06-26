from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any


def create_validation_report(conn: sqlite3.Connection) -> None:
    """Create the validation report table for import quality checks."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS validation_report (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            row_count INTEGER NOT NULL,
            is_empty INTEGER NOT NULL,
            duplicate_candidates TEXT,
            high_null_columns TEXT,
            checked_at TEXT NOT NULL,
            status TEXT NOT NULL
        )
        """
    )
    conn.commit()


def validate_tables(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Check each imported table for basic quality issues."""
    reports: list[dict[str, Any]] = []
    tables = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'sqlite_%'
          AND name NOT IN ('import_registry', 'table_schema_registry', 'validation_report')
        ORDER BY name
        """
    ).fetchall()

    checked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for (table_name,) in tables:
        row_count = int(conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0])
        columns = [row[1] for row in conn.execute(f'PRAGMA table_info("{table_name}")')]

        duplicate_candidates: list[dict[str, Any]] = []
        high_null_columns: list[dict[str, Any]] = []

        for column_name in columns:
            values = conn.execute(f'SELECT "{column_name}" FROM "{table_name}"').fetchall()
            non_null = [value[0] for value in values if value[0] is not None]
            if row_count:
                null_ratio = 1 - (len(non_null) / row_count)
            else:
                null_ratio = 1.0

            if row_count and len(non_null) > 1:
                unique_count = len(set(non_null))
                if unique_count < len(non_null):
                    duplicate_candidates.append(
                        {"column": column_name, "duplicates": len(non_null) - unique_count}
                    )

            if row_count and null_ratio > 0.5:
                high_null_columns.append(
                    {"column": column_name, "null_ratio": round(null_ratio, 2)}
                )

        status = "ok"
        if row_count == 0:
            status = "warning"
        elif duplicate_candidates or high_null_columns:
            status = "warning"

        conn.execute(
            """
            INSERT INTO validation_report (
                table_name,
                row_count,
                is_empty,
                duplicate_candidates,
                high_null_columns,
                checked_at,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                table_name,
                row_count,
                1 if row_count == 0 else 0,
                json.dumps(duplicate_candidates),
                json.dumps(high_null_columns),
                checked_at,
                status,
            ),
        )
        reports.append(
            {
                "table": table_name,
                "row_count": row_count,
                "is_empty": row_count == 0,
                "duplicate_candidates": duplicate_candidates,
                "high_null_columns": high_null_columns,
                "status": status,
            }
        )

    conn.commit()
    return reports
