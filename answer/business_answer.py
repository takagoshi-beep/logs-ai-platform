from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from business.formatter import format_business_result
from ingestion.google_drive_importer import get_storage_catalog


@dataclass(frozen=True)
class AnswerResponse:
    success: bool
    answer: str
    source: str
    source_information: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "answer": self.answer,
            "answer_source": self.source,
            "source_information": self.source_information,
        }


def _build_source_information(results: list[dict[str, Any]], db_path: Path | None = None) -> str:
    catalog = get_storage_catalog(db_path) if db_path is not None else []
    catalog_by_table = {str(item.get("table_name") or ""): item for item in catalog}

    source_blocks: list[str] = []
    seen_sources: set[tuple[str, str]] = set()
    for item in results:
        payload = item.get("result") if isinstance(item.get("result"), dict) else {}
        table_name = str(payload.get("table_name") or item.get("table") or "").strip()
        if not table_name:
            continue
        source = catalog_by_table.get(table_name)
        source_file = str(source.get("source_file") or table_name) if source else table_name
        sheet_name = str(source.get("sheet_name") or table_name) if source else table_name
        row_count = int(source.get("row_count") or payload.get("row_count") or 0) if source else int(payload.get("row_count") or 0)
        key = (source_file, sheet_name)
        if key in seen_sources:
            continue
        seen_sources.add(key)
        source_blocks.append(
            "Source Information\n"
            f"- {source_file}\n"
            f"- Sheet: {sheet_name}\n"
            f"- Rows: {row_count}"
        )

    return "\n\n".join(source_blocks)


def build_business_answer(results: list[dict[str, Any]], db_path: Path | None = None) -> AnswerResponse | None:
    business_items = [item for item in results if item.get("type") == "business" and item.get("status") == "completed"]
    if not business_items:
        return None

    parts = []
    for item in business_items:
        payload = item.get("result")
        if not isinstance(payload, dict):
            continue
        tool_name = str(
            payload.get("_business_tool")
            or item.get("business_tool")
            or item.get("tool")
            or "business"
        )
        parts.append(format_business_result(tool_name, payload))

    if not parts:
        return None
    source_information = _build_source_information(results, db_path=db_path)
    answer = "\n\n".join(parts)
    if source_information:
        answer = f"{source_information}\n\n{answer}"
    return AnswerResponse(success=True, answer=answer, source="business", source_information=source_information)
