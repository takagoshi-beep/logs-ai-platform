"""Claude tool-use definitions mapping to `backend/`'s existing, already
real, already tested Provider `.fetch()` methods (docs/architecture.md
14.21).

No new data-access logic lives here. Every tool below is a thin,
schema-only wrapper around functionality already built and tested this
session (`data_providers.py`'s `LogsysProvider`/`ProductionProvider`,
`production_data.py`). This module's only job is translating between
Claude's tool-call format and those existing functions — the actual SQL,
business-rule filters (e.g. sales status/payment-method exclusions),
and error handling all stay exactly where they already were.
"""
from __future__ import annotations

import json
from typing import Any

TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_sales_lines",
        "description": (
            "実際の売上明細を取得する。粗利や売上金額の集計・分析に使う。"
            "有効な受注のみを対象とする標準フィルタ（ステータス・決済方法）が"
            "既に適用済みなので、取得した行をそのまま合計してよい。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "period_start": {"type": "string", "description": "期間開始日（YYYY-MM-DD形式）"},
                "period_end": {"type": "string", "description": "期間終了日（YYYY-MM-DD形式）"},
                "customer_keyword": {"type": "string", "description": "顧客名の部分一致キーワード"},
            },
        },
    },
    {
        "name": "get_purchase_lines",
        "description": "実際の仕入明細（諸掛り込み金額）を取得する。仕入原価の分析に使う。",
        "input_schema": {
            "type": "object",
            "properties": {
                "period_start": {"type": "string", "description": "期間開始日（YYYY-MM-DD形式）"},
                "period_end": {"type": "string", "description": "期間終了日（YYYY-MM-DD形式）"},
            },
        },
    },
    {
        "name": "get_projects",
        "description": "案件（PO）情報を、案件名または顧客名のキーワードで検索する。",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "案件名または顧客名の部分一致キーワード"},
            },
        },
    },
    {
        "name": "get_customer_master",
        "description": "顧客マスタを検索する。顧客名の表記ゆれ確認・名寄せに使う。",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "顧客名の部分一致キーワード"},
            },
        },
    },
    {
        "name": "get_product_master",
        "description": "商品マスタの全件を取得する。",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_cancelled_sales",
        "description": "仮出庫（未確定出荷）の売上を取得する。正式な売上集計には含めるべきではないデータ。",
        "input_schema": {
            "type": "object",
            "properties": {
                "period_start": {"type": "string", "description": "期間開始日（YYYY-MM-DD形式）"},
                "period_end": {"type": "string", "description": "期間終了日（YYYY-MM-DD形式）"},
            },
        },
    },
    {
        "name": "get_returns",
        "description": "返品（赤伝）を取得する。除外対象ではなく、マイナス計上すべき正規取引として扱うこと。",
        "input_schema": {
            "type": "object",
            "properties": {
                "period_start": {"type": "string", "description": "期間開始日（YYYY-MM-DD形式）"},
                "period_end": {"type": "string", "description": "期間終了日（YYYY-MM-DD形式）"},
            },
        },
    },
    {
        "name": "get_sample_staff_names",
        "description": (
            "サンプル依頼対応の生産担当（回答者）の実在する名前一覧を取得する。"
            "get_ongoing_samples_by_staffを呼ぶ前に、まずこれで名前が実在するか確認すること。"
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_ongoing_samples_by_staff",
        "description": (
            "指定した生産担当が対応中（未通知）のサンプル依頼を、仕入先・商品名とともに取得する。"
            "到着予定日（ETD/ETA/納品日）などのスケジュール情報はこのデータに含まれない"
            "（生産管理チームがその項目を運用していないため）。到着日を聞かれても、"
            "このツールでは分からないと正直に答えること。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "staff_name": {"type": "string", "description": "生産担当の氏名（get_sample_staff_namesで確認した実在の名前）"},
            },
            "required": ["staff_name"],
        },
    },
    {
        "name": "get_production_mass_status",
        "description": "指定したPO番号の量産の生産進捗（工場・PP/TOP日程・ETD/ETA等）を取得する。",
        "input_schema": {
            "type": "object",
            "properties": {
                "po_number": {"type": "string", "description": "PO番号（例: 914-20260626_1）"},
            },
            "required": ["po_number"],
        },
    },
]


def execute_tool(tool_name: str, tool_input: dict[str, Any]) -> str:
    """ツール呼び出しを実行し、Claudeへ返すJSON文字列を返す。

    どんな失敗（未知のツール名、DB接続エラー等）でも例外を投げず、
    Claudeが読める形のエラー情報を返す — そうすることでClaude自身が
    「このデータは取得できなかった」と認識して、次の判断（別のツールを
    試す、正直に分からないと答える等）ができるようにするため。
    """
    from services.data_providers import _PROVIDERS

    try:
        if tool_name == "get_sales_lines":
            result = _PROVIDERS["logsys"].fetch("sales_lines", tool_input)
        elif tool_name == "get_purchase_lines":
            result = _PROVIDERS["logsys"].fetch("purchase_lines", tool_input)
        elif tool_name == "get_projects":
            result = _PROVIDERS["logsys"].fetch("projects", tool_input)
        elif tool_name == "get_customer_master":
            result = _PROVIDERS["logsys"].fetch("customer_master", tool_input)
        elif tool_name == "get_product_master":
            result = _PROVIDERS["logsys"].fetch("product_master", tool_input)
        elif tool_name == "get_cancelled_sales":
            result = _PROVIDERS["logsys"].fetch("cancelled_sales", tool_input)
        elif tool_name == "get_returns":
            result = _PROVIDERS["logsys"].fetch("returns", tool_input)
        elif tool_name == "get_sample_staff_names":
            result = _PROVIDERS["production"].fetch("sample_staff_master", tool_input)
        elif tool_name == "get_ongoing_samples_by_staff":
            result = _PROVIDERS["production"].fetch("ongoing_samples_by_staff", tool_input)
        elif tool_name == "get_production_mass_status":
            from services.production_data import get_production_mass_status
            rows = get_production_mass_status(tool_input.get("po_number", ""))
            result = {
                "status": "ok" if rows else "unavailable",
                "records": rows,
                "summary": f"{len(rows)}件取得",
            }
        else:
            result = {"status": "unavailable", "summary": f"未知のツール: {tool_name}", "records": []}
    except Exception as e:
        result = {"status": "error", "summary": f"データ取得中にエラーが発生しました: {e}", "records": []}

    return json.dumps(result, ensure_ascii=False, default=str)
