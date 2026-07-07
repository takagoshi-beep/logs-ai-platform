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


class LogsysProvider:
    """Logsys(Supabase public schema)。SQLはこのクラスの内部だけが知る。"""

    name = "logsys"

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
                "Logsysから取得できませんでした",
                note=f"テーブル/カラム未整備の可能性（{exc}）",
            )

    def _sales_lines(self, params: dict[str, Any]) -> dict[str, Any]:
        # ステータス・決済方法の集計フィルタは、本番運用中のシステムプロンプト
        # （別アプリ app.py の system_sql）で確認済みの正式ルール。
        # 赤伝（ステータス=3）は返品として含める。仮出庫（決済方法=4）は除外する。
        sql = (
            'SELECT "売上入力日", "得意先ID", "得意先名", "登録商品名", '
            '"事業分類", "数量pcs", "売上金額", "明細粗利" '
            'FROM sales '
            "WHERE \"ステータス\" IN (2, 3, 4, 5) AND \"決済方法\" != '4'"
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
            f"売上明細 {len(rows)}件を取得（{period}、有効な受注のみ・標準フィルタ適用済み）",
            rows,
        )

    def _purchase_lines(self, params: dict[str, Any]) -> dict[str, Any]:
        # ステータスIN(2,3)は本番運用中のシステムプロンプトで確認済みの
        # 仕入集計時の正式フィルタ条件。
        sql = (
            'SELECT "伝票日", "仕入先名", "商品分類", "仕入数量pcs", '
            '"仕入金額円", "諸掛込金額円" '
            'FROM purchases '
            'WHERE "ステータス" IN (2, 3)'
        )
        args: list[Any] = []
        if params.get("period_start"):
            sql += ' AND "伝票日" >= %s'
            args.append(params["period_start"])
        if params.get("period_end"):
            sql += ' AND "伝票日" <= %s'
            args.append(params["period_end"])
        sql += ' ORDER BY "伝票日"'
        rows = self._query(sql, tuple(args))
        return _evidence(
            self.name, "purchase_lines", "ok",
            f"仕入明細 {len(rows)}件を取得（諸掛り込み金額、標準フィルタ適用済み）",
            rows,
        )

    def _projects(self, params: dict[str, Any]) -> dict[str, Any]:
        # 「案件」に相当する実データは purchase_orders テーブル
        # （PO発行〜納品・輸送・検品スケジュール管理、案件単位）。
        sql = (
            'SELECT "ID", "案件名", "顧客名", "ステータス", "顧客納品日" '
            'FROM purchase_orders WHERE 1=1'
        )
        args: list[Any] = []
        if params.get("keyword"):
            sql += ' AND ("案件名" LIKE %s OR "顧客名" LIKE %s)'
            args += [f"%{params['keyword']}%", f"%{params['keyword']}%"]
        sql += ' ORDER BY "顧客納品日"'
        rows = self._query(sql, tuple(args))
        label = f"「{params['keyword']}」関連の" if params.get("keyword") else ""
        return _evidence(self.name, "projects", "ok", f"{label}案件 {len(rows)}件を取得", rows)

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
        # PAYMENT_METHOD=4（仮出庫）は未確定出荷のため集計対象外。
        # SALES_STATUS=3（赤伝）は返品であり、除外せずマイナス計上すべき正規取引のため、ここには含めない。
        sql = (
            'SELECT "売上入力日", "得意先名", "登録商品名", "売上金額", "決済方法" '
            "FROM sales WHERE \"決済方法\" = '4'"
        )
        args: list[Any] = []
        if params.get("period_start"):
            sql += ' AND "売上入力日" >= %s'
            args.append(params["period_start"])
        if params.get("period_end"):
            sql += ' AND "売上入力日" <= %s'
            args.append(params["period_end"])
        rows = self._query(sql, tuple(args))
        return _evidence(
            self.name, "cancelled_sales", "ok",
            f"仮出庫（未確定出荷）{len(rows)}件を取得（code_master PAYMENT_METHOD で確認済み）",
            rows,
            note="赤伝（返品）はここに含めない。返品はマイナス計上すべき正規取引のため。",
        )

    def _returns(self, params: dict[str, Any]) -> dict[str, Any]:
        # SALES_STATUS=3（赤伝）が返品に相当することが code_master で確認済み。
        sql = (
            'SELECT "売上入力日", "得意先名", "登録商品名", "売上金額", "ステータス" '
            "FROM sales WHERE \"ステータス\" = '3'"
        )
        args: list[Any] = []
        if params.get("period_start"):
            sql += ' AND "売上入力日" >= %s'
            args.append(params["period_start"])
        if params.get("period_end"):
            sql += ' AND "売上入力日" <= %s'
            args.append(params["period_end"])
        rows = self._query(sql, tuple(args))
        return _evidence(
            self.name, "returns", "ok",
            f"返品（赤伝）{len(rows)}件を取得（code_master SALES_STATUS で確認済み）",
            rows,
            note="赤伝は除外対象ではなく、マイナス計上すべき正規取引として扱う。",
        )

    def _margin_trend(self, params: dict[str, Any]) -> dict[str, Any]:
        return _evidence(
            self.name, "margin_trend", "unavailable",
            "粗利トレンドは取得できませんでした",
            note="粗利トレンドの算出基準が会社として未整備",
        )


class GmailProvider:
    """Gmail。v0.1はAPI未接続。

    (2026-07-06) 以前はここで固定の架空メール（存在しない差出人・件名）を
    "ok" ステータスで返していた — Reasoning Pipelineの回答に、実データ
    (Supabase由来のsales/purchase_orders等)と見分けのつかない形で
    架空の「証拠」が混入する状態だった。テスト・検証を阻害するため、
    他の未接続Providerと同じ "unavailable" ステータスで正直に返すよう
    修正した。実際にGmail APIへ接続する際は、この fetch() の中身を
    差し替えるだけでよい（呼び出し側のインターフェースは変更不要）。
    """

    name = "gmail"

    def fetch(self, dataset: str, params: dict[str, Any]) -> dict[str, Any]:
        return _evidence(
            self.name, dataset, "unavailable",
            "Gmailは未接続のため取得できません",
            note="次フェーズで実接続予定（現時点ではデータなし）",
        )


class ProjectSheetProvider:
    """案件管理シート。v0.1はシート未接続。

    (2026-07-06) GmailProviderと同じ理由で、固定の架空メモ・タスクを
    "ok" として返す実装から、正直な "unavailable" 表示に変更した。
    """

    name = "project_sheet"

    def fetch(self, dataset: str, params: dict[str, Any]) -> dict[str, Any]:
        label = "タスク履歴" if dataset == "task_history" else "案件メモ"
        return _evidence(
            self.name, dataset, "unavailable",
            f"案件管理シート（{label}）は未接続のため取得できません",
            note="次フェーズで実接続予定（現時点ではデータなし）",
        )


class SlackProvider:
    """Slack。v0.1はAPI未接続。

    (2026-07-06) GmailProviderと同じ理由で、固定の架空投稿を "ok" として
    返す実装から、正直な "unavailable" 表示に変更した。
    """

    name = "slack"

    def fetch(self, dataset: str, params: dict[str, Any]) -> dict[str, Any]:
        return _evidence(
            self.name, dataset, "unavailable",
            "Slackは未接続のため取得できません",
            note="次フェーズで実接続予定（現時点ではデータなし）",
        )


class ProductionProvider:
    """生産管理チームのスプレッドシート由来データ（production_samples/
    production_mass）。Logsys本体（sales/customers等）とは別データソース
    のため、LogsysProviderとは別のProviderとして扱う（docs/architecture.md
    14.16の「別テーブルとして同期し、クエリ時に結合する」方針と一貫させる）。
    """

    name = "production"

    def fetch(self, dataset: str, params: dict[str, Any]) -> dict[str, Any]:
        from services.production_data import get_ongoing_samples_by_staff, list_sample_staff_names

        if dataset == "sample_staff_master":
            names = list_sample_staff_names()
            return _evidence(
                self.name, dataset, "ok",
                f"サンプル対応の生産担当 {len(names)}名を取得（名寄せ用）",
                [{"生産担当": n} for n in names],
            )
        if dataset == "ongoing_samples_by_staff":
            staff_name = params.get("staff_name", "")
            rows = get_ongoing_samples_by_staff(staff_name)
            return _evidence(
                self.name, dataset, "ok",
                f"{staff_name}が対応中のサンプル {len(rows)}件を取得",
                rows,
            )
        return _evidence(self.name, dataset, "unavailable", f"未対応のデータセット: {dataset}")


_PROVIDERS: dict[str, Any] = {
    "logsys": LogsysProvider(),
    "gmail": GmailProvider(),
    "project_sheet": ProjectSheetProvider(),
    "slack": SlackProvider(),
    "production": ProductionProvider(),
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