from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class IngestionSource:
    source_id: str
    source_name: str
    source_type: str
    connector_name: str
    folder_id: str
    file_pattern: str
    data_category: str
    enabled: bool
    description: str


@dataclass(frozen=True)
class IngestionJob:
    job_id: str
    source: str
    status: str
    started_at: str
    finished_at: str | None
    files_processed: int
    source_id: str = ""
    file_metadata: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

