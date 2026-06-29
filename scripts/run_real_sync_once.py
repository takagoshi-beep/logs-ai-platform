from __future__ import annotations

import json
import sys
from time import perf_counter
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import load_settings
from ingestion.google_drive_importer import (
    get_storage_catalog,
    get_sync_status,
    sync_google_drive_to_storage,
    update_sync_status,
)
from storage.sqlite import SQLiteRepository
from validation.report import save_validation_report
from validation.runner import validate_synced_storage


def main() -> int:
    settings = load_settings("dev")
    started = perf_counter()

    sync_result = sync_google_drive_to_storage(
        folder_id=settings.google_drive_folder_id,
        db_path=settings.db_path,
    )
    validation_report = validate_synced_storage(settings.db_path)
    save_validation_report(validation_report)
    update_sync_status(
        db_path=settings.db_path,
        last_synced_at=str(sync_result.get("sync_time") or ""),
        files_processed=int(sync_result.get("files", 0)),
        rows_imported=int(sync_result.get("rows_imported", 0)),
        validation_status=str(validation_report.get("status") or "unknown"),
        errors=[str(item) for item in sync_result.get("errors", [])],
    )

    catalog = get_storage_catalog(settings.db_path)
    status = get_sync_status(settings.db_path)

    with SQLiteRepository(settings.db_path) as repository:
        tables = [item.get("table_name") for item in repository.get_tables()]

    payload = {
        "sync_status": sync_result.get("status"),
        "imported_files": int(sync_result.get("files", 0)),
        "imported_sheets": int(sync_result.get("tables_imported", 0)),
        "imported_rows": int(sync_result.get("rows_imported", 0)),
        "excel_files": int(sync_result.get("excel_files", 0)),
        "spreadsheet_files": int(sync_result.get("spreadsheet_files", 0)),
        "sync_errors": [str(item) for item in sync_result.get("errors", [])],
        "validation_status": str(validation_report.get("status") or "unknown"),
        "validation_issue_count": len(validation_report.get("issues", [])),
        "catalog_entries": len(catalog),
        "storage_tables": [str(name) for name in tables if name],
        "status": status,
        "execution_time_seconds": round(perf_counter() - started, 3),
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
