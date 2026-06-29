from __future__ import annotations

from typing import Any

from answer.formatter import format_business_result, format_knowledge_result, format_ranking_result, format_system_result


def generate_answer(message: str, workflow_result: dict[str, Any]) -> dict[str, Any]:
    results = workflow_result.get("results", []) or []
    sections = []

    for item in results:
        step_type = item.get("type")
        result_payload = item.get("result")

        if step_type == "knowledge":
            sections.append(f"知識:\n{format_knowledge_result(result_payload)}")
        elif step_type == "business":
            sections.append(f"業務:\n{format_business_result(result_payload)}")
        elif step_type == "system":
            sections.append(f"システム:\n{format_system_result(result_payload)}")

    if not sections:
        answer = "処理結果はありませんでした。"
    else:
        answer = "\n\n".join(sections)

    return {"success": True, "message": message, "answer": answer}
