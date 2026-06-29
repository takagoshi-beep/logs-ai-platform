from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConnectorFile:
    source: str
    file_id: str
    name: str
    mime_type: str
    modified_at: str
    path: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConnectorResult:
    success: bool
    source: str
    files: list[ConnectorFile]
    error: str | None = None
