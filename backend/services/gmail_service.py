"""Gmail連携 (docs/architecture.md 14.27 Phase 1: 検索・参照のみ)。

Google Sign-In（IDトークンのみ、本人確認専用）とは別物として、Gmail
読み取りのためのAuthorization Code + refresh_token方式のOAuthをここで
扱う。将来のドラフト作成・送信（Phase 2）は、このモジュールに
gmail.compose/gmail.sendスコープを追加コンセントする形で拡張する
想定 — 今は最小権限の原則でgmail.readonlyのみを要求する。

google-api-python-clientのような重いSDKは使わず、既にbackendの
依存に追加済みのrequestsだけでGmail REST APIを直接叩く（他のtoolと
同じ「必要最小限の依存で済ます」方針に合わせている）。
"""
from __future__ import annotations

import base64
import os
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests

from services.oauth_token_store import delete_token, get_refresh_token, is_connected, save_token

PROVIDER = "google_gmail"
SCOPES = "openid email https://www.googleapis.com/auth/gmail.readonly"
AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


def _client_id() -> str:
    return os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")


def _client_secret() -> str:
    return os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")


def _redirect_uri() -> str:
    return os.environ.get("GMAIL_OAUTH_REDIRECT_URI", "")


def build_auth_url(state: str) -> str:
    params = {
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


def handle_callback(code: str) -> dict[str, Any] | None:
    """認可コードをトークンに交換し、そのGoogleアカウントのメール
    アドレスと一緒に返す。失敗時はNone。呼び出し側で、返ってきた
    emailがログイン中の本人と一致するか必ず確認すること
    （他人のGoogleアカウントを誤って連携しないための必須チェック）。
    """
    try:
        resp = requests.post(
            TOKEN_ENDPOINT,
            data={
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": _redirect_uri(),
            },
            timeout=10,
        )
        resp.raise_for_status()
        tokens = resp.json()
    except Exception as e:
        print(f"Gmail token exchange failed: {e}")
        return None

    refresh_token = tokens.get("refresh_token")
    access_token = tokens.get("access_token")
    if not refresh_token or not access_token:
        # prompt=consent + access_type=offlineでも、Googleが過去に発行済み
        # と判断するとrefresh_tokenを省略することがある。その場合は
        # 「Googleアカウントの設定からこのアプリのアクセス権を一度削除
        # してから再連携してください」と案内する必要がある。
        print("Gmail token exchange succeeded but no refresh_token was returned.")
        return None

    try:
        userinfo_resp = requests.get(
            USERINFO_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        userinfo_resp.raise_for_status()
        granted_email = userinfo_resp.json().get("email", "")
    except Exception as e:
        print(f"Gmail userinfo fetch failed: {e}")
        return None

    return {
        "email": granted_email,
        "refresh_token": refresh_token,
        "scope": tokens.get("scope", SCOPES),
    }


def _refresh_access_token(refresh_token: str) -> str | None:
    try:
        resp = requests.post(
            TOKEN_ENDPOINT,
            data={
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except Exception as e:
        print(f"Gmail access token refresh failed: {e}")
        return None


def _get_access_token(email: str) -> str | None:
    refresh_token = get_refresh_token(email, PROVIDER)
    if not refresh_token:
        return None
    return _refresh_access_token(refresh_token)


def connect_status(email: str) -> bool:
    return is_connected(email, PROVIDER)


def disconnect(email: str) -> None:
    delete_token(email, PROVIDER)


def save_connection(email: str, refresh_token: str, scope: str) -> None:
    save_token(email, PROVIDER, refresh_token, scope)


def search_messages(email: str, query: str, max_results: int = 10) -> dict[str, Any]:
    """ログインユーザー自身のGmailをGmail検索構文で検索し、
    件名・差出人・日時・スニペットのみを返す（本文全体はget_messageで）。
    """
    access_token = _get_access_token(email)
    if not access_token:
        return {
            "status": "unavailable",
            "summary": "Gmail未連携です。設定画面からGmail連携を行ってください。",
            "records": [],
        }

    # 2026-07-14（14.90、Noritsuguが実データで発見）: 商品詳細ページの
    # Gmail検索が、以前想定していた1.1〜1.2秒ではなく実際には2.0〜2.6秒
    # かかっていることが判明。14.76でメール1件ごとの個別取得（メタデータ
    # 取得）は並行化済みだが、それでも遅い場合、「一覧取得(list)」と
    # 「メタデータ取得バッチ」のどちらが支配的かをこれまで区別して計測
    # していなかった（親のtimed()ブロックはsearch_messages全体をまとめて
    # 計測するのみ）。原因を推測せず特定するため、2つのフェーズを個別に
    # 計測するよう分割した。
    from services.timing import timed

    try:
        with timed("gmail_service.search_messages.list"):
            list_resp = requests.get(
                f"{GMAIL_API_BASE}/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"q": query, "maxResults": max(1, min(max_results, 25))},
                timeout=10,
            )
            list_resp.raise_for_status()
            message_ids = [m["id"] for m in list_resp.json().get("messages", [])]
    except requests.exceptions.HTTPError as e:
        body = e.response.text if e.response is not None else ""
        return {"status": "error", "summary": f"Gmail検索中にエラーが発生しました: {e} / {body}", "records": []}
    except Exception as e:
        return {"status": "error", "summary": f"Gmail検索中にエラーが発生しました: {e}", "records": []}

    # 2026-07-10（14.76、Noritsuguが実際の[TIMING]ログの商品ごとの差から
    # 発見）: 以前はヒットしたメール1件ごとに個別のGET（メタデータ取得）
    # を直列に実行していた。ヒット件数に比例して所要時間が増える
    # （実例: ヒットが少ない商品は772ms、ヒットが多い商品は3〜4秒）
    # N+1的な作りだった。ThreadPoolExecutorで各メールのメタデータ取得を
    # 並行実行するよう修正し、所要時間を「一番遅い1件分」に近づけた。
    def _fetch_one(mid: str) -> dict[str, Any] | None:
        try:
            msg_resp = requests.get(
                f"{GMAIL_API_BASE}/messages/{mid}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
                timeout=10,
            )
            msg_resp.raise_for_status()
            msg = msg_resp.json()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            return {
                "message_id": mid,
                "subject": headers.get("Subject", "(件名なし)"),
                "from": headers.get("From", ""),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
            }
        except Exception:
            return None

    records = []
    if message_ids:
        with timed(f"gmail_service.search_messages.metadata_batch(n={len(message_ids)})"):
            with ThreadPoolExecutor(max_workers=min(len(message_ids), 10)) as executor:
                for result in executor.map(_fetch_one, message_ids):
                    if result is not None:
                        records.append(result)

    return {
        "status": "ok",
        "summary": f"{len(records)}件のメールが見つかりました。",
        "records": records,
    }


def get_message(email: str, message_id: str) -> dict[str, Any]:
    """search_messagesで見つけたmessage_idを指定して、本文全体を取得する。"""
    access_token = _get_access_token(email)
    if not access_token:
        return {"status": "unavailable", "summary": "Gmail未連携です。", "records": []}

    try:
        resp = requests.get(
            f"{GMAIL_API_BASE}/messages/{message_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"format": "full"},
            timeout=10,
        )
        resp.raise_for_status()
        msg = resp.json()
    except Exception as e:
        return {"status": "error", "summary": f"メール取得中にエラーが発生しました: {e}", "records": []}

    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    body_text = _extract_plain_text(msg.get("payload", {}))

    return {
        "status": "ok",
        "summary": "メール本文を取得しました。",
        "records": [{
            "message_id": message_id,
            "subject": headers.get("Subject", ""),
            "from": headers.get("From", ""),
            "date": headers.get("Date", ""),
            "body": body_text,
        }],
    }


def _extract_plain_text(payload: dict[str, Any]) -> str:
    """Gmail APIのpayload（ネストしたMIMEパーツ）からtext/plain本文を
    再帰的に探して取り出す（base64url decode込み）。"""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        data = payload["body"]["data"]
        padded = data + "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")

    for part in payload.get("parts", []) or []:
        text = _extract_plain_text(part)
        if text:
            return text
    return ""
