from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SemanticAnalysisResult:
    original_message: str
    normalized_message: str
    original_question: dict[str, Any] = field(default_factory=dict)
    metric: str = "unknown"
    entity_type: str = "unknown"
    operation: str = "unknown"
    period: str = "unknown"
    limit: int | None = None
    category: str | None = None
    customer: str | None = None
    product: str | None = None
    metric_label: str | None = None
    entity_label: str | None = None
    operation_label: str | None = None
    confidence: float = 0.0
    matched_terms: dict[str, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    reason: str = ""
    source: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_message": self.original_message,
            "normalized_message": self.normalized_message,
            "original_question": dict(self.original_question),
            "metric": self.metric,
            "entity_type": self.entity_type,
            "operation": self.operation,
            "period": self.period,
            "limit": self.limit,
            "category": self.category,
            "customer": self.customer,
            "product": self.product,
            "metric_label": self.metric_label,
            "entity_label": self.entity_label,
            "operation_label": self.operation_label,
            "confidence": self.confidence,
            "matched_terms": {key: list(value) for key, value in self.matched_terms.items()},
            "warnings": list(self.warnings),
            "reason": self.reason,
            "source": dict(self.source),
        }