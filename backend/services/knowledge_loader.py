from __future__ import annotations

import re
from pathlib import Path
from typing import Any

KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "knowledge"

_HEADING = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.split("\n")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    meta: dict[str, Any] = {}
    for line in lines[1:end]:
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            meta[key.strip()] = [v.strip() for v in value[1:-1].split(",") if v.strip()]
        else:
            meta[key.strip()] = value
    return meta, "\n".join(lines[end + 1:]).lstrip("\n")


def _first_heading(body: str) -> str | None:
    match = _HEADING.search(body)
    return match.group(1).strip() if match else None


def load_documents() -> list[dict[str, Any]]:
    """Phase A: knowledge/**/*.md を読み込み、カテゴリ・タイトル・タグ・内容を返す。"""
    docs: list[dict[str, Any]] = []
    for path in sorted(KNOWLEDGE_DIR.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)
        rel = path.relative_to(KNOWLEDGE_DIR)
        category = meta.get("category") or (rel.parts[0] if len(rel.parts) > 1 else "uncategorized")
        title = meta.get("title") or _first_heading(body) or path.stem
        tags = meta.get("tags") if isinstance(meta.get("tags"), list) else []
        docs.append(
            {
                "path": rel.as_posix(),
                "category": category,
                "title": title,
                "tags": tags,
                "content": body,
            }
        )
    return docs


def load_section(relative_path: str, heading: str) -> str:
    """指定したknowledgeファイル（KNOWLEDGE_DIRからの相対パス）から、
    `heading`（例:"## 輸入経費率"）に一致する見出しのセクション本文
    だけを抜き出して返す（2026-07-10、14.62。Noritsuguの指定: 用語・
    業務ルールの定義をknowledge/に一本化し、tool_registry.pyのツール
    説明文はそこから動的に読み込む、二重管理を避ける仕組みのため）。

    見出しの直後から、同じ見出しレベル以上の次の見出しの直前までを
    セクション本文として返す。見出しが見つからない場合は空文字列を
    返す（呼び出し側で見つからなかった場合の扱いを決められるように、
    例外は投げない）。
    """
    path = KNOWLEDGE_DIR / relative_path
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    _, body = _parse_frontmatter(text)

    level = len(heading) - len(heading.lstrip("#"))
    heading_text = heading.lstrip("#").strip()
    heading_pattern = re.compile(
        rf"^{'#' * level}\s+{re.escape(heading_text)}\s*$", re.MULTILINE
    )
    match = heading_pattern.search(body)
    if not match:
        return ""

    start = match.end()
    next_heading_pattern = re.compile(rf"^#{{1,{level}}}\s", re.MULTILINE)
    next_match = next_heading_pattern.search(body, start)
    end = next_match.start() if next_match else len(body)
    return body[start:end].strip()
