from __future__ import annotations

from question.extractor import extract_question_fields
from question.models import QuestionUnderstandingResult
from question.normalizer import normalize_message


def parse_question(message: str, intent=None, context=None) -> QuestionUnderstandingResult:
    _ = intent
    _ = context
    normalized = normalize_message(message)
    extracted = extract_question_fields(normalized)

    warnings: list[str] = []
    if extracted["metric"] == "unknown":
        warnings.append("Metric could not be confidently identified")
    if extracted["operation"] == "unknown":
        warnings.append("Operation could not be confidently identified")
    if extracted["entity_type"] == "unknown":
        warnings.append("Entity type could not be confidently identified")

    reason = "rule-based extraction from normalized tokens"
    if warnings:
        reason += "; partial match"

    return QuestionUnderstandingResult(
        original_message=message,
        normalized_message=normalized,
        metric=extracted["metric"],
        operation=extracted["operation"],
        entity_type=extracted["entity_type"],
        category=extracted["category"],
        customer=None,
        product=None,
        period=extracted["period"],
        limit=extracted["limit"],
        filters=extracted["filters"],
        confidence=extracted["confidence"],
        warnings=warnings,
        reason=reason,
    )
