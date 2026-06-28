from __future__ import annotations

from typing import Any

from memory.store import list_memories, search_memories


class MemoryContextProvider:
    def collect(self, message: str, user_id: str, **kwargs: Any) -> dict[str, Any]:
        _ = kwargs
        related = [item for item in search_memories(message, limit=20) if item.get("user_id") == user_id]
        recent = [item for item in list_memories(limit=100) if item.get("user_id") == user_id][:10]

        return {
            "related_memories": related,
            "recent_memories": recent,
            "related_count": len(related),
            "recent_count": len(recent),
        }
