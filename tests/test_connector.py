from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from connector.google_drive import GoogleDriveConnector
from connector.google_sheets import GoogleSheetsConnector
from connector.registry import ConnectorRegistry


def test_connector_registry_registers_connector() -> None:
    registry = ConnectorRegistry()
    registry.register_connector("google_drive", GoogleDriveConnector())
    assert "google_drive" in registry.list_connectors()


def test_google_drive_connector_returns_files() -> None:
    connector = GoogleDriveConnector()
    files = connector.list_files()
    assert files
    assert files[0].source == "google_drive"


def test_google_sheets_connector_exists() -> None:
    connector = GoogleSheetsConnector()
    assert connector is not None


def test_connectors_endpoint_returns_200() -> None:
    client = TestClient(app)
    response = client.get("/connectors")
    assert response.status_code == 200
    payload = response.json()
    assert "connectors" in payload
