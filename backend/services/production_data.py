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

from datetime import datetime
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
    # 2026-07-15（14.106追加、Noritsuguが実データで確認）: "ETD"・"ETA"・
    # "納品日"・"EX_FTY"は対応中サンプル2629件中1件以下しか入力されて
    # おらず、14.19の判断（信頼できないため扱わない）は今も正しい。一方、
    # 同じシートにある別列"SP_ETD"・"SP_ETA"（サンプル専用の予定出荷日/
    # 到着予定日、14.19時点では存在に気づかず未調査だった）は、それぞれ
    # 471件・394件（約15〜18%）に入力があり、実用に耐える。ただし全件
    # 埋まっているわけではない点は呼び出し元（tool_registry.pyの説明文）
    # で明示する。
    "SP_ETD": "sp_planned_etd",
    "SP_ETA": "sp_planned_eta",
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


def list_sample_staff_names() -> list[str]:
    """production_samples の「回答者」（＝生産担当。仕入先とのやり取りを
    担当する人）の実在する名前一覧を返す。質問文にこの中の名前が含まれて
    いるかどうかの突き合わせに使う（Q5の顧客名マッチングと同じ設計）。
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT DISTINCT "回答者" FROM production_samples '
                'WHERE "回答者" IS NOT NULL AND "回答者" != \'\''
            )
            rows = cur.fetchall()
    except Exception as e:
        print(f"Error querying production_samples staff names: {e}")
        return []
    finally:
        conn.close()
    return [r[0] for r in rows if r[0]]


def _parse_flexible_date(value: Any) -> datetime | None:
    """`SP_ETA`等、スプレッドシート由来の自由記述の日付文字列をパースする。

    2026-07-15（14.107、Noritsuguが実チャットで発見）: `SP_ETA`の実際の
    保存形式は"2026/07/06"（スラッシュ区切り）だった。以前は
    `eta_period_start`/`eta_period_end`（"2026-07-01"のようなハイフン
    区切り）とSQL文字列比較（`"SP_ETA" >= %s`）で直接比較していたが、
    区切り文字が違うと文字列としての大小関係が実際の日付の前後関係と
    一致しない（'/'(0x2F)は'-'(0x2D)より大きいため、`<=`の比較が
    ほぼ常に成立せず、期間内のはずの行が全て除外されていた）。これに
    より「今月到着予定」の絞り込みが常に0件を返すという実例があった。
    文字列同士の比較ではなく、実際の日付として解釈してから比較する
    よう修正した。
    """
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def get_ongoing_samples_by_staff(
    staff_name: str, eta_period_start: str | None = None, eta_period_end: str | None = None
) -> list[dict[str, Any]]:
    """指定した生産担当（回答者）が扱っているサンプル依頼を全件返す。

    2026-07-15（14.108、Noritsuguの指定）: 以前は「通知状況」が空欄
    （＝未通知）の行だけを「対応中」として絞り込んでいた（2026-07-06
    確認済みの前提: 実データ上「空欄」「通知完了」の2値のみ）。しかし
    実チャットで、通知状況が「通知完了」であるにも関わらず、今後の
    到着予定日（SP_ETA）が入っている実例（サンプル#1763、王家さん
    担当、2026年7月着予定）が見つかった。「通知完了」は見積回答を
    依頼元に伝え終えたという一つの工程の完了を示すだけで、その後の
    サンプル到着自体は引き続き追跡対象でありうる、という業務実態が
    確認できたため、「通知状況」による絞り込みを撤去した — 指定した
    担当者が関わる全てのサンプル依頼を返す。

    2026-07-15（14.109、Noritsuguの指定）: 「通知状況」の運用自体が
    現在使われていない機能と確認できたため、14.108でいったん結果に
    残していた`notification_status`フィールド自体も取得・返却を
    やめた（絞り込みだけでなく、参照する必要も無い）。

    2026-07-15（14.106、Noritsuguが実データで発見・確認済み）:
    「ETD」・「ETA」・「納品日」・「EX_FTY」は実データの大半で1件以下
    しか入力が無く信頼できないため扱わない（14.19の判断が今も正しい）。
    一方、同じシートにある「SP_ETD」・「SP_ETA」（サンプル専用の予定
    出荷日/到着予定日）は、それぞれ約15〜18%に入力があり実用に耐える
    と確認できたため、`sp_planned_eta`として返す。ただし全件埋まって
    いるわけではない（大半は空欄）ため、呼び出し元（tool_registry.py
    の説明文）でその旨を明示すること。

    `eta_period_start`/`eta_period_end`を指定すると、SP_ETAでの期間
    絞り込みができる（「今月到着予定のサンプル」等の質問向け、
    2026-07-15追加、14.107でSQL文字列比較からPython側の日付パース
    比較に修正 — 実データの区切り文字（"/"）とフィルタ引数の区切り文字
    （"-"）が異なり、文字列比較では正しく絞り込めなかったため）。
    SP_ETAが未入力、または日付としてパースできない行は、期間指定時には
    結果に含まれない点に注意。
    """
    if not staff_name:
        return []

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT "仕入先名", "商品名", "見積No", "依頼内容", "回答日", "SP_ETD", "SP_ETA"
                   FROM production_samples
                   WHERE "回答者" = %s''',
                (staff_name,),
            )
            rows = cur.fetchall()
    except Exception as e:
        print(f"Error querying ongoing samples by staff: {e}")
        return []
    finally:
        conn.close()

    period_start_dt = _parse_flexible_date(eta_period_start)
    period_end_dt = _parse_flexible_date(eta_period_end)

    results = []
    for r in rows:
        sp_planned_eta = r[6]
        if period_start_dt or period_end_dt:
            eta_dt = _parse_flexible_date(sp_planned_eta)
            if eta_dt is None:
                continue  # 期間指定時、パースできない/未入力の行は除外
            if period_start_dt and eta_dt < period_start_dt:
                continue
            if period_end_dt and eta_dt > period_end_dt:
                continue
        results.append({
            "supplier_name": r[0],
            "product_name": r[1],
            "quote_no": r[2],
            "request_content": r[3],
            "answered_date": r[4],
            "sp_planned_etd": r[5],
            "sp_planned_eta": r[6],
        })

    return results