"""Configuration settings."""

from pathlib import Path


class Settings:
    """Application settings."""

    def __init__(self):
        self.db_path = Path(__file__).resolve().parents[2] / "data/sqlite/logsys.db"


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
