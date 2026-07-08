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

2. Full isolation from real Supabase data. As of 2026-07-07
   (docs/architecture.md 14.23), every one of `backend/`'s "runtime
   data" stores (`governance_store`, `document_formats`,
   `capability_instance`, `trace_store`, `status_reporting`,
   `conversation_store`, `learning.repository`) is backed by
   `services.record_store` (Supabase Postgres, JSONB rows) and, for
   `document_formats`, also `services.file_storage` (Supabase Storage).
   Rather than mock psycopg/Supabase-client internals in every test,
   `_isolate_backend_storage` replaces `record_store.append_record`/
   `read_all_records` and `file_storage.upload_file`/`download_file`
   themselves with simple in-memory equivalents (a dict of lists, a
   dict of bytes), fresh for every single test. Every store's own
   business logic is completely unaffected by this swap, since none of
   them ever touch `record_store`/`file_storage` internals directly —
   only their public functions, which behave identically whether
   backed by memory or a real database. Each store's in-memory
   singletons/caches (the `CapabilityRegistry` instance's dicts,
   `learning.repository`'s lazily-constructed singletons,
   `status_reporting._events`) are also reset per test so no state
   leaks between tests.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))


@pytest.fixture(autouse=True)
def _isolate_backend_storage(monkeypatch):
    # --- record_store.py: the shared Supabase-backed persistence used by
    # governance_store, document_formats, capability_instance,
    # trace_store, status_reporting, conversation_store, and
    # learning.repository. One in-memory fake covers all of them. ---
    from services import record_store

    _fake_tables: dict[str, list[dict]] = {}

    def _fake_append_record(table, record):
        _fake_tables.setdefault(table, []).append(record)

    def _fake_read_all_records(table):
        return list(_fake_tables.get(table, []))

    monkeypatch.setattr(record_store, "append_record", _fake_append_record)
    monkeypatch.setattr(record_store, "read_all_records", _fake_read_all_records)

    # --- file_storage.py: Supabase Storage, used only by
    # document_formats.py (template/generated-document binary files). ---
    from services import file_storage

    _fake_buckets: dict[tuple[str, str], bytes] = {}

    def _fake_upload_file(bucket, path, data):
        _fake_buckets[(bucket, path)] = data

    def _fake_download_file(bucket, path):
        if (bucket, path) not in _fake_buckets:
            raise FileNotFoundError(f"{bucket}/{path} not found in fake storage")
        return _fake_buckets[(bucket, path)]

    monkeypatch.setattr(file_storage, "upload_file", _fake_upload_file)
    monkeypatch.setattr(file_storage, "download_file", _fake_download_file)

    # --- capability_instance.py: reset the shared singleton's in-memory
    # state so tests never see real dev data (loaded once at import
    # time, before this fixture ever runs) or leftovers from a previous
    # test in the same session. ---
    from services import capability_instance

    monkeypatch.setattr(capability_instance.registry, "_capabilities", {})
    monkeypatch.setattr(capability_instance.registry, "_execution_history", [])

    # --- learning/repository.py: clear the lazily-constructed
    # singletons so the next get_xxx() call rebuilds them fresh against
    # the fake (empty) record_store instead of returning an
    # already-loaded instance from a previous test. ---
    from learning import repository as learning_repository

    monkeypatch.setattr(learning_repository, "_CANDIDATE_REPO", None)
    monkeypatch.setattr(learning_repository, "_OPERATIONAL_MEMORY", None)
    monkeypatch.setattr(learning_repository, "_APPROVAL_QUEUE", None)
    monkeypatch.setattr(learning_repository, "_POLICY_MEMORY", None)
    monkeypatch.setattr(learning_repository, "_ACTIVITY_FEED", None)

    # --- status_reporting.py: reset the module-level `_events` list it
    # accumulates in memory (in addition to record_store persistence). ---
    from services import status_reporting

    monkeypatch.setattr(status_reporting, "_events", [])

    yield


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
