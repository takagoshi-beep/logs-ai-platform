"""
In-memory repositories for the Learning Domain.

Mirrors the storage pattern used by capability/domain.py (CapabilityRegistry):
process-local dict/list stores behind a singleton accessor. This is the
Learning Domain's MVP persistence layer; durable storage is deferred to the
Memory domain (Blueprint v0.1 §13 Phase 4), per the ★☆☆☆☆ Memory Domain
maturity recorded in BLUEPRINT_ALIGNMENT_CHECK.md.
"""

from __future__ import annotations

from threading import Lock
from typing import Any

from learning.models import ActivityFeedEntry, ApprovalQueueEntry, LearningCandidate, PolicyMemoryEntry


class LearningCandidateRepository:
    """Stores LearningCandidate records."""

    def __init__(self) -> None:
        self._candidates: dict[str, LearningCandidate] = {}
        self._lock = Lock()

    def save(self, candidate: LearningCandidate) -> str:
        with self._lock:
            self._candidates[candidate.id] = candidate
        return candidate.id

    def get(self, candidate_id: str) -> LearningCandidate | None:
        return self._candidates.get(candidate_id)

    def list(
        self,
        *,
        learning_type: str | None = None,
        status: str | None = None,
        scope_type: str | None = None,
    ) -> list[LearningCandidate]:
        items = list(self._candidates.values())
        if learning_type:
            items = [c for c in items if c.learning_type.value == learning_type]
        if status:
            items = [c for c in items if c.status.value == status]
        if scope_type:
            items = [c for c in items if c.scope_type and c.scope_type.value == scope_type]
        return sorted(items, key=lambda c: c.created_at, reverse=True)


class OperationalMemoryStore:
    """
    Scoped key-value store for applied Operational Learning.

    Keyed by (scope_type, scope_id) so that USER/PROJECT/CAPABILITY-scoped
    learning never leaks across boundaries (Blueprint v0.1 §10 Preference &
    Scope Standard; Blueprint v0.2 §8.4 Learning Scope).
    """

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self._lock = Lock()

    def apply(self, scope_type: str, scope_id: str, entry: dict[str, Any]) -> None:
        key = (scope_type, scope_id or "")
        with self._lock:
            self._store.setdefault(key, []).append(entry)

    def get(self, scope_type: str, scope_id: str) -> list[dict[str, Any]]:
        return list(self._store.get((scope_type, scope_id or ""), []))


class ApprovalQueueRepository:
    """Minimal Governance Approval Queue (Blueprint v0.1 §9 GovernanceApproval, MVP)."""

    def __init__(self) -> None:
        self._entries: dict[str, ApprovalQueueEntry] = {}
        self._lock = Lock()

    def enqueue(self, entry: ApprovalQueueEntry) -> str:
        with self._lock:
            self._entries[entry.approval_id] = entry
        return entry.approval_id

    def get(self, approval_id: str) -> ApprovalQueueEntry | None:
        return self._entries.get(approval_id)

    def list_pending(self) -> list[ApprovalQueueEntry]:
        return [e for e in self._entries.values() if e.status == "PENDING"]

    def list_all(self) -> list[ApprovalQueueEntry]:
        return sorted(self._entries.values(), key=lambda e: e.created_at, reverse=True)


class PolicyMemoryRepository:
    """Minimal Policy Memory store (Blueprint v0.1 §9 PolicyRule, MVP)."""

    def __init__(self) -> None:
        self._policies: dict[str, PolicyMemoryEntry] = {}
        self._lock = Lock()

    def save(self, policy: PolicyMemoryEntry) -> str:
        with self._lock:
            self._policies[policy.policy_id] = policy
        return policy.policy_id

    def list_active(self) -> list[PolicyMemoryEntry]:
        return [p for p in self._policies.values() if p.active]

    def list_all(self) -> list[PolicyMemoryEntry]:
        return sorted(self._policies.values(), key=lambda p: p.approved_at, reverse=True)


class ActivityFeedRepository:
    """User-facing Activity Feed entries emitted by the Learning Domain (Blueprint v0.2 §8.9)."""

    def __init__(self) -> None:
        self._entries: list[ActivityFeedEntry] = []
        self._lock = Lock()

    def record(self, entry: ActivityFeedEntry) -> str:
        with self._lock:
            self._entries.append(entry)
        return entry.id

    def list(self, limit: int = 50) -> list[ActivityFeedEntry]:
        return sorted(self._entries, key=lambda e: e.created_at, reverse=True)[:limit]


_CANDIDATE_REPO: LearningCandidateRepository | None = None
_OPERATIONAL_MEMORY: OperationalMemoryStore | None = None
_APPROVAL_QUEUE: ApprovalQueueRepository | None = None
_POLICY_MEMORY: PolicyMemoryRepository | None = None
_ACTIVITY_FEED: ActivityFeedRepository | None = None


def get_candidate_repository() -> LearningCandidateRepository:
    global _CANDIDATE_REPO
    if _CANDIDATE_REPO is None:
        _CANDIDATE_REPO = LearningCandidateRepository()
    return _CANDIDATE_REPO


def get_operational_memory() -> OperationalMemoryStore:
    global _OPERATIONAL_MEMORY
    if _OPERATIONAL_MEMORY is None:
        _OPERATIONAL_MEMORY = OperationalMemoryStore()
    return _OPERATIONAL_MEMORY


def get_approval_queue() -> ApprovalQueueRepository:
    global _APPROVAL_QUEUE
    if _APPROVAL_QUEUE is None:
        _APPROVAL_QUEUE = ApprovalQueueRepository()
    return _APPROVAL_QUEUE


def get_policy_memory() -> PolicyMemoryRepository:
    global _POLICY_MEMORY
    if _POLICY_MEMORY is None:
        _POLICY_MEMORY = PolicyMemoryRepository()
    return _POLICY_MEMORY


def get_activity_feed() -> ActivityFeedRepository:
    global _ACTIVITY_FEED
    if _ACTIVITY_FEED is None:
        _ACTIVITY_FEED = ActivityFeedRepository()
    return _ACTIVITY_FEED
