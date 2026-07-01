"""
Lifecycle and scope rules for the Learning Domain.

Implements Blueprint v0.2 (Draft) §8.4 (Learning Scope) and §8.6/8.7
(Learning Lifecycle / Status).
"""

from __future__ import annotations

from learning.models import LearningCandidate, LearningScopeType, LearningStatus, LearningType

# Valid forward transitions. ARCHIVED can be reached from REJECTED or APPLIED
# (e.g. superseded candidates); APPROVED/REJECTED only follow QUEUED_FOR_GOVERNANCE.
_ALLOWED_TRANSITIONS: dict[LearningStatus, set[LearningStatus]] = {
    LearningStatus.OBSERVED: {LearningStatus.CANDIDATE_CREATED},
    LearningStatus.CANDIDATE_CREATED: {LearningStatus.CLASSIFIED},
    LearningStatus.CLASSIFIED: {LearningStatus.SCOPED},
    LearningStatus.SCOPED: {LearningStatus.APPLIED, LearningStatus.QUEUED_FOR_GOVERNANCE},
    LearningStatus.APPLIED: {LearningStatus.ARCHIVED},
    LearningStatus.QUEUED_FOR_GOVERNANCE: {LearningStatus.APPROVED, LearningStatus.REJECTED},
    LearningStatus.APPROVED: {LearningStatus.ARCHIVED},
    LearningStatus.REJECTED: {LearningStatus.ARCHIVED},
    LearningStatus.ARCHIVED: set(),
}


class InvalidLearningTransition(ValueError):
    """Raised when a LearningCandidate status transition violates the lifecycle."""


def transition(candidate: LearningCandidate, new_status: LearningStatus) -> None:
    """Move a candidate to new_status, enforcing the Blueprint v0.2 §8.6 lifecycle."""
    allowed = _ALLOWED_TRANSITIONS.get(candidate.status, set())
    if new_status not in allowed:
        raise InvalidLearningTransition(
            f"Cannot transition LearningCandidate {candidate.id} "
            f"from {candidate.status.value} to {new_status.value}"
        )
    candidate.status = new_status
    candidate.touch()


# Scope rules (Blueprint v0.2 §8.4):
# - GLOBAL requires Governed Learning approval.
# - CUSTOMER / DEPARTMENT need confirmation in principle, even if Operational.
# - USER / PROJECT / CAPABILITY can be saved as Operational Learning directly.
# - SESSION is temporary, one-time learning (not persisted as durable learning).
_REQUIRES_GOVERNANCE = {LearningScopeType.GLOBAL}
_REQUIRES_CONFIRMATION = {LearningScopeType.CUSTOMER, LearningScopeType.DEPARTMENT}
_DIRECTLY_APPLICABLE = {LearningScopeType.USER, LearningScopeType.PROJECT, LearningScopeType.CAPABILITY}
_TEMPORARY = {LearningScopeType.SESSION}


def requires_governance(scope_type: LearningScopeType) -> bool:
    return scope_type in _REQUIRES_GOVERNANCE


def requires_confirmation(scope_type: LearningScopeType) -> bool:
    return scope_type in _REQUIRES_CONFIRMATION


def is_directly_applicable(scope_type: LearningScopeType) -> bool:
    return scope_type in _DIRECTLY_APPLICABLE


def is_temporary(scope_type: LearningScopeType) -> bool:
    return scope_type in _TEMPORARY


def determine_scope(
    *,
    requested_scope: LearningScopeType,
    learning_type: LearningType,
) -> LearningScopeType:
    """
    Validate/resolve the scope for a candidate given its classification.

    Critical Rule (Blueprint v0.2 §8.4, §8.8): a GLOBAL-scoped candidate must
    never be classified OPERATIONAL — Learning never auto-applies company-wide
    rules. If this combination is requested, the scope is honored but the
    caller (LearningService) must route it to Governance regardless of
    learning_type.
    """
    return requested_scope
