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
