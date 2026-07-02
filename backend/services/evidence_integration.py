"""Evidence Integration Layer v0.1 — 複数Data Providerの取得結果を統合する。

Execution（Data Provider）の後段に位置し、個別Evidenceを
provider+dataset単位でグルーピングしたうえで、重複排除・時系列整理・
優先度整理を行う。SQLや取得手段には関与しない（Providerだけが知る）。
records は全件を保持したまま返す（表示用サンプリングはInterpretation Layerの責務）。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_DATE_KEYS = ("売上日", "仕入日", "納期", "日付", "date")


def _record_signature(record: dict[str, Any]) -> tuple:
    return tuple(sorted((k, str(v)) for k, v in record.items()))


def _record_date(record: dict[str, Any]) -> str:
    for key in _DATE_KEYS:
        value = record.get(key)
        if value:
            return str(value)
    return ""


def _dedupe_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen: set[tuple] = set()
    unique: list[dict[str, Any]] = []
    duplicate_removed = 0
    for record in records:
        signature = _record_signature(record)
        if signature in seen:
            duplicate_removed += 1
            continue
        seen.add(signature)
        unique.append(record)
    return unique, duplicate_removed


def _sort_time_series(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not any(_record_date(r) for r in records):
        return records
    return sorted(records, key=_record_date)


def integrate_evidence(evidence_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """個別EvidenceをProvider+Dataset単位で統合し、Integrated Evidenceを返す。

    - 重複排除: 同一内容のレコードを除去
    - 時系列整理: 日付系フィールドがあれば昇順に並べ替え
    - 優先度整理: 統合後の並び順はRequired Data優先度（最小値）の昇順
    """
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    order: list[tuple[str, str]] = []

    for evidence in evidence_list:
        key = (evidence.get("provider", ""), evidence.get("dataset", ""))
        if key not in groups:
            groups[key] = {
                "provider": evidence.get("provider"),
                "dataset": evidence.get("dataset"),
                "status": evidence.get("status", "unavailable"),
                "summaries": [],
                "records": [],
                "notes": [],
                "sources": [],
            }
            order.append(key)
        group = groups[key]
        if evidence.get("status") == "ok":
            group["status"] = "ok"
        group["summaries"].append(evidence.get("summary", ""))
        group["records"].extend(evidence.get("records", []))
        if evidence.get("note"):
            group["notes"].append(evidence["note"])
        group["sources"].append({
            "priority": evidence.get("priority"),
            "item": evidence.get("item"),
            "fetched_at": evidence.get("fetched_at"),
        })

    integrated: list[dict[str, Any]] = []
    for key in order:
        group = groups[key]
        unique_records, duplicate_removed = _dedupe_records(group["records"])
        ordered_records = _sort_time_series(unique_records)
        priorities = [s["priority"] for s in group["sources"] if s["priority"] is not None]
        integrated.append({
            "provider": group["provider"],
            "dataset": group["dataset"],
            "priority": min(priorities) if priorities else None,
            "items": [s["item"] for s in group["sources"] if s["item"]],
            "status": group["status"],
            "summary": " / ".join(dict.fromkeys(s for s in group["summaries"] if s)),
            "record_count": len(ordered_records),
            "records": ordered_records,
            "duplicate_removed": duplicate_removed,
            "note": " / ".join(dict.fromkeys(group["notes"])) or None,
            "sources": group["sources"],
            "integrated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })

    integrated.sort(key=lambda e: (e["priority"] is None, e["priority"] or 0))
    return integrated
