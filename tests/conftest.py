"""Test-wide fixtures.

Tests assume they run in a fully offline, isolated environment:
- STORAGE_PROVIDER=sqlite: tests that build their own temporary SQLite
  databases (via db_path fixtures) assume this. Production .env sets
  STORAGE_PROVIDER=supabase (see config/settings.py's auto dotenv load),
  which would otherwise silently redirect every test to the real Supabase
  database instead of the test's isolated temp SQLite file.
- GOOGLE_OAUTH_ENABLED=false: tests for the Google Drive connector assume
  mock auth (fake files/folders). If the developer's local .env has real
  OAuth enabled (with real credentials.json present), tests would otherwise
  make real Google Drive API calls with fake folder/file IDs and fail with
  404s instead of exercising the mock path.

This fixture forces both settings for the entire test session, regardless
of what the developer's local .env contains.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _force_offline_test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_PROVIDER", "sqlite")
    monkeypatch.setenv("GOOGLE_OAUTH_ENABLED", "false")

    # Clear the cached settings singleton (if any) so the overridden env
    # vars actually take effect for this test.
    try:
        from config.settings import get_settings

        get_settings.cache_clear()
    except AttributeError:
        pass