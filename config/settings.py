from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
import os
import tomllib
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

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
    supabase_url: str = ""
    supabase_db_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""
    supabase_schema_raw: str = "ai_os_raw"
    supabase_schema_core: str = "ai_os_core"
    supabase_schema_meta: str = "ai_os_meta"
    supabase_batch_size: int = 1000
    supabase_max_retries: int = 5
    supabase_write_mode: str = "insert"
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


def _to_int(value: Any, default: int) -> int:
    if value is None:
        return default
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _resolve(env_key: str, *app_fallbacks: Any) -> Any:
    """環境変数の優先順位を正しく解決する。

    `os.getenv(key) or app.get(...)` は環境変数が明示的に空文字 "" に
    設定されている場合でも偽値として扱われ、意図せず app (toml) 側の
    値へフォールバックしてしまう。これを避けるため、環境変数が
    実際に設定されているか (``env_key in os.environ``) を最優先で判定する。

    環境変数が未設定の場合のみ、app_fallbacks を順番に評価し、
    最初に truthy な値を返す。全て falsy であれば最後の値
    (通常はデフォルト値) を返す。
    """
    if env_key in os.environ:
        return os.environ[env_key]
    result = None
    for value in app_fallbacks:
        result = value
        if value:
            return value
    return result


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
            "supabase_url": "",
            "supabase_db_url": "",
            "supabase_service_role_key": "",
            "supabase_anon_key": "",
            "supabase_schema_raw": "ai_os_raw",
            "supabase_schema_core": "ai_os_core",
            "supabase_schema_meta": "ai_os_meta",
            "supabase_batch_size": 1000,
            "supabase_max_retries": 5,
            "supabase_write_mode": "insert",
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
        _resolve(
            "STORAGE_PROVIDER",
            app.get("storage_provider"),
            app.get("storage_backend", "sqlite"),
        )
    )
    sqlite_path = str(
        _resolve(
            "SQLITE_PATH",
            app.get("sqlite_path"),
            app.get("sqlite_db_path", "data/sqlite/logsys.db"),
        )
    )
    postgres_url = str(_resolve("POSTGRES_URL", app.get("postgres_url", "")))
    supabase_url = str(_resolve("SUPABASE_URL", app.get("supabase_url", "")))
    supabase_db_url = str(
        _resolve(
            "SUPABASE_DB_URL",
            os.environ.get("DATABASE_URL") if "DATABASE_URL" in os.environ else None,
            app.get("supabase_db_url", ""),
            app.get("database_url", ""),
            postgres_url,
        )
    )
    supabase_service_role_key = str(
        _resolve("SUPABASE_SERVICE_ROLE_KEY", app.get("supabase_service_role_key", ""))
    )
    supabase_anon_key = str(
        _resolve("SUPABASE_ANON_KEY", app.get("supabase_anon_key", ""))
    )
    supabase_schema_raw = str(
        _resolve("SUPABASE_SCHEMA_RAW", app.get("supabase_schema_raw", "ai_os_raw"))
    )
    supabase_schema_core = str(
        _resolve("SUPABASE_SCHEMA_CORE", app.get("supabase_schema_core", "ai_os_core"))
    )
    supabase_schema_meta = str(
        _resolve("SUPABASE_SCHEMA_META", app.get("supabase_schema_meta", "ai_os_meta"))
    )
    supabase_batch_size = _to_int(
        _resolve("SUPABASE_BATCH_SIZE", app.get("supabase_batch_size")),
        default=1000,
    )
    supabase_max_retries = _to_int(
        _resolve("SUPABASE_MAX_RETRIES", app.get("supabase_max_retries")),
        default=5,
    )
    supabase_write_mode = str(
        _resolve("SUPABASE_WRITE_MODE", app.get("supabase_write_mode", "insert"))
    ).strip().lower()
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
        _resolve("GOOGLE_DRIVE_FOLDER_ID", app.get("google_drive_folder_id", ""))
    )
    google_drive_logsys_folder_id = str(
        _resolve(
            "GOOGLE_DRIVE_LOGSYS_FOLDER_ID",
            app.get("google_drive_logsys_folder_id", ""),
        )
    )
    google_drive_sales_folder_id = str(
        _resolve(
            "GOOGLE_DRIVE_SALES_FOLDER_ID",
            app.get("google_drive_sales_folder_id", ""),
        )
    )
    google_credentials_path = str(
        _resolve("GOOGLE_CREDENTIALS_PATH", app.get("google_credentials_path", "credentials.json"))
    )
    google_token_path = str(
        _resolve("GOOGLE_TOKEN_PATH", app.get("google_token_path", "token.json"))
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
        supabase_url=supabase_url,
        supabase_db_url=supabase_db_url,
        supabase_service_role_key=supabase_service_role_key,
        supabase_anon_key=supabase_anon_key,
        supabase_schema_raw=supabase_schema_raw,
        supabase_schema_core=supabase_schema_core,
        supabase_schema_meta=supabase_schema_meta,
        supabase_batch_size=supabase_batch_size,
        supabase_max_retries=supabase_max_retries,
        supabase_write_mode=supabase_write_mode,
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