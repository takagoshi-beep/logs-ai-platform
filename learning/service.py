"""
Learning Service: orchestrates the Learning Domain lifecycle.

Implements Blueprint v0.2 (Draft) Chapter 8 end-to-end:
LearningCandidate creation -> classification -> scope assignment ->
Operational application (scoped memory) OR Governed routing (Approval Queue
-> Admin Review -> Policy Memory), with Activity Feed and Debug Trace
integration at each step.

Critical Rule (Blueprint v0.2 §8.8, §9 Critical Rule): Governed Learning is
never saved directly. It only ever moves through
LearningCandidate -> Approval Queue -> Admin Review -> Policy Memory.
"""

from __future__ import annotations

from typing import Any

from learning import classifier, lifecycle
from learning.models import (
    ActivityFeedEntry,
    ApprovalQueueEntry,
    LearningActivityEvent,
    LearningCandidate,
    LearningScopeType,
    LearningSourceType,
    LearningStatus,
    LearningType,
    PolicyMemoryEntry,
)
from learning.repository import (
    get_activity_feed,
    get_approval_queue,
    get_candidate_repository,
    get_operational_memory,
    get_policy_memory,
)

try:
    from observability.tracer import add_trace_record
    from observability.models import TraceSession
except Exception:  # pragma: no cover - observability is optional for Learning
    add_trace_record = None  # type: ignore[assignment]
    TraceSession = None  # type: ignore[assignment]


class GovernanceRoutingError(ValueError):
    """Raised when a Governed/GLOBAL-scoped candidate is about to bypass Governance."""


def create_candidate(
    *,
    title: str,
    description: str,
    source_type: LearningSourceType,
    created_by: str,
    confidence: float = 0.0,
    evidence: list[dict[str, Any]] | None = None,
    suggested_application: str = "",
) -> LearningCandidate:
    """Record a new LearningCandidate (status OBSERVED -> CANDIDATE_CREATED)."""
    candidate = LearningCandidate(
        title=title,
        description=description,
        source_type=source_type,
        created_by=created_by,
        confidence=confidence,
        evidence=evidence or [],
        suggested_application=suggested_application,
    )
    lifecycle.transition(candidate, LearningStatus.CANDIDATE_CREATED)
    get_candidate_repository().save(candidate)
    _emit_activity(
        LearningActivityEvent.LEARNING_CANDIDATE_CREATED,
        candidate,
        summary=f"New learning candidate observed: \"{candidate.title}\"",
    )
    return candidate


def classify_and_scope(
    candidate: LearningCandidate,
    *,
    requested_scope: LearningScopeType,
    scope_id: str | None = None,
    affects_business_rule: bool = False,
    cross_project: bool = False,
) -> LearningCandidate:
    """Classify the candidate and assign its scope (status -> CLASSIFIED -> SCOPED)."""
    learning_type = classifier.classify(
        candidate.source_type,
        confidence=candidate.confidence,
        scope_type=requested_scope,
        affects_business_rule=affects_business_rule,
        cross_project=cross_project,
    )
    candidate.learning_type = learning_type
    lifecycle.transition(candidate, LearningStatus.CLASSIFIED)

    candidate.scope_type = lifecycle.determine_scope(
        requested_scope=requested_scope, learning_type=learning_type
    )
    candidate.scope_id = scope_id
    lifecycle.transition(candidate, LearningStatus.SCOPED)

    get_candidate_repository().save(candidate)
    return candidate


def apply_candidate(candidate: LearningCandidate, *, approver_id: str | None = None) -> LearningCandidate:
    """
    Route a SCOPED candidate to Operational application or Governance.

    Most Important Rule: a candidate whose scope requires governance (GLOBAL)
    is ALWAYS routed to the Approval Queue, even if classification produced
    OPERATIONAL — Learning must never auto-apply globally.
    """
    if candidate.status != LearningStatus.SCOPED:
        raise lifecycle.InvalidLearningTransition(
            f"LearningCandidate {candidate.id} must be SCOPED before it can be applied "
            f"(current status: {candidate.status.value})"
        )

    must_govern = candidate.scope_type is not None and lifecycle.requires_governance(candidate.scope_type)

    if candidate.learning_type == LearningType.GOVERNED or must_govern:
        return _queue_for_governance(candidate)

    if candidate.learning_type == LearningType.OPERATIONAL:
        return _apply_operational(candidate)

    # UNCLASSIFIED: leave SCOPED for re-evaluation, do not apply or queue.
    return candidate


def _apply_operational(candidate: LearningCandidate) -> LearningCandidate:
    if candidate.scope_type is not None and lifecycle.requires_governance(candidate.scope_type):
        raise GovernanceRoutingError(
            f"LearningCandidate {candidate.id} is GLOBAL-scoped and cannot be applied as Operational Learning"
        )

    get_operational_memory().apply(
        candidate.scope_type.value if candidate.scope_type else "unscoped",
        candidate.scope_id or "",
        {
            "candidate_id": candidate.id,
            "title": candidate.title,
            "suggested_application": candidate.suggested_application,
            "confidence": candidate.confidence,
        },
    )
    lifecycle.transition(candidate, LearningStatus.APPLIED)
    get_candidate_repository().save(candidate)
    _emit_activity(
        LearningActivityEvent.OPERATIONAL_LEARNING_APPLIED,
        candidate,
        summary=f"Applied operational learning: \"{candidate.title}\"",
    )
    return candidate


def _queue_for_governance(candidate: LearningCandidate) -> LearningCandidate:
    """Governed Learning Candidate -> Approval Queue. Never writes Policy Memory directly."""
    entry = ApprovalQueueEntry(candidate_id=candidate.id)
    get_approval_queue().enqueue(entry)
    lifecycle.transition(candidate, LearningStatus.QUEUED_FOR_GOVERNANCE)
    get_candidate_repository().save(candidate)
    _emit_activity(
        LearningActivityEvent.GOVERNED_LEARNING_QUEUED,
        candidate,
        summary=f"Queued for Governance approval: \"{candidate.title}\"",
        detail={"approval_id": entry.approval_id},
    )
    return candidate


def review_governed_candidate(
    candidate: LearningCandidate,
    *,
    approval_id: str,
    decision: str,
    approver_id: str,
    reason: str,
) -> LearningCandidate:
    """Admin Review decision on a Governed candidate (Blueprint v0.1 §9 Governance Standard)."""
    if decision not in ("APPROVED", "REJECTED"):
        raise ValueError("decision must be 'APPROVED' or 'REJECTED'")

    queue = get_approval_queue()
    entry = queue.get(approval_id)
    if entry is None or entry.candidate_id != candidate.id:
        raise ValueError(f"No matching approval queue entry {approval_id} for candidate {candidate.id}")

    entry.status = decision
    entry.decision = decision
    entry.approver_id = approver_id
    entry.approval_reason = reason
    queue.save(entry)

    if decision == "APPROVED":
        policy = PolicyMemoryEntry(
            candidate_id=candidate.id,
            approval_id=approval_id,
            rule_definition=candidate.suggested_application or candidate.description,
            approved_by=approver_id,
        )
        get_policy_memory().save(policy)
        lifecycle.transition(candidate, LearningStatus.APPROVED)
        _emit_activity(
            LearningActivityEvent.POLICY_APPROVED,
            candidate,
            summary=f"Governance approved: \"{candidate.title}\"",
            detail={"policy_id": policy.policy_id, "approver_id": approver_id, "reason": reason},
        )
    else:
        lifecycle.transition(candidate, LearningStatus.REJECTED)
        _emit_activity(
            LearningActivityEvent.POLICY_REJECTED,
            candidate,
            summary=f"Governance rejected: \"{candidate.title}\"",
            detail={"approver_id": approver_id, "reason": reason},
        )

    get_candidate_repository().save(candidate)
    return candidate


def update_scope(
    candidate: LearningCandidate, *, new_scope_type: LearningScopeType, new_scope_id: str | None
) -> LearningCandidate:
    """Update a candidate's scope assignment, emitting learning_scope_updated."""
    old_scope = candidate.scope_type
    candidate.scope_type = new_scope_type
    candidate.scope_id = new_scope_id
    candidate.touch()
    get_candidate_repository().save(candidate)
    _emit_activity(
        LearningActivityEvent.LEARNING_SCOPE_UPDATED,
        candidate,
        summary=f"Scope updated for \"{candidate.title}\": {old_scope} -> {new_scope_type.value}",
        detail={"old_scope": old_scope.value if old_scope else None, "new_scope": new_scope_type.value},
    )
    return candidate


def _emit_activity(
    event: LearningActivityEvent,
    candidate: LearningCandidate,
    *,
    summary: str,
    detail: dict[str, Any] | None = None,
) -> None:
    entry = ActivityFeedEntry(
        event=event,
        candidate_id=candidate.id,
        summary=summary,
        detail=detail or {},
    )
    get_activity_feed().record(entry)


def record_debug_trace_usage(
    candidate: LearningCandidate,
    *,
    reason: str,
    trace_session: "TraceSession | None" = None,
) -> dict[str, Any]:
    """
    Debug Trace integration (Blueprint v0.2 §8.10).

    When a decision uses a previously-applied Learning Candidate, this records
    a "Used Learning: ..." entry showing type/scope/policy-version/reason. If a
    live observability.TraceSession is supplied, it is written through
    add_trace_record (layer="learning"); otherwise the shaped record is
    returned for the caller to persist.
    """
    policy_version = None
    if candidate.learning_type == LearningType.GOVERNED:
        policies = [p for p in get_policy_memory().list_all() if p.candidate_id == candidate.id]
        if policies:
            policy_version = policies[0].version

    record = {
        "candidate_id": candidate.id,
        "title": candidate.title,
        "type": candidate.learning_type.value,
        "scope": f"{candidate.scope_type.value if candidate.scope_type else 'unscoped'}:{candidate.scope_id or ''}",
        "policy_version": policy_version,
        "reason": f"Used Learning: {reason}",
    }

    if trace_session is not None and add_trace_record is not None:
        add_trace_record(
            trace_session,
            layer="learning",
            input={"candidate_id": candidate.id},
            output=record,
            elapsed_ms=0.0,
            success=True,
        )

    return record