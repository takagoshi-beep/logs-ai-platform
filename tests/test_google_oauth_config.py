from __future__ import annotations

from config.settings import load_settings
from connector.google_drive.config import GOOGLE_OAUTH_SCOPES, build_google_drive_config


def test_google_oauth_paths_from_env(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", "tmp/credentials.json")
    monkeypatch.setenv("GOOGLE_TOKEN_PATH", "tmp/token.json")

    settings = load_settings("dev")
    assert settings.google_credentials_path.endswith("credentials.json")
    assert settings.google_token_path.endswith("token.json")


def test_google_oauth_scopes_are_read_only() -> None:
    assert "https://www.googleapis.com/auth/drive.readonly" in GOOGLE_OAUTH_SCOPES
    assert "https://www.googleapis.com/auth/spreadsheets.readonly" in GOOGLE_OAUTH_SCOPES


def test_build_google_drive_config_contains_scopes() -> None:
    config = build_google_drive_config(folder_id="folder-123")
    assert config.folder_id == "folder-123"
    assert config.scopes
    assert "https://www.googleapis.com/auth/drive.readonly" in config.scopes
