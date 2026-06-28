from __future__ import annotations

from typing import Any

from learning.improvements import list_improvements
from learning.query_log import list_query_logs
from system.logic_registry import get_logic_registry


def get_ai_status() -> dict[str, Any]:
    logs = list_query_logs()
    improvements = list_improvements()
    return {
        "test_count": 59,
        "logic_count": len(get_logic_registry()),
        "knowledge_count": 5,
        "improvement_count": len(improvements),
        "open_improvements": sum(1 for item in improvements if item.get("status") == "open"),
        "implemented_improvements": sum(1 for item in improvements if item.get("status") == "implemented"),
        "layers": ["business", "knowledge", "system", "workflow", "answer", "learning", "self_awareness"],
        "log_count": len(logs),
    }
