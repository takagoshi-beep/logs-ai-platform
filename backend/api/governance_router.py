"""Governance API endpoints — minimal queue/decide/audit surface.

See `services/governance_store.py` for exactly what is and isn't
implemented (this is a deliberately reduced slice of Blueprint Chapter 11,
not the full approval-level/policy-rule/rollback workflow).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth_router import require_admin
from services import governance_store

router = APIRouter(prefix="/governance", tags=["governance"])


class DecideRequest(BaseModel):
    decision: str  # "APPROVED" | "REJECTED"
    reason: str


@router.get("/queue")
def list_queue(status: Optional[str] = None) -> dict:
    """List governance approvals, optionally filtered by status
    (e.g. `?status=QUEUED_FOR_REVIEW`)."""
    return {"items": governance_store.list_queue(status=status)}


@router.get("/{approval_id}")
def get_approval(approval_id: str) -> dict:
    approval = governance_store.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@router.post("/{approval_id}/decide")
def decide(approval_id: str, request: DecideRequest, user: dict = Depends(require_admin)) -> dict:
    """承認・却下には管理者権限が必要（14.22）。承認者名は、リクエスト
    本文の任意入力ではなく、セッションで検証済みのメールアドレスを使う
    — なりすまし防止のため、クライアントから送られてきた値は信用しない。
    """
    try:
        return governance_store.decide(
            approval_id=approval_id,
            decision=request.decision,
            approver_id=user["email"],
            reason=request.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{approval_id}/audit")
def get_audit(approval_id: str) -> dict:
    return {"items": governance_store.get_audit_trail(approval_id=approval_id)}