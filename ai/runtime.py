from __future__ import annotations

from typing import Any

from answer.generator import generate_answer
from learning.query_log import save_query_log
from planner.plan import create_plan
from workflow.builder import create_workflow
from workflow.engine import execute_workflow


def _enrich_workflow_results(workflow: dict[str, Any], results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    step_types = {step.get("id"): step.get("type", "unknown") for step in workflow.get("steps", [])}
    enriched = []

    for item in results:
        enriched.append(
            {
                "step": item.get("step"),
                "type": step_types.get(item.get("step"), "unknown"),
                "status": item.get("status", "failed"),
                "result": item.get("result"),
            }
        )

    return enriched


def _save_failure_log(
    message: str,
    error: str,
    plan: dict[str, Any] | None = None,
    workflow: dict[str, Any] | None = None,
    answer: str | None = None,
) -> str:
    return save_query_log(
        message=message,
        intent=(plan or {}).get("intent", {}),
        plan=plan or {},
        workflow=workflow or {},
        answer=answer,
        success=False,
        error=error,
    )


def run_chat(message: str) -> dict[str, Any]:
    text = (message or "").strip()

    plan: dict[str, Any] = {}
    workflow: dict[str, Any] = {}
    results: list[dict[str, Any]] = []
    answer_text: str | None = None

    try:
        plan = create_plan(text)
    except Exception as exc:  # noqa: BLE001
        error_text = str(exc)
        try:
            log_id = _save_failure_log(text, error_text)
            return {"success": False, "message": text, "error": error_text, "stage": "planner", "log_id": log_id}
        except Exception as log_exc:  # noqa: BLE001
            return {"success": False, "message": text, "error": f"{error_text}; {log_exc}", "stage": "learning"}

    try:
        workflow = create_workflow(plan)
        workflow_result = execute_workflow(workflow)
        results = _enrich_workflow_results(workflow, workflow_result.get("results", []) or [])
    except Exception as exc:  # noqa: BLE001
        error_text = str(exc)
        try:
            log_id = _save_failure_log(text, error_text, plan=plan, workflow=workflow)
            return {
                "success": False,
                "message": text,
                "error": error_text,
                "stage": "workflow",
                "plan": plan,
                "workflow": workflow,
                "results": results,
                "log_id": log_id,
            }
        except Exception as log_exc:  # noqa: BLE001
            return {"success": False, "message": text, "error": f"{error_text}; {log_exc}", "stage": "learning"}

    try:
        answer_payload = generate_answer(text, {"success": True, "results": results})
        answer_text = answer_payload.get("answer", "")
    except Exception as exc:  # noqa: BLE001
        error_text = str(exc)
        try:
            log_id = _save_failure_log(text, error_text, plan=plan, workflow=workflow)
            return {
                "success": False,
                "message": text,
                "error": error_text,
                "stage": "answer",
                "plan": plan,
                "workflow": workflow,
                "results": results,
                "log_id": log_id,
            }
        except Exception as log_exc:  # noqa: BLE001
            return {"success": False, "message": text, "error": f"{error_text}; {log_exc}", "stage": "learning"}

    success = all(item.get("status") == "completed" for item in results)
    workflow_error = None if success else "workflow execution returned failed steps"

    try:
        log_id = save_query_log(
            message=text,
            intent=plan.get("intent", {}),
            plan=plan,
            workflow=workflow,
            answer=answer_text,
            success=success,
            error=workflow_error,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "message": text,
            "error": str(exc),
            "stage": "learning",
            "plan": plan,
            "workflow": workflow,
            "results": results,
            "answer": answer_text or "",
        }

    if not success:
        return {
            "success": False,
            "message": text,
            "error": workflow_error,
            "stage": "workflow",
            "plan": plan,
            "workflow": workflow,
            "results": results,
            "answer": answer_text or "",
            "log_id": log_id,
        }

    return {
        "success": True,
        "message": text,
        "plan": plan,
        "workflow": workflow,
        "results": results,
        "answer": answer_text or "",
        "log_id": log_id,
    }
