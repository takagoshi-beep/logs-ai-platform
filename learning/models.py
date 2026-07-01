"""
Learning Domain Model for AI OS.

Implements Blueprint v0.2 (Draft) Chapter 8: Learning Domain.
Learning is a cross-cutting domain that observes Project Understanding and
Business Execution, generates LearningCandidate records, classifies them as
Operational or Governed, and routes them to scoped memory or the Governance
approval pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def _now() -> datetime:
    return datetime.now(timezone.utc)


class LearningSourceType(str, Enum):
    """Where a LearningCandidate originates. Blueprint v0.2 §8.3."""

    USER_FEEDBACK = "user_feedback"
    AI_OBSERVATION = "ai_observation"
    EXECUTION_RESULT = "execution_result"
    REPEATED_CORRECTION = "repeated_correction"
    WORKFLOW_PATTERN = "workflow_pattern"
    KPI_SIGNAL = "kpi_signal"
    POLICY_UPDATE = "policy_update"


class LearningType(str, Enum):
    """Classification of a LearningCandidate. Blueprint v0.2 §8.5."""

    OPERATIONAL = "operational"
    GOVERNED = "governed"
    UNCLASSIFIED = "unclassified"


class LearningScopeType(str, Enum):
    """Scope of a LearningCandidate. Blueprint v0.2 §8.4."""

    SESSION = "session"
    USER = "user"
    PROJECT = "project"
    CAPABILITY = "capability"
    CUSTOMER = "customer"
    DEPARTMENT = "department"
    GLOBAL = "global"


class LearningStatus(str, Enum):
    """Lifecycle status of a LearningCandidate. Blueprint v0.2 §8.6/8.7."""

    OBSERVED = "observed"
    CANDIDATE_CREATED = "candidate_created"
    CLASSIFIED = "classified"
    SCOPED = "scoped"
    APPLIED = "applied"
    QUEUED_FOR_GOVERNANCE = "queued_for_governance"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


@dataclass
class LearningCandidate:
    """
    The atomic unit of Learning (Blueprint v0.2 §8.2).

    A LearningCandidate is a proposal. It is never treated as active behavior
    until it has been classified, scoped, and — if Governed — approved.
    """

    title: str
    description: str
    source_type: LearningSourceType
    created_by: str
    id: str = field(default_factory=lambda: f"learn-{uuid4()}")
    learning_type: LearningType = LearningType.UNCLASSIFIED
    scope_type: LearningScopeType | None = None
    scope_id: str | None = None
    status: LearningStatus = LearningStatus.OBSERVED
    confidence: float = 0.0
    evidence: list[dict[str, Any]] = field(default_factory=list)
    suggested_application: str = ""
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

    def touch(self) -> None:
        self.updated_at = _now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "source_type": self.source_type.value,
            "learning_type": self.learning_type.value,
            "scope_type": self.scope_type.value if self.scope_type else None,
            "scope_id": self.scope_id,
            "status": self.status.value,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "suggested_application": self.suggested_application,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class ApprovalQueueEntry:
    """Minimal Governance Approval Queue entry (Blueprint Ch.9 GovernanceApproval, MVP)."""

    candidate_id: str
    approval_id: str = field(default_factory=lambda: f"approval-{uuid4()}")
    status: str = "PENDING"
    decision: str | None = None
    approver_id: str | None = None
    approval_reason: str | None = None
    created_at: datetime = field(default_factory=_now)
    decided_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "candidate_id": self.candidate_id,
            "status": self.status,
            "decision": self.decision,
            "approver_id": self.approver_id,
            "approval_reason": self.approval_reason,
            "created_at": self.created_at.isoformat(),
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
        }


class LearningActivityEvent(str, Enum):
    """Activity Feed event types emitted by the Learning Domain. Blueprint v0.2 §8.9."""

    LEARNING_CANDIDATE_CREATED = "learning_candidate_created"
    OPERATIONAL_LEARNING_APPLIED = "operational_learning_applied"
    GOVERNED_LEARNING_QUEUED = "governed_learning_queued"
    POLICY_APPROVED = "policy_approved"
    POLICY_REJECTED = "policy_rejected"
    LEARNING_SCOPE_UPDATED = "learning_scope_updated"


@dataclass
class ActivityFeedEntry:
    """A single user-facing Activity Feed entry (Blueprint v0.1 §11)."""

    event: LearningActivityEvent
    candidate_id: str
    summary: str
    id: str = field(default_factory=lambda: f"activity-{uuid4()}")
    detail: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event": self.event.value,
            "candidate_id": self.candidate_id,
            "summary": self.summary,
            "detail": self.detail,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class PolicyMemoryEntry:
    """Minimal Policy Memory record (Blueprint Ch.9 PolicyRule, MVP)."""

    candidate_id: str
    approval_id: str
    rule_definition: str
    approved_by: str
    policy_id: str = field(default_factory=lambda: f"policy-{uuid4()}")
    version: int = 1
    active: bool = True
    approved_at: datetime = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "candidate_id": self.candidate_id,
            "approval_id": self.approval_id,
            "version": self.version,
            "rule_definition": self.rule_definition,
            "approved_by": self.approved_by,
            "active": self.active,
            "approved_at": self.approved_at.isoformat(),
        }
