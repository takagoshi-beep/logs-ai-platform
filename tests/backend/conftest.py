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

    # --- document_formats.py ---
    from services import document_formats

    monkeypatch.setattr(document_formats, "DATA_DIR", data_dir)
    monkeypatch.setattr(document_formats, "TEMPLATES_DIR", data_dir / "document_templates")
    monkeypatch.setattr(document_formats, "FORMATS_PATH", data_dir / "document_formats.jsonl")
    monkeypatch.setattr(document_formats, "GENERATED_DOCS_DIR", data_dir / "generated_documents")

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

    yield data_dir
