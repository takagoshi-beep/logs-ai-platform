from __future__ import annotations

import json
import os
from pathlib import Path

from config.settings import load_settings, reset_settings_cache
from ingestion.google_drive_importer import (
    get_storage_catalog,
    sync_google_drive_to_storage,
    update_sync_status,
)
from validation.runner import validate_synced_storage


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#") or "=" not in value:
            continue
        key, raw = value.split("=", 1)
        os.environ[key.strip()] = raw.strip().strip('"')


def main() -> int:
    load_dotenv(Path(".env"))
    os.environ["STORAGE_PROVIDER"] = "supabase"
    reset_settings_cache()
    settings = load_settings("dev")

    print("stage=sync_started", flush=True)
    sync_result = sync_google_drive_to_storage(
        folder_id=settings.google_drive_folder_id,
        db_path=settings.db_path,
    )
    print("stage=sync_finished", flush=True)

    print("stage=validation_started", flush=True)
    validation = validate_synced_storage(settings.db_path)
    print("stage=validation_finished", flush=True)

    update_sync_status(
        db_path=settings.db_path,
        last_synced_at=str(sync_result.get("sync_time") or ""),
        files_processed=int(sync_result.get("files", 0)),
        rows_imported=int(sync_result.get("rows_imported", 0)),
        validation_status=str(validation.get("status") or "unknown"),
        errors=[str(item) for item in sync_result.get("errors", [])],
    )

    catalog = get_storage_catalog(settings.db_path)
    payload = {
        "sync": sync_result,
        "validation": validation,
        "catalog_count": len(catalog),
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
