"""Learning Center API — exposes the repo-root `learning/` domain module
(Blueprint v0.2 Ch.8: Operational/Governed Learning, Approval Queue,
Policy Memory, Activity Feed) to the backend/ (Next.js-facing) surface.

Until 2026-07-06 this domain existed only as a standalone, unit-tested
module (`learning/`, used by the old `app/` reference implementation)
with no route in `backend/api/` at all — the frontend's `/learning` page
called a `GET /api/learning/center` that simply didn't exist anywhere.
This router is the missing connection, not a reimplementation: it reads
and writes through `learning/repository.py` and `learning/service.py`
exactly as they already were (now with durable JSONL persistence, see
`learning/repository.py`'s docstring).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from learning.repository import (
    get_activity_feed,
    get_approval_queue,
    get_candidate_repository,
    get_policy_memory,
)
from learning.service import review_governed_candidate

router = APIRouter(prefix="/api/learning", tags=["learning"])


@router.get("/center")
def learning_center() -> dict:
    """Everything the Learning Center page needs in one call: Operational
    and Governed candidates, the Approval Queue, Policy Memory, and the
    Activity Feed — matching the frontend's `LearningCenterData` shape."""
    candidates = get_candidate_repository()
    return {
        "success": True,
        "operational": [c.to_dict() for c in candidates.list(learning_type="operational")],
        "governed": [c.to_dict() for c in candidates.list(learning_type="governed")],
        "approval_queue": [e.to_dict() for e in get_approval_queue().list_all()],
        "policy_memory": [p.to_dict() for p in get_policy_memory().list_all()],
        "activity": [a.to_dict() for a in get_activity_feed().list(limit=50)],
    }


class ReviewRequest(BaseModel):
    decision: str  # "APPROVED" | "REJECTED"
    approver_id: str
    reason: str


@router.post("/approval-queue/{approval_id}/review")
def review_approval(approval_id: str, request: ReviewRequest) -> dict:
    entry = get_approval_queue().get(approval_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Approval queue entry {approval_id} not found")

    candidate = get_candidate_repository().get(entry.candidate_id)
    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate {entry.candidate_id} for approval {approval_id} not found",
        )

    try:
        updated = review_governed_candidate(
            candidate,
            approval_id=approval_id,
            decision=request.decision,
            approver_id=request.approver_id,
            reason=request.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"success": True, "candidate": updated.to_dict()}