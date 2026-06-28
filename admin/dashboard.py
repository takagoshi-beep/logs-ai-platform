from __future__ import annotations

from typing import Any

from change_management.repository import list_change_requests
from learning.improvements import list_improvements
from self_awareness.capabilities import get_capabilities
from self_awareness.status import get_ai_status
from admin.metrics import get_improvement_metrics, get_quality_metrics, get_usage_metrics


def get_admin_dashboard() -> dict[str, Any]:
    status = get_ai_status()
    improvements = list_improvements()
    changes = list_change_requests()
    return {
        "summary": {
            "total_queries": get_usage_metrics()["total_queries"],
            "feedback_count": get_quality_metrics()["feedback_count"],
            "open_improvements": get_improvement_metrics()["open_improvements"],
            "implemented_improvements": get_improvement_metrics()["implemented_improvements"],
            "test_count": status["test_count"],
            "knowledge_count": status["knowledge_count"],
            "business_logic_count": 4,
            "system_logic_count": status["logic_count"],
            "pending_approval_count": sum(1 for item in changes if item.get("status") == "review"),
            "pending_implementation_count": sum(1 for item in changes if item.get("status") == "approved"),
            "pending_test_count": sum(1 for item in changes if item.get("status") == "implemented"),
            "pending_release_count": sum(1 for item in changes if item.get("status") == "tested"),
        },
        "health": {
            "status": "ok",
            "layers": status["layers"],
        },
        "recent_improvements": improvements[-5:],
        "recommendations": [
            {"title": item.get("title"), "priority": item.get("priority"), "status": item.get("status")}
            for item in improvements[:5]
        ],
    }
