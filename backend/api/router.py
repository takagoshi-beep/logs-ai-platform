from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from api.schemas import ChatRequest, DocumentDraftRequest, ProductEvent, ProposalDraftRequest, TasksRecommendRequest
from services.mock_store import (
    draft_document,
    draft_proposal,
    get_evaluation_summary,
    get_execution,
    get_health,
    get_history,
    get_home_payload,
    get_trace,
    recommend_tasks,
    store_event,
)

router = APIRouter(prefix="/api", tags=["v0.1"])


@router.get("/health")
def health() -> dict:
    return get_health()


@router.post("/chat")
def chat(req: ChatRequest) -> dict:
    execution_id = f"ex-chat-{datetime.now(timezone.utc).strftime('%H%M%S')}"
    trace_id = "trace-1001"
    return {
        "execution_id": execution_id,
        "trace_id": trace_id,
        "intent": "Monitoring",
        "task": "required_action_check",
        "capability": ["Data Query", "Monitoring Alert", "Presentation"],
        "validation": "pass",
        "ai_response": f"Recommended next actions for: {req.message}",
        "references": ["Fanatics task history", "Unpurchased sales alert"],
        "next_actions": ["Open workspace", "Create task batch", "Send follow-up draft"],
    }


@router.post("/tasks/recommend")
def tasks_recommend(_: TasksRecommendRequest) -> dict:
    return {
        "items": recommend_tasks(),
        "home": get_home_payload(),
    }


@router.post("/proposals/draft")
def proposals_draft(req: ProposalDraftRequest) -> dict:
    return {
        "proposal": draft_proposal(req.customer, req.purpose),
        "next_actions": ["Generate PPTX", "Review draft", "Send for approval"],
    }


@router.post("/documents/draft")
def documents_draft(req: DocumentDraftRequest) -> dict:
    return {
        "document": draft_document(req.document_type, req.target_id),
        "next_actions": ["Review missing fields", "Request approval"],
    }


@router.get("/history")
def history() -> dict:
    return {"items": get_history()}


@router.get("/executions/{execution_id}")
def execution(execution_id: str) -> dict:
    return get_execution(execution_id)


@router.get("/evaluation/summary")
def evaluation_summary() -> dict:
    return get_evaluation_summary()


@router.get("/debug/trace/{trace_id}")
def debug_trace(trace_id: str) -> dict:
    return get_trace(trace_id)


@router.post("/events")
def events(event: ProductEvent) -> dict:
    payload = event.model_dump(mode="json")
    return store_event(payload)
