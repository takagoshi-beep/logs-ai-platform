"""Tests for `backend/services/tool_registry.py`.

`execute_tool()` is a thin dispatcher over already-tested Provider
methods (`test_reasoning_pipeline.py`/`test_production_data.py` already
cover those methods' own logic) — these tests verify the dispatch/error
handling itself, not the underlying SQL.
"""
from __future__ import annotations

import json

from services import data_providers, tool_registry


def test_all_tool_schemas_have_required_fields():
    for tool in tool_registry.TOOLS:
        assert "name" in tool
        assert "description" in tool
        assert tool["description"]  # 空文字列でないこと（Claudeが判断できるように）
        assert "input_schema" in tool
        assert tool["input_schema"]["type"] == "object"


def test_execute_tool_dispatches_to_logsys_provider(monkeypatch):
    monkeypatch.setattr(
        data_providers.LogsysProvider, "_customer_master",
        lambda self, params: {"provider": "logsys", "dataset": "customer_master", "status": "ok", "records": [{"顧客名称": "US_LOGS Inc."}]},
    )
    result = json.loads(tool_registry.execute_tool("get_customer_master", {"keyword": "US_LOGS"}))
    assert result["status"] == "ok"
    assert result["records"] == [{"顧客名称": "US_LOGS Inc."}]


def test_execute_tool_dispatches_to_production_provider(monkeypatch):
    from services import production_data
    monkeypatch.setattr(production_data, "list_sample_staff_names", lambda: ["林", "森山"])

    result = json.loads(tool_registry.execute_tool("get_sample_staff_names", {}))
    assert result["status"] == "ok"
    assert {"生産担当": "林"} in result["records"]


def test_execute_tool_dispatches_production_mass_status_directly(monkeypatch):
    from services import production_data
    monkeypatch.setattr(
        production_data, "get_production_mass_status",
        lambda po_number: [{"po_number": po_number, "status": "納品済み"}],
    )
    result = json.loads(tool_registry.execute_tool("get_production_mass_status", {"po_number": "914-20260626_1"}))
    assert result["status"] == "ok"
    assert result["records"][0]["status"] == "納品済み"


def test_execute_tool_returns_unavailable_for_empty_production_mass_status(monkeypatch):
    from services import production_data
    monkeypatch.setattr(production_data, "get_production_mass_status", lambda po_number: [])

    result = json.loads(tool_registry.execute_tool("get_production_mass_status", {"po_number": "does-not-exist"}))
    assert result["status"] == "unavailable"


def test_execute_tool_returns_graceful_error_for_unknown_tool_name():
    result = json.loads(tool_registry.execute_tool("some_made_up_tool", {}))
    assert result["status"] == "unavailable"
    assert "未知のツール" in result["summary"]


def test_execute_tool_catches_provider_exceptions_without_raising(monkeypatch):
    """LogsysProvider.fetch() は既に自身の内部で例外を捕捉し
    "unavailable" として返す設計（今日より前から存在する挙動）。
    execute_tool は例外を外に漏らさないことを確認する
    （実際にどのステータスで返るかはProvider側の既存挙動に委ねる）。"""
    def _boom(self, params):
        raise RuntimeError("DB接続エラー")
    monkeypatch.setattr(data_providers.LogsysProvider, "_sales_lines", _boom)

    result = json.loads(tool_registry.execute_tool("get_sales_lines", {}))
    assert result["status"] == "unavailable"  # LogsysProvider.fetch()自身が吸収する


def test_execute_tool_returns_error_status_for_exceptions_outside_provider_fetch(monkeypatch):
    """execute_tool 自身のtry/exceptは、Provider.fetch()の外側で起きる
    予期しない不具合に対する安全網。production_data.get_production_mass_status
    自体が例外を投げるケース（_PROVIDERS経由ではなく直接呼んでいる箇所）で検証する。"""
    from services import production_data

    def _boom(po_number):
        raise RuntimeError("想定外のエラー")
    monkeypatch.setattr(production_data, "get_production_mass_status", _boom)

    result = json.loads(tool_registry.execute_tool("get_production_mass_status", {"po_number": "914-20260626_1"}))
    assert result["status"] == "error"
    assert "想定外のエラー" in result["summary"]
