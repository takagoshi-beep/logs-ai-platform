from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StorageConfig:
    provider: str
    sqlite_path: str
    postgres_url: str
    environment: str
