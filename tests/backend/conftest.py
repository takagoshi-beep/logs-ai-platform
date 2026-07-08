"""Test fixtures for `backend/`'s own service-level tests.

Two things every test here needs, handled once:

1. `backend/` on `sys.path`. `pytest.ini`'s `pythonpath = .` only puts
   the repo root on the path — `backend/`'s own modules use bare
   imports like `from services.document_formats import ...`, which only
   resolve correctly when `backend/` itself is also on `sys.path` (this
   is how `backend/main.py` is actually run — from inside `backend/` via
   `uvicorn main:app`). Inserted at position 0 so it's found before the
   repo-root `pythonpath` entry, in case a same-named module existed at
   the root too (see docs/architecture.md 14.14 for exactly how much
   confusion that ambiguity caused before the old root-level `services/`,
   `domain/` etc. were deleted).

2. Full isolation from real `backend/data/` files. Every service here
   (`governance_store`, `document_formats`, `capability_instance`,
   `trace_store`, `learning.repository`) resolves its storage paths at
   *import time* relative to `backend/`, so without this, running the
   test suite would read and write the same JSONL files the developer's
   real running server uses — corrupting real Governance/Learning/
   Capability history, or (worse) leaking real business data into a
   test's assertions. `_isolate_backend_storage` monkeypatches every one
   of those path constants to a fresh `tmp_path` for every single test,
   and resets each module's in-memory state (the `CapabilityRegistry`
   singleton's dicts, `learning.repository`'s lazily-constructed
   singletons) so no state leaks between tests either.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))


@pytest.fixture(autouse=True)
def _isolate_backend_storage(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # --- governance_store.py ---
    from services import governance_store

    monkeypatch.setattr(governance_store, "DATA_DIR", data_dir)
    monkeypatch.setattr(governance_store, "APPROVALS_PATH", data_dir / "governance_approvals.jsonl")
    monkeypatch.setattr(governance_store, "AUDIT_PATH", data_dir / "governance_audit.jsonl")

    # --- document_formats.py (2026-07-06: migrated to Supabase via
    # record_store/file_storage — docs/architecture.md 14.23). Rather than
    # mocking psycopg2 cursors in every test, replace record_store's/
    # file_storage's public functions with simple in-memory equivalents
    # that behave exactly like the real thing (append-then-read-back,
    # upload-then-download) — every existing document_formats test then
    # keeps working unchanged, since document_formats.py itself never
    # touches record_store/file_storage's internals directly. ---
    from services import record_store, file_storage

    _fake_tables: dict[str, list[dict]] = {}

    def _fake_append_record(table, record):
        _fake_tables.setdefault(table, []).append(record)

    def _fake_read_all_records(table):
        return list(_fake_tables.get(table, []))

    monkeypatch.setattr(record_store, "append_record", _fake_append_record)
    monkeypatch.setattr(record_store, "read_all_records", _fake_read_all_records)

    _fake_buckets: dict[tuple[str, str], bytes] = {}

    def _fake_upload_file(bucket, path, data):
        _fake_buckets[(bucket, path)] = data

    def _fake_download_file(bucket, path):
        if (bucket, path) not in _fake_buckets:
            raise FileNotFoundError(f"{bucket}/{path} not found in fake storage")
        return _fake_buckets[(bucket, path)]

    monkeypatch.setattr(file_storage, "upload_file", _fake_upload_file)
    monkeypatch.setattr(file_storage, "download_file", _fake_download_file)

    # --- trace_store.py ---
    from services import trace_store

    monkeypatch.setattr(trace_store, "TRACE_LOG_DIR", data_dir)
    monkeypatch.setattr(trace_store, "TRACE_LOG_PATH", data_dir / "traces.jsonl")

    # --- capability_instance.py: redirect future writes, and reset the
    # shared singleton's in-memory state so tests never see real dev
    # data (loaded once at import time, before this fixture ever runs)
    # or leftovers from a previous test in the same session. ---
    from services import capability_instance

    monkeypatch.setattr(capability_instance, "EXECUTION_LOG_DIR", data_dir)
    monkeypatch.setattr(capability_instance, "EXECUTION_LOG_PATH", data_dir / "capability_executions.jsonl")
    monkeypatch.setattr(capability_instance.registry, "_capabilities", {})
    monkeypatch.setattr(capability_instance.registry, "_execution_history", [])

    # --- learning/repository.py: redirect future writes, and clear the
    # lazily-constructed singletons so the next get_xxx() call rebuilds
    # them fresh against the new (empty) tmp path instead of returning
    # an already-loaded instance from a previous test's tmp path. ---
    from learning import repository as learning_repository

    monkeypatch.setattr(learning_repository, "_DATA_DIR", data_dir / "learning")
    monkeypatch.setattr(learning_repository, "_CANDIDATE_REPO", None)
    monkeypatch.setattr(learning_repository, "_OPERATIONAL_MEMORY", None)
    monkeypatch.setattr(learning_repository, "_APPROVAL_QUEUE", None)
    monkeypatch.setattr(learning_repository, "_POLICY_MEMORY", None)
    monkeypatch.setattr(learning_repository, "_ACTIVITY_FEED", None)

    # --- status_reporting.py: redirect events.jsonl, and reset the
    # module-level `_events` list it accumulates in memory. ---
    from services import status_reporting

    monkeypatch.setattr(status_reporting, "EVENT_LOG_DIR", data_dir)
    monkeypatch.setattr(status_reporting, "EVENT_LOG_PATH", data_dir / "events.jsonl")
    monkeypatch.setattr(status_reporting, "_events", [])

    # --- conversation_store.py ---
    from services import conversation_store

    monkeypatch.setattr(conversation_store, "DATA_DIR", data_dir)
    monkeypatch.setattr(conversation_store, "CONVERSATION_LOG_PATH", data_dir / "conversations.jsonl")

    yield data_dir


@pytest.fixture(autouse=True)
def _default_authenticated_session():
    """既存のテストの大半は認証そのものを検証する意図ではなく、各機能の
    ロジックを検証するためのものだったため、デフォルトでは「管理者として
    ログイン済み」として扱う。認証・権限そのものを検証するテスト
    （test_auth_router.py、および各ルーターの「管理者でなければ403」系の
    テスト）は、このオーバーライドを明示的に解除して実施する。
    """
    from main import app
    from api.auth_router import require_admin, require_login

    fake_admin = {"email": "test-admin@example.com", "name": "Test Admin", "role": "admin"}
    app.dependency_overrides[require_login] = lambda: fake_admin
    app.dependency_overrides[require_admin] = lambda: fake_admin
    yield
    app.dependency_overrides.pop(require_login, None)
    app.dependency_overrides.pop(require_admin, None)
