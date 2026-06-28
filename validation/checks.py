from __future__ import annotations

from pathlib import Path
from typing import Any

from database.importer import import_latest_excel_to_sqlite
from database.inspector import get_table_row_count, get_table_sample, list_tables
from database.schema_inspector import SYSTEM_TABLE_NAMES, get_table_columns, list_schema_objects

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_EXCEL_DIR = ROOT_DIR / "data" / "excel"
DEFAULT_DB_PATH = ROOT_DIR / "data" / "sqlite" / "logsys.db"


def _collect_excel_files(excel_dir: Path) -> list[Path]:
    suffixes = {".xlsx", ".xls", ".xlsm"}
    return [path for path in excel_dir.iterdir() if path.is_file() and path.suffix.lower() in suffixes]


def check_excel_files(excel_dir: Path | None = None) -> dict[str, Any]:
    path = excel_dir or DEFAULT_EXCEL_DIR
    path.mkdir(parents=True, exist_ok=True)
    files = sorted(_collect_excel_files(path), key=lambda item: item.name.lower())
    success = len(files) > 0
    issues: list[dict[str, str]] = []
    if not success:
        issues.append({"severity": "error", "message": f"No Excel files found under {path}"})

    return {
        "name": "check_excel_files",
        "success": success,
        "excel_dir": str(path),
        "excel_file_count": len(files),
        "excel_files": [item.name for item in files],
        "issues": issues,
    }


def check_sqlite_database(db_path: Path | None = None, excel_dir: Path | None = None) -> dict[str, Any]:
    sqlite_path = db_path or DEFAULT_DB_PATH
    excel_path = excel_dir or DEFAULT_EXCEL_DIR
    sqlite_exists_before = sqlite_path.exists()
    import_result: dict[str, Any] | None = None
    issues: list[dict[str, str]] = []

    if not sqlite_exists_before:
        import_result = import_latest_excel_to_sqlite(excel_path, sqlite_path)

    sqlite_exists_after = sqlite_path.exists()
    success = sqlite_exists_after
    if not success:
        issues.append({"severity": "error", "message": f"SQLite database is missing: {sqlite_path}"})
    elif import_result and import_result.get("status") != "ok":
        issues.append({"severity": "warning", "message": str(import_result.get("message", "import returned warning"))})

    return {
        "name": "check_sqlite_database",
        "success": success,
        "db_path": str(sqlite_path),
        "db_exists": sqlite_exists_after,
        "db_created_by_import": (not sqlite_exists_before) and sqlite_exists_after,
        "import_status": (import_result or {}).get("status"),
        "issues": issues,
    }


def check_tables(db_path: Path | None = None) -> dict[str, Any]:
    sqlite_path = db_path or DEFAULT_DB_PATH
    if not sqlite_path.exists():
        return {
            "name": "check_tables",
            "success": False,
            "table_count": 0,
            "tables": [],
            "issues": [{"severity": "error", "message": f"Database file not found: {sqlite_path}"}],
        }

    tables = list_tables(sqlite_path)
    issues: list[dict[str, str]] = []
    if not tables:
        issues.append({"severity": "error", "message": "No tables found in database"})

    return {
        "name": "check_tables",
        "success": len(tables) > 0,
        "table_count": len(tables),
        "tables": tables,
        "issues": issues,
    }


def check_table_columns(db_path: Path | None = None) -> dict[str, Any]:
    sqlite_path = db_path or DEFAULT_DB_PATH
    if not sqlite_path.exists():
        return {
            "name": "check_table_columns",
            "success": False,
            "table_columns": {},
            "issues": [{"severity": "error", "message": f"Database file not found: {sqlite_path}"}],
        }

    table_columns: dict[str, list[str]] = {}
    issues: list[dict[str, str]] = []
    for table_name in list_schema_objects(sqlite_path):
        columns = get_table_columns(sqlite_path, table_name)
        names = [column.get("name", "") for column in columns]
        table_columns[table_name] = names
        if not names:
            issues.append({"severity": "warning", "message": f"Table has no columns: {table_name}"})

    return {
        "name": "check_table_columns",
        "success": len(table_columns) > 0,
        "table_columns": table_columns,
        "issues": issues,
    }


def check_table_row_counts(db_path: Path | None = None) -> dict[str, Any]:
    sqlite_path = db_path or DEFAULT_DB_PATH
    if not sqlite_path.exists():
        return {
            "name": "check_table_row_counts",
            "success": False,
            "row_counts": {},
            "issues": [{"severity": "error", "message": f"Database file not found: {sqlite_path}"}],
        }

    row_counts: dict[str, int] = {}
    samples: dict[str, list[dict[str, Any]]] = {}
    issues: list[dict[str, str]] = []
    for table_name in list_schema_objects(sqlite_path):
        count = get_table_row_count(sqlite_path, table_name)
        row_counts[table_name] = count
        samples[table_name] = get_table_sample(sqlite_path, table_name, limit=3)
        if count == 0:
            issues.append({"severity": "warning", "message": f"Table has zero rows: {table_name}"})

    return {
        "name": "check_table_row_counts",
        "success": len(row_counts) > 0,
        "row_counts": row_counts,
        "sample_rows": samples,
        "issues": issues,
    }


def check_business_table_candidates(db_path: Path | None = None) -> dict[str, Any]:
    sqlite_path = db_path or DEFAULT_DB_PATH
    if not sqlite_path.exists():
        return {
            "name": "check_business_table_candidates",
            "success": False,
            "business_tables": [],
            "system_tables": [],
            "candidates": {},
            "issues": [{"severity": "error", "message": f"Database file not found: {sqlite_path}"}],
        }

    keywords = {
        "sales": ["sales", "売上", "revenue", "請求"],
        "customer": ["customer", "顧客", "得意先", "取引先"],
        "product": ["product", "商品", "item"],
        "amount": ["amount", "金額", "単価", "原価", "price", "total"],
        "date": ["date", "日", "日時", "伝票日", "created", "updated"],
        "code": ["code", "コード", "sku", "id"],
    }

    business_tables: list[str] = []
    system_tables: list[str] = []
    candidates: dict[str, dict[str, list[str]]] = {}
    for table_name in list_schema_objects(sqlite_path):
        if table_name in SYSTEM_TABLE_NAMES:
            system_tables.append(table_name)
            continue

        business_tables.append(table_name)
        columns = [column.get("name", "") for column in get_table_columns(sqlite_path, table_name)]
        lower_map = {name: name.lower() for name in columns}
        categorized: dict[str, list[str]] = {}
        for category, hints in keywords.items():
            matched = [name for name, lower in lower_map.items() if any(hint.lower() in lower for hint in hints)]
            if matched:
                categorized[category] = matched[:10]
        candidates[table_name] = categorized

    issues: list[dict[str, str]] = []
    if not business_tables:
        issues.append({"severity": "error", "message": "No business tables detected"})

    return {
        "name": "check_business_table_candidates",
        "success": len(business_tables) > 0,
        "business_tables": business_tables,
        "system_tables": system_tables,
        "candidates": candidates,
        "issues": issues,
    }
