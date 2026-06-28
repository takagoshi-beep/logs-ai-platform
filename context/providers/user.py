from __future__ import annotations

from typing import Any


USER_PROFILES = {
    "default": {
        "user_id": "default",
        "display_name": "Default User",
        "role": "operator",
        "locale": "ja-JP",
    },
    "takagoshi": {
        "user_id": "takagoshi",
        "display_name": "Takagoshi",
        "role": "admin",
        "locale": "ja-JP",
    },
}


class UserContextProvider:
    def collect(self, message: str, user_id: str, **kwargs: Any) -> dict[str, Any]:
        _ = message
        _ = kwargs

        key = (user_id or "default").strip().lower() or "default"
        profile = USER_PROFILES.get(key) or {
            "user_id": user_id or "default",
            "display_name": "Unknown User",
            "role": "operator",
            "locale": "ja-JP",
        }
        return dict(profile)
