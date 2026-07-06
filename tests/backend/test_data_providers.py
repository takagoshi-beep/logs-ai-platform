"""Tests for `backend/services/data_providers.py`'s not-yet-connected
providers (Gmail, ProjectSheet, Slack).

Regression test for the 2026-07-06 fix (docs/architecture.md 14.17):
these three previously returned hardcoded fictional data (fake emails,
fake Slack messages) with status "ok", indistinguishable in shape from
real Supabase-backed evidence — polluting reasoning_pipeline's answers
with fabricated "evidence" and making manual verification/testing
unreliable. They now honestly report "unavailable" instead.
"""
from __future__ import annotations

from services.data_providers import GmailProvider, ProjectSheetProvider, SlackProvider


def test_gmail_provider_reports_unavailable_not_fake_data():
    result = GmailProvider().fetch("recent_messages", {})
    assert result["status"] == "unavailable"
    assert result["records"] == []
    assert result["record_count"] == 0


def test_project_sheet_provider_reports_unavailable_not_fake_data():
    result = ProjectSheetProvider().fetch("project_notes", {})
    assert result["status"] == "unavailable"
    assert result["records"] == []


def test_project_sheet_provider_task_history_also_unavailable():
    result = ProjectSheetProvider().fetch("task_history", {})
    assert result["status"] == "unavailable"
    assert "タスク履歴" in result["summary"]


def test_slack_provider_reports_unavailable_not_fake_data():
    result = SlackProvider().fetch("recent_messages", {})
    assert result["status"] == "unavailable"
    assert result["records"] == []


def test_unavailable_providers_never_claim_ok_status():
    """None of these three should ever report success — there is
    nothing real behind them yet, regardless of dataset/params passed."""
    for provider in (GmailProvider(), ProjectSheetProvider(), SlackProvider()):
        result = provider.fetch("any_dataset", {"keyword": "anything"})
        assert result["status"] != "ok"