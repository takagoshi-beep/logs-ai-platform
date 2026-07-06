"""Test-wide fixtures.

Tests assume they run in a fully offline, isolated environment:
- STORAGE_PROVIDER=sqlite: tests that build their own temporary SQLite
  databases (via db_path fixtures) assume this.
- GOOGLE_OAUTH_ENABLED=false: tests for the Google Drive connector assume
  mock auth (fake files/folders). If the developer's local .env has real
  OAuth enabled (with real credentials.json present), tests would otherwise
  make real Google Drive API calls with fake folder/file IDs and fail with
  404s instead of exercising the mock path.

This fixture forces both settings for the entire test session, regardless
of what the developer's local .env contains.

(2026-07-06: the old `config.settings.get_settings.cache_clear()` call
that used to live here was removed along with the rest of the app/-era
top-level packages (docs/architecture.md 14.14) — it existed only to
stop that old module's cached settings singleton from leaking into
tests, and no longer applies to anything backend/ actually uses.)
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _force_offline_test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_PROVIDER", "sqlite")
    monkeypatch.setenv("GOOGLE_OAUTH_ENABLED", "false")