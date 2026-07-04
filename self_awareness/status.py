from __future__ import annotations

from typing import Any

from knowledge.glossary import get_glossary_terms
from learning.improvements import list_improvements
from learning.query_log import list_query_logs
from system.logic_registry import get_logic_registry

# NOTE: test_count is a manually-maintained figure, not computed at runtime
# (there is no lightweight way to count the test suite without invoking
# pytest itself). Update this value when the test suite size changes
# meaningfully; do not treat it as a live, verified count.
_KNOWN_TEST_COUNT = 59


def get_ai_status() -> dict[str, Any]:
    logs = list_query_logs()
    improvements = list_improvements()
    return {
        "test_count": _KNOWN_TEST_COUNT,
        "logic_count": len(get_logic_registry()),
        "knowledge_count": len(get_glossary_terms()),
        "improvement_count": len(improvements),
        "open_improvements": sum(1 for item in improvements if item.get("status") == "open"),
        "implemented_improvements": sum(1 for item in improvements if item.get("status") == "implemented"),
        "layers": ["business", "knowledge", "system", "workflow", "answer", "learning", "self_awareness"],
        "log_count": len(logs),
    }