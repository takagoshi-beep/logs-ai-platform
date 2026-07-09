"""商品(products.ID)を軸にした横断参照 (docs/architecture.md 14.30)。

案件(purchase_orders)はPO単位、商品はID単位という別の粒度を持つ。
1つのPOに数十商品が含まれることも珍しくない実データ（例: PO
914-20260630_1は27商品）ため、案件詳細に商品明細まで全部持たせると
重くなりすぎる。代わりに「商品」を独立した単位として扱い、その商品が
どのPO・売上・仕入に含まれているかを横断的に見られるようにする。

キーについて重要な訂正（2026-07-08、Noritsuguの指摘）: 商品には
商品ID（内部キー、常に存在）→Sample_CODE（サンプル対応時に払い出し）
→LOGS_CODE（発注フラグが立った時に払い出し）という順で識別子が
段階的に付与される。つまりLOGS_CODEがNULLの商品は「まだ発注されて
いないだけ」の正常な状態であり、異常値でもレコード不備でもない。
そのため商品の一覧・詳細のキーは常に存在するproducts."ID"（商品ID）
を使い、LOGS_CODEは「あれば表示し、あればPO/売上/仕入との横断検索に
使う」という補助的な扱いにする。LOGS_CODEが無い商品は、PO/売上/仕入
の横断結果が単に空になるだけで、商品自体は正常に一覧・詳細に表示する。

商品への「関連」判定（Noritsuguの明示的な整理、2026-07-08）:
  直接: products.作成者名 == 本人
  間接（取引経由、LOGS_CODEで突合）: purchase_orders/sales/purchasesの
      担当者列のいずれかが本人と一致する明細を持つ商品
      - purchasesだけ担当者列が伝票・明細の二重構造。明細を優先し、
        明細が空なら伝票の値を採用する（COALESCE）。
  間接（仕入先経由）: products.仕入先ID → suppliers.生産管理担当者名 が本人
  間接（サンプル経由、Sample_CODEで突合）: products.Sample_CODE を
      production_samples.SPL品番に接続し、回答者または依頼元が本人

これら全てをUNIONした1回のクエリで取得する（案件一覧の高速化
（14.28）で学んだ「N回接続ではなく1回にまとめる」教訓を踏襲）。
"""
from __future__ import annotations

from typing import Any

from services.supabase_client import get_connection

_RELATED_PRODUCT_IDS_SQL = """
SELECT DISTINCT p."ID" FROM products p
JOIN purchase_orders po ON p."LOGS_CODE" = po."LOGS_CODE"
WHERE po."営業担当者名" = %(name)s OR po."営業事務担当者名" = %(name)s
   OR po."生産管理担当者名" = %(name)s OR po."企画担当者名" = %(name)s

UNION

SELECT DISTINCT p."ID" FROM products p
JOIN sales s ON p."LOGS_CODE" = s."LOGS_CODE"
WHERE s."営業担当者名" = %(name)s OR s."事務処理担当者名" = %(name)s OR s."経理担当者名" = %(name)s

UNION

SELECT DISTINCT p."ID" FROM products p
JOIN purchases pu ON p."LOGS_CODE" = pu."LOGS_CODE"
WHERE COALESCE(NULLIF(pu."明細営業担当者名", ''), pu."営業担当者名") = %(name)s
   OR COALESCE(NULLIF(pu."明細営業事務担当者名", ''), pu."営業事務担当者名") = %(name)s
   OR pu."生産管理担当者名" = %(name)s

UNION

SELECT "ID" FROM products WHERE "作成者名" = %(name)s

UNION

SELECT p."ID" FROM products p
JOIN suppliers s ON p."仕入先ID" = s."ID"
WHERE s."生産管理担当者名" = %(name)s

UNION

SELECT p."ID" FROM products p
JOIN production_samples ps ON p."Sample_CODE" = ps."SPL品番"
WHERE ps."回答者" = %(name)s OR ps."依頼元" = %(name)s
"""


_PRODUCT_CATEGORY_LABELS = {
    1: "帽子", 2: "バッグ", 3: "財布/小物", 4: "サングラス/メガネ",
    5: "巻物", 6: "アパレル", 7: "ベルト", 8: "履物", 9: "アクセサリー",
}


def _product_category_label(code: Any) -> str:
    """商品分類の数値コードを実際の名称に変換する。対応表は既存の
    reference/02_database/sync/sync.py の v_product_master ビュー定義と
    完全に一致させている（2026-07-08、表記のズレを防ぐため二重管理は
    避けたいが、DBビューのCASE式をPython側から再利用する手段が無いため
    やむを得ず複製— 変更する際は両方を合わせて直すこと）。
    """
    return _PRODUCT_CATEGORY_LABELS.get(code, "その他")


def _format_logs_code(value: Any) -> str | None:
    """LOGS_CODE列はSupabase上でdouble precision型のため、13564のような
    整数値でもPythonからは13564.0という浮動小数点として返ってくる。
    表示・外部検索（Gmail/Slack）用に「.0」を取り除いた整数表記へ正規化
    する（2026-07-08、Slack検索が実際には"13564.0"という存在しない
    文字列で行われ0件になっていた不具合の修正）。DB側のWHERE句比較には
    使わない — 元のdouble precision値のまま渡す方が型として素直なため、
    こちらは表示・検索文字列専用。
    """
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def sample_code_sort_key(sample_code: Any) -> tuple:
    """Sample_CODEの降順ソート用キー。数値として解釈できる場合は数値として
    比較し（"9"が"10"より前に来る、のような文字列比較の誤りを避ける）、
    数値でない場合やNoneは文字列として扱い、常に数値側より後ろに来る
    （2026-07-08、Noritsuguの指定によるソート順）。
    """
    if sample_code is None:
        return (0, "")
    s = str(sample_code)
    try:
        return (1, float(s))
    except ValueError:
        return (0, s)


def _query_all(conn, sql: str, params: tuple) -> tuple[list[tuple], list[str]]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    return rows, columns


def _rows_to_dicts(rows: list[tuple], columns: list[str]) -> list[dict[str, Any]]:
    return [dict(zip(columns, row)) for row in rows]


def get_all_products(limit: int = 50) -> list[dict[str, Any]]:
    """商品マスタ全件から、直近登録分をlimit件だけ取得する(scope=all)。
    LOGS_CODEがNULLの商品（未発注）も正常に含める。

    現時点ではMVP実装: "ID"降順（直近登録順）でlimit件だけ取得してから
    Sample_CODEでソートし直している。商品マスタの総件数が大きい場合、
    本当の意味での「Sample_CODE全体で見た上位N件」にはならない
    （limit件に絞り込んだ後でのソートのため）。ページング等を含めた
    設計は、Noritsuguの指摘の通り今後の検討課題（2026-07-08）。
    """
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT "ID", "LOGS_CODE", "Sample_CODE", "商品名", "型番", "仕入先名" '
                    'FROM products ORDER BY "ID" DESC LIMIT %s',
                    (limit,),
                )
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
        finally:
            conn.close()
    except Exception as e:
        print(f"Error fetching all products: {e}")
        return []

    products = _rows_to_dicts(rows, columns)
    products.sort(key=lambda p: sample_code_sort_key(p.get("Sample_CODE")), reverse=True)
    return products


def get_related_product_ids(owner_name: str, limit: int = 50) -> list[str]:
    """自分に直接・間接的に関連する商品のID（内部キー）一覧を、1回の
    クエリでまとめて取得する。owner_nameが空、もしくはDB接続に失敗した
    場合は空リストを返す（架空の一覧を作らない）。
    """
    if not owner_name:
        return []

    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(_RELATED_PRODUCT_IDS_SQL, {"name": owner_name})
                rows = cur.fetchall()
        finally:
            conn.close()
    except Exception as e:
        print(f"Error looking up related products: {e}")
        return []

    ids = [str(row[0]) for row in rows if row[0] is not None]
    return ids[:limit]


def get_products_master_batch(product_ids: list[str]) -> dict[str, dict[str, Any]]:
    """複数の商品ID（内部キー）の商品マスタ情報（+仕入先の生産管理担当者名）
    を、1回のクエリでまとめて取得する。"""
    if not product_ids:
        return {}

    conn = get_connection()
    try:
        rows, columns = _query_all(
            conn,
            'SELECT p."ID", p."LOGS_CODE", p."Sample_CODE", p."商品名", p."型番", p."商品分類", '
            'p."仕入先ID", p."仕入先名", p."作成者名", p."通常売価", p."論理原価", '
            's."生産管理担当者名" AS "supplier_production_staff" '
            'FROM products p '
            'LEFT JOIN suppliers s ON p."仕入先ID" = s."ID" '
            'WHERE p."ID" = ANY(%s)',
            (list(product_ids),),
        )
    except Exception as e:
        print(f"Error batch-fetching product master: {e}")
        return {}
    finally:
        conn.close()

    result = {}
    for d in _rows_to_dicts(rows, columns):
        result[str(d.get("ID"))] = d
    return result


def get_related_communications_for_product(
    user_email: str | None,
    logs_code: str | None,
    sample_code: str | None,
    max_results: int = 5,
) -> dict[str, Any]:
    """ログイン中の本人のGmail/Slackを、LOGS_CODE・Sample_CODE（SPL品番）
    をキーに検索する。

    Gmail: LOGS_CODE・Sample_CODEを引用符付きでOR結合する。引用符付き
    フレーズ検索が正しく機能することを実際のデータで確認済み。

    Slack: **Sample_CODEのみ、引用符なし**で検索する。2026-07-08の実機
    診断で判明した2つの実際の問題を踏まえた設計:
      1. Slackの検索は、ハイフンを含む語を引用符で囲むと一致しなくなる
         （実例: `"SLG-06120"`は0件だが、`SLG-06120`（引用符なし）は
         正しく1件ヒットした）。そのためSlackでは引用符を使わない。
      2. LOGS_CODEのような素の数字だけでの検索は、無関係な別の数値
         （実例: 全く別件の「売上ID：13564」がヒットした）と衝突し
         やすく精度が低い。そのためSlackではLOGS_CODEを検索キーに
         含めない（Sample_CODEはハイフン入りの複合文字列で衝突しにくい
         ため採用）。

    未連携の場合はgmail_service/slack_serviceが返す'unavailable'を
    そのまま伝える（架空の関連メッセージを作らない）。
    """
    if not user_email:
        unavailable = {"status": "unavailable", "summary": "ログインユーザーが特定できません。", "records": []}
        return {"gmail": unavailable, "slack": unavailable}

    logs_code = _format_logs_code(logs_code)
    gmail_parts = [f'"{logs_code}"'] if logs_code else []
    if sample_code:
        gmail_parts.append(f'"{sample_code}"')
    gmail_query = " OR ".join(gmail_parts)
    slack_query = sample_code or ""

    if not gmail_query and not slack_query:
        unavailable = {"status": "unavailable", "summary": "検索に使えるキー（LOGS_CODE・Sample_CODE）がありませんでした。", "records": []}
        return {"gmail": unavailable, "slack": unavailable}

    if gmail_query:
        try:
            from services import gmail_service
            gmail_result = gmail_service.search_messages(user_email, gmail_query, max_results)
        except Exception as e:
            gmail_result = {"status": "error", "summary": f"Gmail検索中にエラーが発生しました: {e}", "records": []}
    else:
        gmail_result = {"status": "unavailable", "summary": "検索に使えるキーがありませんでした。", "records": []}

    if slack_query:
        try:
            from services import slack_service
            slack_result = slack_service.search_messages(user_email, slack_query, max_results)
        except Exception as e:
            slack_result = {"status": "error", "summary": f"Slack検索中にエラーが発生しました: {e}", "records": []}
    else:
        slack_result = {"status": "unavailable", "summary": "Sample_CODEが無いため、Slack検索はできません。", "records": []}

    return {"gmail": gmail_result, "slack": slack_result}


def get_product_detail(product_id: str) -> dict[str, Any] | None:
    """1商品(products.ID)について、マスタ情報 + PO/売上/仕入/サンプルの
    横断履歴をまとめて返す。商品マスタに存在しない場合はNone。

    LOGS_CODEがNULL（未発注）の商品は、PO/売上/仕入の横断結果が
    空リストになるだけで、正常に詳細を返す（サンプル対応履歴は
    Sample_CODEがあれば独立して取得できる）。
    """
    conn = get_connection()
    try:
        master_rows, master_cols = _query_all(
            conn,
            'SELECT p.*, s."生産管理担当者名" AS "supplier_production_staff" '
            'FROM products p LEFT JOIN suppliers s ON p."仕入先ID" = s."ID" '
            'WHERE p."ID" = %s',
            (product_id,),
        )
        if not master_rows:
            return None
        master = _rows_to_dicts(master_rows, master_cols)[0]
        master["商品分類名"] = _product_category_label(master.get("商品分類"))
        logs_code = master.get("LOGS_CODE")  # 生の値（double precision）をDBクエリの比較に使う
        sample_code = master.get("Sample_CODE")
        master["LOGS_CODE"] = _format_logs_code(logs_code)  # レスポンス用に表示を正規化（13564.0 → "13564"）

        po_rows: list[tuple] = []
        po_cols: list[str] = []
        sales_rows: list[tuple] = []
        sales_cols: list[str] = []
        purchase_rows: list[tuple] = []
        purchase_cols: list[str] = []
        if logs_code:
            po_rows, po_cols = _query_all(
                conn,
                'SELECT "ID", "PO_No", "顧客名", "営業担当者名", "営業事務担当者名", '
                '"生産管理担当者名", "企画担当者名", "発注数量", "発注金額", "PO発行日", '
                '"発注単価", "輸入経費率", "売上原価", "通貨" '
                'FROM purchase_orders WHERE "LOGS_CODE" = %s ORDER BY "PO発行日" DESC',
                (logs_code,),
            )
            sales_rows, sales_cols = _query_all(
                conn,
                'SELECT "得意先名", "営業担当者名", "事務処理担当者名", "経理担当者名", '
                '"数量pcs", "売上金額", "売上入力日" '
                'FROM sales WHERE "LOGS_CODE" = %s ORDER BY "売上入力日" DESC',
                (logs_code,),
            )
            purchase_rows, purchase_cols = _query_all(
                conn,
                'SELECT "仕入先名", '
                'COALESCE(NULLIF("明細営業担当者名", \'\'), "営業担当者名") AS "営業担当者名", '
                'COALESCE(NULLIF("明細営業事務担当者名", \'\'), "営業事務担当者名") AS "営業事務担当者名", '
                '"生産管理担当者名", "仕入数量pcs", "仕入金額円", "伝票日", '
                '"経費率", "実際原価" '
                'FROM purchases WHERE "LOGS_CODE" = %s ORDER BY "伝票日" DESC',
                (logs_code,),
            )

        sample_rows: list[dict[str, Any]] = []
        if sample_code:
            raw_sample_rows, sample_cols = _query_all(
                conn,
                'SELECT "見積No", "仕入先名", "依頼内容", "カラー", "サイズ", "数量", '
                '"回答者", "依頼元", "回答日", "通知状況" '
                'FROM production_samples WHERE "SPL品番" = %s ORDER BY "回答日" DESC',
                (sample_code,),
            )
            sample_rows = _rows_to_dicts(raw_sample_rows, sample_cols)
    except Exception as e:
        print(f"Error building product detail: {e}")
        return None
    finally:
        conn.close()

    # 商品マスタ自体には営業事務担当者の列が存在しない（PO・仕入の
    # 伝票にしか記録されない）ため、この商品のPO履歴・仕入履歴から
    # 導出して商品情報として表示する（PO発行日の新しい順で最初に
    # 見つかった値を採用。無ければ仕入履歴を見る。2026-07-09、
    # 営業事務担当者を商品にも紐づけたいという要望への対応）。
    po_dicts = _rows_to_dicts(po_rows, po_cols)
    purchase_dicts = _rows_to_dicts(purchase_rows, purchase_cols)
    sales_admin = next((r["営業事務担当者名"] for r in po_dicts if r.get("営業事務担当者名")), None)
    if not sales_admin:
        sales_admin = next((r["営業事務担当者名"] for r in purchase_dicts if r.get("営業事務担当者名")), None)
    master["営業事務担当者名"] = sales_admin

    # 2026-07-09（14.44・14.46、Noritsuguの指定）: 発注単価・予定輸入
    # 経費率・予定原価単価はpurchase_orders（明細レベル）の最新行
    # （PO発行日が新しい順）から、実績輸入経費率・実績原価はpurchases
    # （明細レベル）の最新行（伝票日が新しい順）から取る。po_dicts/
    # purchase_dictsは既に日付降順なので、[0]がそれぞれ最新行。
    #
    # purchase_orders."売上原価"は明細の合計金額（発注数量×単価。列の
    # 並び順が発注数量・発注数量(pcs)・発注金額・売上原価・売上金額と
    # 連続しており、いずれも合計値であることをExcel原本で確認済み）
    # であり単価ではないため、"発注数量"で割って単価化する（14.46、
    # Noritsuguの指摘で判明した誤り）。
    #
    # "発注単価"は"通貨"列（円ではない場合がある）で表示するため、
    # 通貨コードも一緒に持たせる。
    latest_po = po_dicts[0] if po_dicts else {}
    latest_purchase = purchase_dicts[0] if purchase_dicts else {}
    po_quantity = latest_po.get("発注数量")
    po_total_cost = latest_po.get("売上原価")
    master["発注単価"] = latest_po.get("発注単価")
    master["発注単価通貨"] = latest_po.get("通貨")
    master["予定輸入経費率"] = latest_po.get("輸入経費率")
    master["予定原価単価"] = (
        po_total_cost / po_quantity if po_total_cost is not None and po_quantity else None
    )
    master["実績輸入経費率"] = latest_purchase.get("経費率")
    master["実績原価"] = latest_purchase.get("実際原価")

    return {
        "master": master,
        "purchase_orders": po_dicts,
        "sales": _rows_to_dicts(sales_rows, sales_cols),
        "purchases": purchase_dicts,
        "samples": sample_rows,
        "status": {
            "po_issued": len(po_rows) > 0,
            "sales_recorded": len(sales_rows) > 0,
            "purchase_recorded": len(purchase_rows) > 0,
            "sample_requested": len(sample_rows) > 0,
        },
    }
