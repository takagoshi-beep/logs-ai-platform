from __future__ import annotations

from typing import Any

from ai.gateway import LLMGateway
from answer.generator import generate_answer
from context.builder import build_context
from intent.classifier import classify_intent
from learning.query_log import save_query_log
from memory.store import save_memory
from planner.plan import create_plan
from validation.report import get_latest_validation_report
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
    intent: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None,
    workflow: dict[str, Any] | None = None,
    answer: str | None = None,
) -> str:
    return save_query_log(
        message=message,
        intent=intent or (plan or {}).get("intent", {}),
        plan=plan or {},
        workflow=workflow or {},
        answer=answer,
        success=False,
        error=error,
    )


def run_chat(message: str, user_id: str = "default") -> dict[str, Any]:
    text = (message or "").strip()

    plan: dict[str, Any] = {}
    workflow: dict[str, Any] = {}
    results: list[dict[str, Any]] = []
    answer_text: str | None = None
    context: dict[str, Any] = {}
    intent: dict[str, Any] = {}
    validation: dict[str, Any] = {}

    latest_validation = get_latest_validation_report()
    if latest_validation:
        validation = {
            "report_id": latest_validation.get("report_id"),
            "status": latest_validation.get("status"),
            "checked_at": latest_validation.get("checked_at"),
            "score": latest_validation.get("score"),
        }

    try:
        context_result = build_context(text, user_id=user_id)
        context = context_result.to_dict()
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "message": text, "error": str(exc), "stage": "context"}

    try:
        intent_result = classify_intent(text, context=context)
        intent = intent_result.to_dict()
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "message": text, "error": str(exc), "stage": "intent"}

    try:
        plan = create_plan(text, context, intent)
    except Exception as exc:  # noqa: BLE001
        error_text = str(exc)
        try:
            log_id = _save_failure_log(text, error_text, intent=intent)
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
        draft_answer = answer_payload.get("answer", "")
        gateway = LLMGateway.from_env()
        answer_text = gateway.generate_answer(
            message=text,
            plan=plan,
            workflow=workflow,
            results=results,
            draft_answer=draft_answer,
        )
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
            intent=intent or plan.get("intent", {}),
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
                "intent": intent,
            "plan": plan,
            "workflow": workflow,
            "results": results,
            "answer": answer_text or "",
        }

    try:
        tools_used = [str(step.get("name", "")) for step in workflow.get("steps", []) if step.get("name")]
        tags = list(plan.get("intent", {}).get("keywords", []) or [])
        save_memory(
            {
                "user_id": user_id,
                "message": text,
                "answer": answer_text or "",
                "intent": plan.get("intent", {}),
                "tools_used": tools_used,
                "tags": tags,
                "importance": "normal",
                "source_log_id": log_id,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "message": text,
            "error": str(exc),
            "stage": "memory",
            "plan": plan,
            "workflow": workflow,
            "results": results,
            "answer": answer_text or "",
            "log_id": log_id,
        }

    if not success:
        return {
            "success": False,
            "message": text,
            "error": workflow_error,
            "stage": "workflow",
            "context": context,
            "validation": validation,
            "plan": plan,
            "workflow": workflow,
            "results": results,
            "answer": answer_text or "",
            "log_id": log_id,
        }

    return {
        "success": True,
        "message": text,
        "intent": intent,
        "context": context,
        "validation": validation,
        "plan": plan,
        "workflow": workflow,
        "results": results,
        "answer": answer_text or "",
        "log_id": log_id,
    }
