from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.main import app


def _prepare_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "sqlite" / "logsys.db"
    main.DEFAULT_DB_PATH = db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    from storage.sqlite import SQLiteRepository

    repository = SQLiteRepository(db_path)
    repository.execute_query("CREATE TABLE sales (id INTEGER PRIMARY KEY, customer TEXT, amount REAL)")
    repository.execute_query("INSERT INTO sales (customer, amount) VALUES (?, ?)", ("Acme", 100.0))
    repository.close()
    return db_path


def test_system_operations_endpoints_return_counts(tmp_path: Path) -> None:
    _prepare_db(tmp_path)
    client = TestClient(app)

    health = client.get("/system/health")
    info = client.get("/system/info")
    manifest = client.get("/system/manifest")
    diagnostics = client.get("/system/diagnostics")

    assert health.status_code == 200
    assert info.status_code == 200
    assert manifest.status_code == 200
    assert diagnostics.status_code == 200

    health_payload = health.json()
    info_payload = info.json()
    manifest_payload = manifest.json()
    diagnostics_payload = diagnostics.json()

    assert health_payload["version"] == "v1.0.0-RC1"
    assert "database" in health_payload
    assert info_payload["business_tools_count"] > 0
    assert info_payload["repositories_count"] >= 1
    assert "metric_count" in info_payload
    assert "last_sync_at" in manifest_payload
    assert "files" in manifest_payload
    assert set(diagnostics_payload.keys()) == {
        "connector_status",
        "validation_status",
        "storage_status",
        "business_status",
        "semantic_status",
        "authorization_status",
    }