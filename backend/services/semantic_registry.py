"""Semantic Registry v0.1 — LOGS業務用語とSemantic Catalog(knowledge/semantic/*.md)を対応付ける。

Knowledge Registry（knowledge_registry.py）とは独立したレジストリ。
Reasoningのmeaningは業務用語からこのRegistryを経由してSemantic Catalogを参照し、
DB列名を直接扱わない（質問 → Semantic Catalog → DB構造）。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

SEMANTIC_DIR = Path(__file__).resolve().parents[2] / "knowledge" / "semantic"
_REGISTRY_FILE = SEMANTIC_DIR / "semantic_registry.md"

_ENTRY_HEADING = re.compile(r"^####\s+(SEM-\d+):\s*(.+)$", re.MULTILINE)
_NEXT_HEADING = re.compile(r"^#{1,4}\s", re.MULTILINE)


def _extract_field(section: str, label: str) -> str:
    match = re.search(rf"\*\*{label}:\*\*\s*(.+)", section)
    return match.group(1).strip() if match else ""


def build_registry() -> list[dict[str, Any]]:
    if not _REGISTRY_FILE.exists():
        return []
    content = _REGISTRY_FILE.read_text(encoding="utf-8")
    entries: list[dict[str, Any]] = []
    matches = list(_ENTRY_HEADING.finditer(content))
    for match in matches:
        start = match.end()
        next_heading = _NEXT_HEADING.search(content, start)
        end = next_heading.start() if next_heading else len(content)
        section = content[start:end]
        entries.append(
            {
                "sem_id": match.group(1),
                "name": match.group(2).strip(),
                "used_by": _extract_field(section, "利用箇所"),
                "tables": _extract_field(section, "使用テーブル"),
                "detail_source": _extract_field(section, "詳細"),
                "status": _extract_field(section, "確認状態"),
            }
        )
    return entries


_cache: list[dict[str, Any]] | None = None
_cache_mtime: float | None = None


def get_registry() -> list[dict[str, Any]]:
    global _cache, _cache_mtime
    mtime = _REGISTRY_FILE.stat().st_mtime if _REGISTRY_FILE.exists() else None
    if _cache is None or mtime != _cache_mtime:
        _cache = build_registry()
        _cache_mtime = mtime
    return _cache


def find_semantic(name: str) -> dict[str, Any] | None:
    for entry in get_registry():
        if entry["name"] == name:
            return entry
    return None


def find_semantic_by_id(sem_id: str) -> dict[str, Any] | None:
    for entry in get_registry():
        if entry["sem_id"] == sem_id:
            return entry
    return None
