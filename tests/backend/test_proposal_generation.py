"""Tests for `backend/services/proposal_generation.py`.

The LLM calls (`generate_text`/`generate_text_with_web_search`) are
always mocked — these tests verify proposal_generation's own logic
(Governance submission, internal-history gathering, the disabled image
feature), not Claude's actual output quality, and must never make real,
billed API calls.
"""
from __future__ import annotations

import pytest

from services import proposal_generation as pg


@pytest.fixture(autouse=True)
def _no_real_internal_history_fetch(monkeypatch):
    """Isolate from real Supabase/Logsys — tests that don't care about
    the internal-history content can rely on this default "not found"
    response."""
    monkeypatch.setattr(pg, "fetch_required_data", lambda required_data: [])


def test_draft_proposal_returns_draft_text_from_mocked_llm(monkeypatch):
    monkeypatch.setattr(pg, "generate_text", lambda prompt, max_tokens=1500, system=None, feature=None: "ダミードラフト本文")

    result = pg.draft_proposal("US_LOGS Inc.", "テスト提案")
    assert result["draft_text"] == "ダミードラフト本文"
    assert result["customer"] == "US_LOGS Inc."


def test_draft_proposal_is_always_queued_for_review_never_auto_approved(monkeypatch):
    """governance_level=HIGH per the module's own docstring — the
    Blueprint Chapter 11 Approval Levels table says HIGH never
    auto-approves regardless of confidence."""
    monkeypatch.setattr(pg, "generate_text", lambda prompt, max_tokens=1500, system=None, feature=None: "テスト")

    result = pg.draft_proposal("テスト商事", "テスト目的")
    assert result["status"] == "QUEUED_FOR_REVIEW"
    assert "承認前は顧客への送付不可" in result["note"]


def test_draft_proposal_reports_no_internal_history_honestly(monkeypatch):
    monkeypatch.setattr(pg, "generate_text", lambda prompt, max_tokens=1500, system=None, feature=None: "テスト")
    result = pg.draft_proposal("架空の会社", "テスト目的")
    assert "見つかりませんでした" in result["internal_history_used"]


def test_draft_proposal_uses_web_search_when_include_external_true(monkeypatch):
    monkeypatch.setattr(
        pg, "generate_text_with_web_search",
        lambda prompt, max_tokens=3000, feature=None: ("web検索込みのドラフト", ["https://example.com/a", "https://example.com/b"]),
    )
    # include_external=True のときは generate_text ではなく generate_text_with_web_search が呼ばれる。
    # 呼ばれてはいけない方は例外を投げるようにして、誤って呼ばれたら検知できるようにする。
    def _should_not_be_called(*a, **k):
        raise AssertionError("generate_text should not be called when include_external=True")
    monkeypatch.setattr(pg, "generate_text", _should_not_be_called)

    result = pg.draft_proposal("US_LOGS Inc.", "テスト提案", include_external=True)
    assert result["draft_text"] == "web検索込みのドラフト"
    assert result["external_sources"] == ["https://example.com/a", "https://example.com/b"]
    assert "外部調査は含まれていません" not in result["note"]


def test_draft_proposal_without_include_external_does_not_call_web_search(monkeypatch):
    def _should_not_be_called(*a, **k):
        raise AssertionError("generate_text_with_web_search should not be called when include_external=False")
    monkeypatch.setattr(pg, "generate_text_with_web_search", _should_not_be_called)
    monkeypatch.setattr(pg, "generate_text", lambda prompt, max_tokens=1500, system=None, feature=None: "テスト")

    result = pg.draft_proposal("US_LOGS Inc.", "テスト提案", include_external=False)
    assert result["external_sources"] == []
    assert "外部調査は含まれていません" in result["note"]


def test_draft_proposal_include_image_has_no_effect(monkeypatch):
    """Image generation was disabled as a business decision (2026-07-05):
    users should use their own generative-AI tools individually. Passing
    include_image=True must have zero effect."""
    monkeypatch.setattr(pg, "generate_text", lambda prompt, max_tokens=1500, system=None, feature=None: "テスト")

    result = pg.draft_proposal("US_LOGS Inc.", "テスト提案", include_image=True)
    assert result["image_path"] is None
    assert "画像生成機能は現在無効化されています" in result["note"]


def test_draft_proposal_failure_marks_execution_failed_and_reraises(monkeypatch):
    def _boom(prompt, max_tokens=1500, system=None, feature=None):
        raise RuntimeError("LLM API error")
    monkeypatch.setattr(pg, "generate_text", _boom)

    with pytest.raises(RuntimeError, match="LLM API error"):
        pg.draft_proposal("US_LOGS Inc.", "テスト提案")

    from services.capability_instance import registry
    executions = [
        ex for ex in registry._execution_history
        if ex.capability_id == "proposal_draft_generation"
    ]
    assert len(executions) == 1
    assert executions[0].status.value == "failed"
    assert executions[0].error_message == "LLM API error"


def test_draft_proposal_registers_capability_execution_with_customer_and_purpose(monkeypatch):
    monkeypatch.setattr(pg, "generate_text", lambda prompt, max_tokens=1500, system=None, feature=None: "テスト")
    pg.draft_proposal("US_LOGS Inc.", "来期の追加発注に向けた提案")

    from services.capability_instance import registry
    executions = [
        ex for ex in registry._execution_history
        if ex.capability_id == "proposal_draft_generation"
    ]
    assert len(executions) == 1
    assert executions[0].inputs["customer"] == "US_LOGS Inc."
    assert executions[0].inputs["purpose"] == "来期の追加発注に向けた提案"
