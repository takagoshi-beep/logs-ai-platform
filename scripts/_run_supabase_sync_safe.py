from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import load_settings, reset_settings_cache
from ingestion.google_drive_importer import sync_google_drive_to_storage


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
    try:
        load_dotenv(ROOT_DIR / ".env")
        os.environ["STORAGE_PROVIDER"] = "supabase"
        reset_settings_cache()
        settings = load_settings("dev")

        print("phase=sync started", flush=True)

        def _progress(stage: str, details: dict[str, object]) -> None:
            print(json.dumps({"stage": stage, "details": details}, ensure_ascii=False), flush=True)

        result = sync_google_drive_to_storage(
            folder_id=settings.google_drive_folder_id,
            db_path=settings.db_path,
            progress_callback=_progress,
        )
        print("phase=sync finished", flush=True)
        print(json.dumps({"sync_result": result}, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:  # noqa: BLE001
        print("phase=sync failed", flush=True)
        print(str(exc), flush=True)
        print(traceback.format_exc(), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
