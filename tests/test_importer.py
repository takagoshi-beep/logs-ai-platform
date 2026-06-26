from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pandas as pd

from database import importer


def test_find_latest_excel_file_prefers_newest_file(tmp_path: Path) -> None:
    excel_dir = tmp_path / "excel"
    excel_dir.mkdir(parents=True)

    older = excel_dir / "older.xlsx"
    latest = excel_dir / "latest.xlsx"
    older.write_bytes(b"old")
    latest.write_bytes(b"new")

    os.utime(older, (1, 1))
    os.utime(latest, (2, 2))

    assert importer.find_latest_excel_file(excel_dir) == latest


def test_import_latest_excel_to_sqlite_creates_database_and_registry(tmp_path: Path) -> None:
    excel_dir = tmp_path / "excel"
    excel_dir.mkdir(parents=True)
    db_path = tmp_path / "sqlite" / "logsys.db"

    latest = excel_dir / "latest.xlsx"
    with pd.ExcelWriter(latest) as writer:
        pd.DataFrame({"id": [1], "name": ["alpha"]}).to_excel(
            writer, sheet_name="Sheet1", index=False
        )
        pd.DataFrame({"value": [2]}).to_excel(writer, sheet_name="Sheet2", index=False)

    result = importer.import_latest_excel_to_sqlite(excel_dir, db_path)

    assert result["status"] == "ok"
    assert db_path.exists()

    with sqlite3.connect(db_path) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        registry_rows = conn.execute("SELECT COUNT(*) FROM import_registry").fetchone()[0]
        schema_rows = conn.execute("SELECT COUNT(*) FROM table_schema_registry").fetchone()[0]
        validation_rows = conn.execute("SELECT COUNT(*) FROM validation_report").fetchone()[0]

    assert ("sheet1",) in tables
    assert ("sheet2",) in tables
    assert registry_rows >= 1
    assert schema_rows >= 1
    assert validation_rows >= 1
