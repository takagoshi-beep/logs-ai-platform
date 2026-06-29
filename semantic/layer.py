from __future__ import annotations

from typing import Any

from question.normalizer import normalize_message

from semantic.models import SemanticAnalysisResult
from semantic.registry import SemanticRegistry, get_default_semantic_registry


def _normalize_question(question: dict[str, Any] | None) -> dict[str, Any]:
    if not question:
        return {}
    if hasattr(question, "to_dict"):
        return dict(question.to_dict())
    return dict(question)


def _pick_canonical_message_value(
    registry: SemanticRegistry,
    section: str,
    message: str,
    fallback: str,
) -> tuple[str, str | None, str | None, dict[str, Any]]:
    match = registry.match_section(section, message)
    if match is not None:
        return match.canonical, match.label, match.matched_term, match.metadata
    if fallback and fallback != "unknown":
        section_match = registry.section_metadata(section, fallback)
        label = str(section_match.get("label")) if section_match.get("label") else None
        return fallback, label, fallback, section_match
    return fallback or "unknown", None, None, {}


def _pick_metric_value(registry: SemanticRegistry, message: str, fallback: str) -> tuple[str, str | None, str | None, dict[str, Any]]:
    match = registry.metric_match(message)
    if match is not None:
        return match.canonical, match.label, match.matched_term, match.metadata
    if fallback and fallback != "unknown":
        metadata = registry.metric_metadata(fallback)
        label = str(metadata.get("label")) if metadata.get("label") else None
        return fallback, label, fallback, metadata
    return fallback or "unknown", None, None, {}


def analyze_semantics(
    message: str,
    question: dict[str, Any] | None = None,
    intent: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    registry: SemanticRegistry | None = None,
) -> SemanticAnalysisResult:
    _ = intent
    _ = context
    semantic_registry = registry or get_default_semantic_registry()
    original_message = message or ""
    normalized_message = normalize_message(original_message)
    question_data = _normalize_question(question)

    original_metric = str(question_data.get("metric", "unknown"))
    original_entity_type = str(question_data.get("entity_type", "unknown"))
    original_operation = str(question_data.get("operation", "unknown"))
    original_period = str(question_data.get("period", "unknown"))

    metric, metric_label, metric_match, metric_metadata = _pick_metric_value(semantic_registry, original_message, original_metric)
    entity_type, entity_label, entity_match, entity_metadata = _pick_canonical_message_value(
        semantic_registry,
        "entity",
        original_message,
        original_entity_type,
    )
    operation, operation_label, operation_match, operation_metadata = _pick_canonical_message_value(
        semantic_registry,
        "operation",
        original_message,
        original_operation,
    )
    period, period_label, period_match, period_metadata = _pick_canonical_message_value(
        semantic_registry,
        "period",
        original_message,
        original_period,
    )
    category, category_label, category_match, category_metadata = _pick_canonical_message_value(
        semantic_registry,
        "product_category",
        original_message,
        str(question_data.get("category") or "unknown"),
    )
    customer, customer_label, customer_match, customer_metadata = _pick_canonical_message_value(
        semantic_registry,
        "customer",
        original_message,
        str(question_data.get("customer") or "unknown"),
    )

    original_limit = question_data.get("limit")
    limit = original_limit if isinstance(original_limit, int) else None
    filters = dict(question_data.get("filters") or {})
    if period != "unknown":
        filters.setdefault("period", period)
    if category != "unknown":
        filters.setdefault("category", category)

    matched_terms = {
        "metric": [term for term in [metric_match] if term],
        "entity": [term for term in [entity_match] if term],
        "operation": [term for term in [operation_match] if term],
        "period": [term for term in [period_match] if term],
        "product_category": [term for term in [category_match] if term],
        "customer": [term for term in [customer_match] if term],
    }

    confidence = float(question_data.get("confidence", 0.4) or 0.4)
    for value in [metric_match, entity_match, operation_match, period_match, category_match, customer_match]:
        if value:
            confidence += 0.08
    if limit is not None:
        confidence += 0.03

    warnings: list[str] = []
    if metric == "unknown":
        warnings.append("Metric could not be standardized")
    if entity_type == "unknown":
        warnings.append("Entity type could not be standardized")
    if operation == "unknown":
        warnings.append("Operation could not be standardized")

    reason_parts = ["semantic normalization using business dictionary and metric registry"]
    if any(matched_terms.values()):
        reason_parts.append("matched synonyms and canonical registry entries")
    if warnings:
        reason_parts.append("partial semantic coverage")

    return SemanticAnalysisResult(
        original_message=original_message,
        normalized_message=normalized_message,
        original_question=question_data,
        metric=metric,
        entity_type=entity_type,
        operation=operation,
        period=period,
        limit=limit,
        category=category if category != "unknown" else None,
        customer=customer if customer != "unknown" else None,
        product=str(question_data.get("product") or "") or None,
        metric_label=metric_label,
        entity_label=entity_label,
        operation_label=operation_label,
        confidence=min(confidence, 0.99),
        matched_terms=matched_terms,
        warnings=warnings,
        reason="; ".join(reason_parts),
        source={
            "business_dictionary": semantic_registry.source_paths["business_dictionary"],
            "metric_registry": semantic_registry.source_paths["metric_registry"],
            "metric_metadata": metric_metadata,
            "entity_metadata": entity_metadata,
            "operation_metadata": operation_metadata,
            "period_metadata": period_metadata,
            "product_category_metadata": category_metadata,
            "customer_metadata": customer_metadata,
        },
    )