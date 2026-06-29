from __future__ import annotations

from connector.google_drive import GoogleDriveClient, GoogleDriveConfig, GoogleDriveConnector, GoogleDriveService
from connector.google_drive.config import GOOGLE_OAUTH_SCOPES


def test_google_drive_client_authenticate_mock() -> None:
    client = GoogleDriveClient(use_mock_auth=True)
    auth = client.authenticate()
    assert auth["status"] == "authenticated"
    assert auth["mock"] is True


def test_google_drive_service_fetches_excel_and_spreadsheet() -> None:
    client = GoogleDriveClient(use_mock_auth=True)
    service = GoogleDriveService(
        client,
        GoogleDriveConfig(
            folder_id="folder-001",
            credentials_path="credentials.json",
            token_path="token.json",
            scopes=list(GOOGLE_OAUTH_SCOPES),
            oauth_enabled=False,
        ),
    )
    result = service.fetch_folder_files()
    assert result.folder_id == "folder-001"
    assert result.excel_files
    assert result.spreadsheet_files


def test_google_drive_connector_lists_files_by_type() -> None:
    connector = GoogleDriveConnector(folder_id="folder-001")
    excel_files = connector.list_excel_files()
    spreadsheet_files = connector.list_spreadsheet_files()
    assert excel_files
    assert spreadsheet_files
    assert all(item.source == "google_drive" for item in [*excel_files, *spreadsheet_files])


def test_google_drive_connector_skips_non_target_files() -> None:
    connector = GoogleDriveConnector(folder_id="folder-001")
    files = connector.list_files()
    assert files
    assert all(item.mime_type != "application/pdf" for item in files)
