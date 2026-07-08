"""Slack連携 (docs/architecture.md 14.27 Phase 1: 検索のみ)。

Gmail連携（gmail_service.py）と同じ構造・同じ考え方に揃えている:
- 個人単位のOAuth（そのユーザー自身が参加しているDM・チャンネルのみが対象）
- 連携時に、Slack側から返ってきたメールアドレスがログイン中の本人と
  一致するか必ず確認してから保存する
- 未連携・エラー時は正直にその旨を返す（架空のメッセージを作らない）

GmailとSlackで異なる点: SlackのユーザートークンはGoogleのような
refresh_tokenの更新サイクルが基本的に不要（トークンローテーションを
有効にしていないアプリでは長期間有効なトークンがそのまま使える）。
そのためgmail_service.pyの_refresh_access_token相当の処理は無く、
保存したトークンをそのまま使う。
"""
from __future__ import annotations

import os
import urllib.parse
from typing import Any

import requests

from services.oauth_token_store import delete_token, get_refresh_token, is_connected, save_token

PROVIDER = "slack"
USER_SCOPES = "search:read,users:read,users:read.email"
AUTH_ENDPOINT = "https://slack.com/oauth/v2/authorize"
TOKEN_ENDPOINT = "https://slack.com/api/oauth.v2.access"
USERS_INFO_ENDPOINT = "https://slack.com/api/users.info"
SEARCH_ENDPOINT = "https://slack.com/api/search.messages"


def _client_id() -> str:
    return os.environ.get("SLACK_CLIENT_ID", "")


def _client_secret() -> str:
    return os.environ.get("SLACK_CLIENT_SECRET", "")


def _redirect_uri() -> str:
    return os.environ.get("SLACK_OAUTH_REDIRECT_URI", "")


def build_auth_url(state: str) -> str:
    params = {
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri(),
        "user_scope": USER_SCOPES,
        "state": state,
    }
    return f"{AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


def handle_callback(code: str) -> dict[str, Any] | None:
    """認可コードをユーザートークンに交換し、そのSlackアカウントの
    メールアドレスと一緒に返す。失敗時はNone。呼び出し側で、返ってきた
    emailがログイン中の本人と一致するか必ず確認すること。
    """
    try:
        resp = requests.post(
            TOKEN_ENDPOINT,
            data={
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "code": code,
                "redirect_uri": _redirect_uri(),
            },
            timeout=10,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        print(f"Slack token exchange failed: {e}")
        return None

    if not payload.get("ok"):
        print(f"Slack token exchange returned ok=false: {payload.get('error')}")
        return None

    authed_user = payload.get("authed_user", {})
    user_token = authed_user.get("access_token")
    slack_user_id = authed_user.get("id")
    if not user_token or not slack_user_id:
        print("Slack token exchange succeeded but authed_user.access_token was missing.")
        return None

    try:
        info_resp = requests.get(
            USERS_INFO_ENDPOINT,
            headers={"Authorization": f"Bearer {user_token}"},
            params={"user": slack_user_id},
            timeout=10,
        )
        info_resp.raise_for_status()
        info = info_resp.json()
    except Exception as e:
        print(f"Slack users.info fetch failed: {e}")
        return None

    if not info.get("ok"):
        print(f"Slack users.info returned ok=false: {info.get('error')}")
        return None

    granted_email = info.get("user", {}).get("profile", {}).get("email", "")
    if not granted_email:
        print("Slack users.info succeeded but no email was present (users:read.email scope missing?).")
        return None

    return {
        "email": granted_email,
        "access_token": user_token,
        "scope": authed_user.get("scope", USER_SCOPES),
    }


def connect_status(email: str) -> bool:
    return is_connected(email, PROVIDER)


def disconnect(email: str) -> None:
    delete_token(email, PROVIDER)


def save_connection(email: str, access_token: str, scope: str) -> None:
    # Slackのユーザートークンは（トークンローテーション未使用の場合）
    # refresh不要の長期間有効なトークンなので、Gmailのrefresh_tokenと
    # 同じ列にそのまま保存し、使うときも直接使う。
    save_token(email, PROVIDER, access_token, scope)


def _get_access_token(email: str) -> str | None:
    return get_refresh_token(email, PROVIDER)


def search_messages(email: str, query: str, max_results: int = 10) -> dict[str, Any]:
    """ログインユーザー自身が参加しているチャンネル・DMの中からSlack
    メッセージを検索する。Slack検索構文（from:, in:, before:, after: 等）
    が使える。
    """
    access_token = _get_access_token(email)
    if not access_token:
        return {
            "status": "unavailable",
            "summary": "Slack未連携です。設定画面からSlack連携を行ってください。",
            "records": [],
        }

    try:
        resp = requests.get(
            SEARCH_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
            params={"query": query, "count": max(1, min(max_results, 25))},
            timeout=10,
        )
        resp.raise_for_status()
        payload = resp.json()
    except requests.exceptions.HTTPError as e:
        body = e.response.text if e.response is not None else ""
        return {"status": "error", "summary": f"Slack検索中にエラーが発生しました: {e} / {body}", "records": []}
    except Exception as e:
        return {"status": "error", "summary": f"Slack検索中にエラーが発生しました: {e}", "records": []}

    if not payload.get("ok"):
        error = payload.get("error", "unknown_error")
        return {"status": "error", "summary": f"Slack検索でエラーが返されました: {error}", "records": []}

    print(f"[slack debug] query={query!r} total={payload.get('messages', {}).get('total')} raw={payload}")

    matches = payload.get("messages", {}).get("matches", [])
    records = [
        {
            "channel": m.get("channel", {}).get("name", ""),
            "username": m.get("username", ""),
            "timestamp": m.get("ts", ""),
            "text": m.get("text", ""),
            "permalink": m.get("permalink", ""),
        }
        for m in matches
    ]

    return {
        "status": "ok",
        "summary": f"{len(records)}件のメッセージが見つかりました。",
        "records": records,
    }
