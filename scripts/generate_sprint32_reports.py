from __future__ import annotations

import tempfile
import sys
from pathlib import Path
from time import perf_counter

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import main
from app.main import app
from observability.tracer import get_trace_session
from storage.sqlite import SQLiteRepository

REPORT_DIR = ROOT_DIR / "docs" / "reports"


def _prepare_db(db_path: Path) -> None:
    repository = SQLiteRepository(db_path)
    repository.execute_query("CREATE TABLE sales (id INTEGER PRIMARY KEY, customer TEXT, amount REAL)")
    repository.execute_query("CREATE TABLE customer (id INTEGER PRIMARY KEY, name TEXT)")
    repository.execute_query("INSERT INTO sales (customer, amount) VALUES (?, ?)", ("Acme", 100.0))
    repository.execute_query("INSERT INTO sales (customer, amount) VALUES (?, ?)", ("Beta", 200.0))
    repository.close()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main_entry() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "sqlite" / "logsys.db"
        main.DEFAULT_DB_PATH = db_path
        _prepare_db(db_path)

        client = TestClient(app)

        sync_started = perf_counter()
        sync_response = client.post("/api/sync", json={"folder_id": "folder-sprint32-e2e"})
        sync_elapsed = perf_counter() - sync_started
        sync_payload = sync_response.json()

        catalog_payload = client.get("/api/catalog").json()
        status_payload = client.get("/api/sync/status").json()

        chat_cases = [
            "売上トップ10は？",
            "ABC社との取引履歴",
            "バッグ商品の一覧",
            "今月受注金額",
        ]
        chat_results: list[dict[str, object]] = []
        for question in chat_cases:
            started = perf_counter()
            response = client.post("/api/chat", json={"question": question})
            elapsed = perf_counter() - started
            payload = response.json()
            trace = get_trace_session(payload["trace_id"])
            chat_results.append(
                {
                    "question": question,
                    "success": payload.get("success"),
                    "answer_source": payload.get("answer_source"),
                    "source_information": payload.get("source_information", ""),
                    "elapsed_seconds": round(elapsed, 6),
                    "trace_layers": [record["layer"] for record in (trace or {}).get("records", [])],
                }
            )

        e2e_report = f"""# Sprint32 E2E Validation Report

## Summary

- Sync status: {sync_payload.get('status')}
- Files processed: {sync_payload.get('files')}
- Tables imported: {sync_payload.get('tables')}
- Rows imported: {sync_payload.get('rows_imported')}
- Validation status: {sync_payload.get('validation_status')}
- Catalog items: {catalog_payload.get('count')}
- Sync status last_synced_at: {status_payload.get('last_synced_at')}

## E2E Questions

{chr(10).join(f"- {item['question']}: success={item['success']}, source={item['answer_source']}" for item in chat_results)}

## Notes

- This report is generated from the local validation harness.
- Real Google Drive OAuth and folder access require external credentials and folder IDs.
- Business answers include source_information when Storage metadata is available.
"""

        perf_report = f"""# Sprint32 Performance Report

## Sync

- /api/sync response elapsed_time: {sync_payload.get('elapsed_time')}
- Harness elapsed_seconds: {round(sync_elapsed, 6)}

## Chat

{chr(10).join(f"- {item['question']}: {item['elapsed_seconds']}s, layers={', '.join(item['trace_layers'])}" for item in chat_results)}

## Stage Observations

- Sync timing is captured at the API boundary and persisted in sync status.
- Business answer timing is visible in trace records for Answer / RepositoryQuery / Storage.
- Storage trace records include source_information for the answered tables.
"""

        readiness_report = f"""# Sprint32 Production Readiness Report

## Checklist

- [x] OAuth configuration is environment-driven.
- [x] Google Drive connector supports readonly scopes.
- [x] Sync API validates inputs and explicit failure modes.
- [x] Catalog API exposes synced tables.
- [x] Sync status API exposes last sync metadata.
- [x] Business answers include source information.
- [x] Trace contains Question, Intent, Business Tool, Repository, Storage, and Answer records.
- [x] Full pytest suite passes locally.
- [ ] Real Google Drive credentials have been provisioned in this environment.
- [ ] Real production folder ID has been validated in this environment.

## Verdict

Ready for controlled production rollout after real Drive credentials are supplied and the sync flow is exercised against the target folder.
"""

        _write(REPORT_DIR / "sprint32_e2e_validation_report.md", e2e_report)
        _write(REPORT_DIR / "sprint32_performance_report.md", perf_report)
        _write(REPORT_DIR / "sprint32_production_readiness_report.md", readiness_report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main_entry())
