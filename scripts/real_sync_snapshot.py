from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import load_settings
from connector.google_drive import GoogleDriveClient
from connector.google_drive.client import EXCEL_MIME_TYPES, SPREADSHEET_MIME_TYPE
from ingestion.google_drive_importer import (
    get_storage_catalog,
    get_sync_status,
    sync_google_drive_to_storage,
    update_sync_status,
)
from validation.report import save_validation_report
from validation.runner import validate_synced_storage


LOG_PATH = ROOT_DIR / "tmp_real_sync_progress.log"


def _log(message: str) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as fp:
        fp.write(message + "\n")


def main() -> int:
    LOG_PATH.write_text("", encoding="utf-8")
    _log("start")
    settings = load_settings("dev")
    folder_id = settings.google_drive_folder_id
    _log(f"folder_id={folder_id}")

    client = GoogleDriveClient(
        credentials_path=settings.google_credentials_path,
        token_path=settings.google_token_path,
        use_mock_auth=False,
    )
    _log("authenticating")
    client.authenticate()
    _log("authenticated")
    _log("listing_raw_files")
    raw = [
        {
            "id": item.file_id,
            "name": item.name,
            "mimeType": item.mime_type,
            "modifiedTime": item.modified_at,
        }
        for item in client.list_files(folder_id)
    ]
    _log(f"raw_files={len(raw)}")

    target = [
        item for item in raw if item.get("mimeType") in EXCEL_MIME_TYPES or item.get("mimeType") == SPREADSHEET_MIME_TYPE
    ]
    skipped = [
        item for item in raw if item.get("mimeType") not in EXCEL_MIME_TYPES and item.get("mimeType") != SPREADSHEET_MIME_TYPE
    ]
    _log(f"target_files={len(target)}")
    _log(f"skipped_files={len(skipped)}")

    _log("running_importer_sync")

    def progress(stage: str, details: dict[str, object]) -> None:
        suffix = " ".join(f"{key}={value}" for key, value in details.items())
        _log(f"{stage}{(': ' + suffix) if suffix else ''}")

    sync_result = sync_google_drive_to_storage(
        folder_id=folder_id,
        db_path=settings.db_path,
        progress_callback=progress,
    )

    _log(f"sync_result_status={sync_result.get('status')}")
    _log("running_validate_synced_storage")
    validation_report = validate_synced_storage(settings.db_path)
    _log(f"validation_status={validation_report.get('status')}")
    _log("saving_validation_report")
    save_validation_report(validation_report)
    _log("updating_sync_status")
    update_sync_status(
        db_path=settings.db_path,
        last_synced_at=str(sync_result.get("sync_time") or ""),
        files_processed=int(sync_result.get("files", 0)),
        rows_imported=int(sync_result.get("rows_imported", 0)),
        validation_status=str(validation_report.get("status") or "unknown"),
        errors=[str(item) for item in sync_result.get("errors", [])],
    )
    _log("reading_catalog")
    catalog = get_storage_catalog(settings.db_path)
    _log(f"catalog_count={len(catalog)}")
    _log("reading_sync_status")
    status = get_sync_status(settings.db_path)

    payload = {
        "folder_id": folder_id,
        "raw_files_total": len(raw),
        "target_files_total": len(target),
        "skipped_files_total": len(skipped),
        "raw_files": raw,
        "skipped_files": skipped,
        "sync": sync_result,
        "validation": validation_report,
        "catalog": {"count": len(catalog), "items": catalog},
        "status": status,
    }
    _log("done")
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())