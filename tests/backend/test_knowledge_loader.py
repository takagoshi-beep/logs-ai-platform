"""Tests for `backend/services/knowledge_loader.py`'s `load_section()`
(docs/architecture.md 14.62).

Context: Noritsugu pointed out that get_purchase_lines' tool description
(backend/services/tool_registry.py) hardcoded the import-cost-ratio
definition directly in Python, duplicating the same concept that already
lives in knowledge/semantic/purchase.md. `load_section()` lets tool
descriptions pull the authoritative text from a knowledge/ markdown file
at import time instead of re-typing it, so knowledge/ becomes the single
source of truth ("ナレッジがマスタとなってそこから情報が生成される").
"""
from __future__ import annotations

from pathlib import Path

from services import knowledge_loader


def _write_knowledge_file(tmp_path: Path, relative_path: str, content: str) -> None:
    full_path = tmp_path / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")


def test_load_section_extracts_body_between_matching_heading_and_next_same_level(monkeypatch, tmp_path):
    monkeypatch.setattr(knowledge_loader, "KNOWLEDGE_DIR", tmp_path)
    _write_knowledge_file(
        tmp_path, "semantic/purchase.md",
        "# 仕入\n\n## 定義\n\n仕入の定義本文。\n\n## 輸入経費率\n\nここが抜き出したい本文。\n複数行にわたる。\n\n## 次のセクション\n\nここは含まれない。\n",
    )

    section = knowledge_loader.load_section("semantic/purchase.md", "## 輸入経費率")

    assert section == "ここが抜き出したい本文。\n複数行にわたる。"


def test_load_section_does_not_stop_at_a_deeper_sub_heading(monkeypatch, tmp_path):
    """"## 輸入経費率"の中に"### 定義"のような下位見出しがあっても、
    そこで切れずに次の"##"（同レベル以上）まで拾う。"""
    monkeypatch.setattr(knowledge_loader, "KNOWLEDGE_DIR", tmp_path)
    _write_knowledge_file(
        tmp_path, "semantic/purchase.md",
        "# 仕入\n\n## 輸入経費率\n\n概要文。\n\n### 定義\n\n1.xxの比率。\n\n### 参照データ\n\n経費率列。\n\n## 次のセクション\n\n含まれない。\n",
    )

    section = knowledge_loader.load_section("semantic/purchase.md", "## 輸入経費率")

    assert "### 定義" in section
    assert "1.xxの比率。" in section
    assert "### 参照データ" in section
    assert "次のセクション" not in section


def test_load_section_returns_empty_string_when_heading_not_found(monkeypatch, tmp_path):
    monkeypatch.setattr(knowledge_loader, "KNOWLEDGE_DIR", tmp_path)
    _write_knowledge_file(tmp_path, "semantic/purchase.md", "# 仕入\n\n## 別の見出し\n\n本文。\n")

    section = knowledge_loader.load_section("semantic/purchase.md", "## 存在しない見出し")

    assert section == ""


def test_load_section_returns_empty_string_when_file_does_not_exist(monkeypatch, tmp_path):
    monkeypatch.setattr(knowledge_loader, "KNOWLEDGE_DIR", tmp_path)

    section = knowledge_loader.load_section("semantic/does_not_exist.md", "## 何か")

    assert section == ""


def test_load_section_extracts_to_end_of_file_when_it_is_the_last_section(monkeypatch, tmp_path):
    monkeypatch.setattr(knowledge_loader, "KNOWLEDGE_DIR", tmp_path)
    _write_knowledge_file(
        tmp_path, "semantic/purchase.md",
        "# 仕入\n\n## 輸入経費率\n\n最後のセクションの本文。\n",
    )

    section = knowledge_loader.load_section("semantic/purchase.md", "## 輸入経費率")

    assert section == "最後のセクションの本文。"
