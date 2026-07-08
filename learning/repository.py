"""
Repositories for the Learning Domain, with durable persistence (added
2026-07-06, closing the gap this module's original docstring flagged as
deferred to "the Memory domain, Blueprint v0.1 Phase 4"; migrated off
local JSONL to Supabase on 2026-07-07, docs/architecture.md 14.23, same
reason/pattern as every other store this session — a local file
wouldn't survive a Render redeploy).

Storage convention matches the rest of backend/ (governance_store.py,
document_formats.py): append-only records, "latest record per id wins"
for anything updated over its lifecycle (LearningCandidate,
ApprovalQueueEntry), plain accumulation for anything append-only/
immutable (PolicyMemoryEntry, ActivityFeedEntry, OperationalMemoryStore
entries).

Repositories keep the same in-memory, in-process shape/behavior as
before — they just load from Supabase on first access and write
through on every mutation, so a server restart no longer silently
erases Learning Domain history.

Lives at the repo root (not under `backend/`), so `services.record_store`
is only importable here when `backend/` is already on `sys.path` — true
at runtime (`backend/main.py` adds the repo root, and is itself run
from inside `backend/`) and true in every test in this repo (all
Learning tests live under `tests/backend/`, where `conftest.py` puts
`backend/` on `sys.path` for every test).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

from learning.models import (
    ActivityFeedEntry,
    ApprovalQueueEntry,
    LearningActivityEvent,
    LearningCandidate,
    LearningScopeType,
    LearningSourceType,
    LearningStatus,
    LearningType,
    PolicyMemoryEntry,
)
from services import record_store

_TABLE_PREFIX = "app_learning_"


def _append_jsonl(filename: str, record: dict[str, Any]) -> None:
    """名前はJSONL時代のまま、実体はrecord_store経由でSupabaseに保存する
    （filenameは各クラスの`_FILE`、例: "candidates.jsonl" → テーブル名
    "app_learning_candidates" に変換する）。"""
    table = _TABLE_PREFIX + filename.replace(".jsonl", "")
    record_store.append_record(table, record)


def _read_jsonl(filename: str) -> list[dict[str, Any]]:
    """同上 — 名前はJSONL時代のまま、実体はSupabaseから読む。"""
    table = _TABLE_PREFIX + filename.replace(".jsonl", "")
    return record_store.read_all_records(table)


def _candidate_from_dict(d: dict[str, Any]) -> LearningCandidate:
    return LearningCandidate(
        title=d["title"],
        description=d["description"],
        source_type=LearningSourceType(d["source_type"]),
        created_by=d["created_by"],
        id=d["id"],
        learning_type=LearningType(d["learning_type"]),
        scope_type=LearningScopeType(d["scope_type"]) if d.get("scope_type") else None,
        scope_id=d.get("scope_id"),
        status=LearningStatus(d["status"]),
        confidence=d["confidence"],
        evidence=d.get("evidence") or [],
        suggested_application=d.get("suggested_application", ""),
        created_at=datetime.fromisoformat(d["created_at"]),
        updated_at=datetime.fromisoformat(d["updated_at"]),
    )


def _approval_from_dict(d: dict[str, Any]) -> ApprovalQueueEntry:
    return ApprovalQueueEntry(
        candidate_id=d["candidate_id"],
        approval_id=d["approval_id"],
        status=d["status"],
        decision=d.get("decision"),
        approver_id=d.get("approver_id"),
        approval_reason=d.get("approval_reason"),
        created_at=datetime.fromisoformat(d["created_at"]),
        decided_at=datetime.fromisoformat(d["decided_at"]) if d.get("decided_at") else None,
    )


def _policy_from_dict(d: dict[str, Any]) -> PolicyMemoryEntry:
    return PolicyMemoryEntry(
        candidate_id=d["candidate_id"],
        approval_id=d["approval_id"],
        rule_definition=d["rule_definition"],
        approved_by=d["approved_by"],
        policy_id=d["policy_id"],
        version=d["version"],
        active=d["active"],
        approved_at=datetime.fromisoformat(d["approved_at"]),
    )


def _activity_from_dict(d: dict[str, Any]) -> ActivityFeedEntry:
    return ActivityFeedEntry(
        event=LearningActivityEvent(d["event"]),
        candidate_id=d["candidate_id"],
        summary=d["summary"],
        id=d["id"],
        detail=d.get("detail") or {},
        created_at=datetime.fromisoformat(d["created_at"]),
    )


class LearningCandidateRepository:
    """Stores LearningCandidate records, persisted to
    data/learning/candidates.jsonl (latest record per id wins, since a
    candidate is saved repeatedly as it moves through its lifecycle)."""

    _FILE = "candidates.jsonl"

    def __init__(self) -> None:
        self._candidates: dict[str, LearningCandidate] = {}
        self._lock = Lock()
        for record in _read_jsonl(self._FILE):
            try:
                candidate = _candidate_from_dict(record)
                self._candidates[candidate.id] = candidate
            except Exception:
                continue

    def save(self, candidate: LearningCandidate) -> str:
        with self._lock:
            self._candidates[candidate.id] = candidate
        _append_jsonl(self._FILE, candidate.to_dict())
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
    Scoped key-value store for applied Operational Learning, persisted to
    data/learning/operational_memory.jsonl (append-only — each
    application is a distinct historical fact, not something a later
    record overwrites).

    Keyed by (scope_type, scope_id) so that USER/PROJECT/CAPABILITY-scoped
    learning never leaks across boundaries (Blueprint v0.1 §10 Preference &
    Scope Standard; Blueprint v0.2 §8.4 Learning Scope).
    """

    _FILE = "operational_memory.jsonl"

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self._lock = Lock()
        for record in _read_jsonl(self._FILE):
            key = (record.get("scope_type", ""), record.get("scope_id", ""))
            self._store.setdefault(key, []).append(record.get("entry", {}))

    def apply(self, scope_type: str, scope_id: str, entry: dict[str, Any]) -> None:
        key = (scope_type, scope_id or "")
        with self._lock:
            self._store.setdefault(key, []).append(entry)
        _append_jsonl(self._FILE, {"scope_type": scope_type, "scope_id": scope_id or "", "entry": entry})

    def get(self, scope_type: str, scope_id: str) -> list[dict[str, Any]]:
        return list(self._store.get((scope_type, scope_id or ""), []))


class ApprovalQueueRepository:
    """Minimal Governance Approval Queue (Blueprint v0.1 §9 GovernanceApproval, MVP),
    persisted to data/learning/approval_queue.jsonl (latest record per
    approval_id wins, since status/decision change on review)."""

    _FILE = "approval_queue.jsonl"

    def __init__(self) -> None:
        self._entries: dict[str, ApprovalQueueEntry] = {}
        self._lock = Lock()
        for record in _read_jsonl(self._FILE):
            try:
                entry = _approval_from_dict(record)
                self._entries[entry.approval_id] = entry
            except Exception:
                continue

    def enqueue(self, entry: ApprovalQueueEntry) -> str:
        with self._lock:
            self._entries[entry.approval_id] = entry
        _append_jsonl(self._FILE, entry.to_dict())
        return entry.approval_id

    def save(self, entry: ApprovalQueueEntry) -> None:
        """Persist an update to an already-enqueued entry (e.g. after a
        review sets status/decision/approver_id) — `enqueue` only covers
        the initial creation."""
        with self._lock:
            self._entries[entry.approval_id] = entry
        _append_jsonl(self._FILE, entry.to_dict())

    def get(self, approval_id: str) -> ApprovalQueueEntry | None:
        return self._entries.get(approval_id)

    def list_pending(self) -> list[ApprovalQueueEntry]:
        return [e for e in self._entries.values() if e.status == "PENDING"]

    def list_all(self) -> list[ApprovalQueueEntry]:
        return sorted(self._entries.values(), key=lambda e: e.created_at, reverse=True)


class PolicyMemoryRepository:
    """Minimal Policy Memory store (Blueprint v0.1 §9 PolicyRule, MVP),
    persisted to data/learning/policy_memory.jsonl."""

    _FILE = "policy_memory.jsonl"

    def __init__(self) -> None:
        self._policies: dict[str, PolicyMemoryEntry] = {}
        self._lock = Lock()
        for record in _read_jsonl(self._FILE):
            try:
                policy = _policy_from_dict(record)
                self._policies[policy.policy_id] = policy
            except Exception:
                continue

    def save(self, policy: PolicyMemoryEntry) -> str:
        with self._lock:
            self._policies[policy.policy_id] = policy
        _append_jsonl(self._FILE, policy.to_dict())
        return policy.policy_id

    def list_active(self) -> list[PolicyMemoryEntry]:
        return [p for p in self._policies.values() if p.active]

    def list_all(self) -> list[PolicyMemoryEntry]:
        return sorted(self._policies.values(), key=lambda p: p.approved_at, reverse=True)


class ActivityFeedRepository:
    """User-facing Activity Feed entries emitted by the Learning Domain
    (Blueprint v0.2 §8.9), persisted to
    data/learning/activity_feed.jsonl (append-only)."""

    _FILE = "activity_feed.jsonl"

    def __init__(self) -> None:
        self._entries: list[ActivityFeedEntry] = []
        self._lock = Lock()
        for record in _read_jsonl(self._FILE):
            try:
                self._entries.append(_activity_from_dict(record))
            except Exception:
                continue

    def record(self, entry: ActivityFeedEntry) -> str:
        with self._lock:
            self._entries.append(entry)
        _append_jsonl(self._FILE, entry.to_dict())
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