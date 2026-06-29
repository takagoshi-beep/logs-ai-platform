from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import main
from app.main import app
from observability.tracer import get_trace_session
from storage.sqlite import SQLiteRepository


REPORT_PATH = ROOT_DIR / "docs" / "reports" / "v1_0_rc1_report.md"


def _prepare_db(db_path: Path) -> None:
    repository = SQLiteRepository(db_path)
    repository.execute_query("CREATE TABLE sales (id INTEGER PRIMARY KEY, customer TEXT, amount REAL)")
    repository.execute_query("INSERT INTO sales (customer, amount) VALUES (?, ?)", ("Acme", 100.0))
    repository.execute_query("INSERT INTO sales (customer, amount) VALUES (?, ?)", ("Beta", 200.0))
    repository.close()


def build_report() -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "sqlite" / "logsys.db"
        main.DEFAULT_DB_PATH = db_path
        _prepare_db(db_path)

        client = TestClient(app)
        sync_response = client.post("/api/sync", json={"folder_id": "folder-rc1"})
        explain_response = client.post("/api/explain", json={"question": "売上トップ10は？"})
        chat_response = client.post("/chat", json={"message": "売上トップ10は？"})
        trace = get_trace_session(chat_response.json()["trace_id"])
        trace_layers = [record["layer"] for record in (trace or {}).get("records", [])]

        system_health = client.get("/system/health").json()
        system_info = client.get("/system/info").json()
        system_manifest = client.get("/system/manifest").json()
        system_diagnostics = client.get("/system/diagnostics").json()

        report = f"""# LOGS AI OS v1.0 RC1 Report

## Summary

- Version: {system_info.get('version')}
- Environment: {system_info.get('environment')}
- System health: {system_health.get('status')}
- Sync status: {sync_response.status_code}

## System Operations

- Health: {system_health}
- Info: {system_info}
- Manifest: {system_manifest}
- Diagnostics: {system_diagnostics}

## Explain

- Question: {explain_response.json().get('question')}
- Selected tool: {explain_response.json().get('selected_business_tool', {}).get('selected_tool')}
- Source information present: {bool(explain_response.json().get('source_information'))}

## Trace

- Layers: {', '.join(trace_layers)}

## Verdict

- RC1 APIs are available locally.
- Real Google Drive validation remains environment-dependent.
"""
        return report


def main_entry() -> int:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(build_report(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_entry())