from __future__ import annotations

from connector.google_drive import GoogleDriveConnector
from connector.google_sheets import GoogleSheetsConnector


def test_google_drive_connector_accepts_folder_id() -> None:
    connector = GoogleDriveConnector(folder_id="folder-123", target_folder_type="logsys")
    assert connector.folder_id == "folder-123"


def test_google_drive_list_target_files_logsys() -> None:
    connector = GoogleDriveConnector(folder_id="folder-123", target_folder_type="logsys")
    files = connector.list_target_files("logsys")
    assert files


def test_google_drive_list_target_files_sales() -> None:
    connector = GoogleDriveConnector(folder_id="folder-456", target_folder_type="sales")
    files = connector.list_target_files("sales")
    assert files


def test_google_sheets_connector_accepts_spreadsheet_id() -> None:
    connector = GoogleSheetsConnector(spreadsheet_id="spreadsheet-123")
    assert connector.spreadsheet_id == "spreadsheet-123"


def test_google_sheets_list_sheets_returns_mock() -> None:
    connector = GoogleSheetsConnector(spreadsheet_id="spreadsheet-123")
    sheets = connector.list_sheets("spreadsheet-123")
    assert sheets
    assert sheets[0]["spreadsheet_id"] == "spreadsheet-123"


def test_google_sheets_read_sheet_returns_mock() -> None:
    connector = GoogleSheetsConnector(spreadsheet_id="spreadsheet-123")
    data = connector.read_sheet("spreadsheet-123", "Sales")
    assert data["spreadsheet_id"] == "spreadsheet-123"
    assert data["sheet_name"] == "Sales"
    assert data["rows"]
