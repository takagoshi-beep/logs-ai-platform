"""Execution Layer v0.1 — Data Provider抽象化。

Reasoningは required_data の provider/dataset を指定するだけで、
取得手段（SQL・API・シート）は各Provider内部に隠蔽される。
取得結果は Evidence として返す。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from services.supabase_client import get_connection


_PRODUCT_CATEGORY_LABELS = {
    1: "帽子", 2: "バッグ", 3: "財布/小物", 4: "サングラス/メガネ",
    5: "巻物", 6: "アパレル", 7: "ベルト", 8: "履物", 9: "アクセサリー",
}


def _product_category_label(code: Any) -> str:
    """商品分類の数値コードを実際の名称に変換する。対応表は既存の
    reference/02_database/sync/sync.py の v_product_master ビュー定義、
    および services/product_service.py の同名関数と完全に一致させている
    （2026-07-09、DBビューのCASE式をPython側から直接再利用する手段が
    無いため複製している。変更する際は3箇所とも合わせて直すこと）。
    """
    return _PRODUCT_CATEGORY_LABELS.get(code, "その他")


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
        # v_sales_enriched（14.32）を経由することで、商品分類・顧客分類・
        # 仕入先の生産管理担当者・各担当者のメール/Slack IDも一緒に返す。
        where = "\"ステータス\" IN (2, 3, 4, 5) AND \"決済方法\" != '4'"
        args: list[Any] = []
        if params.get("period_start"):
            where += ' AND "売上入力日" >= %s'
            args.append(params["period_start"])
        if params.get("period_end"):
            where += ' AND "売上入力日" <= %s'
            args.append(params["period_end"])
        if params.get("customer_keyword"):
            where += ' AND "得意先名" LIKE %s'
            args.append(f"%{params['customer_keyword']}%")
        if params.get("sales_rep_keyword"):
            # 「〇〇さんの売上/伝票」という聞き方は役割を問わないことが多い
            # ため、営業担当者・営業事務(事務処理担当者)・経理担当・伝票の
            # 作成者(データ入力した人)のいずれかに名前があればヒットする
            # ようにOR結合している（2026-07-09、「髙橋さんが作成した伝票」
            # という質問が営業担当者名だけの検索では0件になった実例の修正）。
            where += (
                ' AND ("営業担当者名" LIKE %s OR "事務処理担当者名" LIKE %s '
                'OR "経理担当者名" LIKE %s OR "作成者名" LIKE %s)'
            )
            kw = f"%{params['sales_rep_keyword']}%"
            args.extend([kw, kw, kw, kw])

        sql = (
            'SELECT "売上入力日", "得意先ID", "得意先名", "登録商品名", '
            '"LOGS_CODE", "SAMPLE_CODE", "product_category", '
            '"事業分類", "数量pcs", "売上金額", "明細粗利", '
            '"営業担当者名", "事務処理担当者名", "経理担当者名", "作成者名", '
            '"customer_category", "customer_business_scale", "customer_trade_tendency", '
            '"supplier_production_staff", "sales_rep_email", "sales_admin_email", "accounting_email" '
            f'FROM v_sales_enriched WHERE {where} ORDER BY "売上入力日"'
        )
        rows = self._query(sql, tuple(args))

        # 2026-07-09: この行一覧はツール結果の上限（_MAX_RECORDS_FOR_CLAUDE）で
        # 切り捨てられることがあるため、合計金額・件数は切り捨て後のサンプルを
        # Claudeが手計算するのではなく、SQL側で正確に計算して別途渡す
        # （「石川さんの7月の売上」のような質問で、643件のうち200件しか見えず
        # 実際より少ない金額を回答してしまっていた実例の修正）。
        agg_sql = (
            'SELECT COUNT(*) AS "件数", COALESCE(SUM("売上金額"), 0) AS "売上金額合計", '
            'COALESCE(SUM("明細粗利"), 0) AS "粗利合計" '
            f'FROM v_sales_enriched WHERE {where}'
        )
        agg_rows = self._query(agg_sql, tuple(args))
        aggregate = agg_rows[0] if agg_rows else {"件数": len(rows), "売上金額合計": 0, "粗利合計": 0}

        period = (
            f"{params.get('period_start', '')}〜{params.get('period_end', '')}"
            if params.get("period_start") else "全期間"
        )
        evidence = _evidence(
            self.name, "sales_lines", "ok",
            f"売上明細 {len(rows)}件を取得（{period}、有効な受注のみ・標準フィルタ適用済み）。"
            f"合計金額・件数はaggregateフィールドの値を使うこと（recordsが後で"
            f"切り捨てられても、aggregateは常にフィルタ条件全体に対する正確な値）。",
            rows,
        )
        evidence["aggregate"] = aggregate
        return evidence

    _SALES_GROUP_BY_COLUMNS = {
        "product_category": "product_category",
        "customer_category": "customer_category",
    }

    def _sales_by_category(self, params: dict[str, Any]) -> dict[str, Any]:
        """商品分類・顧客分類ごとの売上をSQL側でGROUP BY集計する
        (docs/architecture.md 14.32)。sales_lines/aggregateと違い、分類は
        9種類程度しかないため200件の壁に一切引っかからず、正確な内訳が
        返せる（「商品分類がバッグの売上は？」のような質問で、salesと
        productsを手動で照合しようとして破綻していた実例の修正）。
        """
        group_by = self._SALES_GROUP_BY_COLUMNS.get(params.get("group_by", "product_category"))
        if not group_by:
            return _evidence(
                self.name, "sales_by_category", "unavailable",
                f"group_byには{list(self._SALES_GROUP_BY_COLUMNS)}のいずれかを指定してください。",
            )

        where = "\"ステータス\" IN (2, 3, 4, 5) AND \"決済方法\" != '4'"
        args: list[Any] = []
        if params.get("period_start"):
            where += ' AND "売上入力日" >= %s'
            args.append(params["period_start"])
        if params.get("period_end"):
            where += ' AND "売上入力日" <= %s'
            args.append(params["period_end"])
        if params.get("sales_rep_keyword"):
            where += (
                ' AND ("営業担当者名" LIKE %s OR "事務処理担当者名" LIKE %s '
                'OR "経理担当者名" LIKE %s OR "作成者名" LIKE %s)'
            )
            kw = f"%{params['sales_rep_keyword']}%"
            args.extend([kw, kw, kw, kw])

        sql = (
            f'SELECT "{group_by}", COUNT(*) AS "件数", '
            'COALESCE(SUM("売上金額"), 0) AS "売上金額合計", '
            'COALESCE(SUM("明細粗利"), 0) AS "粗利合計" '
            f'FROM v_sales_enriched WHERE {where} '
            f'GROUP BY "{group_by}" ORDER BY "売上金額合計" DESC'
        )
        rows = self._query(sql, tuple(args))
        return _evidence(
            self.name, "sales_by_category", "ok",
            f"{group_by}別の売上を{len(rows)}分類分集計しました（分類数が少ないため全件、切り捨てなし）。",
            rows,
        )

    def _purchase_lines(self, params: dict[str, Any]) -> dict[str, Any]:
        # ステータスIN(2,3)は本番運用中のシステムプロンプトで確認済みの
        # 仕入集計時の正式フィルタ条件。
        # 営業担当者名は伝票レベル・明細レベルの両方に存在するため、
        # 明細を優先し、空欄の場合のみ伝票の値を採用する（14.30で確認した
        # purchasesテーブル特有の二重構造）。
        #
        # 2026-07-09（14.59修正、Noritsuguの指摘）: 以前は"経費率"列
        # （既に確定済みの1.xxの比率。project_service.py/product_service.py
        # で今日一日かけて定義・整理した値と同じ列）を渡していなかった
        # ため、Claudeが"仕入金額円"と"諸掛込金額円"から自分で（誤った）
        # パーセンテージ計算をしてしまっていた（実例: 25.5%という表記は
        # 諸掛込原価÷商品原価=1.xxという定義とは異なる、独自のマークアップ
        # 率計算になっていた）。"経費率"をそのまま渡し、Claudeが再計算
        # しないよう明記する。
        #
        # また、参照データの信頼性確認のため、識別情報（POnum・LOGS_CODE）
        # も明記する（Noritsuguの指摘: 実データであることを確認できるよう、
        # 数量・仕入先だけでなくPO番号等も示すべき）。
        where = '"ステータス" IN (2, 3)'
        args: list[Any] = []
        if params.get("period_start"):
            where += ' AND "伝票日" >= %s'
            args.append(params["period_start"])
        if params.get("period_end"):
            where += ' AND "伝票日" <= %s'
            args.append(params["period_end"])
        if params.get("sales_rep_keyword"):
            where += ' AND COALESCE(NULLIF("明細営業担当者名", \'\'), "営業担当者名") LIKE %s'
            args.append(f"%{params['sales_rep_keyword']}%")

        sql = (
            'SELECT "伝票日", "POnum", "LOGS_CODE", "仕入先名", "商品分類", "仕入数量pcs", '
            '"仕入金額円", "諸掛込金額円", "経費率", '
            'COALESCE(NULLIF("明細営業担当者名", \'\'), "営業担当者名") AS "営業担当者名" '
            f'FROM purchases WHERE {where} ORDER BY "伝票日"'
        )
        rows = self._query(sql, tuple(args))

        # 2026-07-09: sales_linesと同じ理由で、正確な合計はSQL側で
        # 別途計算する（recordsの切り捨てとは無関係な値にするため）。
        # 輸入経費率の集計値は、project_service.py/product_service.pyと
        # 同じ計算方法（SUM(諸掛込金額円)/SUM(仕入金額円)の加重平均、
        # 諸掛込金額円がNULLの行（国内仕入）は仕入金額円にフォールバック）
        # で、1.xxの比率として返す。単純平均や独自のパーセンテージ計算を
        # Claudeがしないよう、この値をそのまま使わせる。
        agg_sql = (
            'SELECT COUNT(*) AS "件数", COALESCE(SUM("仕入金額円"), 0) AS "仕入金額合計", '
            'COALESCE(SUM("諸掛込金額円"), 0) AS "諸掛込金額合計", '
            'SUM(COALESCE("諸掛込金額円", "仕入金額円")) / NULLIF(SUM("仕入金額円"), 0) AS "輸入経費率" '
            f'FROM purchases WHERE {where}'
        )
        agg_rows = self._query(agg_sql, tuple(args))
        aggregate = agg_rows[0] if agg_rows else {"件数": len(rows), "仕入金額合計": 0, "諸掛込金額合計": 0, "輸入経費率": None}

        for row in rows:
            row["商品分類名"] = _product_category_label(row.get("商品分類"))

        evidence = _evidence(
            self.name, "purchase_lines", "ok",
            f"仕入明細 {len(rows)}件を取得（諸掛り込み金額、標準フィルタ適用済み）。"
            f"合計金額・件数・輸入経費率はaggregateフィールドの値を使うこと。"
            f"「経費率」列は既に確定済みの1.xxの比率（諸掛込原価÷商品原価）であり、"
            f"仕入金額円・諸掛込金額円から独自に計算し直してはいけない（パーセンテージ"
            f"表記にする場合は経費率をそのまま%表示するのではなく、「経費率1.xx」という"
            f"元の定義のまま伝えること。1ドル=◯◯円のような仮定の為替レートを使った"
            f"架空の計算例を作ってはいけない — 実データに無い数値は答えないこと）。"
            f"POnum（PO番号）・LOGS_CODEは、この仕入明細が実データであることを示す"
            f"識別情報として、回答内で具体的に示すこと。",
            rows,
        )
        evidence["aggregate"] = aggregate
        return evidence

    def _projects(self, params: dict[str, Any]) -> dict[str, Any]:
        """「案件」に相当する実データは purchase_orders テーブル
        （PO発行〜納品・輸送・検品スケジュール管理、案件単位）。

        2026-07-09（14.57修正）: 以前は「納品済みか」を判定する手段が
        無く、Claudeが信頼できない"顧客納品日"（POに入力される予定日
        であり、実際に納品されたかどうかとは無関係）から推測しようと
        して破綻していた実例があった（KBFの未納品案件を尋ねられ、
        200件の壁もあって正しく答えられなかった）。docs/architecture.md
        14.33で確立した「納品済みか＝sales（売上）に実データがあるか、
        または生産管理『量産』シートの表示フラグ=0か」という判定を、
        このチャットツールにも反映した。delivery_statusで絞り込める
        ようにし、集計件数（aggregate）は200件の壁の影響を受けない
        正確な値を返す（14.31と同じ理由）。
        """
        keyword = params.get("keyword")
        delivery_status = params.get("delivery_status")  # "delivered" | "undelivered" | None

        base_select = (
            'SELECT po."ID", po."案件名", po."顧客名", po."ステータス", po."PO_No", po."顧客納品日", '
            'EXISTS(SELECT 1 FROM sales s WHERE s."LOGS_CODE" = po."LOGS_CODE") AS "has_sales", '
            'EXISTS('
            '    SELECT 1 FROM production_mass pm '
            '    WHERE pm."POnum" = po."PO_No" AND pm."表示"::text = \'0\''
            ') AS "production_closed" '
            'FROM purchase_orders po WHERE 1=1'
        )
        args: list[Any] = []
        if keyword:
            base_select += ' AND (po."案件名" LIKE %s OR po."顧客名" LIKE %s)'
            args += [f"%{keyword}%", f"%{keyword}%"]

        delivery_clause = ""
        if delivery_status == "undelivered":
            delivery_clause = ' WHERE NOT ("has_sales" OR "production_closed")'
        elif delivery_status == "delivered":
            delivery_clause = ' WHERE ("has_sales" OR "production_closed")'

        sql = f'SELECT * FROM ({base_select}) sub{delivery_clause} ORDER BY "顧客納品日"'
        rows = self._query(sql, tuple(args))

        agg_sql = f'SELECT COUNT(*) AS "件数" FROM ({base_select}) sub{delivery_clause}'
        agg_rows = self._query(agg_sql, tuple(args))
        aggregate = agg_rows[0] if agg_rows else {"件数": len(rows)}

        label = f"「{keyword}」関連の" if keyword else ""
        status_label = {"undelivered": "未納品の", "delivered": "納品済みの"}.get(delivery_status, "")
        evidence = _evidence(
            self.name, "projects", "ok",
            f"{label}{status_label}案件 {len(rows)}件を取得（合計件数はaggregateフィールドを使うこと。"
            f"納品判定はhas_sales（売上実データの有無）またはproduction_closed"
            f"（生産管理『量産』シートの表示フラグ=0）に基づく。顧客納品日はPOへの"
            f"入力予定日であり実際の納品有無とは無関係なので、納品判定には使わないこと）。",
            rows,
        )
        evidence["aggregate"] = aggregate
        return evidence

    def _customer_master(self, params: dict[str, Any]) -> dict[str, Any]:
        sql = 'SELECT "ID", "顧客名称", "営業担当者名" FROM customers WHERE 1=1'
        args: list[Any] = []
        if params.get("keyword"):
            sql += ' AND "顧客名称" LIKE %s'
            args.append(f"%{params['keyword']}%")
        rows = self._query(sql, tuple(args))
        return _evidence(self.name, "customer_master", "ok", f"顧客マスタ {len(rows)}件を取得（名寄せ・営業担当確認用）", rows)

    def _product_master(self, params: dict[str, Any]) -> dict[str, Any]:
        rows = self._query(
            'SELECT "LOGS_CODE", "Sample_CODE", "商品名", "型番", "商品分類", "仕入先名" FROM products'
        )
        for row in rows:
            row["商品分類名"] = _product_category_label(row.get("商品分類"))
        return _evidence(self.name, "product_master", "ok", f"商品マスタ {len(rows)}件を取得", rows)

    def _code_master(self, params: dict[str, Any]) -> dict[str, Any]:
        """code_masterテーブルの中身を、列名を決め打ちせず全て取得する。

        2026-07-06に発見: chat_agent（Function Calling）が「事業分類」の
        意味を code_master で確認せず一般常識で推測し、実際とは異なる
        誤った対応（2=OEM事業またはODM事業 等、正しくは2=商品仕入れ海外）
        を回答したことがあった。code_master テーブルの実際の列名は、
        元のExcelシート（logsys-chatリポジトリのsync.pyが読む「コード」
        タブ）の見出しをそのまま使っており、この開発環境からは正確な
        列名が分からない — 列名を決め打ちして再度誤った推測をするより、
        `SELECT *` で実際の列名・値をそのまま返し、Claude自身に読み取ら
        せる方が安全（sync.pyの列名クレンジング処理と同じ理由で、＃や
        全角記号を含む列名になっている可能性があるため）。件数が少ない
        参照用マスタテーブルという性質上、全件取得しても問題にならない。
        """
        rows = self._query("SELECT * FROM code_master")
        return _evidence(
            self.name, "code_master", "ok",
            f"コードマスタ {len(rows)}件を取得（各テーブルの数値コードの意味を確認する用途）",
            rows,
        )

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
            'SELECT "売上入力日", "得意先名", "登録商品名", "売上金額", "決済方法", "営業担当者名" '
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
            'SELECT "売上入力日", "得意先名", "登録商品名", "売上金額", "ステータス", "営業担当者名" '
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