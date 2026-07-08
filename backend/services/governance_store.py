"""Minimal Governance Queue for the backend API surface.

Implements a deliberately reduced slice of
`docs/blueprint/AI_OS_BLUEPRINT_v0.2_DRAFT.md` Chapter 11 (Governance
Standard): a single-step QUEUED_FOR_REVIEW -> APPROVED/REJECTED workflow
with a durable audit trail, backed by JSONL storage (same convention as
`trace_store.py` and `capability_instance.py`).

Deliberately NOT implemented (left for a future phase):
- Approval levels (LOW/MEDIUM/HIGH/ADMIN_APPROVED_REQUIRED) and
  auto-approval by confidence threshold.
- PolicyRule creation/activation/versioning/rollback.
- Approver authority/role validation — `decide()` trusts whatever
  approver_id is passed in; there is no auth check.
- Post-activation monitoring.

What IS implemented, and why it matters: the Blueprint's "Critical Rule"
for this chapter is that human approval is mandatory before any AI-derived
rule is applied — "AI never applies rules without approval." This module
gives that rule a real, working home: `reasoning_pipeline.py`'s Phase 13
knowledge candidates are auto-submitted here instead of sitting inert in
an API response, and a human decision (approve/reject/why) is durably
recorded. Approving a proposal here does NOT automatically edit any
`knowledge/` file — that "apply the approved rule" step is intentionally
left as a manual follow-up / future phase, so nothing changes business
behavior without a person deliberately doing it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from services import record_store

# 2026-07-06 (Web化準備、docs/architecture.md 14.23): ローカルJSONLから
# Supabase保存に切り替えた。document_formats.pyと全く同じ理由・同じ方式。
APPROVALS_TABLE = "app_governance_approvals"
AUDIT_TABLE = "app_governance_audit"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class GovernanceApproval:
    approval_id: str
    proposal_id: str
    source_capability_id: str
    concept: str
    ai_hypothesis: str
    confidence_score: float
    trace_id: str
    governance_level: str = "medium"
    status: str = "QUEUED_FOR_REVIEW"  # QUEUED_FOR_REVIEW | APPROVED | REJECTED
    decision: Optional[str] = None
    approver_id: Optional[str] = None
    approval_reason: Optional[str] = None
    created_at: str = field(default_factory=_now)
    decided_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _append_jsonl(table: str, record: dict[str, Any]) -> None:
    """名前はJSONL時代のまま、実体はrecord_store経由でSupabaseに保存する。"""
    try:
        record_store.append_record(table, record)
    except Exception:
        # Persistence must never block the actual response.
        pass


def _read_jsonl(table: str) -> list[dict[str, Any]]:
    """同上 — 名前はJSONL時代のまま、実体はSupabaseから読む。"""
    return record_store.read_all_records(table)


def _record_audit(approval_id: str, action: str, actor: str, details: dict[str, Any]) -> None:
    _append_jsonl(AUDIT_TABLE, {
        "audit_id": f"audit-{uuid4().hex[:8]}",
        "approval_id": approval_id,
        "action": action,
        "timestamp": _now(),
        "actor": actor,
        "details": details,
    })


AUTO_APPROVE_THRESHOLD = 0.85
"""Blueprint Chapter 11 "Approval Levels" table: LOW governance level
auto-approves only if confidence > 0.85. MEDIUM/HIGH/ADMIN_APPROVED_REQUIRED
never auto-approve regardless of confidence, per the same table."""


def submit_proposal(
    source_capability_id: str,
    concept: str,
    ai_hypothesis: str,
    confidence_score: float,
    trace_id: str,
    proposal_id: Optional[str] = None,
    governance_level: str = "medium",
) -> GovernanceApproval:
    """Submit a Learning-derived candidate for Governance review.

    Every call creates a *new* record. Callers that want to avoid
    duplicate queue entries for the same underlying proposal should pass a
    stable `proposal_id` (e.g. the originating `hypothesis_id`) and check
    `list_queue()` first — this is not enforced here, to keep this reduced
    implementation simple.

    `governance_level` (one of `capability.domain.GovernanceLevel`'s
    values: "low"/"medium"/"high"/"admin_approved_required") determines
    whether this can auto-approve. Per the Blueprint's Chapter 11 Approval
    Levels table, only "low" + confidence > `AUTO_APPROVE_THRESHOLD`
    auto-approves; everything else always lands in the manual queue
    (`QUEUED_FOR_REVIEW`) regardless of confidence.
    """
    auto_approved = (
        governance_level == "low" and confidence_score > AUTO_APPROVE_THRESHOLD
    )
    now = _now()

    approval = GovernanceApproval(
        approval_id=f"gov-{uuid4().hex[:8]}",
        proposal_id=proposal_id or f"proposal-{uuid4().hex[:8]}",
        source_capability_id=source_capability_id,
        concept=concept,
        ai_hypothesis=ai_hypothesis,
        confidence_score=confidence_score,
        trace_id=trace_id,
        governance_level=governance_level,
        status="APPROVED" if auto_approved else "QUEUED_FOR_REVIEW",
        decision="APPROVED" if auto_approved else None,
        approver_id="system:auto-approved" if auto_approved else None,
        approval_reason=(
            f"Auto-approved: governance_level=low and confidence "
            f"{confidence_score:.2f} > {AUTO_APPROVE_THRESHOLD} "
            f"(Blueprint Chapter 11 Approval Levels table)"
        ) if auto_approved else None,
        decided_at=now if auto_approved else None,
    )
    _append_jsonl(APPROVALS_TABLE, approval.to_dict())
    _record_audit(
        approval.approval_id,
        "AUTO_APPROVED" if auto_approved else "PROPOSAL_RECEIVED",
        actor="system",
        details={"concept": concept, "governance_level": governance_level, "confidence_score": confidence_score},
    )
    return approval


def _latest_by_approval_id() -> dict[str, dict[str, Any]]:
    """Approvals are append-only snapshots; the latest line per
    approval_id wins — same "most recent record" pattern as
    `trace_store.get_trace`.
    """
    latest: dict[str, dict[str, Any]] = {}
    for record in _read_jsonl(APPROVALS_TABLE):
        approval_id = record.get("approval_id")
        if approval_id:
            latest[approval_id] = record
    return latest


def list_queue(status: Optional[str] = None) -> list[dict[str, Any]]:
    """List governance approvals, optionally filtered by status."""
    records = list(_latest_by_approval_id().values())
    if status:
        records = [r for r in records if r.get("status") == status]
    records.sort(key=lambda r: r.get("created_at", ""))
    return records


def get_approval(approval_id: str) -> Optional[dict[str, Any]]:
    return _latest_by_approval_id().get(approval_id)


def decide(
    approval_id: str,
    decision: str,
    approver_id: str,
    reason: str,
) -> dict[str, Any]:
    """Record a human decision on a queued approval.

    `decision` must be "APPROVED" or "REJECTED". This does not check
    approver identity/authority (see module docstring) — recording *who*
    claims to have decided, and *why*, is the minimum the Blueprint's
    Critical Rule requires; role enforcement is future work.
    """
    if decision not in ("APPROVED", "REJECTED"):
        raise ValueError(f"decision must be APPROVED or REJECTED, got {decision!r}")

    current = get_approval(approval_id)
    if not current:
        raise ValueError(f"Approval {approval_id} not found")
    if current.get("status") != "QUEUED_FOR_REVIEW":
        raise ValueError(
            f"Approval {approval_id} is not pending (status={current.get('status')})"
        )

    updated = dict(current)
    updated["status"] = decision
    updated["decision"] = decision
    updated["approver_id"] = approver_id
    updated["approval_reason"] = reason
    updated["decided_at"] = _now()

    _append_jsonl(APPROVALS_TABLE, updated)
    _record_audit(approval_id, decision, actor=approver_id, details={"reason": reason})
    return updated


def get_audit_trail(approval_id: Optional[str] = None) -> list[dict[str, Any]]:
    records = _read_jsonl(AUDIT_TABLE)
    if approval_id:
        records = [r for r in records if r.get("approval_id") == approval_id]
    return records