"""Tests for `backend/services/reasoning_pipeline.py`.

Covers the fixed-pattern routing (Q1-Q4), the customer-name fallback
(Q5), and the final "回答不可" fallback for anything matching none of
them — this last case is a real, repeatedly-observed limitation from
manual testing this session (docs/architecture.md 13.6/14.4): free-form
questions outside the 4 fixed patterns get a clear "please rephrase"
response rather than a wrong answer or a crash.

`fetch_required_data` is monkeypatched to return an empty evidence list
for all Q1-Q4 tests — these tests care about *routing* (which Q-function
gets selected, and what its intent/decision_gate look like), not about
real Supabase data. Q5's customer-name matching is tested separately
with `LogsysProvider._customer_master` mocked directly, matching the
manual verification pattern used throughout this session's actual
development.
"""
from __future__ import annotations

import pytest

from services import reasoning_pipeline as rp


@pytest.fixture(autouse=True)
def _no_real_evidence_fetch(monkeypatch):
    """Q1-Q4 always call fetch_required_data() -> integrate_evidence() ->
    interpret_evidence() after routing. Stubbing the first call to return
    an empty list is enough to isolate routing-logic tests from Supabase/
    Logsys, since both integration/interpretation functions handle an
    empty evidence list as a normal, valid case."""
    monkeypatch.setattr(rp, "fetch_required_data", lambda required_data: [])


def test_q1_routes_on_oem_and_gross_profit_keywords():
    result = rp._reason_impl("今月のOEM事業の粗利を教えて")
    assert result["intent"]["category"] == "Analysis"
    assert result["intent"]["type"] == "KPI分析"
    assert result["meaning"]["items"]["entity"] == "OEM事業"


def test_q2_routes_on_fanatics_and_status_keywords():
    result = rp._reason_impl("Fanatics案件の状況を教えて")
    assert result["intent"]["category"] == "Monitoring"
    assert result["intent"]["type"] == "案件確認"


def test_q3_routes_on_priority_and_project_keywords():
    result = rp._reason_impl("今日優先すべき案件は？")
    assert result["intent"]["category"] == "Monitoring"
    assert result["intent"]["type"] == "タスク優先度判定"


def test_q4_routes_on_sales_customer_superlative_keywords():
    result = rp._reason_impl("今月売上が一番大きい顧客は？")
    assert result["intent"]["category"] == "Analysis"
    assert result["intent"]["type"] == "KPI分析"
    # Q1と intent が同一のため、meaning.items の中身でQ4であることを確認する
    assert "顧客" in result["meaning"]["items"]["entity"]


def test_unmatched_question_falls_back_to_project_lookup_or_unclassified(monkeypatch):
    """A free-form question matching none of Q1-Q4's keywords, and no
    known customer name either, must land on the honest "回答不可"
    fallback (not a guess, not a crash) — the exact behavior observed
    firsthand via manual browser testing this session."""
    from services import data_providers

    monkeypatch.setattr(data_providers.LogsysProvider, "_customer_master", lambda self, params: {"records": []})

    result = rp._reason_impl("6月の売上と粗利を教えてください")
    assert result["intent"]["category"] == "Unclassified"
    assert result["decision_gate"]["verdict"] == "回答不可"
    assert result["decision_gate"]["confidence"] == pytest.approx(0.9)


def test_question_matching_known_customer_name_routes_to_project_lookup(monkeypatch):
    from services import data_providers

    monkeypatch.setattr(
        data_providers.LogsysProvider,
        "_customer_master",
        lambda self, params: {"records": [{"顧客名称": "US_LOGS Inc."}]},
    )
    monkeypatch.setattr(data_providers.LogsysProvider, "_projects", lambda self, params: {"records": []})

    result = rp._reason_impl("US_LOGS Inc.の状況を教えて")
    assert result["intent"]["category"] == "ProjectLookup"
    assert result["meaning"]["items"]["matched_customer"] == "US_LOGS Inc."


def test_question_with_no_matching_customer_name_falls_back(monkeypatch):
    from services import data_providers

    monkeypatch.setattr(data_providers.LogsysProvider, "_customer_master", lambda self, params: {"records": []})

    result = rp._reason_impl("聞いたことのない会社の状況を教えて")
    assert result["intent"]["category"] == "Unclassified"
    assert result["decision_gate"]["verdict"] == "回答不可"


def test_reason_public_entrypoint_attaches_trace_id_and_registers_execution():
    from services.data_providers import LogsysProvider
    import services.data_providers as data_providers

    original = data_providers.LogsysProvider._customer_master
    data_providers.LogsysProvider._customer_master = lambda self, params: {"records": []}
    try:
        result = rp.reason("聞いたことのない会社の状況を教えて")
    finally:
        data_providers.LogsysProvider._customer_master = original

    assert result["trace_id"].startswith("reasoning-")
    assert result["question"] == "聞いたことのない会社の状況を教えて"

    from services.capability_instance import registry
    executions = [
        ex for ex in registry._execution_history
        if ex.capability_id == "business_question_reasoning"
    ]
    assert len(executions) == 1
    assert executions[0].inputs["question"] == "聞いたことのない会社の状況を教えて"
    assert executions[0].status.value == "completed"


def test_q6_routes_on_matched_staff_name_and_returns_supplier_breakdown(monkeypatch):
    import services.production_data as production_data
    from services.data_providers import fetch_required_data as real_fetch_required_data

    # このテストは ProductionProvider 経由の実データ取得ロジックそのものを
    # 検証したいので、ファイル冒頭の autouse フィクスチャが固定した
    # rp.fetch_required_data（常に空リストを返す）を、本物の実装に戻す。
    monkeypatch.setattr(rp, "fetch_required_data", real_fetch_required_data)
    monkeypatch.setattr(production_data, "list_sample_staff_names", lambda: ["林", "森山"])
    monkeypatch.setattr(
        production_data, "get_ongoing_samples_by_staff",
        lambda staff_name: [
            {"supplier_name": "A社", "product_name": "商品1", "quote_no": "Q1", "request_content": None, "answered_date": None},
            {"supplier_name": "A社", "product_name": "商品2", "quote_no": "Q2", "request_content": None, "answered_date": None},
            {"supplier_name": "B社", "product_name": "商品3", "quote_no": "Q3", "request_content": None, "answered_date": None},
        ],
    )

    result = rp._reason_impl("林さんが対応中のサンプルは何件ありますか")
    assert result["intent"]["category"] == "ProductionLookup"
    assert result["meaning"]["items"]["matched_staff"] == "林"
    facts = result["evidence"][0]["facts"]
    assert "対応中のサンプル依頼は合計3件" in facts
    assert "A社: 2件" in facts[1]


def test_q6_falls_back_honestly_when_staff_name_not_found(monkeypatch):
    import services.production_data as production_data
    monkeypatch.setattr(production_data, "list_sample_staff_names", lambda: ["林", "森山"])

    result = rp._reason_impl("鈴木さんが対応中のサンプルは何件ありますか")
    assert result["intent"]["category"] == "Unclassified"
    assert result["decision_gate"]["verdict"] == "回答不可"


def test_q6_does_not_interfere_with_other_fixed_patterns(monkeypatch):
    monkeypatch.setattr(rp, "fetch_required_data", lambda required_data: [])
    result = rp._reason_impl("今月のOEM事業の粗利を教えて")
    assert result["intent"]["category"] == "Analysis"


def test_unknown_from_reason_creates_an_operational_learning_candidate(monkeypatch):
    from services import data_providers
    from learning.repository import get_candidate_repository

    monkeypatch.setattr(data_providers.LogsysProvider, "_customer_master", lambda self, params: {"records": []})

    rp.reason("聞いたことのない会社の状況を教えて")

    candidates = get_candidate_repository().list()
    assert len(candidates) == 1
    assert candidates[0].source_type.value == "ai_observation"
    assert candidates[0].learning_type.value == "operational"
    assert candidates[0].status.value == "applied"  # 承認不要で自動適用される


def test_repeated_identical_unknown_does_not_create_duplicate_candidates(monkeypatch):
    """同じunknown（=同じ限界）を引き起こす質問が何度来ても、
    候補は1件しか作られない — 質問内容が違っても、unknownのテキストが
    同じなら重複とみなす設計（2026-07-06）。"""
    from services import data_providers
    from learning.repository import get_candidate_repository

    monkeypatch.setattr(data_providers.LogsysProvider, "_customer_master", lambda self, params: {"records": []})

    rp.reason("聞いたことのない会社の状況を教えて")
    rp.reason("別の知らない会社の状況を教えて")  # 違う質問文だが同じunknownメッセージ

    candidates = get_candidate_repository().list()
    assert len(candidates) == 1


def test_distinct_unknown_messages_create_separate_candidates(monkeypatch):
    from services import data_providers, production_data
    from learning.repository import get_candidate_repository

    monkeypatch.setattr(data_providers.LogsysProvider, "_customer_master", lambda self, params: {"records": []})
    monkeypatch.setattr(production_data, "list_sample_staff_names", lambda: ["林"])
    monkeypatch.setattr(production_data, "get_ongoing_samples_by_staff", lambda staff_name: [])

    rp.reason("聞いたことのない会社の状況を教えて")  # _fallback()のunknown
    rp.reason("林さんが対応中のサンプルは何件ありますか")  # Q6のunknown（内容が異なる）

    candidates = get_candidate_repository().list()
    assert len(candidates) == 2


def test_learning_recording_failure_never_blocks_the_actual_answer(monkeypatch):
    """Learning記録処理自体が壊れていても、本来の回答は必ず返る
    （ベストエフォート設計）。"""
    from services import data_providers
    import learning.service as learning_service

    monkeypatch.setattr(data_providers.LogsysProvider, "_customer_master", lambda self, params: {"records": []})
    monkeypatch.setattr(learning_service, "create_candidate", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    result = rp.reason("聞いたことのない会社の状況を教えて")
    assert result["intent"]["category"] == "Unclassified"  # 回答自体は正常に返る