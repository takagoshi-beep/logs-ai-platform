from __future__ import annotations

import os
from typing import Any


class RuntimeContextProvider:
    def collect(self, message: str, user_id: str, **kwargs: Any) -> dict[str, Any]:
        _ = message
        _ = user_id
        _ = kwargs

        return {
            "runtime": "LOGS AI Runtime",
            "llm_provider": (os.getenv("LLM_PROVIDER") or "openai").strip().lower(),
            "available_layers": [
                "context",
                "memory",
                "planner",
                "workflow",
                "tools",
                "business",
                "knowledge",
                "system",
                "answer",
                "learning",
            ],
            "constraints": [
                "context does not execute business logic",
                "context does not update database",
                "llm connection is not used in context providers",
                "external api integration is not used in context providers",
                "vector search is not enabled",
            ],
        }
