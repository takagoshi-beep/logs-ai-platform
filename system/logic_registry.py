from __future__ import annotations

from typing import Any

from system.definitions import LOGIC_DEFINITIONS


def get_logic_registry() -> list[dict[str, Any]]:
    return [dict(logic) for logic in LOGIC_DEFINITIONS]


def get_logic_by_name(logic_name: str) -> dict[str, Any] | None:
    for logic in LOGIC_DEFINITIONS:
        if logic["name"] == logic_name:
            return dict(logic)
    return None


def get_system_map() -> dict[str, Any]:
    domains = []
    seen = set()
    for logic in LOGIC_DEFINITIONS:
        domain_name = logic["domain"]
        if domain_name not in seen:
            seen.add(domain_name)
            domains.append(
                {
                    "name": domain_name,
                    "logics": [dict(item) for item in LOGIC_DEFINITIONS if item["domain"] == domain_name],
                }
            )
    return {"domains": domains}
