from __future__ import annotations

from authorization.layer import check_authorization


def test_authorization_layer_allows_by_default() -> None:
    decision = check_authorization("user-1", "business.execute_tool", {"tool_name": "business.sales_top"})

    payload = decision.to_dict()
    assert payload["allowed"] is True
    assert payload["policy"] == "allow-all"
    assert payload["action"] == "business.execute_tool"