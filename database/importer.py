from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

import openpyxl  # noqa: F401
import pandas as pd

from database.registry import create_import_registry, record_import
from database.schema import create_table_schema_registry, record_table_schema
from database.validator import create_validation_report, validate_tables
from database.views import create_analysis_views


def normalize_table_name(sheet_name: str) -> str:
    """Convert an Excel sheet name into a safe SQLite table name."""
    name = sheet_name.strip().lower()
    name = re.sub(r"[^0-9a-zA-Z_\u3040-\u30ff\u3400-\u9fff]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "sheet"


def clean_column_name(col: Any, index: int) -> str:
    """Create stable column names even when source headers are messy."""
    text = str(col).strip() if col is not None else ""
    text = re.sub(r"\s+", "_", text)
    text = text.replace("'", "").replace('"', "")
    return text or f"column_{index + 1}"


def ensure_unique_column_names(columns: list[Any]) -> list[str]:
    """Ensure column names are unique for SQLite export."""
    cleaned = [clean_column_name(col, i) for i, col in enumerate(columns)]
    seen: set[str] = set()
    unique: list[str] = []

    for name in cleaned:
        candidate = name
        suffix = 1
        while candidate in seen:
            candidate = f"{name}_{suffix}"
            suffix += 1
        seen.add(candidate)
        unique.append(candidate)

    return unique


def find_latest_excel_file(excel_dir: Path) -> Path:
    """Return the newest Excel workbook under the given directory."""
    excel_dir.mkdir(parents=True, exist_ok=True)
    suffixes = {".xlsx", ".xls", ".xlsm", ".csv"}
    excel_files = [
        path
        for path in excel_dir.iterdir()
        if path.is_file() and path.suffix.lower() in suffixes
    ]

    if not excel_files:
        raise FileNotFoundError(f"No Excel files found in {excel_dir}")

    return max(excel_files, key=lambda path: path.stat().st_mtime)


def import_excel_to_sqlite(excel_path: Path, db_path: Path) -> dict:
    """Import every visible sheet from a Logsys Excel workbook into SQLite."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        excel = pd.ExcelFile(excel_path, engine="openpyxl")
        imported: list[dict] = []

        with sqlite3.connect(db_path) as conn:
            create_import_registry(conn)
            create_table_schema_registry(conn)
            create_validation_report(conn)
            create_analysis_views(conn)

            total_rows = 0
            for sheet_name in excel.sheet_names:
                df = pd.read_excel(
                    excel_path,
                    sheet_name=sheet_name,
                    dtype=object,
                    engine="openpyxl",
                )
                df.columns = ensure_unique_column_names(list(df.columns))
                table_name = normalize_table_name(sheet_name)
                df.to_sql(table_name, conn, if_exists="replace", index=False)
                total_rows += int(len(df))
                imported.append(
                    {
                        "sheet": sheet_name,
                        "table": table_name,
                        "rows": int(len(df)),
                        "columns": int(len(df.columns)),
                    }
                )
                record_table_schema(conn, 0, sheet_name, table_name, list(df.columns))

            import_id = record_import(conn, excel_path, len(imported), total_rows)
            conn.execute(
                "UPDATE table_schema_registry SET import_id = ? WHERE import_id = 0",
                (import_id,),
            )
            conn.commit()
            validation_results = validate_tables(conn)

        return {
            "status": "ok",
            "excel_path": str(excel_path),
            "db_path": str(db_path),
            "tables": imported,
            "import_id": import_id,
            "validation": validation_results,
        }
    except Exception as exc:  # pragma: no cover - exercised in CLI/error handling
        return {
            "status": "error",
            "excel_path": str(excel_path),
            "db_path": str(db_path),
            "message": f"Failed to import Excel workbook: {exc}",
            "tables": [],
        }


def import_latest_excel_to_sqlite(excel_dir: Path, db_path: Path) -> dict:
    """Find the latest Excel file and import all of its sheets into SQLite."""
    try:
        excel_path = find_latest_excel_file(excel_dir)
        return import_excel_to_sqlite(excel_path, db_path)
    except FileNotFoundError as exc:
        return {
            "status": "error",
            "excel_path": str(excel_dir),
            "db_path": str(db_path),
            "message": str(exc),
            "tables": [],
        }
    except Exception as exc:  # pragma: no cover - exercised in CLI/error handling
        return {
            "status": "error",
            "excel_path": str(excel_dir),
            "db_path": str(db_path),
            "message": f"Failed to resolve input workbook: {exc}",
            "tables": [],
        }


def main() -> int:
    """CLI entrypoint for importing the latest Excel workbook into SQLite."""
    root_dir = Path(__file__).resolve().parents[1]
    excel_dir = root_dir / "data" / "excel"
    db_path = root_dir / "data" / "sqlite" / "logsys.db"

    result = import_latest_excel_to_sqlite(excel_dir, db_path)
    if result["status"] != "ok":
        print(result.get("message", "Import failed"), file=sys.stderr)
        return 1

    print(f"Database created at {db_path}")
    print(f"Imported workbook: {result['excel_path']}")
    print(f"Sheets imported: {len(result['tables'])}")
    print(f"Total rows imported: {sum(table['rows'] for table in result['tables'])}")
    for table in result["tables"]:
        print(
            f"- {table['sheet']} -> {table['table']}: {table['rows']} rows, {table['columns']} columns"
        )
    if result.get("validation"):
        print("Validation summary:")
        for item in result["validation"]:
            print(f"- {item['table']}: {item['status']} ({item['row_count']} rows)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
