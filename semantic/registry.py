from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT_DIR / "config"


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fp:
        payload = yaml.safe_load(fp) or {}
    if not isinstance(payload, dict):
        return {}
    return dict(payload)


def _normalize_alias(value: str) -> str:
    return str(value or "").strip().lower()


@dataclass(frozen=True)
class SemanticTermMatch:
    canonical: str
    label: str | None
    matched_term: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SemanticRegistry:
    business_dictionary: dict[str, Any]
    metric_registry: dict[str, Any]
    source_paths: dict[str, str]

    @classmethod
    def load(cls, base_dir: Path | None = None) -> "SemanticRegistry":
        config_dir = base_dir or CONFIG_DIR
        business_dictionary = _load_yaml_mapping(config_dir / "business_dictionary.yaml")
        metric_registry = _load_yaml_mapping(config_dir / "metric_registry.yaml")
        return cls(
            business_dictionary=business_dictionary,
            metric_registry=metric_registry,
            source_paths={
                "business_dictionary": str(config_dir / "business_dictionary.yaml"),
                "metric_registry": str(config_dir / "metric_registry.yaml"),
            },
        )

    def _section_entries(self, section: str) -> dict[str, Any]:
        raw_section = self.business_dictionary.get(section, {})
        if isinstance(raw_section, dict):
            return raw_section
        return {}

    def _build_alias_index(self, section: str) -> list[tuple[str, SemanticTermMatch]]:
        entries = self._section_entries(section)
        indexed: list[tuple[str, SemanticTermMatch]] = []
        for key, payload in entries.items():
            if isinstance(payload, dict):
                canonical = str(payload.get("canonical") or key)
                label = payload.get("label")
                aliases = [key, canonical]
                aliases.extend(str(item) for item in payload.get("synonyms", []) if item)
            else:
                canonical = str(payload or key)
                label = None
                aliases = [key, canonical]
            seen: set[str] = set()
            for alias in aliases:
                normalized_alias = _normalize_alias(alias)
                if not normalized_alias or normalized_alias in seen:
                    continue
                seen.add(normalized_alias)
                indexed.append(
                    (
                        normalized_alias,
                        SemanticTermMatch(
                            canonical=canonical,
                            label=str(label) if label else None,
                            matched_term=str(alias),
                            metadata=dict(payload) if isinstance(payload, dict) else {},
                        ),
                    )
                )
        indexed.sort(key=lambda item: len(item[0]), reverse=True)
        return indexed

    def match_section(self, section: str, message: str) -> SemanticTermMatch | None:
        raw_text = (message or "").lower()
        normalized_text = _normalize_alias(message)
        best_match: SemanticTermMatch | None = None
        best_alias_length = 0

        for alias, match in self._build_alias_index(section):
            if not alias:
                continue
            if alias in raw_text or alias in normalized_text:
                if len(alias) >= best_alias_length:
                    best_match = match
                    best_alias_length = len(alias)

        if best_match is not None:
            return best_match

        return None

    def metric_match(self, message: str) -> SemanticTermMatch | None:
        registry_entries = self.metric_registry if isinstance(self.metric_registry, dict) else {}
        raw_text = (message or "").lower()
        normalized_text = _normalize_alias(message)
        best_match: SemanticTermMatch | None = None
        best_alias_length = 0
        for key, payload in registry_entries.items():
            if not isinstance(payload, dict):
                continue
            canonical = str(key)
            label = payload.get("label")
            aliases = [key, canonical]
            aliases.extend(str(item) for item in payload.get("aliases", []) if item)
            for alias in aliases:
                normalized_alias = _normalize_alias(alias)
                if not normalized_alias:
                    continue
                if (normalized_alias in raw_text or normalized_alias in normalized_text) and len(normalized_alias) >= best_alias_length:
                    best_match = SemanticTermMatch(
                        canonical=canonical,
                        label=str(label) if label else None,
                        matched_term=str(alias),
                        metadata=dict(payload),
                    )
                    best_alias_length = len(normalized_alias)
        return best_match

    def metric_metadata(self, canonical: str) -> dict[str, Any]:
        payload = self.metric_registry.get(canonical, {})
        if isinstance(payload, dict):
            return dict(payload)
        return {}

    def section_metadata(self, section: str, canonical: str) -> dict[str, Any]:
        entries = self._section_entries(section)
        for key, payload in entries.items():
            if not isinstance(payload, dict):
                continue
            if str(payload.get("canonical") or key) == canonical:
                return dict(payload)
        return {}


@lru_cache(maxsize=1)
def get_default_semantic_registry() -> SemanticRegistry:
    return SemanticRegistry.load()