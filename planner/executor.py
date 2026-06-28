from __future__ import annotations

from typing import Any

from business.router import route_business_query
from knowledge.glossary import search_knowledge
from system.logic_registry import get_logic_registry


def execute_plan(plan: dict[str, Any]) -> dict[str, Any]:
    results = []
    for step in plan.get("steps", []):
        step_type = step.get("type")
        target = step.get("target")

        if step_type == "knowledge":
            query = plan.get("message", "")
            payload = search_knowledge(query)
            results.append({"step": step.get("step"), "status": "ok", "type": step_type, "target": target, "result": payload})
        elif step_type == "business":
            query = plan.get("message", "")
            payload = route_business_query(query)
            results.append({"step": step.get("step"), "status": "ok", "type": step_type, "target": target, "result": payload})
        elif step_type == "system":
            payload = get_logic_registry()
            results.append({"step": step.get("step"), "status": "ok", "type": step_type, "target": target, "result": payload})
        else:
            results.append({"step": step.get("step"), "status": "skipped", "type": step_type, "target": target, "result": None})

    return {"success": True, "plan": plan, "results": results}
