from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from storage.repository import BaseRepository


@dataclass(frozen=True)
class TransformResult:
    status: str
    source_schema: str
    target_schema: str
    table_mappings: list[dict[str, str]]


class TransformPipeline:
    """Placeholder transform interface for ai_os_raw -> ai_os_core."""

    def __init__(self, repository: BaseRepository, *, source_schema: str = "ai_os_raw", target_schema: str = "ai_os_core") -> None:
        self.repository = repository
        self.source_schema = source_schema
        self.target_schema = target_schema

    def run(self, raw_table_names: list[str]) -> TransformResult:
        mappings = [
            {
                "source_table": name,
                "target_table": name,
                "mode": "pass_through",
            }
            for name in raw_table_names
        ]
        return TransformResult(
            status="pass_through",
            source_schema=self.source_schema,
            target_schema=self.target_schema,
            table_mappings=mappings,
        )
