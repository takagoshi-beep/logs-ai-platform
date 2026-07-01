"""
Request/response shaping helpers for the Learning Domain API surface.

This codebase does not use pydantic (see capability/domain.py, domain/project.py
for the established dataclass + to_dict() convention) — schemas here are plain
dict validators/shapers consistent with that style.
"""

from __future__ import annotations

from typing import Any

from learning.models import LearningCandidate, LearningScopeType, LearningSourceType

REQUIRED_CREATE_FIELDS = ("title", "description", "source_type", "created_by")


class LearningValidationError(ValueError):
    """Raised when an incoming Learning Domain payload is malformed."""


def validate_create_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a create-candidate request payload, returning normalized fields."""
    missing = [f for f in REQUIRED_CREATE_FIELDS if not payload.get(f)]
    if missing:
        raise LearningValidationError(f"Missing required fields: {', '.join(missing)}")

    try:
        source_type = LearningSourceType(payload["source_type"])
    except ValueError as exc:
        valid = ", ".join(s.value for s in LearningSourceType)
        raise LearningValidationError(f"Invalid source_type: {payload['source_type']!r}. Valid: {valid}") from exc

    confidence = float(payload.get("confidence", 0.0))
    if not 0.0 <= confidence <= 1.0:
        raise LearningValidationError("confidence must be between 0.0 and 1.0")

    return {
        "title": str(payload["title"]),
        "description": str(payload["description"]),
        "source_type": source_type,
        "created_by": str(payload["created_by"]),
        "confidence": confidence,
        "evidence": list(payload.get("evidence") or []),
        "suggested_application": str(payload.get("suggested_application", "")),
    }


def validate_scope_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a classify/scope request payload."""
    raw_scope = payload.get("scope_type")
    if not raw_scope:
        raise LearningValidationError("scope_type is required")
    try:
        scope_type = LearningScopeType(raw_scope)
    except ValueError as exc:
        valid = ", ".join(s.value for s in LearningScopeType)
        raise LearningValidationError(f"Invalid scope_type: {raw_scope!r}. Valid: {valid}") from exc

    return {
        "requested_scope": scope_type,
        "scope_id": payload.get("scope_id"),
        "affects_business_rule": bool(payload.get("affects_business_rule", False)),
        "cross_project": bool(payload.get("cross_project", False)),
    }


def candidate_to_response(candidate: LearningCandidate) -> dict[str, Any]:
    """Shape a LearningCandidate for API/UI consumption."""
    return candidate.to_dict()
