from __future__ import annotations

import re
from typing import Any

from knowledge.brands import get_brand_info
from knowledge.company import get_company_info
from knowledge.glossary import get_glossary_terms, search_knowledge


def _contains_any_token(haystack: str, tokens: list[str]) -> bool:
    lowered = haystack.lower()
    return any(token and token in lowered for token in tokens)


class KnowledgeContextProvider:
    def collect(self, message: str, user_id: str, **kwargs: Any) -> dict[str, Any]:
        _ = user_id
        _ = kwargs

        text = (message or "").strip()
        tokens = [token.lower() for token in re.findall(r"[a-zA-Z0-9_]+", text) if len(token) >= 2]
        if text:
            tokens.append(text.lower())
        tokens = list(dict.fromkeys(tokens))

        glossary = search_knowledge(text)
        if not glossary:
            token_matches = []
            for token in tokens:
                token_matches.extend(search_knowledge(token))
            unique: dict[str, dict[str, Any]] = {}
            for item in token_matches:
                key = str(item.get("term") or item.get("name") or "")
                if key and key not in unique:
                    unique[key] = item
            glossary = list(unique.values())

        company_candidates = []
        for item in get_company_info():
            haystack = " ".join(
                [
                    str(item.get("name", "")),
                    str(item.get("description", "")),
                    " ".join(item.get("aliases", []) or []),
                ]
            )
            if _contains_any_token(haystack, tokens):
                company_candidates.append(item)

        brand_candidates = []
        for item in get_brand_info():
            haystack = " ".join(
                [
                    str(item.get("name", "")),
                    str(item.get("description", "")),
                    " ".join(item.get("aliases", []) or []),
                ]
            )
            if _contains_any_token(haystack, tokens):
                brand_candidates.append(item)

        if not text:
            glossary = get_glossary_terms()[:5]
            company_candidates = get_company_info()[:3]
            brand_candidates = get_brand_info()[:3]

        return {
            "query": text,
            "glossary_candidates": glossary[:10],
            "company_candidates": company_candidates[:10],
            "brand_candidates": brand_candidates[:10],
        }
