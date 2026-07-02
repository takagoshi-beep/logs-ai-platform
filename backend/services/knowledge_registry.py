from __future__ import annotations

import re
from typing import Any

from services.knowledge_loader import KNOWLEDGE_DIR, load_documents

_RULE_HEADING = re.compile(r"^###\s+([A-Z][A-Z0-9-]{2,}):\s*(.+)$", re.MULTILINE)
_NEXT_HEADING = re.compile(r"^#{2,3}\s", re.MULTILINE)


def _extract_statement(section: str) -> str:
    marker = re.search(r"\*\*(?:Statement|Gate Statement):\*\*\s*\n?", section)
    rest = section[marker.end():] if marker else section
    for para in re.split(r"\n\s*\n", rest):
        para = para.strip()
        if para and not para.startswith("**") and not para.startswith("```") and not para.startswith("#"):
            return re.sub(r"\s+", " ", para)
    return ""


def _extract_updated(section: str) -> str:
    match = re.search(r"\*\*Status:\*\*.*?(\d{4}-\d{2}-\d{2})", section)
    return match.group(1) if match else ""


def _extract_rules(content: str) -> list[dict[str, Any]]:
    matches = list(_RULE_HEADING.finditer(content))
    rules: list[dict[str, Any]] = []
    for match in matches:
        start = match.end()
        next_heading = _NEXT_HEADING.search(content, start)
        end = next_heading.start() if next_heading else len(content)
        section = content[start:end]
        rules.append(
            {
                "rule_id": match.group(1),
                "title": match.group(2).strip(),
                "statement": _extract_statement(section),
                "updated": _extract_updated(section),
                "verified": "Verified" in section,
            }
        )
    return rules


def _first_paragraph(content: str) -> str:
    for para in re.split(r"\n\s*\n", content):
        para = para.strip()
        if para and not para.startswith("#") and not para.startswith("```"):
            return re.sub(r"\s+", " ", para)[:120]
    return ""


def build_registry() -> list[dict[str, Any]]:
    """Phase B: 全Knowledgeを走査し、ルール単位のRegistry（KR-xxx）を構築する。"""
    entries: list[dict[str, Any]] = []
    counter = 1
    for doc in load_documents():
        rules = _extract_rules(doc["content"])
        if rules:
            for rule in rules:
                entries.append(
                    {
                        "kr_id": f"KR-{counter:03d}",
                        "rule_id": rule["rule_id"],
                        "name": rule["title"],
                        "category": doc["category"],
                        "used_by": "Reasoning Engine / 相談エンジン",
                        "updated": rule["updated"],
                        "priority": "high" if rule["verified"] else "normal",
                        "source": doc["path"],
                        "summary": rule["statement"],
                    }
                )
                counter += 1
        else:
            entries.append(
                {
                    "kr_id": f"KR-{counter:03d}",
                    "rule_id": None,
                    "name": doc["title"],
                    "category": doc["category"],
                    "used_by": "AI全般（参照ドキュメント）",
                    "updated": "",
                    "priority": "normal",
                    "source": doc["path"],
                    "summary": _first_paragraph(doc["content"]),
                }
            )
            counter += 1
    return entries


_cache: list[dict[str, Any]] | None = None
_cache_key: tuple | None = None


def _current_key() -> tuple:
    return tuple(
        (path.as_posix(), path.stat().st_mtime) for path in sorted(KNOWLEDGE_DIR.rglob("*.md"))
    )


def get_registry() -> list[dict[str, Any]]:
    global _cache, _cache_key
    key = _current_key()
    if _cache is None or key != _cache_key:
        _cache = build_registry()
        _cache_key = key
    return _cache


def find_rule(rule_id: str) -> dict[str, Any] | None:
    for entry in get_registry():
        if entry["rule_id"] == rule_id:
            return entry
    return None
