from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from ingestion.source_registry import get_default_source_registry
from ingestion.sync import sync_source


def test_default_sources_are_listed() -> None:
    registry = get_default_source_registry()
    sources = registry.list_sources()
    assert sources


def test_logsys_sources_exist() -> None:
    registry = get_default_source_registry()
    source_ids = [item.source_id for item in registry.list_sources()]
    assert "logsys_excel" in source_ids
    assert "logsys_spreadsheet" in source_ids


def test_sales_sources_exist() -> None:
    registry = get_default_source_registry()
    source_ids = [item.source_id for item in registry.list_sources()]
    assert "sales_management_spreadsheet" in source_ids


def test_sources_can_be_filtered_by_category() -> None:
    registry = get_default_source_registry()
    sales_sources = registry.list_sources_by_category("sales")
    assert sales_sources
    assert all(item.data_category == "sales" for item in sales_sources)


def test_unknown_source_raises_error() -> None:
    with pytest.raises(ValueError):
        sync_source("unknown_source")


def test_sync_source_uses_source_registry() -> None:
    job = sync_source("logsys_excel")
    assert job.source_id == "logsys_excel"
    assert isinstance(job.file_metadata, list)


def test_ingestion_sources_endpoint_returns_200() -> None:
    client = TestClient(app)
    response = client.get("/ingestion/sources")
    assert response.status_code == 200
    payload = response.json()
    assert "sources" in payload
