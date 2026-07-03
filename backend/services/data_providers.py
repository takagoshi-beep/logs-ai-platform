"""Execution Layer v0.1 — Data Provider抽象化。

Reasoningは required_data の provider/dataset を指定するだけで、
取得手段（SQL・API・シート）は各Provider内部に隠蔽される。
取得結果は Evidence として返す。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from services.supabase_client import get_connection


def _evidence(
    provider: str,
    dataset: str,
    status: str,
    summary: str,
    records: list[dict[str, Any]] | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """取得結果を Evidence として返す。records は全件を保持する

    （表示用のサンプリングはEvidence Integration/Interpretation Layerの責務）。
    """
    records = records or []
    return {
        "provider": provider,
        "dataset": dataset,
        "status": status,
        "summary": summary,
        "record_count": len(records),
        "records": records,
        "note": note,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


class LogisysProvider:
    """Logisys(Supabase public schema)。SQLはこのクラスの内部だけが知る。"""

    name = "logisys"

    def _query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                columns = [desc[0] for desc in cur.description] if cur.description else []
                rows = cur.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        finally:
            conn.close()

    def fetch(self, dataset: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            handler = getattr(self, f"_{dataset}", None)
            if handler is None:
                return _evidence(self.name, dataset, "unavailable", f"未対応のデータセット: {dataset}")
            return handler(params)
        except Exception as exc:  # noqa: BLE001
            return _evidence(
                self.name, dataset, "unavailable",
                "Logisysから取得できませんでした",
                note=f"テーブル/カラム未整備の可能性（{exc}）",
            )

    def _sales_lines(self, params: dict[str, Any]) -> dict[str, Any]:
        sql = (
            'SELECT "売上入力日", "得意先ID", "得意先名", "登録商品名", '
            '"事業分類", "数量pcs", "売上金額", "明細粗利" '
            'FROM sales WHERE 1=1'
        )
        args: list[Any] = []
        if params.get("period_start"):
            sql += ' AND "売上入力日" >= %s'
            args.append(params["period_start"])
        if params.get("period_end"):
            sql += ' AND "売上入力日" <= %s'
            args.append(params["period_end"])
        if params.get("customer_keyword"):
            sql += ' AND "得意先名" LIKE %s'
            args.append(f"%{params['customer_keyword']}%")
        sql += ' ORDER BY "売上入力日"'
        rows = self._query(sql, tuple(args))
        period = (
            f"{params.get('period_start', '')}〜{params.get('period_end', '')}"
            if params.get("period_start") else "全期間"
        )
        return _evidence(
            self.name, "sales_lines", "ok",
            f"売上明細 {len(rows)}件を取得（{period}）",
            rows,
            note="有効/無効の絞り込み基準（ステータス・決済方法の意味）は未確認のため、フィルタ未適用",
        )

    def _purchase_lines(self, params: dict[str, Any]) -> dict[str, Any]:
        return _evidence(
            self.name, "purchase_lines", "unavailable",
            "仕入明細は取得できませんでした",
            note="実データでの対応テーブル（purchases / purchase_orders）が未確認のため保留",
        )

    def _projects(self, params: dict[str, Any]) -> dict[str, Any]:
        return _evidence(
            self.name, "projects", "unavailable",
            "案件データは取得できませんでした",
            note="実データでの「案件」に相当するテーブル対応が未確認のため保留",
        )

    def _customer_master(self, params: dict[str, Any]) -> dict[str, Any]:
        sql = 'SELECT "ID", "顧客名称" FROM customers WHERE 1=1'
        args: list[Any] = []
        if params.get("keyword"):
            sql += ' AND "顧客名称" LIKE %s'
            args.append(f"%{params['keyword']}%")
        rows = self._query(sql, tuple(args))
        return _evidence(self.name, "customer_master", "ok", f"顧客マスタ {len(rows)}件を取得（名寄せ用）", rows)

    def _product_master(self, params: dict[str, Any]) -> dict[str, Any]:
        rows = self._query('SELECT "LOGS_CODE", "商品名", "商品分類" FROM products')
        return _evidence(self.name, "product_master", "ok", f"商品マスタ {len(rows)}件を取得", rows)

    def _project_classification(self, params: dict[str, Any]) -> dict[str, Any]:
        # 事業分類のコード対応は code_master(BUSINESS_TYPE)で確認済み:
        # 1=OEM, 2=商品仕入れ（海外）, 3=商品仕入れ（国内）
        rows = self._query('SELECT "事業分類", COUNT(*) AS 件数 FROM sales GROUP BY "事業分類"')
        return _evidence(
            self.name, "project_classification", "ok",
            f"事業分類フィールドを確認（区分 {len(rows)}種類が存在。code_masterで確認済み）",
            rows,
        )

    def _cancelled_sales(self, params: dict[str, Any]) -> dict[str, Any]:
        return _evidence(
            self.name, "cancelled_sales", "unavailable",
            "キャンセル・集計対象外の売上は取得できませんでした",
            note="ステータス・決済方法のコード値の意味が未確認のため保留",
        )

    def _returns(self, params: dict[str, Any]) -> dict[str, Any]:
        return _evidence(
            self.name, "returns", "unavailable",
            "返品データは取得できませんでした",
            note="返品テーブルが未整備（返品の扱いは会社ルールとして未決定）",
        )

    def _margin_trend(self, params: dict[str, Any]) -> dict[str, Any]:
        return _evidence(
            self.name, "margin_trend", "unavailable",
            "粗利トレンドは取得できませんでした",
            note="粗利トレンドの算出基準が会社として未整備",
        )


class GmailProvider:
    """Gmail。v0.1はAPI未接続のためデモデータを返すスタブ。"""

    name = "gmail"
    _MESSAGES = [
        {"date": "2026-07-01", "from": "fanatics-jp@example.com", "subject": "Re: 2026SS OEMジャージ 納期確認", "snippet": "7/15納品分の出荷スケジュールについて確認です…"},
        {"date": "2026-06-30", "from": "supplier-a@example.com", "subject": "キャップ追加ロット 見積送付", "snippet": "追加200個の見積を添付します…"},
        {"date": "2026-06-29", "from": "zozo-md@example.com", "subject": "夏物スニーカー 追加発注の件", "snippet": "販売好調のため追加発注を検討しています…"},
    ]

    def fetch(self, dataset: str, params: dict[str, Any]) -> dict[str, Any]:
        keyword = params.get("keyword", "")
        rows = [m for m in self._MESSAGES if not keyword or keyword in (m["subject"] + m["snippet"])]
        rows = rows or self._MESSAGES
        return _evidence(
            self.name, dataset, "ok",
            f"直近のメール {len(rows)}件を取得",
            rows,
            note="デモデータ（Gmail API未接続。次フェーズで実接続）",
        )


class ProjectSheetProvider:
    """案件管理シート。v0.1はシート未接続のためデモデータを返すスタブ。"""

    name = "project_sheet"
    _NOTES = [
        {"案件": "Fanatics 2026SS OEMジャージ", "次アクション": "出荷前検品の日程確定", "担当": "担当A", "メモ": "納期7/15厳守"},
        {"案件": "Fanatics キャップ追加ロット", "次アクション": "納品遅延の顧客連絡", "担当": "担当B", "メモ": "納期超過中・要フォロー"},
        {"案件": "ZOZO 夏物スニーカー", "次アクション": "追加発注の要否確認", "担当": "担当A", "メモ": "販売好調"},
    ]
    _TASKS = [
        {"日付": "2026-07-01", "案件": "Fanatics キャップ追加ロット", "タスク": "工場へ納期督促", "状態": "完了"},
        {"日付": "2026-07-02", "案件": "Fanatics 2026SS OEMジャージ", "タスク": "出荷前検品の手配", "状態": "未着手"},
        {"日付": "2026-07-02", "案件": "ZOZO 夏物スニーカー", "タスク": "追加発注数量の確認", "状態": "進行中"},
    ]

    def fetch(self, dataset: str, params: dict[str, Any]) -> dict[str, Any]:
        keyword = params.get("keyword", "")
        source = self._TASKS if dataset == "task_history" else self._NOTES
        rows = [r for r in source if not keyword or any(keyword in str(v) for v in r.values())]
        rows = rows or source
        label = "タスク履歴" if dataset == "task_history" else "案件メモ"
        return _evidence(
            self.name, dataset, "ok",
            f"案件管理シートから{label} {len(rows)}件を取得",
            rows,
            note="デモデータ（シート未接続。次フェーズで実接続）",
        )


class SlackProvider:
    """Slack。v0.1はAPI未接続のためデモデータを返すスタブ。"""

    name = "slack"
    _MESSAGES = [
        {"date": "2026-07-02", "channel": "#oem-案件", "user": "担当B", "text": "Fanaticsキャップ、工場から7/8出荷予定と連絡あり"},
        {"date": "2026-07-01", "channel": "#sales", "user": "担当A", "text": "ZOZO夏物、追加発注ありそう。数量確認中"},
    ]

    def fetch(self, dataset: str, params: dict[str, Any]) -> dict[str, Any]:
        keyword = params.get("keyword", "")
        rows = [m for m in self._MESSAGES if not keyword or keyword in m["text"]]
        rows = rows or self._MESSAGES
        return _evidence(
            self.name, dataset, "ok",
            f"直近のSlack投稿 {len(rows)}件を取得",
            rows,
            note="デモデータ（Slack API未接続。次フェーズで実接続）",
        )


_PROVIDERS: dict[str, Any] = {
    "logisys": LogisysProvider(),
    "gmail": GmailProvider(),
    "project_sheet": ProjectSheetProvider(),
    "slack": SlackProvider(),
}


def fetch_required_data(required_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Required Data（priority順）を各Providerへ振り分け、Evidence一覧を返す。"""
    evidence_list: list[dict[str, Any]] = []
    for item in required_data:
        provider_name = item.get("provider")
        provider = _PROVIDERS.get(provider_name)
        if provider is None:
            evidence = _evidence(
                provider_name or "unknown", item.get("dataset", ""), "unavailable",
                "対応するData Providerがありません",
            )
        else:
            evidence = provider.fetch(item.get("dataset", ""), item.get("params", {}))
        evidence["priority"] = item.get("priority")
        evidence["item"] = item.get("item")
        evidence_list.append(evidence)
    return evidence_list