from __future__ import annotations

from typing import Any

from learning.feedback import list_feedbacks
from learning.query_log import list_query_logs


def get_learning_summary() -> dict[str, Any]:
    logs = list_query_logs()
    feedbacks = list_feedbacks()
    return {
        "total_logs": len(logs),
        "total_feedbacks": len(feedbacks),
        "successful_logs": sum(1 for item in logs if item.get("success")),
        "negative_feedback": [item for item in feedbacks if item.get("status") in {"wrong", "not_helpful", "needs_followup"}],
    }


def suggest_improvements() -> list[dict[str, Any]]:
    logs = list_query_logs()
    suggestions = []
    for item in logs:
        if item.get("feedback_status") in {"wrong", "not_helpful", "needs_followup"}:
            suggestions.append(
                {
                    "source_log_id": item.get("log_id"),
                    "title": f"改善候補: {item.get('message', '')[:20]}",
                    "description": item.get("feedback_comment") or "フィードバックから改善候補を作成しました。",
                    "category": "answer_quality",
                }
            )
    return suggestions
