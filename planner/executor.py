from __future__ import annotations

from typing import Any

from tools.registry import get_default_registry


def execute_plan(plan: dict[str, Any]) -> dict[str, Any]:
    results = []
    registry = get_default_registry()
    for step in plan.get("steps", []):
        step_type = step.get("type", "unknown")
        tool_name = step.get("tool") or step.get("target") or step_type
        target = step.get("target", tool_name)

        try:
            payload = registry.execute(str(tool_name), {"message": plan.get("message", "")})
            results.append({"step": step.get("step"), "status": "ok", "type": step_type, "target": target, "result": payload})
        except ValueError:
            results.append({"step": step.get("step"), "status": "skipped", "type": step_type, "target": target, "result": None})
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "step": step.get("step"),
                    "status": "error",
                    "type": step_type,
                    "target": target,
                    "result": {"error": str(exc)},
                }
            )

    return {"success": True, "plan": plan, "results": results}
