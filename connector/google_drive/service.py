from __future__ import annotations

from typing import Any

from connector.base import BaseConnector
from connector.models import ConnectorFile
from connector.google_drive.client import EXCEL_MIME_TYPES, SPREADSHEET_MIME_TYPE, GoogleDriveClient
from connector.google_drive.config import GoogleDriveConfig, build_google_drive_config
from connector.google_drive.models import GoogleDriveFetchResult, GoogleDriveFile

ALLOWED_TARGET_FOLDER_TYPES = {"logsys", "sales", "unknown"}


class GoogleDriveService:
    def __init__(self, client: GoogleDriveClient, config: GoogleDriveConfig) -> None:
        self.client = client
        self.config = config

    def fetch_folder_files(self, folder_id: str | None = None) -> GoogleDriveFetchResult:
        active_folder = folder_id or self.config.folder_id or "mock-folder-id"
        raw_files = self.client.list_files(active_folder)

        excel_files = [item for item in raw_files if item.mime_type in EXCEL_MIME_TYPES]
        spreadsheet_files = [item for item in raw_files if item.mime_type == SPREADSHEET_MIME_TYPE]

        return GoogleDriveFetchResult(
            folder_id=active_folder,
            excel_files=excel_files,
            spreadsheet_files=spreadsheet_files,
        )


class GoogleDriveConnector(BaseConnector):
    def __init__(
        self,
        folder_id: str = "",
        target_folder_type: str = "unknown",
        enabled: bool = True,
        client: GoogleDriveClient | None = None,
        service: GoogleDriveService | None = None,
    ) -> None:
        normalized_target = target_folder_type if target_folder_type in ALLOWED_TARGET_FOLDER_TYPES else "unknown"
        self.folder_id = folder_id
        self.target_folder_type = normalized_target
        self.enabled = enabled

        config = build_google_drive_config(folder_id=folder_id)
        self.client = client or GoogleDriveClient(
            credentials_path=config.credentials_path,
            token_path=config.token_path,
            use_mock_auth=config.use_mock_auth,
            scopes=config.scopes,
        )
        self.service = service or GoogleDriveService(self.client, config)

    @staticmethod
    def _to_connector_file(item: GoogleDriveFile, target_folder_type: str) -> ConnectorFile:
        metadata = dict(item.metadata)
        metadata.setdefault("folder_id", item.folder_id)
        metadata.setdefault("target_folder_type", target_folder_type)
        if item.mime_type in EXCEL_MIME_TYPES:
            metadata.setdefault("data_category", "logsys")
        elif item.mime_type == SPREADSHEET_MIME_TYPE:
            metadata.setdefault("data_category", "spreadsheet")

        return ConnectorFile(
            source=item.source,
            file_id=item.file_id,
            name=item.name,
            mime_type=item.mime_type,
            modified_at=item.modified_at,
            path=item.path,
            metadata=metadata,
        )

    def list_files(self, folder_id: str | None = None, mime_types: list[str] | None = None) -> list[ConnectorFile]:
        if not self.enabled:
            return []

        result = self.service.fetch_folder_files(folder_id=folder_id or self.folder_id)
        files = [
            self._to_connector_file(item, self.target_folder_type)
            for item in result.files
            if item.mime_type in EXCEL_MIME_TYPES or item.mime_type == SPREADSHEET_MIME_TYPE
        ]

        if mime_types:
            return [item for item in files if item.mime_type in mime_types]
        return files

    def list_excel_files(self, folder_id: str | None = None) -> list[ConnectorFile]:
        return self.list_files(folder_id=folder_id, mime_types=sorted(EXCEL_MIME_TYPES))

    def list_spreadsheet_files(self, folder_id: str | None = None) -> list[ConnectorFile]:
        return self.list_files(folder_id=folder_id, mime_types=[SPREADSHEET_MIME_TYPE])

    def list_target_files(self, target_type: str) -> list[ConnectorFile]:
        normalized = target_type if target_type in ALLOWED_TARGET_FOLDER_TYPES else "unknown"
        files = self.list_files(folder_id=self.folder_id)
        if normalized == "unknown":
            return files
        return [
            item
            for item in files
            if str(item.metadata.get("data_category", "unknown")) in {normalized, "unknown", "spreadsheet"}
        ]

    def read_file(self, file_id: str) -> bytes:
        if not self.enabled:
            raise RuntimeError("Google Drive connector is disabled")
        return self.client.download_file(file_id)

    def get_metadata(self, file_id: str) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Google Drive connector is disabled")

        return {
            "source": "google_drive",
            "file_id": file_id,
            "folder_id": self.folder_id,
            "target_folder_type": self.target_folder_type,
            "placeholder": True,
            "api_ready": False,
        }
