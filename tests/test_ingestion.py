from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from ingestion.models import IngestionJob
from ingestion.sync import sync_source


def test_sync_source_returns_ingestion_job() -> None:
    job = sync_source("google_drive")
    assert isinstance(job, IngestionJob)
    assert job.source == "google_drive"


def test_sync_source_unknown_source_raises_error() -> None:
    with pytest.raises(ValueError):
        sync_source("unknown_source")


def test_ingestion_sync_endpoint_returns_200() -> None:
    client = TestClient(app)
    response = client.post("/ingestion/sync/google_drive")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["job"]["source"] == "google_drive"