from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
import os
import tomllib


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class AppSettings:
    environment: str
    app_name: str
    version: str
    runtime_mode: str
    storage_backend: str
    sqlite_db_path: str
    default_user_id: str = "default"
    default_organization_id: str = "default"

    @property
    def db_path(self) -> Path:
        return ROOT_DIR / self.sqlite_db_path


def _default_payload(environment: str) -> dict[str, Any]:
    return {
        "app": {
            "environment": environment,
            "name": "LOGS AI Platform",
            "version": "0.2.0",
            "runtime_mode": "cloud-ready",
            "storage_backend": "sqlite",
            "sqlite_db_path": "data/sqlite/logsys.db",
            "default_user_id": "default",
            "default_organization_id": "default",
        }
    }


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
    return AppSettings(
        environment=str(app.get("environment", selected_environment)),
        app_name=str(app.get("name", "LOGS AI Platform")),
        version=str(app.get("version", "0.2.0")),
        runtime_mode=str(app.get("runtime_mode", "cloud-ready")),
        storage_backend=str(app.get("storage_backend", "sqlite")),
        sqlite_db_path=str(app.get("sqlite_db_path", "data/sqlite/logsys.db")),
        default_user_id=str(app.get("default_user_id", "default")),
        default_organization_id=str(app.get("default_organization_id", "default")),
    )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return load_settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()