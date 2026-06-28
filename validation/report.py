from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_PATH = ROOT_DIR / "data" / "validation" / "reports.jsonl"


def _report_path() -> Path:
    configured = (os.getenv("VALIDATION_REPORT_PATH") or "").strip()
    if configured:
        return Path(configured)
    return DEFAULT_REPORT_PATH


def _ensure_report_file() -> Path:
    path = _report_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")
    return path


def _load_reports() -> list[dict[str, Any]]:
    path = _ensure_report_file()
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            text = line.strip()
            if not text:
                continue
            try:
                item = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows


def save_validation_report(report: dict) -> str:
    item = dict(report or {})
    report_id = str(item.get("report_id") or f"validation-{uuid4()}")
    item["report_id"] = report_id
    item["saved_at"] = item.get("saved_at") or datetime.now(timezone.utc).isoformat()

    path = _ensure_report_file()
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(item, ensure_ascii=False) + "\n")
    return report_id


def get_latest_validation_report() -> dict[str, Any] | None:
    rows = _load_reports()
    if not rows:
        return None
    return rows[-1]


def list_validation_reports(limit: int = 20) -> list[dict[str, Any]]:
    rows = list(reversed(_load_reports()))
    return rows[: max(0, limit)]
