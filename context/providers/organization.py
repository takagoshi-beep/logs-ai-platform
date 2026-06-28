from __future__ import annotations

from typing import Any

from knowledge.company import get_company_info


class OrganizationContextProvider:
    def collect(self, message: str, user_id: str, **kwargs: Any) -> dict[str, Any]:
        _ = user_id
        _ = kwargs

        text = (message or "").lower()
        companies = get_company_info()

        focus_candidates = [item for item in companies if item.get("name", "").lower() in text]
        if not focus_candidates:
            priority = {"LOGS", "丸太屋", "FOLTEK"}
            focus_candidates = [item for item in companies if item.get("name") in priority]

        return {
            "organizations": companies,
            "focus_organizations": focus_candidates,
        }
