"""Evidence Interpretation Layer v0.1 — Integrated Evidenceから事実(Facts)を抽出する。

データ → 特徴抽出 → 事実整理 → 判断材料(Facts) の工程を独立させたLayer。
ここでは事実の列挙のみを行い、判断（Decision）は行わない。
Facts はDataset・Providerごとの専用ロジックで、取得データ全件から生成する
（表示用のサンプリングとは完全に分離し、一部データだけを見て誤った事実を
導かないようにする）。
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Callable


def _fmt_amount(value: int) -> str:
    if value >= 10000:
        return f"{value // 10000}万円"
    return f"{value}円"


def _sales_lines_facts(records: list[dict[str, Any]]) -> list[str]:
    if not records:
        return []
    facts: list[str] = []
    by_type = Counter(r.get("案件区分") or "不明" for r in records)
    for category, count in by_type.items():
        facts.append(f"{category}案件は{count}件")
    by_customer: dict[str, int] = {}
    for r in records:
        name = r.get("顧客名") or "不明"
        by_customer[name] = by_customer.get(name, 0) + (r.get("金額") or 0)
    if by_customer:
        top_customer = max(by_customer, key=by_customer.get)
        facts.append(f"{top_customer}が最大売上")
    gross_profit = sum(r.get("概算粗利") or 0 for r in records)
    if gross_profit:
        facts.append(f"概算粗利{_fmt_amount(gross_profit)}")
    return facts


def _purchase_lines_facts(records: list[dict[str, Any]]) -> list[str]:
    if not records:
        return []
    facts = [f"仕入明細{len(records)}件"]
    total = sum(r.get("金額") or 0 for r in records)
    if total:
        facts.append(f"仕入合計{_fmt_amount(total)}")
    suppliers = {r.get("仕入先名") for r in records if r.get("仕入先名")}
    if suppliers:
        facts.append(f"仕入先は{len(suppliers)}社")
    return facts


def _project_classification_facts(records: list[dict[str, Any]]) -> list[str]:
    facts = []
    for r in records:
        category = r.get("案件区分")
        if category is not None:
            facts.append(f"案件区分「{category}」は{r.get('件数')}件")
    return facts


def _product_master_facts(records: list[dict[str, Any]]) -> list[str]:
    if not records:
        return []
    by_category = Counter(r.get("分類") or "不明" for r in records)
    return [f"{category}商品は{count}件" for category, count in by_category.items()]


def _projects_facts(records: list[dict[str, Any]]) -> list[str]:
    if not records:
        return []
    facts = []
    by_status = Counter(r.get("ステータス") or "不明" for r in records)
    for status, count in by_status.items():
        facts.append(f"{status}の案件が{count}件")
    with_due = [r for r in records if r.get("納期")]
    if with_due:
        nearest = min(with_due, key=lambda r: r["納期"])
        facts.append(f"最も近い納期は{nearest['納期']}（{nearest.get('案件名', '不明')}）")
    return facts


def _customer_master_facts(records: list[dict[str, Any]]) -> list[str]:
    if not records:
        return []
    facts = []
    for r in records:
        name = r.get("顧客名")
        alias = r.get("別名")
        if name:
            facts.append(f"正式名称は{name}" + (f"（別名: {alias}）" if alias else ""))
    if len(records) > 1:
        facts.append(f"該当する顧客は{len(records)}件")
    return facts


def _cancelled_sales_facts(records: list[dict[str, Any]]) -> list[str]:
    if not records:
        return []
    facts = [f"キャンセル・集計対象外の売上が{len(records)}件"]
    total = sum(r.get("金額") or 0 for r in records)
    if total:
        facts.append(f"除外対象の金額合計は{_fmt_amount(total)}")
    return facts


def _task_history_facts(records: list[dict[str, Any]]) -> list[str]:
    if not records:
        return []
    by_state = Counter(r.get("状態") or "不明" for r in records)
    return [f"{state}のタスクが{count}件" for state, count in by_state.items()]


def _project_notes_facts(records: list[dict[str, Any]]) -> list[str]:
    if not records:
        return []
    facts = []
    actions = [r.get("次アクション") for r in records if r.get("次アクション")]
    if actions:
        facts.append(f"次アクション: {actions[0]}")
    owners = sorted({r.get("担当") for r in records if r.get("担当")})
    if owners:
        facts.append(f"担当: {'、'.join(owners)}")
    return facts


def _gmail_facts(records: list[dict[str, Any]]) -> list[str]:
    if not records:
        return []
    facts = [f"メール{len(records)}件を検出"]
    latest = records[0]
    if latest.get("subject"):
        facts.append(f"件名:「{latest['subject']}」")
    if any("納期" in ((r.get("subject") or "") + (r.get("snippet") or "")) for r in records):
        facts.append("納期に関する問い合わせあり")
    return facts


def _slack_facts(records: list[dict[str, Any]]) -> list[str]:
    if not records:
        return []
    facts = [f"投稿{len(records)}件を検出"]
    latest = records[0]
    if latest.get("text"):
        facts.append(f"直近の投稿:「{latest['text']}」")
    return facts


def _ongoing_samples_facts(records: list[dict[str, Any]]) -> list[str]:
    if not records:
        return ["対応中のサンプル依頼はありません"]
    facts = [f"対応中のサンプル依頼は合計{len(records)}件"]
    by_supplier = Counter(r.get("supplier_name") or "不明" for r in records)
    breakdown = "、".join(f"{supplier}: {count}件" for supplier, count in by_supplier.most_common(5))
    facts.append(f"仕入先別内訳: {breakdown}")
    return facts


_INTERPRETERS: dict[tuple[str, str], Callable[[list[dict[str, Any]]], list[str]]] = {
    ("logsys", "sales_lines"): _sales_lines_facts,
    ("logsys", "purchase_lines"): _purchase_lines_facts,
    ("logsys", "project_classification"): _project_classification_facts,
    ("logsys", "product_master"): _product_master_facts,
    ("logsys", "projects"): _projects_facts,
    ("logsys", "customer_master"): _customer_master_facts,
    ("logsys", "cancelled_sales"): _cancelled_sales_facts,
    ("project_sheet", "task_history"): _task_history_facts,
    ("project_sheet", "project_notes"): _project_notes_facts,
    ("gmail", "recent_messages"): _gmail_facts,
    ("slack", "recent_messages"): _slack_facts,
    ("production", "ongoing_samples_by_staff"): _ongoing_samples_facts,
}


def _facts_for(group: dict[str, Any], records: list[dict[str, Any]]) -> list[str]:
    if group.get("status") != "ok":
        return [group.get("note") or group.get("summary") or "データを取得できませんでした"]
    handler = _INTERPRETERS.get((group.get("provider"), group.get("dataset")))
    facts = handler(records) if handler else []
    return facts or ["特筆すべき事実はありません"]


_DISPLAY_LIMIT = 5


def interpret_evidence(integrated_evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Integrated Evidence各グループに facts（事実のみ）を付与して返す。

    factsは必ず取得データ全件（group["records"]）から生成する。
    表示用のdisplay_recordsは最大 _DISPLAY_LIMIT 件のサンプルであり、
    factsの生成には一切使用しない（サンプルのみを見て誤った事実を導かないため）。
    Decisionはこの facts のみを参照し、records（元データ）へは直接依存しない。
    """
    interpreted = []
    for group in integrated_evidence:
        records = group.get("records", [])
        facts = _facts_for(group, records)
        display_records = records[:_DISPLAY_LIMIT]
        sample_note = (
            f"詳細表示は一部サンプルです（全{len(records)}件中{len(display_records)}件を表示）"
            if len(records) > len(display_records)
            else None
        )
        interpreted.append({
            "priority": group.get("priority"),
            "provider": group.get("provider"),
            "dataset": group.get("dataset"),
            "items": group.get("items", []),
            "status": group.get("status"),
            "facts": facts,
            "record_count": len(records),
            "display_records": display_records,
            "sample_note": sample_note,
            "summary": group.get("summary"),
            "duplicate_removed": group.get("duplicate_removed", 0),
            "note": group.get("note"),
            "sources": group.get("sources", []),
            "integrated_at": group.get("integrated_at"),
        })
    return interpreted