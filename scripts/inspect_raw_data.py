from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from validation.checks import (
    check_business_table_candidates,
    check_excel_files,
    check_sqlite_database,
    check_table_columns,
    check_table_row_counts,
    check_tables,
)
from validation.runner import run_validation


def main() -> int:
    validation = run_validation()
    excel_check = check_excel_files()
    sqlite_check = check_sqlite_database()
    table_check = check_tables()
    column_check = check_table_columns()
    row_check = check_table_row_counts()
    candidate_check = check_business_table_candidates()

    print(f"Validation status: {validation['status']} score={validation['score']}")
    print(f"Checked at: {validation['checked_at']}")
    print(f"Excel files: {', '.join(excel_check.get('excel_files', []))}")
    print(f"SQLite DB: {sqlite_check.get('db_path')}")
    print(f"Table count: {table_check.get('table_count', 0)}")

    table_columns = column_check.get("table_columns", {})
    row_counts = row_check.get("row_counts", {})
    sample_rows = row_check.get("sample_rows", {})
    candidates = candidate_check.get("candidates", {})

    for item in table_check.get("tables", []):
        table_name = item.get("table_name", "")
        print(f"- {table_name} rows={row_counts.get(table_name, 0)}")
        print(f"  columns: {', '.join(table_columns.get(table_name, []))}")
        print(f"  sample3: {sample_rows.get(table_name, [])[:3]}")
        if candidates.get(table_name):
            categorized = []
            for category, names in candidates.get(table_name, {}).items():
                categorized.append(f"{category}=[{', '.join(names[:8])}]")
            print(f"  likely business columns: {'; '.join(categorized)}")

    if validation.get("issues"):
        print("Issues:")
        for issue in validation["issues"]:
            print(f"- [{issue['severity']}] {issue['check']}: {issue['message']}")

    return 0 if validation["status"] in {"ok", "warning"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
