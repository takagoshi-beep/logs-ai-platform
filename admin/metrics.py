from __future__ import annotations

from typing import Any

from learning.feedback import list_feedbacks
from learning.improvements import list_improvements
from learning.query_log import list_query_logs
from self_awareness.capabilities import get_capabilities
from self_awareness.status import get_ai_status


def get_usage_metrics() -> dict[str, Any]:
    logs = list_query_logs()
    return {
        "total_queries": len(logs),
        "successful_queries": sum(1 for item in logs if item.get("success")),
        "failed_queries": sum(1 for item in logs if not item.get("success")),
    }


def get_improvement_metrics() -> dict[str, Any]:
    improvements = list_improvements()
    return {
        "open_improvements": sum(1 for item in improvements if item.get("status") == "open"),
        "proposed_improvements": sum(1 for item in improvements if item.get("status") == "proposed"),
        "approved_improvements": sum(1 for item in improvements if item.get("status") == "approved"),
        "implemented_improvements": sum(1 for item in improvements if item.get("status") == "implemented"),
    }


def get_quality_metrics() -> dict[str, Any]:
    logs = list_query_logs()
    feedbacks = list_feedbacks()
    return {
        "feedback_count": len(feedbacks),
        "negative_feedback_count": sum(1 for item in feedbacks if item.get("status") in {"wrong", "not_helpful", "needs_followup"}),
        "successful_queries": sum(1 for item in logs if item.get("success")),
        "failed_queries": sum(1 for item in logs if not item.get("success")),
    }
