from __future__ import annotations

from context.selector import select_context_providers


def test_select_context_providers_prioritizes_memory_and_knowledge_for_follow_up() -> None:
    result = select_context_providers("前回のOEMの話の続き")

    assert "memory" in result["selected_providers"]
    assert "knowledge" in result["selected_providers"]
    assert result["priorities"]["memory"] >= result["priorities"]["knowledge"]


def test_select_context_providers_prioritizes_knowledge_for_definition_question() -> None:
    result = select_context_providers("OEMとは？")

    assert "knowledge" in result["selected_providers"]
    assert result["priorities"]["knowledge"] >= 90


def test_select_context_providers_prioritizes_user_for_self_reference() -> None:
    result = select_context_providers("私は何を担当していますか？")

    assert "user" in result["selected_providers"]
    assert result["priorities"]["user"] >= 80


def test_select_context_providers_prioritizes_organization_for_company_question() -> None:
    result = select_context_providers("LOGSの会社情報")

    assert "organization" in result["selected_providers"]
    assert result["priorities"]["organization"] >= 85


def test_select_context_providers_prioritizes_runtime_for_capability_question() -> None:
    result = select_context_providers("何ができますか？")

    assert "runtime" in result["selected_providers"]
    assert result["priorities"]["runtime"] >= 75
