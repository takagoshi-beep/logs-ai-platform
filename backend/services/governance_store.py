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

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
APPROVALS_PATH = DATA_DIR / "governance_approvals.jsonl"
AUDIT_PATH = DATA_DIR / "governance_audit.jsonl"


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
    status: str = "QUEUED_FOR_REVIEW"  # QUEUED_FOR_REVIEW | APPROVED | REJECTED
    decision: Optional[str] = None
    approver_id: Optional[str] = None
    approval_reason: Optional[str] = None
    created_at: str = field(default_factory=_now)
    decided_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception:
        # Persistence must never block the actual response.
        pass


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _record_audit(approval_id: str, action: str, actor: str, details: dict[str, Any]) -> None:
    _append_jsonl(AUDIT_PATH, {
        "audit_id": f"audit-{uuid4().hex[:8]}",
        "approval_id": approval_id,
        "action": action,
        "timestamp": _now(),
        "actor": actor,
        "details": details,
    })


def submit_proposal(
    source_capability_id: str,
    concept: str,
    ai_hypothesis: str,
    confidence_score: float,
    trace_id: str,
    proposal_id: Optional[str] = None,
) -> GovernanceApproval:
    """Submit a Learning-derived candidate for Governance review.

    Every call creates a *new* QUEUED_FOR_REVIEW record. Callers that want
    to avoid duplicate queue entries for the same underlying proposal
    should pass a stable `proposal_id` (e.g. the originating
    `hypothesis_id`) and check `list_queue()` first — this is not enforced
    here, to keep this reduced implementation simple.
    """
    approval = GovernanceApproval(
        approval_id=f"gov-{uuid4().hex[:8]}",
        proposal_id=proposal_id or f"proposal-{uuid4().hex[:8]}",
        source_capability_id=source_capability_id,
        concept=concept,
        ai_hypothesis=ai_hypothesis,
        confidence_score=confidence_score,
        trace_id=trace_id,
    )
    _append_jsonl(APPROVALS_PATH, approval.to_dict())
    _record_audit(
        approval.approval_id, "PROPOSAL_RECEIVED", actor="system",
        details={"concept": concept},
    )
    return approval


def _latest_by_approval_id() -> dict[str, dict[str, Any]]:
    """Approvals are append-only snapshots; the latest line per
    approval_id wins — same "most recent record" pattern as
    `trace_store.get_trace`.
    """
    latest: dict[str, dict[str, Any]] = {}
    for record in _read_jsonl(APPROVALS_PATH):
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

    _append_jsonl(APPROVALS_PATH, updated)
    _record_audit(approval_id, decision, actor=approver_id, details={"reason": reason})
    return updated


def get_audit_trail(approval_id: Optional[str] = None) -> list[dict[str, Any]]:
    records = _read_jsonl(AUDIT_PATH)
    if approval_id:
        records = [r for r in records if r.get("approval_id") == approval_id]
    return records