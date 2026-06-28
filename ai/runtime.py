from __future__ import annotations

from time import perf_counter
from typing import Any

from ai.gateway import LLMGateway
from answer.generator import generate_answer
from context.builder import build_context
from conversation.resolver import resolve_conversation_context
from conversation.store import create_conversation, save_turn
from intent.classifier import classify_intent
from learning.query_log import save_query_log
from memory.store import save_memory
from observability.tracer import add_trace_record, start_trace_session
from planner.plan import create_plan
from session.manager import attach_trace_id, create_session
from config.settings import get_settings
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


def _finalize_trace(
    trace_session,
    runtime_input: dict[str, Any],
    response: dict[str, Any],
    started_at: float,
    error: str | None = None,
) -> dict[str, Any]:
    elapsed_ms = (perf_counter() - started_at) * 1000.0
    trace_session.success = bool(response.get("success"))
    add_trace_record(trace_session, "Runtime", runtime_input, response, elapsed_ms, bool(response.get("success")), error=error)
    response["trace_id"] = trace_session.trace_id
    return response


def run_chat(
    message: str,
    user_id: str = "default",
    session_id: str | None = None,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    text = (message or "").strip()
    settings = get_settings()
    session = create_session(user_id=user_id, organization_id=settings.default_organization_id, session_id=session_id)
    trace_session = start_trace_session(text, user_id=user_id)
    runtime_input = {"message": text, "user_id": user_id}
    started_at = perf_counter()
    attach_trace_id(session.session_id, trace_session.trace_id)

    conversation_context = resolve_conversation_context(text, conversation_id, user_id=user_id)
    conversation_id = str(conversation_context.get("conversation_id") or conversation_id or create_conversation(user_id))

    plan: dict[str, Any] = {}
    workflow: dict[str, Any] = {}
    results: list[dict[str, Any]] = []
    answer_text: str | None = None
    context: dict[str, Any] = {}
    intent: dict[str, Any] = {}
    validation: dict[str, Any] = {}

    latest_validation = get_latest_validation_report()
    validation_output = {
        "report_id": None,
        "status": None,
        "checked_at": None,
        "score": None,
    }
    if latest_validation:
        validation_output = {
            "report_id": latest_validation.get("report_id"),
            "status": latest_validation.get("status"),
            "checked_at": latest_validation.get("checked_at"),
            "score": latest_validation.get("score"),
        }
    validation = validation_output
    add_trace_record(trace_session, "Validation", {"latest_validation": latest_validation}, validation_output, 0.0, True)

    try:
        context_started_at = perf_counter()
        context_result = build_context(text, user_id=user_id, conversation_context=conversation_context)
        context = context_result.to_dict()
        add_trace_record(
            trace_session,
            "Context",
            {"message": text, "user_id": user_id},
            context,
            (perf_counter() - context_started_at) * 1000.0,
            True,
        )
    except Exception as exc:  # noqa: BLE001
        response = {"success": False, "message": text, "error": str(exc), "stage": "context"}
        add_trace_record(trace_session, "Context", {"message": text, "user_id": user_id}, response, 0.0, False, error=str(exc))
        return _finalize_trace(trace_session, runtime_input, response, started_at, error=str(exc))

    try:
        intent_started_at = perf_counter()
        intent_result = classify_intent(text, context=context)
        intent = intent_result.to_dict()
        add_trace_record(
            trace_session,
            "Intent",
            {"message": text, "context": context},
            intent,
            (perf_counter() - intent_started_at) * 1000.0,
            True,
        )
    except Exception as exc:  # noqa: BLE001
        response = {"success": False, "message": text, "error": str(exc), "stage": "intent"}
        add_trace_record(trace_session, "Intent", {"message": text, "context": context}, response, 0.0, False, error=str(exc))
        return _finalize_trace(trace_session, runtime_input, response, started_at, error=str(exc))

    try:
        planner_started_at = perf_counter()
        plan = create_plan(text, context, intent)
        add_trace_record(
            trace_session,
            "Planner",
            {"message": text, "context": context, "intent": intent},
            plan,
            (perf_counter() - planner_started_at) * 1000.0,
            True,
        )
    except Exception as exc:  # noqa: BLE001
        error_text = str(exc)
        failure_response = {"success": False, "message": text, "error": error_text, "stage": "planner"}
        add_trace_record(trace_session, "Planner", {"message": text, "context": context, "intent": intent}, failure_response, 0.0, False, error=error_text)
        try:
            log_id = _save_failure_log(text, error_text, intent=intent)
            failure_response["log_id"] = log_id
            return _finalize_trace(trace_session, runtime_input, failure_response, started_at, error=error_text)
        except Exception as log_exc:  # noqa: BLE001
            response = {"success": False, "message": text, "error": f"{error_text}; {log_exc}", "stage": "learning"}
            return _finalize_trace(trace_session, runtime_input, response, started_at, error=response["error"])

    try:
        workflow_started_at = perf_counter()
        workflow = create_workflow(plan)
        workflow_result = execute_workflow(workflow)
        results = _enrich_workflow_results(workflow, workflow_result.get("results", []) or [])
        add_trace_record(
            trace_session,
            "Workflow",
            {"plan": plan, "workflow": workflow},
            {"workflow_result": workflow_result, "results": results},
            (perf_counter() - workflow_started_at) * 1000.0,
            True,
        )
        step_by_id = {str(step.get("id")): step for step in workflow.get("steps", [])}
        for item in results:
            layer = str(item.get("type") or "").strip().lower()
            if layer not in {"business", "knowledge"}:
                continue
            step = step_by_id.get(str(item.get("step")), {})
            item_result = item.get("result")
            step_success = item.get("status") == "completed"
            step_error = None
            if not step_success:
                if isinstance(item_result, dict):
                    step_error = str(item_result.get("error", "workflow step failed"))
                else:
                    step_error = str(item_result)
            add_trace_record(
                trace_session,
                layer.capitalize(),
                {"step": step, "result": item},
                item_result,
                0.0,
                step_success,
                error=step_error,
            )
    except Exception as exc:  # noqa: BLE001
        error_text = str(exc)
        failure_response = {
            "success": False,
            "message": text,
            "error": error_text,
            "stage": "workflow",
            "plan": plan,
            "workflow": workflow,
            "results": results,
        }
        add_trace_record(trace_session, "Workflow", {"plan": plan, "workflow": workflow}, failure_response, 0.0, False, error=error_text)
        try:
            log_id = _save_failure_log(text, error_text, plan=plan, workflow=workflow)
            failure_response["log_id"] = log_id
            return _finalize_trace(trace_session, runtime_input, failure_response, started_at, error=error_text)
        except Exception as log_exc:  # noqa: BLE001
            response = {"success": False, "message": text, "error": f"{error_text}; {log_exc}", "stage": "learning"}
            return _finalize_trace(trace_session, runtime_input, response, started_at, error=response["error"])

    try:
        answer_started_at = perf_counter()
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
        add_trace_record(
            trace_session,
            "Answer",
            {"message": text, "plan": plan, "workflow": workflow, "results": results, "draft_answer": draft_answer},
            {"answer": answer_text},
            (perf_counter() - answer_started_at) * 1000.0,
            True,
        )
    except Exception as exc:  # noqa: BLE001
        error_text = str(exc)
        failure_response = {
            "success": False,
            "message": text,
            "error": error_text,
            "stage": "answer",
            "plan": plan,
            "workflow": workflow,
            "results": results,
        }
        add_trace_record(trace_session, "Answer", {"message": text, "plan": plan, "workflow": workflow, "results": results}, failure_response, 0.0, False, error=error_text)
        try:
            log_id = _save_failure_log(text, error_text, plan=plan, workflow=workflow)
            failure_response["log_id"] = log_id
            return _finalize_trace(trace_session, runtime_input, failure_response, started_at, error=error_text)
        except Exception as log_exc:  # noqa: BLE001
            response = {"success": False, "message": text, "error": f"{error_text}; {log_exc}", "stage": "learning"}
            return _finalize_trace(trace_session, runtime_input, response, started_at, error=response["error"])

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
        response = {
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
        return _finalize_trace(trace_session, runtime_input, response, started_at, error=str(exc))

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
        response = {
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
        return _finalize_trace(trace_session, runtime_input, response, started_at, error=str(exc))

    try:
        save_turn(
            conversation_id=conversation_id,
            user_id=user_id,
            message=text,
            answer=answer_text or "",
            trace_id=trace_session.trace_id,
            intent_type=intent.get("intent_type") if isinstance(intent, dict) else None,
        )
    except Exception as exc:  # noqa: BLE001
        response = {
            "success": False,
            "message": text,
            "error": str(exc),
            "stage": "conversation",
            "session_id": session.session_id,
            "conversation_id": conversation_id,
            "plan": plan,
            "workflow": workflow,
            "results": results,
            "answer": answer_text or "",
        }
        return _finalize_trace(trace_session, runtime_input, response, started_at, error=str(exc))

    if not success:
        response = {
            "success": False,
            "message": text,
            "error": workflow_error,
            "stage": "workflow",
            "context": context,
            "validation": validation,
            "session_id": session.session_id,
            "conversation_id": conversation_id,
            "plan": plan,
            "workflow": workflow,
            "results": results,
            "answer": answer_text or "",
            "log_id": log_id,
        }
        return _finalize_trace(trace_session, runtime_input, response, started_at, error=workflow_error)

    response = {
        "success": True,
        "message": text,
        "intent": intent,
        "context": context,
        "validation": validation,
        "session_id": session.session_id,
        "conversation_id": conversation_id,
        "plan": plan,
        "workflow": workflow,
        "results": results,
        "answer": answer_text or "",
        "log_id": log_id,
    }
    return _finalize_trace(trace_session, runtime_input, response, started_at)
