from __future__ import annotations

from config.settings import AppSettings, get_settings
from connector.base import BaseConnector
from connector.google_drive import GoogleDriveConnector
from connector.google_sheets import GoogleSheetsConnector


class ConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, BaseConnector] = {}

    def register_connector(self, name: str, connector: BaseConnector) -> None:
        self._connectors[name] = connector

    def get_connector(self, name: str) -> BaseConnector:
        try:
            return self._connectors[name]
        except KeyError as exc:
            raise KeyError(f"Connector not found: {name}") from exc

    def list_connectors(self) -> list[str]:
        return sorted(self._connectors.keys())


def create_default_connector_registry(settings: AppSettings | None = None) -> ConnectorRegistry:
    active_settings = settings or get_settings()
    registry = ConnectorRegistry()

    registry.register_connector(
        "google_drive",
        GoogleDriveConnector(
            folder_id=active_settings.google_drive_logsys_folder_id,
            target_folder_type="logsys",
            enabled=active_settings.google_drive_enabled,
        ),
    )
    registry.register_connector(
        "google_sheets",
        GoogleSheetsConnector(enabled=active_settings.google_sheets_enabled),
    )
    return registry


_DEFAULT_CONNECTOR_REGISTRY: ConnectorRegistry | None = None


def get_default_connector_registry() -> ConnectorRegistry:
    global _DEFAULT_CONNECTOR_REGISTRY
    if _DEFAULT_CONNECTOR_REGISTRY is None:
        _DEFAULT_CONNECTOR_REGISTRY = create_default_connector_registry()
    return _DEFAULT_CONNECTOR_REGISTRY
