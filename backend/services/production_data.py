"""Read access to the production team's `production_mass`/
`production_samples` tables (docs/architecture.md 14.16/14.18).

These are synced independently from `purchase_orders` (see
`scripts/sync_production_data.py`) — this module is the read-side
counterpart, joining them to a project by PO number at query time
rather than at ingestion time, matching the `purchases`⇔`products`
pattern already used elsewhere in this codebase.

A PO can have more than one `production_mass` row (confirmed against
the real data: 9 out of 2,364 real PO numbers have 2 rows — e.g. a
reorder or a split shipment) — callers must not assume exactly one row
per project.
"""
from __future__ import annotations

from typing import Any

from services.supabase_client import get_connection

# production_mass の実列名 → フロントエンドに返すキー名。
# 列名は scripts/sync_production_data.py の列名クレンジング結果と必ず
# 一致させること（例: "PO#" → "POnum"、"PP logs着予定日" → "PP_logs着予定日"）。
_MASS_COLUMNS = {
    "POnum": "po_number",
    "Status": "status",
    "工場": "factory",
    "生産担当": "production_staff",
    "PP": "pp",
    "PP_logs着予定日": "pp_expected_date",
    "PP_承認日": "pp_approved_date",
    "TOP": "top",
    "TOP_logs着予定日": "top_expected_date",
    "TOP_承認日": "top_approved_date",
    "Ex-F": "ex_factory",
    "ETD": "etd",
    "ETA": "eta",
    "通関": "customs_clearance",
    "納品日": "delivery_date",
    "案件名": "project_name",
}

_SAMPLE_COLUMNS = {
    "見積No": "quote_no",
    "仕入先名": "supplier_name",
    "依頼内容": "request_content",
    "SPL品番": "spl_product_no",
    "カラー": "color",
    "サイズ": "size",
    "数量": "quantity",
    "価格": "price",
    "回答日": "answered_date",
    "通知状況": "notification_status",
    "商品名": "product_name",
}


def _select_clause(columns: dict[str, str]) -> str:
    return ", ".join(f'"{col}"' for col in columns)


def get_production_mass_status(po_number: str) -> list[dict[str, Any]]:
    """指定PO番号に紐づく量産の生産進捗を全件返す（0件・複数件どちらもあり得る）。"""
    if not po_number:
        return []
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f'SELECT {_select_clause(_MASS_COLUMNS)} FROM production_mass WHERE "POnum" = %s',
                (po_number,),
            )
            rows = cur.fetchall()
    except Exception as e:
        print(f"Error querying production_mass: {e}")
        return []
    finally:
        conn.close()

    source_keys = list(_MASS_COLUMNS.keys())
    return [
        {_MASS_COLUMNS[k]: v for k, v in zip(source_keys, row)}
        for row in rows
    ]


def search_production_samples(keyword: str, limit: int = 20) -> list[dict[str, Any]]:
    """仕入先名・見積No・SPL品番のいずれかにキーワードが含まれるサンプル依頼を検索する。

    量産と異なり、サンプル依頼はPO発行前の段階のものが多く、PO番号での
    突合ができない（見積No自体がPOではなく案件の識別子のため）。ここでは
    案件名・仕入先名などのキーワード検索のみ提供する。
    """
    if not keyword:
        return []
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f'''SELECT {_select_clause(_SAMPLE_COLUMNS)} FROM production_samples
                    WHERE "見積No" ILIKE %s OR "仕入先名" ILIKE %s OR "SPL品番" ILIKE %s
                    LIMIT %s''',
                (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit),
            )
            rows = cur.fetchall()
    except Exception as e:
        print(f"Error querying production_samples: {e}")
        return []
    finally:
        conn.close()

    source_keys = list(_SAMPLE_COLUMNS.keys())
    return [
        {_SAMPLE_COLUMNS[k]: v for k, v in zip(source_keys, row)}
        for row in rows
    ]