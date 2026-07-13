"""Tests for `backend/services/usage_tracking.py`
(docs/architecture.md 14.105: Claude APIの利用量・概算コストの記録/集計)。

record_store自体はtests/backend/conftest.pyの共通フィクスチャで
インメモリのフェイクに差し替えられている（実際のSupabaseには繋がない）。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from services import usage_tracking


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def test_record_usage_and_get_summary_counts_todays_records():
    usage_tracking.record_usage(feature="chat", model="claude-sonnet-4-5", input_tokens=100, output_tokens=20)
    usage_tracking.record_usage(feature="chat", model="claude-sonnet-4-5", input_tokens=200, output_tokens=40)

    summary = usage_tracking.get_usage_summary()

    assert summary["today"]["total_calls"] == 2
    assert summary["today"]["input_tokens"] == 300
    assert summary["today"]["output_tokens"] == 60


def test_get_usage_summary_breaks_down_by_feature():
    usage_tracking.record_usage(feature="chat", model="claude-sonnet-4-5", input_tokens=100, output_tokens=10)
    usage_tracking.record_usage(feature="proposal_draft", model="claude-sonnet-4-5", input_tokens=500, output_tokens=100)
    usage_tracking.record_usage(feature="proposal_draft", model="claude-sonnet-4-5", input_tokens=500, output_tokens=100)

    summary = usage_tracking.get_usage_summary()
    by_feature = {f["feature"]: f for f in summary["today"]["by_feature"]}

    assert by_feature["chat"]["calls"] == 1
    assert by_feature["chat"]["input_tokens"] == 100
    assert by_feature["proposal_draft"]["calls"] == 2
    assert by_feature["proposal_draft"]["input_tokens"] == 1000
    assert by_feature["proposal_draft"]["output_tokens"] == 200


def test_get_usage_summary_computes_estimated_cost():
    usage_tracking.record_usage(feature="chat", model="claude-sonnet-4-5", input_tokens=1_000_000, output_tokens=1_000_000)

    summary = usage_tracking.get_usage_summary()
    expected_cost = (
        usage_tracking.PLACEHOLDER_INPUT_PRICE_PER_MTOK + usage_tracking.PLACEHOLDER_OUTPUT_PRICE_PER_MTOK
    )
    assert summary["today"]["estimated_cost_usd"] == round(expected_cost, 4)


def test_get_usage_summary_excludes_records_before_the_bucket_start(monkeypatch):
    """先週の記録は「今日」「今週」の集計に含まれず、「今月」には含まれる
    （同じ月内であれば）ことの確認。"""
    from services import record_store

    now = datetime.now(timezone.utc)
    last_week = now - timedelta(days=8)

    record_store.append_record(usage_tracking.USAGE_TABLE, {
        "feature": "chat", "model": "claude-sonnet-4-5",
        "input_tokens": 999, "output_tokens": 999,
        "recorded_at": _iso(last_week),
    })
    usage_tracking.record_usage(feature="chat", model="claude-sonnet-4-5", input_tokens=1, output_tokens=1)

    summary = usage_tracking.get_usage_summary()

    assert summary["today"]["input_tokens"] == 1  # 先週の分は含まれない
    assert summary["this_week"]["input_tokens"] == 1  # 先週の分は含まれない


def test_get_usage_summary_returns_zeroes_when_no_records():
    summary = usage_tracking.get_usage_summary()
    assert summary["today"]["total_calls"] == 0
    assert summary["today"]["input_tokens"] == 0
    assert summary["today"]["estimated_cost_usd"] == 0
    assert summary["today"]["by_feature"] == []


def test_get_usage_summary_includes_pricing_note_disclaimer():
    """14.105: 単価は参考値であり要確認、という注記が必ず含まれること
    （断定しない、というこのプロジェクトの一貫した方針）。"""
    summary = usage_tracking.get_usage_summary()
    assert "要確認" in summary["pricing_note"] or "確認" in summary["pricing_note"]
