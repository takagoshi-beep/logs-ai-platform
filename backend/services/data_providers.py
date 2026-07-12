"""Execution Layer v0.1 — Data Provider抽象化。

Reasoningは required_data の provider/dataset を指定するだけで、
取得手段（SQL・API・シート）は各Provider内部に隠蔽される。
取得結果は Evidence として返す。
"""
from __future__ import annotations

import statistics
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from services.supabase_client import get_connection


_PRODUCT_CATEGORY_LABELS = {
    1: "帽子", 2: "バッグ", 3: "財布/小物", 4: "サングラス/メガネ",
    5: "巻物", 6: "アパレル", 7: "ベルト", 8: "履物", 9: "アクセサリー",
}

# 2026-07-13（14.81追加）: 事業分類（salesテーブルの"事業分類"列）コード。
# code_masterのBUSINESS_TYPEで確認済みの対応表（reasoning_pipeline.py
# のQ1「OEM粗利」固定パターンが`事業分類=1`のSQLフィルタとして既に
# 使っている値と同じ）。chatの`get_sales_by_category`にbusiness_type
# 集計を追加する際、この対応表で人間可読なラベルに変換する。
_BUSINESS_TYPE_LABELS = {1: "OEM", 2: "商品仕入れ（海外）", 3: "商品仕入れ（国内）"}

# 2026-07-10（14.63追加）: 輸送方法コード（purchasesテーブルの"輸送方法"
# 列）。別チャット（app.py）で確立済みの対応表と一致させている。
_TRANSPORT_LABELS = {
    1: "OCEAN(CY)", 2: "OCEAN(CFS)", 3: "SKI EXPRESS", 4: "FERRY_CFS",
    5: "FERRY_CY", 6: "AIR", 7: "DHL", 8: "FEDEX", 9: "Score Japan",
    10: "S.F.EXPRESS", 11: "LOCAL DELIVERY", 12: "その他", 13: "OCS",
}

# NEWHATTANブランドの仕入先キーワード（app.pyと同じデフォルト除外仕入先）。
_NEWHATTAN_KEYWORDS = ["NEWHATTAN", "NEW HATTAN"]


def _product_category_label(code: Any) -> str:
    """商品分類の数値コードを実際の名称に変換する。対応表は既存の
    reference/02_database/sync/sync.py の v_product_master ビュー定義、
    および services/product_service.py の同名関数と完全に一致させている
    （2026-07-09、DBビューのCASE式をPython側から直接再利用する手段が
    無いため複製している。変更する際は3箇所とも合わせて直すこと）。
    """
    return _PRODUCT_CATEGORY_LABELS.get(code, "その他")


# 2026-07-09（14.60追加）: code_master CURRENCY の対応表。
# services/product_service.py の同名の辞書・関数と完全に一致させている
# （1=USD, 2=円, 3=RMB、Noritsuguが実際にcode_masterで確認して提示）。
_CURRENCY_LABELS = {1: "USD", 2: "円", 3: "RMB"}


def _currency_label(code: Any) -> str | None:
    if code is None:
        return None
    try:
        return _CURRENCY_LABELS.get(int(code), str(code))
    except (TypeError, ValueError):
        return str(code)


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
            # 2026-07-10（14.67修正、Noritsuguの指摘）: 以前はこの例外を
            # note フィールドに入れてClaudeに渡すだけで、Renderのログには
            # 一切出力していなかった。Claudeが実際のエラー文をそのまま
            # 画面に出さず「技術的な問題が発生しています」のように言い
            # 換えてしまうため、繰り返しログを確認しても原因が分からない
            # という状況が続いていた。print()で実際の例外をログに出す
            # ようにした（14.56のtimingログと同じ考え方）。
            import traceback
            print(f"[ERROR] LogsysProvider.fetch({dataset!r}, {params!r}) failed: {exc}")
            traceback.print_exc()
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
        "business_type": "事業分類",
    }

    def _sales_by_category(self, params: dict[str, Any]) -> dict[str, Any]:
        """商品分類・顧客分類・事業分類ごとの売上をSQL側でGROUP BY集計する
        (docs/architecture.md 14.32、事業分類は14.81で追加)。sales_lines/
        aggregateと違い、分類は数種類程度しかないため200件の壁に一切
        引っかからず、正確な内訳が返せる（「商品分類がバッグの売上は？」
        のような質問で、salesとproductsを手動で照合しようとして破綻して
        いた実例の修正）。

        事業分類（business_type）は「今月のOEMの売上は？」のような質問で、
        chatが正確な集計手段を持たず「ツールの限界です」としか答えられなかった
        実例（2026-07-12、Noritsuguが実チャットで発見）の修正。
        reasoning_pipeline.py のQ1固定パターンが`事業分類=1`で既に使っている
        のと同じcode_master確認済みの対応表を使う。
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
        if group_by == "事業分類":
            for row in rows:
                row["事業分類名"] = _BUSINESS_TYPE_LABELS.get(row.get("事業分類"), "その他")
        return _evidence(
            self.name, "sales_by_category", "ok",
            f"{group_by}別の売上を{len(rows)}分類分集計しました（分類数が少ないため全件、切り捨てなし）。",
            rows,
        )

    def _import_cost_estimate(self, params: dict[str, Any]) -> dict[str, Any]:
        """輸入経費の推定を、輸送方法別の実データ集計表として返す
        （2026-07-10、14.63、別チャットで確立済みのapp.py::
        run_import_cost_estimate()を移植）。

        「バッグ100個×5ドルの輸入経費は？」のような仮定の質問に対して、
        Claudeが少数の「実例」を選んで散文で外挿すると、①仕入先名から
        国籍等を作り話してしまう、②実データの分布が見えず検証しにくい、
        という問題が実際に起きた（Noritsuguの指摘）。この関数は、条件に
        近い伝票を全て集計し、輸送方法ごとに件数・数量範囲・経費率の
        範囲（最小〜最大、中央値）・想定金額を表形式で返す。Claudeは
        個別の実例を選んで外挿するのではなく、この集計結果をそのまま
        提示すること。

        商品分類・数量帯（質問の数量の0.5〜1.5倍）で対象を絞り込み、
        伝票（"伝票番号"）単位に集計してから輸送方法ごとにグループ化
        する（1伝票に複数商品の明細行があるため、明細行単位で集計すると
        同じ伝票が重複してカウントされてしまう）。

        NEWHATTANブランドの仕入先は既定で除外する（app.pyの既存
        ルールを継承。include_newhattan=Trueで明示的に含める）。

        為替レートは、実際の直近の仕入データから取得する（架空の為替
        レートを仮定しない、Noritsuguの指定）。直近データが無い場合は
        推定を行わずunavailableを返す。
        """
        qty = params.get("quantity")
        unit_price_usd = params.get("unit_price_usd")
        cat_code = params.get("category_code")
        include_newhattan = bool(params.get("include_newhattan", False))

        if qty is None or unit_price_usd is None or cat_code is None:
            return _evidence(
                self.name, "import_cost_estimate", "unavailable",
                "quantity（数量）・unit_price_usd（単価USD）・category_code（商品分類コード）は"
                "いずれも必須。不明な場合はユーザーに確認すること。",
            )

        fx_rows = self._query(
            'SELECT "為替" FROM purchases WHERE "為替" > 1 ORDER BY "ID" DESC LIMIT 1'
        )
        if not fx_rows or not fx_rows[0].get("為替"):
            return _evidence(
                self.name, "import_cost_estimate", "unavailable",
                "直近の為替レートが実データから取得できなかったため、推定できません。"
                "架空の為替レートを仮定して計算してはいけない。",
            )
        latest_fx = float(fx_rows[0]["為替"])

        qty_min, qty_max = qty * 0.5, qty * 1.5

        sql = (
            'WITH voucher_agg AS ('
            '  SELECT "伝票番号", MIN("輸送方法") AS "輸送方法", MIN("仕入先名") AS "仕入先名", '
            '         SUM("仕入数量pcs") AS "合計数量pcs", SUM("仕入金額円") AS "合計仕入金額円", '
            '         SUM("諸掛込金額円") AS "合計諸掛込金額円" '
            '  FROM purchases '
            '  WHERE "ステータス" IN (2, 3) AND "商品分類" = %s AND "仕入金額円" > 0 '
            '    AND "諸掛込金額円" > "仕入金額円" '
            '    AND "伝票日" >= CURRENT_DATE - INTERVAL \'1 year\' '
            '  GROUP BY "伝票番号"'
            ') '
            'SELECT "伝票番号", "輸送方法", "仕入先名", "合計数量pcs", '
            '       "合計諸掛込金額円" / "合計仕入金額円" AS "経費率" '
            'FROM voucher_agg '
            'WHERE "合計数量pcs" BETWEEN %s AND %s'
        )
        rows = self._query(sql, (cat_code, qty_min, qty_max))

        if not include_newhattan:
            rows = [
                r for r in rows
                if not any(kw in str(r.get("仕入先名", "")).upper() for kw in _NEWHATTAN_KEYWORDS)
            ]

        if not rows:
            return _evidence(
                self.name, "import_cost_estimate", "unavailable",
                f"条件（商品分類={cat_code}、数量{int(qty_min)}〜{int(qty_max)}個）に一致する"
                f"直近1年の仕入データが見つかりませんでした。架空の推定値を作ってはいけない。",
            )

        by_transport: dict[Any, list[dict[str, Any]]] = {}
        for r in rows:
            by_transport.setdefault(r.get("輸送方法"), []).append(r)

        buy_jpy = qty * unit_price_usd * latest_fx
        results = []
        for transport_code, group in by_transport.items():
            ratios = [g["経費率"] for g in group]
            rate_med = statistics.median(ratios)
            rate_min, rate_max = min(ratios), max(ratios)
            est_landed = buy_jpy * rate_med
            est_cost = est_landed - buy_jpy
            est_landed_min = buy_jpy * rate_min
            est_landed_max = buy_jpy * rate_max

            quantities = [g["合計数量pcs"] for g in group]
            suppliers = [g.get("仕入先名") for g in group if g.get("仕入先名")]
            top_suppliers = [name for name, _ in Counter(suppliers).most_common(3)]

            results.append({
                "輸送方法": _TRANSPORT_LABELS.get(transport_code, f"不明({transport_code})"),
                "伝票数": len(group),
                "データ不足": len(group) < 3,
                "対象数量_平均": round(sum(quantities) / len(quantities)),
                "対象数量_最小": min(quantities),
                "対象数量_最大": max(quantities),
                "推奨経費率": round(rate_med, 3),
                "経費率_最小": round(rate_min, 3),
                "経費率_最大": round(rate_max, 3),
                "推定仕入金額円": round(buy_jpy),
                "推定輸入経費円": round(est_cost),
                "推定諸掛込原価円": round(est_landed),
                "推定諸掛込原価_最小円": round(est_landed_min),
                "推定諸掛込原価_最大円": round(est_landed_max),
                "1個あたり原価円": round(est_landed / qty),
                "主な仕入先": top_suppliers,
            })

        results.sort(key=lambda r: r["伝票数"], reverse=True)

        return _evidence(
            self.name, "import_cost_estimate", "ok",
            f"商品分類={_product_category_label(cat_code)}、数量{int(qty_min)}〜{int(qty_max)}個、"
            f"直近1年の実データを輸送方法別に集計（伝票単位、{len(rows)}伝票、"
            f"適用為替レート{latest_fx}円/USD、実データから取得）。"
            f"各輸送方法の結果をそのまま提示すること（少数の実例を選んで外挿しない）。"
            f"「主な仕入先」に含まれていない属性（国籍等）を作り話してはいけない。"
            f"「データ不足」がTrueの輸送方法は伝票数が3件未満のため、参考値である旨を"
            f"必ず伝えること。",
            results,
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
        #
        # 2026-07-09（14.60追加、Noritsuguの指摘）: 「輸入経費率は輸送方法
        # によって変動する」とClaudeが実データを見ずに述べてしまった
        # 実例があった。実際には"輸送方法"（伝票レベル）・"通貨"・"為替"
        # （明細レベル、輸入経費率の定義式=諸掛込原価÷商品原価(商品単価
        # ×数量×為替)そのものに関わる列）はpurchasesに実在するが、以前は
        # このツールが選択していなかった。実在する列を選択することで、
        # 推測ではなく実データに基づいて要因を説明できるようにした。
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
            '"仕入金額円", "諸掛込金額円", "経費率", "輸送方法", "通貨", "為替", '
            'COALESCE(NULLIF("明細営業担当者名", \'\'), "営業担当者名") AS "営業担当者名" '
            f'FROM purchases WHERE {where} ORDER BY "伝票日"'
        )
        rows = self._query(sql, tuple(args))

        # 2026-07-09: sales_linesと同じ理由で、正確な合計はSQL側で
        # 別途計算する（recordsの切り捨てとは無関係な値にするため）。
        #
        # 2026-07-10（14.62修正）: 輸入経費率の集計は、knowledge/semantic/
        # purchase.md「輸入経費率」節の定義に統一した。国内仕入（諸掛込
        # 金額円が仕入金額円以下、輸入諸掛が実質発生していない行）は
        # 輸入経費率の統計からは除外する（含めると輸入経費の実態を示す
        # 統計として薄まってしまうため。以前はCOALESCEで仕入金額円に
        # フォールバックして含めていたが、knowledge/に一本化した定義に
        # 合わせて除外に変更した）。仕入金額合計・諸掛込金額合計は
        # 引き続き全行の合計（実績原価としての用途もあるため）。
        agg_sql = (
            'SELECT COUNT(*) AS "件数", COALESCE(SUM("仕入金額円"), 0) AS "仕入金額合計", '
            'COALESCE(SUM("諸掛込金額円"), 0) AS "諸掛込金額合計", '
            'SUM("諸掛込金額円") FILTER (WHERE "諸掛込金額円" > "仕入金額円") '
            '  / NULLIF(SUM("仕入金額円") FILTER (WHERE "諸掛込金額円" > "仕入金額円"), 0) '
            '  AS "輸入経費率" '
            f'FROM purchases WHERE {where}'
        )
        agg_rows = self._query(agg_sql, tuple(args))
        aggregate = agg_rows[0] if agg_rows else {"件数": len(rows), "仕入金額合計": 0, "諸掛込金額合計": 0, "輸入経費率": None}

        for row in rows:
            row["商品分類名"] = _product_category_label(row.get("商品分類"))
            row["通貨名"] = _currency_label(row.get("通貨"))

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

    def _find_similar_name(self, params: dict[str, Any]) -> dict[str, Any]:
        """あいまい検索（2026-07-10、14.65、Noritsuguの指定）: 入力文字列
        （表記ゆれ・スペルミス・曖昧な入力を含む）に最も近い実在の顧客名・
        社員氏名を、pg_trgmのトライグラム類似度でランキングして返す。

        これまでの検索は全てLIKE '%キーワード%'（部分一致）のみで、
        「たかはし」と「タカハシ」のような表記ゆれには対応できなかった。
        get_sales_lines等のsales_rep_keyword・customer_keywordで0件、
        または該当が不確かな場合は、まずこのツールで実在する正式名称を
        確認し、「『XX』を『YY』として検索しました」と明示してから
        本来のツールを呼び出すこと（架空の名前で検索を続けてはいけない）。
        """
        term = params.get("term")
        domain = params.get("domain")
        if not term or domain not in ("customer", "staff"):
            return _evidence(
                self.name, "find_similar_name", "unavailable",
                "term（検索したい名前）とdomain（customerまたはstaff）はいずれも必須。",
            )

        table, column = ("customers", "顧客名称") if domain == "customer" else ("staff", "社員氏名")
        # 2026-07-10（14.68修正、Renderのログで確認したエラー）: pg_trgmの
        # 類似検索演算子"%"が、psycopgのプレースホルダ記法（%s）と衝突し、
        # "incomplete placeholder"エラーになっていた。リテラルの"%"は
        # "%%"にエスケープする必要がある。
        sql = (
            f'SELECT "{column}" AS "名称", similarity("{column}", %s) AS "類似度" '
            f'FROM {table} '
            f'WHERE "{column}" %% %s '
            f'ORDER BY "類似度" DESC LIMIT 5'
        )
        rows = self._query(sql, (term, term))

        if not rows:
            return _evidence(
                self.name, "find_similar_name", "unavailable",
                f"「{term}」に類似する{'顧客名' if domain == 'customer' else '社員氏名'}が"
                f"見つかりませんでした。架空の名前で検索を続けてはいけない — "
                f"ユーザーに正確な名称を確認すること。",
            )

        return _evidence(
            self.name, "find_similar_name", "ok",
            f"「{term}」に類似する{'顧客名' if domain == 'customer' else '社員氏名'}を"
            f"類似度順に{len(rows)}件取得。最も類似度が高いものが必ずしも正解とは"
            f"限らないため、複数候補がある場合はユーザーに確認すること。",
            rows,
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