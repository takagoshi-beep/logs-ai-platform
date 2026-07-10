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


def test_get_purchase_lines_description_is_sourced_from_knowledge_base():
    """2026-07-10（14.62、Noritsuguの指定）: 用語・業務ルールの定義は
    knowledge/配下のMarkdownを唯一の正とし、tool_registry.pyのツール
    説明文はそこから動的に読み込んで組み込む（手で書き写して二重管理
    にしない、「ナレッジがマスタとなってそこから情報が生成される」
    仕組み）。knowledge/semantic/purchase.mdの内容が実際に
    get_purchase_linesの説明文に含まれていることを確認する。"""
    from services.knowledge_loader import load_section

    expected_section = load_section("semantic/purchase.md", "## 輸入経費率")
    assert expected_section, "knowledge/semantic/purchase.mdに輸入経費率の節が見つからない"

    tool = next(t for t in tool_registry.TOOLS if t["name"] == "get_purchase_lines")
    assert expected_section in tool["description"]


def test_get_code_master_tool_is_registered():
    names = [t["name"] for t in tool_registry.TOOLS]
    assert "get_code_master" in names


def test_execute_tool_dispatches_get_code_master_without_assuming_column_names(monkeypatch):
    """code_masterの実際の列名はこの開発環境からは分からないため、
    列名を決め打ちせず SELECT * でそのまま返す設計であることを確認する。
    どんな列名の組み合わせが来ても、そのままrecordsに反映されればよい。"""
    monkeypatch.setattr(
        data_providers.LogsysProvider, "_code_master",
        lambda self, params: {
            "provider": "logsys", "dataset": "code_master", "status": "ok",
            "summary": "コードマスタ 3件を取得",
            "records": [
                {"テーブル名": "sales", "コード値": "1", "コード名": "OEM"},
                {"テーブル名": "sales", "コード値": "2", "コード名": "商品仕入れ（海外）"},
                {"テーブル名": "sales", "コード値": "3", "コード名": "商品仕入れ（国内）"},
            ],
        },
    )
    result = json.loads(tool_registry.execute_tool("get_code_master", {}))
    assert result["status"] == "ok"
    assert len(result["records"]) == 3
    assert result["records"][1]["コード名"] == "商品仕入れ（海外）"


def test_execute_tool_dispatches_to_logsys_provider(monkeypatch):
    monkeypatch.setattr(
        data_providers.LogsysProvider, "_customer_master",
        lambda self, params: {"provider": "logsys", "dataset": "customer_master", "status": "ok", "records": [{"顧客名称": "US_LOGS Inc."}]},
    )
    result = json.loads(tool_registry.execute_tool("get_customer_master", {"keyword": "US_LOGS"}))
    assert result["status"] == "ok"
    assert result["records"] == [{"顧客名称": "US_LOGS Inc."}]


def test_get_my_projects_surfaces_status_badges_and_delivery_month_bucket(monkeypatch):
    """2026-07-09（14.58修正）: 以前はstate（14.39でstatus_badgesに
    置き換える前の古い単一状態）を返していた。build_project_aggregates_
    bulk()自体は最新のロジックを使っているため（このツールは元々
    ProjectServiceを直接呼んでおり複製実装ではなかった）、取り出す
    フィールドだけを最新（status_badges・delivery_month_bucket）に
    更新した。"""
    from services import auth_service
    from services.project_service import ProjectService

    monkeypatch.setattr(auth_service, "get_staff_name_by_email", lambda email: "山田太郎")
    monkeypatch.setattr(
        ProjectService, "_query_projects_from_db",
        lambda self, limit, owner_name: [{"id": "1"}],
    )

    class _FakeData:
        project_name = "SLOBE IENA_ハーフオーバルベルト"
        customer_name = "US_LOGS Inc."

    class _FakeAgg:
        project_id = "1"
        po_number = "914-1"
        data = _FakeData()
        status_badges = ["sales_unconfirmed", "cost_unconfirmed", "po_not_issued"]
        delivery_month_bucket = "next_month"
        actions = []

    monkeypatch.setattr(ProjectService, "build_project_aggregates_bulk", lambda self, ids: [_FakeAgg()])

    result = json.loads(tool_registry.execute_tool("get_my_projects", {}, user_email="yamada@logs.co.jp"))

    assert result["status"] == "ok"
    record = result["records"][0]
    assert record["status_badges"] == ["sales_unconfirmed", "cost_unconfirmed", "po_not_issued"]
    assert record["delivery_month_bucket"] == "next_month"
    assert "state" not in record  # 古いフィールドはもう返さない
    assert "priority" not in record


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


def test_execute_tool_caps_large_record_counts_before_returning_to_claude(monkeypatch):
    """2026-07-06に実際のブラウザ操作で発見した実バグの再発防止テスト:
    期間指定なしの get_sales_lines が sales テーブル全件（実際は約20万件）
    をそのままClaudeに渡そうとし、Anthropic APIの1リクエストあたりの
    トークン上限（20万）を超えてエラーになった
    （"prompt is too long: 228537 tokens > 200000 maximum"）。"""
    huge_records = [{"売上金額": i} for i in range(50_000)]
    monkeypatch.setattr(
        data_providers.LogsysProvider, "_sales_lines",
        lambda self, params: {
            "provider": "logsys", "dataset": "sales_lines", "status": "ok",
            "summary": "売上明細 50000件を取得", "records": huge_records,
        },
    )

    result = json.loads(tool_registry.execute_tool("get_sales_lines", {}))
    assert len(result["records"]) == tool_registry._MAX_RECORDS_FOR_CLAUDE
    assert result["truncated"] is True
    assert result["total_record_count"] == 50_000
    assert "50000" in result["summary"] or "50,000" in result["summary"]


def test_execute_tool_does_not_touch_small_record_counts(monkeypatch):
    small_records = [{"売上金額": i} for i in range(3)]
    monkeypatch.setattr(
        data_providers.LogsysProvider, "_sales_lines",
        lambda self, params: {
            "provider": "logsys", "dataset": "sales_lines", "status": "ok",
            "summary": "売上明細 3件を取得", "records": small_records,
        },
    )

    result = json.loads(tool_registry.execute_tool("get_sales_lines", {}))
    assert result["records"] == small_records
    assert "truncated" not in result