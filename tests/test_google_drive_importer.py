from __future__ import annotations

from pathlib import Path

from connector.google_drive import GoogleDriveConnector
from ingestion.google_drive_importer import sync_google_drive_to_storage
from storage.sqlite import SQLiteRepository


def test_google_drive_importer_updates_storage(tmp_path: Path) -> None:
    db_path = tmp_path / "sqlite" / "logsys.db"
    result = sync_google_drive_to_storage(folder_id="folder-sync-001", db_path=db_path)

    assert result["status"] == "success"
    assert result["files"] >= 1
    assert result["excel_files"] >= 1
    assert result["spreadsheet_files"] >= 1
    assert result["storage_mode"] == "replace"


def test_google_drive_importer_full_replace(tmp_path: Path) -> None:
    db_path = tmp_path / "sqlite" / "logsys.db"
    connector = GoogleDriveConnector(folder_id="folder-sync-002")

    first = sync_google_drive_to_storage(folder_id="folder-sync-002", db_path=db_path, connector=connector)
    repository = SQLiteRepository(db_path)
    repository.execute_query(
        "INSERT OR REPLACE INTO gdrive_excel_files (file_id, name, mime_type, modified_at, path, folder_id, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "manual-extra",
            "manual-extra.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "2026-01-01T00:00:00+00:00",
            "/drive/folder-sync-002/manual-extra.xlsx",
            "folder-sync-002",
            "{}",
        ),
    )
    row_with_manual = repository.get_table_row_count("gdrive_excel_files")
    assert row_with_manual > int(first["excel_files"])

    second = sync_google_drive_to_storage(folder_id="folder-sync-002", db_path=db_path, connector=connector)
    row_after_replace = repository.get_table_row_count("gdrive_excel_files")
    repository.close()

    assert row_after_replace == int(second["excel_files"])


def test_google_drive_importer_repository_tables_exist(tmp_path: Path) -> None:
    db_path = tmp_path / "sqlite" / "logsys.db"
    sync_google_drive_to_storage(folder_id="folder-sync-003", db_path=db_path)

    repository = SQLiteRepository(db_path)
    tables = {item["table_name"] for item in repository.get_tables()}
    repository.close()

    assert "gdrive_excel_files" in tables
    assert "gdrive_spreadsheet_files" in tables
    assert "gdrive_sync_registry" in tables
