from __future__ import annotations

from pathlib import Path
from typing import Any
import os

from authorization.layer import get_default_authorization_layer
from business.tool_registry import get_default_business_tool_registry
from config.settings import ROOT_DIR, get_settings
from connector.registry import get_default_connector_registry
from database.repository import get_repository
from ingestion.google_drive_importer import get_storage_catalog, get_sync_status
from semantic.registry import get_default_semantic_registry
from self_awareness.status import get_ai_status
from storage import PostgresRepository, SQLiteRepository
from validation.report import get_latest_validation_report


def _db_path() -> Path:
    try:
        from app import main as app_main

        return Path(getattr(app_main, "DEFAULT_DB_PATH", get_settings().db_path))
    except Exception:
        return get_settings().db_path


def _count_tests() -> int:
    tests_dir = ROOT_DIR / "tests"
    return sum(1 for _ in tests_dir.rglob("test_*.py")) if tests_dir.exists() else 0


def _count_semantic_terms() -> int:
    registry = get_default_semantic_registry()
    terms: set[str] = set()

    def _add(value: Any) -> None:
        text = str(value or "").strip().lower()
        if text:
            terms.add(text)

    for section_name, section in registry.business_dictionary.items():
        if not isinstance(section, dict):
            continue
        _add(section_name)
        for key, item in section.items():
            _add(key)
            if isinstance(item, dict):
                _add(item.get("canonical") or key)
                _add(item.get("label"))
                for synonym in item.get("synonyms", []) or []:
                    _add(synonym)

    for key, item in registry.metric_registry.items():
        _add(key)
        if isinstance(item, dict):
            _add(item.get("label"))
            for alias in item.get("aliases", []) or []:
                _add(alias)

    return len(terms)


def _count_metric_definitions() -> int:
    registry = get_default_semantic_registry()
    return len(registry.metric_registry)


def _count_connectors() -> int:
    return len(get_default_connector_registry().list_connectors())


def _count_business_tools() -> int:
    return len(get_default_business_tool_registry().list_business_tools())


def _count_repositories() -> int:
    return len([SQLiteRepository, PostgresRepository])


def _storage_catalog() -> list[dict[str, Any]]:
    db_path = _db_path()
    if not db_path.exists():
        return []
    return get_storage_catalog(db_path)


def get_system_health() -> dict[str, Any]:
    settings = get_settings()
    db_path = _db_path()
    catalog = _storage_catalog()
    sync_status = get_sync_status(db_path) if db_path.exists() else {"validation_status": "not_synced", "errors": []}
    ai_status = get_ai_status()
    llm_status = "configured" if os.getenv("OPENAI_API_KEY") else "mock"
    storage_status = "ok" if catalog else ("missing" if not db_path.exists() else "empty")
    database_status = "ok" if db_path.exists() else "missing"
    business_status = "ok" if _count_business_tools() else "unavailable"
    semantic_status = "ok" if _count_semantic_terms() else "unavailable"
    authorization_status = "ok" if get_default_authorization_layer() else "unavailable"
    sync_value = str(sync_status.get("validation_status") or "not_synced")
    overall = "ok"
    if database_status != "ok" or storage_status not in {"ok", "empty"}:
        overall = "degraded"

    return {
        "status": overall,
        "version": settings.version,
        "database": database_status,
        "storage": storage_status,
        "sync": sync_value,
        "business": business_status,
        "semantic": semantic_status,
        "authorization": authorization_status,
        "llm": llm_status,
        "ai": {
            "test_count": ai_status.get("test_count", 0),
            "logic_count": ai_status.get("logic_count", 0),
        },
    }


def get_system_info() -> dict[str, Any]:
    settings = get_settings()
    return {
        "version": settings.version,
        "environment": settings.environment,
        "business_tools_count": _count_business_tools(),
        "repositories_count": _count_repositories(),
        "storage_tables_count": len(_storage_catalog()),
        "semantic_terms_count": _count_semantic_terms(),
        "metric_count": _count_metric_definitions(),
        "connectors_count": _count_connectors(),
        "tests_count": _count_tests(),
    }


def get_system_manifest() -> dict[str, Any]:
    db_path = _db_path()
    catalog = _storage_catalog()
    sync_status = get_sync_status(db_path) if db_path.exists() else {
        "last_synced_at": None,
        "files_processed": 0,
        "rows_imported": 0,
        "validation_status": "not_synced",
        "errors": [],
    }
    validation_report = get_latest_validation_report() or {}
    warnings = []
    validation_warnings = [issue.get("message") for issue in validation_report.get("issues", []) or [] if issue.get("severity") == "warning"]
    warnings.extend(str(item) for item in validation_warnings if item)
    if not catalog:
        warnings.append("Storage catalog is empty")
    files = int(sync_status.get("files_processed") or 0)
    sheets = len(catalog)
    tables = len({str(item.get("table_name") or "") for item in catalog if item.get("table_name")})
    rows = sum(int(item.get("row_count") or 0) for item in catalog)
    errors = [str(item) for item in sync_status.get("errors", []) or [] if str(item).strip()]
    errors.extend(str(issue.get("message")) for issue in validation_report.get("issues", []) or [] if issue.get("severity") == "error")
    return {
        "last_sync_at": sync_status.get("last_synced_at"),
        "files": files,
        "sheets": sheets,
        "tables": tables,
        "rows": rows,
        "errors": errors,
        "warnings": warnings,
    }


def get_system_diagnostics() -> dict[str, Any]:
    settings = get_settings()
    catalog = _storage_catalog()
    validation_report = get_latest_validation_report() or {}
    validation_status = str(validation_report.get("status") or "not_found")
    connector_status = "ok" if _count_connectors() else "unavailable"
    storage_status = "ok" if catalog else "not_synced"
    business_status = "ok" if _count_business_tools() else "unavailable"
    semantic_status = "ok" if _count_semantic_terms() else "unavailable"
    authorization_status = "ok"
    if settings.google_oauth_enabled and not Path(settings.google_credentials_path).exists():
        connector_status = "missing_credentials"
    return {
        "connector_status": connector_status,
        "validation_status": validation_status,
        "storage_status": storage_status,
        "business_status": business_status,
        "semantic_status": semantic_status,
        "authorization_status": authorization_status,
    }


def get_system_manifest_data() -> dict[str, Any]:
    return get_system_manifest()