from __future__ import annotations

from typing import Any

from memory.store import list_memories, search_memories


def build_context(message: str, user_id: str = "default") -> dict[str, Any]:
    related = [item for item in search_memories(message, limit=20) if item.get("user_id") == user_id]
    recent = [item for item in list_memories(limit=100) if item.get("user_id") == user_id][:10]

    summary_parts = []
    if related:
        summary_parts.append(f"related={len(related)}")
    if recent:
        summary_parts.append(f"recent={len(recent)}")
        latest = recent[0]
        latest_message = str(latest.get("message", ""))[:80]
        if latest_message:
            summary_parts.append(f"latest=\"{latest_message}\"")

    context_summary = "no prior context"
    if summary_parts:
        context_summary = ", ".join(summary_parts)

    return {
        "user_id": user_id,
        "related_memories": related,
        "recent_memories": recent,
        "context_summary": context_summary,
    }
