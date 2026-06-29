from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ingestion.google_drive_importer import get_storage_catalog
from validation.checks import (
    check_business_table_candidates,
    check_excel_files,
    check_sqlite_database,
    check_table_columns,
    check_table_row_counts,
    check_tables,
)


def _flatten_issues(check_results: list[dict[str, Any]]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for result in check_results:
        for issue in result.get("issues", []) or []:
            issues.append(
                {
                    "check": str(result.get("name", "unknown")),
                    "severity": str(issue.get("severity", "warning")),
                    "message": str(issue.get("message", "")),
                }
            )
    return issues


def run_validation() -> dict[str, Any]:
    checks = [
        check_excel_files(),
        check_sqlite_database(),
        check_tables(),
        check_table_columns(),
        check_table_row_counts(),
        check_business_table_candidates(),
    ]

    issues = _flatten_issues(checks)
    error_count = sum(1 for item in issues if item["severity"] == "error")
    warning_count = sum(1 for item in issues if item["severity"] == "warning")

    score = max(0, 100 - (error_count * 25) - (warning_count * 10))
    status = "ok"
    if error_count > 0:
        status = "error"
    elif warning_count > 0:
        status = "warning"

    return {
        "success": status != "error",
        "status": status,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "score": score,
        "issues": issues,
        "summary": {
            "checks": checks,
            "check_count": len(checks),
            "passed_count": sum(1 for item in checks if item.get("success")),
            "error_count": error_count,
            "warning_count": warning_count,
        },
    }


def validate_synced_storage(db_path: Path) -> dict[str, Any]:
    catalog = get_storage_catalog(db_path)
    issues: list[dict[str, str]] = []

    if not catalog:
        issues.append({"severity": "error", "message": "No synced tables were found in storage catalog"})

    zero_rows = [item for item in catalog if int(item.get("row_count") or 0) <= 0]
    for item in zero_rows:
        issues.append(
            {
                "severity": "error",
                "message": f"Synced table has zero rows: {item.get('table_name')} ({item.get('source_file')})",
            }
        )

    error_count = sum(1 for item in issues if item["severity"] == "error")
    warning_count = sum(1 for item in issues if item["severity"] == "warning")
    status = "ok" if error_count == 0 else "error"

    return {
        "success": status != "error",
        "status": status,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "score": max(0, 100 - (error_count * 30) - (warning_count * 10)),
        "issues": issues,
        "summary": {
            "checks": [
                {
                    "name": "validate_synced_storage",
                    "success": status != "error",
                    "synced_table_count": len(catalog),
                    "issues": issues,
                }
            ],
            "check_count": 1,
            "passed_count": 1 if status != "error" else 0,
            "error_count": error_count,
            "warning_count": warning_count,
        },
    }
