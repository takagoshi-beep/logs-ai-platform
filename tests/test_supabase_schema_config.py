from __future__ import annotations

from config.settings import load_settings, reset_settings_cache


def test_supabase_schema_defaults(monkeypatch) -> None:
    monkeypatch.delenv("SUPABASE_SCHEMA_RAW", raising=False)
    monkeypatch.delenv("SUPABASE_SCHEMA_CORE", raising=False)
    monkeypatch.delenv("SUPABASE_SCHEMA_META", raising=False)
    monkeypatch.delenv("SUPABASE_BATCH_SIZE", raising=False)
    monkeypatch.delenv("SUPABASE_MAX_RETRIES", raising=False)
    monkeypatch.delenv("SUPABASE_WRITE_MODE", raising=False)
    reset_settings_cache()

    settings = load_settings("dev")

    assert settings.supabase_schema_raw == "ai_os_raw"
    assert settings.supabase_schema_core == "ai_os_core"
    assert settings.supabase_schema_meta == "ai_os_meta"
    assert settings.supabase_batch_size == 1000
    assert settings.supabase_max_retries == 5
    assert settings.supabase_write_mode == "insert"


def test_supabase_schema_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_SCHEMA_RAW", "raw_x")
    monkeypatch.setenv("SUPABASE_SCHEMA_CORE", "core_x")
    monkeypatch.setenv("SUPABASE_SCHEMA_META", "meta_x")
    monkeypatch.setenv("SUPABASE_BATCH_SIZE", "250")
    monkeypatch.setenv("SUPABASE_MAX_RETRIES", "7")
    monkeypatch.setenv("SUPABASE_WRITE_MODE", "copy")
    reset_settings_cache()

    settings = load_settings("dev")

    assert settings.supabase_schema_raw == "raw_x"
    assert settings.supabase_schema_core == "core_x"
    assert settings.supabase_schema_meta == "meta_x"
    assert settings.supabase_batch_size == 250
    assert settings.supabase_max_retries == 7
    assert settings.supabase_write_mode == "copy"
