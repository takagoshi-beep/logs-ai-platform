from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TraceRecord:
    trace_id: str
    timestamp: str
    layer: str
    input: Any
    output: Any
    elapsed_ms: float
    success: bool
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "layer": self.layer,
            "input": self.input,
            "output": self.output,
            "elapsed_ms": self.elapsed_ms,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class TraceSession:
    trace_id: str
    timestamp: str
    message: str
    user_id: str
    records: list[TraceRecord] = field(default_factory=list)
    success: bool = True

    def add_record(self, record: TraceRecord) -> None:
        self.records.append(record)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "message": self.message,
            "user_id": self.user_id,
            "success": self.success,
            "records": [item.to_dict() for item in self.records],
        }