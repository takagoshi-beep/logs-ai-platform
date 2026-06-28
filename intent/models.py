from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IntentResult:
    intent_type: str
    domain: str
    action: str
    confidence: float
    entities: dict[str, Any] = field(default_factory=dict)
    requires_memory: bool = False
    requires_business_logic: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_type": self.intent_type,
            "domain": self.domain,
            "action": self.action,
            "confidence": self.confidence,
            "entities": self.entities,
            "requires_memory": self.requires_memory,
            "requires_business_logic": self.requires_business_logic,
            "reason": self.reason,
        }
