from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

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
