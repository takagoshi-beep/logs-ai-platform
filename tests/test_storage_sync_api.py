from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.main import app
from observability.tracer import get_trace_session


def test_storage_sync_api_returns_expected_payload(tmp_path: Path) -> None:
    db_path = tmp_path / "sqlite" / "logsys.db"
    main.DEFAULT_DB_PATH = db_path

    client = TestClient(app)
    response = client.post("/storage/sync", json={"folder_id": "folder-api-001"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["files"] >= 1
    assert payload["tables"] >= 1
    assert payload["folder_id"] == "folder-api-001"
    assert payload["trace_id"]


def test_storage_sync_trace_contains_required_fields(tmp_path: Path) -> None:
    db_path = tmp_path / "sqlite" / "logsys.db"
    main.DEFAULT_DB_PATH = db_path

    client = TestClient(app)
    response = client.post("/storage/sync", json={"folder_id": "folder-api-002"})
    payload = response.json()

    trace = get_trace_session(payload["trace_id"])
    assert trace is not None
    records = [item for item in trace["records"] if item["layer"] == "StorageSync"]
    assert records

    output = records[0]["output"]
    assert output["sync_time"]
    assert output["folder_id"] == "folder-api-002"
    assert output["files"] >= 1
    assert output["table_count"] >= 1
    assert float(output["elapsed_time"]) >= 0.0
