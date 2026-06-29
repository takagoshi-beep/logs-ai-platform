from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.main import app
from config.settings import reset_settings_cache


def _reset_settings(monkeypatch, **env: str) -> None:
    for key in [
        "GOOGLE_OAUTH_ENABLED",
        "GOOGLE_DRIVE_FOLDER_ID",
        "GOOGLE_CREDENTIALS_PATH",
        "GOOGLE_TOKEN_PATH",
    ]:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    reset_settings_cache()


def test_api_sync_runs_full_flow(tmp_path: Path) -> None:
    db_path = tmp_path / "sqlite" / "logsys.db"
    main.DEFAULT_DB_PATH = db_path

    client = TestClient(app)
    response = client.post("/api/sync", json={"folder_id": "folder-sync-api-001"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "success"
    assert payload["files"] >= 1
    assert payload["tables"] >= 1
    assert payload["rows_imported"] >= 1
    assert payload["validation_status"] in {"ok", "warning", "error"}


def test_api_sync_returns_400_when_folder_id_is_missing(monkeypatch) -> None:
    _reset_settings(monkeypatch, GOOGLE_OAUTH_ENABLED="false", GOOGLE_DRIVE_FOLDER_ID="")
    client = TestClient(app)
    response = client.post("/api/sync", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "folder_id is required"


def test_api_sync_returns_400_when_credentials_are_missing(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "sqlite" / "logsys.db"
    main.DEFAULT_DB_PATH = db_path
    _reset_settings(
        monkeypatch,
        GOOGLE_OAUTH_ENABLED="true",
        GOOGLE_DRIVE_FOLDER_ID="folder-sync-api-cred",
        GOOGLE_CREDENTIALS_PATH=str(tmp_path / "missing-credentials.json"),
        GOOGLE_TOKEN_PATH=str(tmp_path / "missing-token.json"),
    )

    client = TestClient(app)
    response = client.post("/api/sync", json={})

    assert response.status_code == 400
    assert "Google credentials file not found" in response.json()["detail"]


def test_api_sync_returns_400_when_no_target_files(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "sqlite" / "logsys.db"
    main.DEFAULT_DB_PATH = db_path
    _reset_settings(monkeypatch, GOOGLE_OAUTH_ENABLED="false", GOOGLE_DRIVE_FOLDER_ID="folder-sync-api-empty")

    monkeypatch.setattr(main, "sync_google_drive_to_storage", lambda **_kwargs: {"status": "error", "errors": ["No target Excel or Spreadsheet files found in the specified folder"]})

    client = TestClient(app)
    response = client.post("/api/sync", json={"folder_id": "folder-sync-api-empty"})

    assert response.status_code == 400
    assert response.json()["detail"]["errors"]


def test_api_sync_returns_400_when_validation_fails(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "sqlite" / "logsys.db"
    main.DEFAULT_DB_PATH = db_path
    _reset_settings(monkeypatch, GOOGLE_OAUTH_ENABLED="false", GOOGLE_DRIVE_FOLDER_ID="folder-sync-api-validation")

    monkeypatch.setattr(main, "validate_synced_storage", lambda _db_path: {"status": "error", "issues": [{"severity": "error", "message": "simulated validation failure"}]})

    client = TestClient(app)
    response = client.post("/api/sync", json={"folder_id": "folder-sync-api-validation"})

    assert response.status_code == 400
    assert response.json()["detail"]["errors"]


def test_api_catalog_returns_storage_items(tmp_path: Path) -> None:
    db_path = tmp_path / "sqlite" / "logsys.db"
    main.DEFAULT_DB_PATH = db_path

    client = TestClient(app)
    sync_response = client.post("/api/sync", json={"folder_id": "folder-sync-api-002"})
    assert sync_response.status_code == 200

    catalog_response = client.get("/api/catalog")
    assert catalog_response.status_code == 200
    payload = catalog_response.json()

    assert payload["count"] >= 1
    item = payload["items"][0]
    assert "table_name" in item
    assert "sheet_name" in item
    assert "row_count" in item
    assert "source_file" in item
    assert "imported_at" in item


def test_api_sync_status_returns_latest_sync_state(tmp_path: Path) -> None:
    db_path = tmp_path / "sqlite" / "logsys.db"
    main.DEFAULT_DB_PATH = db_path

    client = TestClient(app)
    sync_response = client.post("/api/sync", json={"folder_id": "folder-sync-api-003"})
    assert sync_response.status_code == 200

    status_response = client.get("/api/sync/status")
    assert status_response.status_code == 200
    payload = status_response.json()

    assert payload["last_synced_at"]
    assert payload["files_processed"] >= 1
    assert payload["rows_imported"] >= 1
    assert payload["validation_status"] in {"ok", "warning", "error", "unknown", "not_synced"}
    assert isinstance(payload["errors"], list)


def test_api_chat_alias_accepts_question_payload(tmp_path: Path) -> None:
    db_path = tmp_path / "sqlite" / "logsys.db"
    main.DEFAULT_DB_PATH = db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    from storage.sqlite import SQLiteRepository

    repository = SQLiteRepository(db_path)
    repository.execute_query("CREATE TABLE sales (id INTEGER PRIMARY KEY, customer TEXT, amount REAL)")
    repository.execute_query("INSERT INTO sales (customer, amount) VALUES (?, ?)", ("Acme", 100.0))
    repository.close()

    client = TestClient(app)
    response = client.post("/api/chat", json={"question": "売上トップ10は？"})

    assert response.status_code == 200
    assert response.json()["success"] is True
