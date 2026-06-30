from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass
class MemoryRecord:
    memory_id: str
    memory_type: str
    title: str
    summary: str
    related_entities: list[str] = field(default_factory=list)
    related_customers: list[str] = field(default_factory=list)
    related_projects: list[str] = field(default_factory=list)
    related_staff: list[str] = field(default_factory=list)
    related_dates: list[str] = field(default_factory=list)
    source_type: str = "internal"
    source_name: str = "memory_store_stub"
    occurred_at: str = ""
    recorded_at: str = ""
    confidence: float = 0.8
    importance: str = "medium"
    sensitivity: str = "internal"
    permission_scope: str = "team"
    retention_policy: str = "standard"
    citation_required: bool = True
    linked_documents: list[str] = field(default_factory=list)
    linked_messages: list[str] = field(default_factory=list)
    linked_tasks: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _recent_iso(days_ago: int = 7) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def _stub_record(memory_type: str, query: str) -> MemoryRecord:
    return MemoryRecord(
        memory_id=f"mem-{memory_type}-stub",
        memory_type=memory_type,
        title=f"{memory_type} reference",
        summary=f"Stub memory for query: {query}",
        source_type="internal",
        source_name="memory_store_stub",
        occurred_at=_recent_iso(7),
        recorded_at=_now_iso(),
        confidence=0.78,
        importance="medium",
        sensitivity="internal",
        permission_scope="team",
        retention_policy="standard",
        citation_required=True,
        tags=["stub", "theme23"],
    )


def retrieve_memory(query: str, required_memory_types: list[str] | None = None) -> list[MemoryRecord]:
    """Stub memory retrieval dispatcher.

    Real Gmail/Slack/Drive and enterprise memory retrieval are intentionally not implemented.
    """
    types = required_memory_types or ["project_memory", "task_memory", "communication_memory"]
    return [_stub_record(memory_type=item, query=query) for item in types]


def retrieve_customer_memory(customer: str, query: str | None = None) -> list[MemoryRecord]:
    q = query or customer
    records = retrieve_memory(q, required_memory_types=["customer_memory", "proposal_memory", "feedback_memory"])
    for item in records:
        item.related_customers = [customer]
    return records


def retrieve_project_memory(project: str, query: str | None = None) -> list[MemoryRecord]:
    q = query or project
    records = retrieve_memory(q, required_memory_types=["project_memory", "issue_memory", "task_memory"])
    for item in records:
        item.related_projects = [project]
    return records


def retrieve_proposal_memory(entity: str, query: str | None = None) -> list[MemoryRecord]:
    q = query or entity
    records = retrieve_memory(q, required_memory_types=["proposal_memory", "meeting_memory", "learning_memory"])
    for item in records:
        item.related_entities = [entity]
    return records


def retrieve_task_memory(scope: str = "today", query: str | None = None) -> list[MemoryRecord]:
    q = query or scope
    records = retrieve_memory(q, required_memory_types=["task_memory", "project_memory", "communication_memory"])
    for item in records:
        item.tags.append(scope)
    return records


def prioritize_memory(records: list[MemoryRecord]) -> list[MemoryRecord]:
    """Prioritize memory by importance, confidence, and recency."""
    importance_rank = {"high": 0, "medium": 1, "low": 2}

    def _sort_key(item: MemoryRecord) -> tuple[Any, ...]:
        occurred = item.occurred_at or ""
        return (
            importance_rank.get(item.importance, 9),
            -float(item.confidence),
            -len(occurred),
            item.memory_type,
            item.memory_id,
        )

    return sorted(records, key=_sort_key)


def filter_memory_by_permission(records: list[MemoryRecord], allowed_scopes: list[str] | None = None) -> list[MemoryRecord]:
    scopes = allowed_scopes or ["team", "department", "internal"]
    allowed = set(scopes)
    return [item for item in records if item.permission_scope in allowed]


def merge_knowledge_and_memory(knowledge_context: dict[str, Any], memory_records: list[MemoryRecord]) -> dict[str, Any]:
    """Return merged metadata payload for execution/presentation planning."""
    prioritized = prioritize_memory(memory_records)
    filtered = filter_memory_by_permission(prioritized)

    return {
        "knowledge_scope": knowledge_context.get("required_knowledge_scope"),
        "knowledge_used_internal": knowledge_context.get("internal_sources", []),
        "knowledge_used_external": knowledge_context.get("external_sources", []),
        "memory_types": [item.memory_type for item in filtered],
        "memory_count": len(filtered),
        "permission_filtered": len(filtered) != len(prioritized),
        "citation_required": bool(knowledge_context.get("citation_required")) or any(item.citation_required for item in filtered),
        "memory_trace": [
            {
                "memory_id": item.memory_id,
                "memory_type": item.memory_type,
                "title": item.title,
                "occurred_at": item.occurred_at,
                "confidence": item.confidence,
                "permission_scope": item.permission_scope,
                "source_name": item.source_name,
            }
            for item in filtered
        ],
    }
