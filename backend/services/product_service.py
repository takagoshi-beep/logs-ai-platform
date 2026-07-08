"""商品(LOGS_CODE)を軸にした横断参照 (docs/architecture.md 14.30)。

案件(purchase_orders)はPO単位、商品はLOGS_CODE単位という別の粒度を持つ。
1つのPOに数十商品が含まれることも珍しくない実データ（例: PO
914-20260630_1は27商品）ため、案件詳細に商品明細まで全部持たせると
重くなりすぎる。代わりに「商品」を独立した単位として扱い、その商品が
どのPO・売上・仕入に含まれているかを横断的に見られるようにする。

商品への「関連」判定（Noritsuguの明示的な整理、2026-07-08）:
  直接: products.作成者名 == 本人
  間接（取引経由）: purchase_orders/sales/purchasesの担当者列のいずれかが
      本人と一致する明細のLOGS_CODE
      - purchasesだけ担当者列が伝票・明細の二重構造。明細を優先し、
        明細が空なら伝票の値を採用する（COALESCE）。
  間接（仕入先経由）: products.仕入先ID → suppliers.生産管理担当者名 が本人
  間接（サンプル経由）: products.Sample_CODE を production_samples.SPL品番
      に接続し、回答者または依頼元が本人

これら全てをUNIONした1回のクエリで取得する（案件一覧の高速化
（14.28）で学んだ「N回接続ではなく1回にまとめる」教訓を踏襲）。
"""
from __future__ import annotations

from typing import Any

from services.supabase_client import get_connection

_RELATED_LOGS_CODES_SQL = """
SELECT DISTINCT "LOGS_CODE" FROM purchase_orders
WHERE "営業担当者名" = %(name)s OR "営業事務担当者名" = %(name)s
   OR "生産管理担当者名" = %(name)s OR "企画担当者名" = %(name)s

UNION

SELECT DISTINCT "LOGS_CODE" FROM sales
WHERE "営業担当者名" = %(name)s OR "事務処理担当者名" = %(name)s OR "経理担当者名" = %(name)s

UNION

SELECT DISTINCT "LOGS_CODE" FROM purchases
WHERE COALESCE(NULLIF("明細営業担当者名", ''), "営業担当者名") = %(name)s
   OR COALESCE(NULLIF("明細営業事務担当者名", ''), "営業事務担当者名") = %(name)s
   OR "生産管理担当者名" = %(name)s

UNION

SELECT DISTINCT "LOGS_CODE" FROM products
WHERE "作成者名" = %(name)s

UNION

SELECT DISTINCT p."LOGS_CODE" FROM products p
JOIN suppliers s ON p."仕入先ID" = s."ID"
WHERE s."生産管理担当者名" = %(name)s

UNION

SELECT DISTINCT p."LOGS_CODE" FROM products p
JOIN production_samples ps ON p."Sample_CODE" = ps."SPL品番"
WHERE ps."回答者" = %(name)s OR ps."依頼元" = %(name)s
"""


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


def get_all_products(limit: int = 50) -> list[dict[str, Any]]:
    """商品マスタ全件から、直近登録分をlimit件だけ取得する(scope=all)。

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
                    'SELECT "LOGS_CODE", "Sample_CODE", "商品名", "型番", "仕入先名" '
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


def get_related_logs_codes(owner_name: str, limit: int = 50) -> list[str]:
    """自分に直接・間接的に関連する商品のLOGS_CODE一覧を、1回のクエリで
    まとめて取得する。owner_nameが空、もしくはDB接続に失敗した場合は
    空リストを返す（架空の一覧を作らない）。
    """
    if not owner_name:
        return []

    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(_RELATED_LOGS_CODES_SQL, {"name": owner_name})
                rows = cur.fetchall()
        finally:
            conn.close()
    except Exception as e:
        print(f"Error looking up related products: {e}")
        return []

    codes = [row[0] for row in rows if row[0]]
    return codes[:limit]


def _query_all(conn, sql: str, params: tuple) -> tuple[list[tuple], list[str]]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    return rows, columns


def _rows_to_dicts(rows: list[tuple], columns: list[str]) -> list[dict[str, Any]]:
    return [dict(zip(columns, row)) for row in rows]


def get_products_master_batch(logs_codes: list[str]) -> dict[str, dict[str, Any]]:
    """複数のLOGS_CODEの商品マスタ情報（+仕入先の生産管理担当者名）を、
    1回のクエリでまとめて取得する。"""
    if not logs_codes:
        return {}

    conn = get_connection()
    try:
        rows, columns = _query_all(
            conn,
            'SELECT p."LOGS_CODE", p."Sample_CODE", p."商品名", p."型番", p."商品分類", '
            'p."仕入先ID", p."仕入先名", p."作成者名", p."通常売価", p."論理原価", '
            's."生産管理担当者名" AS "supplier_production_staff" '
            'FROM products p '
            'LEFT JOIN suppliers s ON p."仕入先ID" = s."ID" '
            'WHERE p."LOGS_CODE" = ANY(%s)',
            (list(logs_codes),),
        )
    except Exception as e:
        print(f"Error batch-fetching product master: {e}")
        return {}
    finally:
        conn.close()

    result = {}
    for d in _rows_to_dicts(rows, columns):
        code = str(d.get("LOGS_CODE"))
        result[code] = d
    return result


def get_related_communications_for_product(
    user_email: str | None,
    logs_code: str,
    sample_code: str | None,
    max_results: int = 5,
) -> dict[str, Any]:
    """ログイン中の本人のGmail/Slackを、LOGS_CODE・Sample_CODE（SPL品番）
    をキーに検索する。案件のPO番号のような「担当者メールへのフォール
    バック」は行わない — LOGS_CODE/Sample_CODEはどちらもそれ自体が
    十分に一意な識別子であり、案件のような「PO番号は一致しないが
    担当者は一致する」という精度低下の心配がないため、単純にOR結合で
    良いと判断した（2026-07-08）。

    未連携の場合はgmail_service/slack_serviceが返す'unavailable'を
    そのまま伝える（架空の関連メッセージを作らない）。
    """
    if not user_email:
        unavailable = {"status": "unavailable", "summary": "ログインユーザーが特定できません。", "records": []}
        return {"gmail": unavailable, "slack": unavailable}

    parts = [f'"{logs_code}"'] if logs_code else []
    if sample_code:
        parts.append(f'"{sample_code}"')
    query = " OR ".join(parts)

    if not query:
        unavailable = {"status": "unavailable", "summary": "検索に使えるキーがありませんでした。", "records": []}
        return {"gmail": unavailable, "slack": unavailable}

    try:
        from services import gmail_service
        gmail_result = gmail_service.search_messages(user_email, query, max_results)
    except Exception as e:
        gmail_result = {"status": "error", "summary": f"Gmail検索中にエラーが発生しました: {e}", "records": []}

    try:
        from services import slack_service
        slack_result = slack_service.search_messages(user_email, query, max_results)
    except Exception as e:
        slack_result = {"status": "error", "summary": f"Slack検索中にエラーが発生しました: {e}", "records": []}

    return {"gmail": gmail_result, "slack": slack_result}


def get_product_detail(logs_code: str) -> dict[str, Any] | None:
    """1商品(LOGS_CODE)について、マスタ情報 + PO/売上/仕入/サンプルの
    横断履歴をまとめて返す。商品マスタに存在しない場合はNone。
    """
    conn = get_connection()
    try:
        master_rows, master_cols = _query_all(
            conn,
            'SELECT p.*, s."生産管理担当者名" AS "supplier_production_staff" '
            'FROM products p LEFT JOIN suppliers s ON p."仕入先ID" = s."ID" '
            'WHERE p."LOGS_CODE" = %s',
            (logs_code,),
        )
        if not master_rows:
            return None
        master = _rows_to_dicts(master_rows, master_cols)[0]
        sample_code = master.get("Sample_CODE")

        po_rows, po_cols = _query_all(
            conn,
            'SELECT "ID", "PO_No", "顧客名", "営業担当者名", "営業事務担当者名", '
            '"生産管理担当者名", "企画担当者名", "発注数量", "発注金額", "PO発行日" '
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
            '"生産管理担当者名", "仕入数量pcs", "仕入金額円", "伝票日" '
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

    return {
        "master": master,
        "purchase_orders": _rows_to_dicts(po_rows, po_cols),
        "sales": _rows_to_dicts(sales_rows, sales_cols),
        "purchases": _rows_to_dicts(purchase_rows, purchase_cols),
        "samples": sample_rows,
        "status": {
            "po_issued": len(po_rows) > 0,
            "sales_recorded": len(sales_rows) > 0,
            "purchase_recorded": len(purchase_rows) > 0,
            "sample_requested": len(sample_rows) > 0,
        },
    }
