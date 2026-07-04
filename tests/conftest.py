"""Test-wide fixtures.

Tests that build their own temporary SQLite databases (via db_path fixtures)
assume STORAGE_PROVIDER=sqlite. Production .env sets STORAGE_PROVIDER=supabase
(see config/settings.py's auto dotenv load), which would otherwise silently
redirect every test to the real Supabase database instead of the test's
isolated temp SQLite file. This fixture forces sqlite mode for the entire
test session, regardless of what the developer's local .env contains.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _force_sqlite_storage_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_PROVIDER", "sqlite")

    # Clear the cached settings singleton (if any) so the overridden env
    # var actually takes effect for this test.
    try:
        from config.settings import get_settings

        get_settings.cache_clear()
    except AttributeError:
        pass