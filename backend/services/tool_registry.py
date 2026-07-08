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
            "件数が多くなりやすいため、可能な限りperiod_start/period_endで"
            "期間を絞り込んで呼び出すこと（「今月」なら今月の初日〜末日を指定する）。"
            "取得した行には「事業分類」という数値コード列が含まれるが、"
            "その意味を推測してはいけない。get_code_masterで実際の意味を確認すること。"
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
        "description": "実際の仕入明細（諸掛り込み金額）を取得する。仕入原価の分析に使う。件数が多くなりやすいため、可能な限りperiod_start/period_endで期間を絞り込むこと。",
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
        "name": "get_code_master",
        "description": (
            "各テーブルの数値コード（事業分類、ステータス、決済方法、諸掛区分ID等）が"
            "実際に何を意味するかを確認する、コードマスタの全件を取得する。"
            "数値コードの意味を一般常識や推測で判断してはいけない。"
            "「事業分類=1」「ステータス=2」のような数値コードが出てきたら、"
            "回答する前に必ずこのツールで実際の意味を確認すること。"
        ),
        "input_schema": {"type": "object", "properties": {}},
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
    {
        "name": "search_gmail",
        "description": (
            "ログインユーザー自身のGmailを検索する。Gmail検索構文"
            "（from:, to:, subject:, after:YYYY/MM/DD, is:unread 等）が使える。"
            "件名・差出人・日時・スニペットのみを返す（本文全体はget_gmail_messageで取得すること）。"
            "'unavailable' が返ってきた場合はGmail未連携ということなので、"
            "設定画面からのGmail連携を案内すること。架空のメール内容を作ってはいけない。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Gmail検索クエリ"},
                "max_results": {"type": "integer", "description": "取得件数（既定10、最大25）"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_gmail_message",
        "description": "search_gmailで見つけたmessage_idを指定して、そのメールの本文全体を取得する。",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "search_gmailの結果に含まれるmessage_id"},
            },
            "required": ["message_id"],
        },
    },
    {
        "name": "search_slack",
        "description": (
            "ログインユーザー自身が参加しているSlackのチャンネル・DMからメッセージを検索する。"
            "Slack検索構文が使える: from:@ユーザー名, in:#チャンネル名, "
            "before:YYYY-MM-DD, after:YYYY-MM-DD, on:YYYY-MM-DD（日付は必ずハイフン区切り。"
            "Gmailのafter:YYYY/MM/DDとは書式が異なるので混同しないこと）。"
            "'unavailable' が返ってきた場合はSlack未連携ということなので、"
            "設定画面からのSlack連携を案内すること。架空のメッセージ内容を作ってはいけない。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Slack検索クエリ"},
                "max_results": {"type": "integer", "description": "取得件数（既定10、最大25）"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_my_projects",
        "description": (
            "ログインユーザー自身が「営業担当者」または「営業事務担当者」になっている"
            "案件（PO）を取得する。「自分の案件」「私が担当している案件」「自分の残タスク」"
            "のような質問に使う。ログイン中のメールアドレスが社員マスタの氏名と一致しない"
            "場合は取得できない（'unavailable'）ので、その場合は正直に担当者名を特定できな"
            "かった旨を伝えること。架空の案件を作ってはいけない。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "取得件数（既定20）"},
            },
        },
    },
]


_MAX_RECORDS_FOR_CLAUDE = 200


def _cap_records(result: dict[str, Any]) -> dict[str, Any]:
    """ツール結果のrecordsが多すぎる場合、Claudeへ渡す前に件数を制限する。

    2026-07-06に実際のブラウザ操作で発見: "今月のOEM事業の粗利を教えて"
    のような、期間指定なしでも呼び出せてしまう質問に対し、Claudeが
    get_sales_lines を period_start/period_end なしで呼んだ結果、
    sales テーブル全件（約20万件）がそのままツール結果としてClaudeに
    返され、Anthropic APIの1リクエストあたりの上限（20万トークン）を
    超えてエラーになった（実際のエラー: "prompt is too long: 228537
    tokens > 200000 maximum"）。

    evidence_interpreter.py の _DISPLAY_LIMIT（表示は代表サンプルに
    絞り、全件はrecord_countで件数のみ伝える）と同じ考え方を、Claudeに
    渡すツール結果にも適用する。Claude側に「件数が多いため絞り込んで
    ほしい」ことを伝え、次のターンで期間や顧客名を指定した再検索を
    促せるようにする。
    """
    records = result.get("records")
    if not isinstance(records, list) or len(records) <= _MAX_RECORDS_FOR_CLAUDE:
        return result

    total = len(records)
    capped = dict(result)
    capped["records"] = records[:_MAX_RECORDS_FOR_CLAUDE]
    capped["truncated"] = True
    capped["total_record_count"] = total
    original_summary = result.get("summary", "")
    capped["summary"] = (
        f"{original_summary}（件数が多いため先頭{_MAX_RECORDS_FOR_CLAUDE}件のみ返却。"
        f"全{total}件。期間や顧客名などで絞り込んで再度呼び出してください）"
    )
    return capped


def execute_tool(tool_name: str, tool_input: dict[str, Any], user_email: str | None = None) -> str:
    """ツール呼び出しを実行し、Claudeへ返すJSON文字列を返す。

    どんな失敗（未知のツール名、DB接続エラー等）でも例外を投げず、
    Claudeが読める形のエラー情報を返す — そうすることでClaude自身が
    「このデータは取得できなかった」と認識して、次の判断（別のツールを
    試す、正直に分からないと答える等）ができるようにするため。

    user_email: 今チャットしている本人のメールアドレス（ログインセッション
    由来）。Gmail/Slackのような「本人自身のデータ」を扱うツールにのみ
    必要で、それ以外の全社共通データ系ツールでは使わない。
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
        elif tool_name == "get_code_master":
            result = _PROVIDERS["logsys"].fetch("code_master", tool_input)
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
        elif tool_name == "search_gmail":
            if not user_email:
                result = {"status": "unavailable", "summary": "ユーザーが特定できないため、Gmail検索はできません。", "records": []}
            else:
                from services import gmail_service
                result = gmail_service.search_messages(
                    user_email, tool_input.get("query", ""), tool_input.get("max_results", 10)
                )
        elif tool_name == "get_gmail_message":
            if not user_email:
                result = {"status": "unavailable", "summary": "ユーザーが特定できないため、メール取得はできません。", "records": []}
            else:
                from services import gmail_service
                result = gmail_service.get_message(user_email, tool_input.get("message_id", ""))
        elif tool_name == "search_slack":
            if not user_email:
                result = {"status": "unavailable", "summary": "ユーザーが特定できないため、Slack検索はできません。", "records": []}
            else:
                from services import slack_service
                result = slack_service.search_messages(
                    user_email, tool_input.get("query", ""), tool_input.get("max_results", 10)
                )
        elif tool_name == "get_my_projects":
            if not user_email:
                result = {"status": "unavailable", "summary": "ユーザーが特定できないため取得できません。", "records": []}
            else:
                from services.auth_service import get_staff_name_by_email
                from services.project_service import ProjectService

                owner_name = get_staff_name_by_email(user_email)
                if not owner_name:
                    result = {
                        "status": "unavailable",
                        "summary": "ログイン中のメールアドレスが社員マスタの氏名と一致しないため、担当案件を特定できません。",
                        "records": [],
                    }
                else:
                    service = ProjectService()
                    limit = tool_input.get("limit", 20)
                    project_ids = service._query_projects_from_db(limit=limit, owner_name=owner_name)
                    records = []
                    for proj in project_ids:
                        agg = service.build_project_aggregate(proj["id"], record_capability=False)
                        if agg:
                            records.append({
                                "project_id": agg.project_id,
                                "po_number": agg.po_number,
                                "customer": agg.data.customer_name,
                                "state": agg.state.value,
                                "priority": agg.priority,
                                "actions_count": len(agg.actions),
                            })
                    result = {
                        "status": "ok" if records else "unavailable",
                        "summary": f"{owner_name}さんが担当する案件を{len(records)}件取得しました。" if records else f"{owner_name}さんが担当する案件は見つかりませんでした。",
                        "records": records,
                    }
        else:
            result = {"status": "unavailable", "summary": f"未知のツール: {tool_name}", "records": []}
    except Exception as e:
        result = {"status": "error", "summary": f"データ取得中にエラーが発生しました: {e}", "records": []}

    result = _cap_records(result)
    return json.dumps(result, ensure_ascii=False, default=str)