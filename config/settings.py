from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
import os
import tomllib


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = Path(__file__).resolve().parent
VERSION_FILE = ROOT_DIR / "VERSION"


@dataclass(frozen=True)
class AppSettings:
    environment: str
    app_name: str
    version: str
    runtime_mode: str
    storage_backend: str
    sqlite_db_path: str
    storage_provider: str = "sqlite"
    sqlite_path: str = "data/sqlite/logsys.db"
    postgres_url: str = ""
    google_drive_enabled: bool = True
    google_sheets_enabled: bool = True
    google_oauth_enabled: bool = False
    google_drive_folder_id: str = ""
    google_drive_logsys_folder_id: str = ""
    google_drive_sales_folder_id: str = ""
    google_credentials_path: str = "credentials.json"
    google_token_path: str = "token.json"
    default_user_id: str = "default"
    default_organization_id: str = "default"

    @property
    def db_path(self) -> Path:
        return ROOT_DIR / self.sqlite_path


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _default_payload(environment: str) -> dict[str, Any]:
    return {
        "app": {
            "environment": environment,
            "name": "LOGS AI Platform",
            "version": _read_version(),
            "runtime_mode": "cloud-ready",
            "storage_backend": "sqlite",
            "sqlite_db_path": "data/sqlite/logsys.db",
            "storage_provider": "sqlite",
            "sqlite_path": "data/sqlite/logsys.db",
            "postgres_url": "",
            "google_drive_enabled": True,
            "google_sheets_enabled": True,
            "google_oauth_enabled": False,
            "google_drive_folder_id": "",
            "google_drive_logsys_folder_id": "",
            "google_drive_sales_folder_id": "",
            "google_credentials_path": "credentials.json",
            "google_token_path": "token.json",
            "default_user_id": "default",
            "default_organization_id": "default",
        }
    }


def _read_version() -> str:
    try:
        if VERSION_FILE.exists():
            return VERSION_FILE.read_text(encoding="utf-8").strip() or "0.2.0"
    except OSError:
        pass
    return "0.2.0"


def _load_payload(environment: str) -> dict[str, Any]:
    config_path = CONFIG_DIR / f"{environment}.toml"
    if not config_path.exists():
        config_path = CONFIG_DIR / "dev.toml"
    if not config_path.exists():
        return _default_payload(environment)

    with config_path.open("rb") as fp:
        payload = tomllib.load(fp)
    if "app" not in payload:
        payload["app"] = {}
    return payload


def load_settings(environment: str | None = None) -> AppSettings:
    selected_environment = (environment or os.getenv("APP_ENV") or "dev").strip().lower()
    payload = _load_payload(selected_environment)
    app = payload.get("app", {})
    storage_provider = str(
        os.getenv("STORAGE_PROVIDER")
        or app.get("storage_provider")
        or app.get("storage_backend", "sqlite")
    )
    sqlite_path = str(os.getenv("SQLITE_PATH") or app.get("sqlite_path") or app.get("sqlite_db_path", "data/sqlite/logsys.db"))
    postgres_url = str(os.getenv("POSTGRES_URL") or app.get("postgres_url", ""))
    google_drive_enabled = _to_bool(
        os.getenv("GOOGLE_DRIVE_ENABLED", app.get("google_drive_enabled")),
        default=True,
    )
    google_sheets_enabled = _to_bool(
        os.getenv("GOOGLE_SHEETS_ENABLED", app.get("google_sheets_enabled")),
        default=True,
    )
    google_oauth_enabled = _to_bool(
        os.getenv("GOOGLE_OAUTH_ENABLED", app.get("google_oauth_enabled")),
        default=False,
    )
    google_drive_folder_id = str(
        os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        or app.get("google_drive_folder_id", "")
    )
    google_drive_logsys_folder_id = str(
        os.getenv("GOOGLE_DRIVE_LOGSYS_FOLDER_ID")
        or app.get("google_drive_logsys_folder_id", "")
    )
    google_drive_sales_folder_id = str(
        os.getenv("GOOGLE_DRIVE_SALES_FOLDER_ID")
        or app.get("google_drive_sales_folder_id", "")
    )
    google_credentials_path = str(
        os.getenv("GOOGLE_CREDENTIALS_PATH")
        or app.get("google_credentials_path", "credentials.json")
    )
    google_token_path = str(
        os.getenv("GOOGLE_TOKEN_PATH")
        or app.get("google_token_path", "token.json")
    )

    return AppSettings(
        environment=str(app.get("environment", selected_environment)),
        app_name=str(app.get("name", "LOGS AI Platform")),
        version=_read_version(),
        runtime_mode=str(app.get("runtime_mode", "cloud-ready")),
        storage_backend=storage_provider,
        sqlite_db_path=sqlite_path,
        storage_provider=storage_provider,
        sqlite_path=sqlite_path,
        postgres_url=postgres_url,
        google_drive_enabled=google_drive_enabled,
        google_sheets_enabled=google_sheets_enabled,
        google_oauth_enabled=google_oauth_enabled,
        google_drive_folder_id=google_drive_folder_id,
        google_drive_logsys_folder_id=google_drive_logsys_folder_id,
        google_drive_sales_folder_id=google_drive_sales_folder_id,
        google_credentials_path=google_credentials_path,
        google_token_path=google_token_path,
        default_user_id=str(app.get("default_user_id", "default")),
        default_organization_id=str(app.get("default_organization_id", "default")),
    )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return load_settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()