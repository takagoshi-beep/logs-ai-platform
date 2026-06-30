from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class KnowledgeRecord:
    source_type: str
    source_name: str
    trust_level: str
    freshness: str
    updated_at: str
    retrieval_method: str
    cost: str
    permission: str
    citation_required: bool
    content: dict[str, Any] = field(default_factory=dict)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def retrieve_internal(query: str, required_sources: list[str] | None = None) -> list[KnowledgeRecord]:
    """Stub retrieval for internal sources.

    This function intentionally does not access real systems yet.
    It only returns metadata placeholders for architecture integration.
    """
    sources = required_sources or ["Internal Database", "Business Dictionary", "Business Rules"]
    return [
        KnowledgeRecord(
            source_type="internal",
            source_name=source,
            trust_level="high",
            freshness="normal",
            updated_at=_now_iso(),
            retrieval_method="stub",
            cost="low",
            permission="internal_read",
            citation_required=False,
            content={"query": query},
        )
        for source in sources
    ]


def retrieve_external(query: str, required_sources: list[str] | None = None) -> list[KnowledgeRecord]:
    """Stub retrieval for external sources.

    Web/news/market integrations are intentionally not implemented yet.
    """
    sources = required_sources or ["Web Search", "News", "Industry Report"]
    return [
        KnowledgeRecord(
            source_type="external",
            source_name=source,
            trust_level="medium",
            freshness="high",
            updated_at=_now_iso(),
            retrieval_method="stub",
            cost="medium",
            permission="external_read",
            citation_required=True,
            content={"query": query},
        )
        for source in sources
    ]


def prioritize_sources(records: list[KnowledgeRecord]) -> list[KnowledgeRecord]:
    """Prioritize by trust level and freshness.

    Order: high trust > medium trust > low trust, then high freshness first.
    """

    trust_rank = {"high": 0, "medium": 1, "low": 2}
    freshness_rank = {"high": 0, "normal": 1, "low": 2}

    return sorted(
        records,
        key=lambda item: (
            trust_rank.get(item.trust_level, 9),
            freshness_rank.get(item.freshness, 9),
            item.source_type,
            item.source_name,
        ),
    )


def merge_context(internal_records: list[KnowledgeRecord], external_records: list[KnowledgeRecord]) -> dict[str, Any]:
    """Merge internal/external context into a single runtime payload."""
    combined = prioritize_sources([*internal_records, *external_records])
    return {
        "knowledge_used_internal": [r.source_name for r in combined if r.source_type == "internal"],
        "knowledge_used_external": [r.source_name for r in combined if r.source_type == "external"],
        "citation_required": any(r.citation_required for r in combined),
        "records": [
            {
                "source_type": r.source_type,
                "source_name": r.source_name,
                "trust_level": r.trust_level,
                "freshness": r.freshness,
                "updated_at": r.updated_at,
                "retrieval_method": r.retrieval_method,
                "cost": r.cost,
                "permission": r.permission,
                "citation_required": r.citation_required,
            }
            for r in combined
        ],
    }
