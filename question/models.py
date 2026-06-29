from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QuestionUnderstandingResult:
    original_message: str
    normalized_message: str
    metric: str = "unknown"
    operation: str = "unknown"
    entity_type: str = "unknown"
    category: str | None = None
    customer: str | None = None
    product: str | None = None
    period: str = "unknown"
    limit: int | None = None
    filters: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_message": self.original_message,
            "normalized_message": self.normalized_message,
            "metric": self.metric,
            "operation": self.operation,
            "entity_type": self.entity_type,
            "category": self.category,
            "customer": self.customer,
            "product": self.product,
            "period": self.period,
            "limit": self.limit,
            "filters": self.filters,
            "confidence": self.confidence,
            "warnings": list(self.warnings),
            "reason": self.reason,
        }
