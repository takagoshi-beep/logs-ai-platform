"""
Classification logic for the Learning Domain.

Implements Blueprint v0.2 (Draft) §8.5: maps a LearningCandidate's source_type,
scope, and evidence to a LearningType (OPERATIONAL, GOVERNED, UNCLASSIFIED).
"""

from __future__ import annotations

from learning.models import LearningScopeType, LearningSourceType, LearningType

# Confidence below this threshold leaves a candidate UNCLASSIFIED regardless
# of source type, pending more evidence.
MIN_CLASSIFICATION_CONFIDENCE = 0.5

# Source types that are GOVERNED by default because they imply business-rule
# or company-wide change rather than personal/local efficiency improvement.
_GOVERNED_BY_DEFAULT = {
    LearningSourceType.KPI_SIGNAL,
    LearningSourceType.POLICY_UPDATE,
}

# Source types that are OPERATIONAL by default.
_OPERATIONAL_BY_DEFAULT = {
    LearningSourceType.AI_OBSERVATION,
    LearningSourceType.EXECUTION_RESULT,
}


def classify(
    source_type: LearningSourceType,
    *,
    confidence: float,
    scope_type: LearningScopeType | None = None,
    affects_business_rule: bool = False,
    cross_project: bool = False,
) -> LearningType:
    """
    Classify a LearningCandidate as OPERATIONAL, GOVERNED, or UNCLASSIFIED.

    Rules (Blueprint v0.2 §8.5, §8.4):
    - GLOBAL scope always forces GOVERNED (never auto-applied).
    - KPI_SIGNAL / POLICY_UPDATE are GOVERNED by default.
    - AI_OBSERVATION / EXECUTION_RESULT are OPERATIONAL by default.
    - USER_FEEDBACK / REPEATED_CORRECTION / WORKFLOW_PATTERN depend on whether
      they affect a business rule or cross multiple projects.
    - Below MIN_CLASSIFICATION_CONFIDENCE, the candidate is UNCLASSIFIED.
    """
    if confidence < MIN_CLASSIFICATION_CONFIDENCE:
        return LearningType.UNCLASSIFIED

    if scope_type == LearningScopeType.GLOBAL:
        return LearningType.GOVERNED

    if source_type in _GOVERNED_BY_DEFAULT:
        return LearningType.GOVERNED

    if source_type in _OPERATIONAL_BY_DEFAULT:
        return LearningType.OPERATIONAL

    if source_type == LearningSourceType.WORKFLOW_PATTERN:
        return LearningType.GOVERNED if cross_project else LearningType.OPERATIONAL

    if source_type in (
        LearningSourceType.USER_FEEDBACK,
        LearningSourceType.REPEATED_CORRECTION,
    ):
        return LearningType.GOVERNED if affects_business_rule else LearningType.OPERATIONAL

    return LearningType.UNCLASSIFIED
