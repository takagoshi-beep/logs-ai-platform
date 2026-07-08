"""Gmail/Slack等、個人単位の外部サービス連携エンドポイント
(docs/architecture.md 14.27)。

連携は必ずログイン中の本人自身のアカウントに対してのみ行う —
Googleから返ってきたメールアドレスがセッションのログインメール
アドレスと一致することを確認してから保存する。他人のGoogle
アカウントを誤って（あるいは意図的に）連携できないようにするための
必須チェック。
"""
from __future__ import annotations

import os
import secrets

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from api.auth_router import require_login
from services import gmail_service, slack_service

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

_STATE_SESSION_KEY = "gmail_oauth_state"
_SLACK_STATE_SESSION_KEY = "slack_oauth_state"


def _frontend_url() -> str:
    return os.environ.get("FRONTEND_URL", "http://localhost:3000")


@router.get("/gmail/connect")
def gmail_connect(request: Request, user: dict = Depends(require_login)) -> RedirectResponse:
    state = secrets.token_urlsafe(24)
    request.session[_STATE_SESSION_KEY] = state
    return RedirectResponse(gmail_service.build_auth_url(state))


@router.get("/gmail/callback")
def gmail_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    user: dict = Depends(require_login),
) -> RedirectResponse:
    expected_state = request.session.pop(_STATE_SESSION_KEY, None)

    if error or not code or not state or state != expected_state:
        return RedirectResponse(f"{_frontend_url()}/settings?gmail=error")

    result = gmail_service.handle_callback(code)
    if result is None:
        return RedirectResponse(f"{_frontend_url()}/settings?gmail=error")

    if result["email"].strip().lower() != user["email"].strip().lower():
        # 別人のGoogleアカウントで許可された（例: 個人用アカウントで
        # ログインし直した等） — ログイン中の本人のものではないため
        # 保存しない。
        return RedirectResponse(f"{_frontend_url()}/settings?gmail=mismatch")

    gmail_service.save_connection(user["email"], result["refresh_token"], result["scope"])
    return RedirectResponse(f"{_frontend_url()}/settings?gmail=connected")


@router.get("/gmail/status")
def gmail_status(user: dict = Depends(require_login)) -> dict:
    return {"connected": gmail_service.connect_status(user["email"])}


@router.delete("/gmail")
def gmail_disconnect(user: dict = Depends(require_login)) -> dict:
    gmail_service.disconnect(user["email"])
    return {"success": True}


@router.get("/slack/connect")
def slack_connect(request: Request, user: dict = Depends(require_login)) -> RedirectResponse:
    state = secrets.token_urlsafe(24)
    request.session[_SLACK_STATE_SESSION_KEY] = state
    return RedirectResponse(slack_service.build_auth_url(state))


@router.get("/slack/callback")
def slack_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    user: dict = Depends(require_login),
) -> RedirectResponse:
    expected_state = request.session.pop(_SLACK_STATE_SESSION_KEY, None)

    if error or not code or not state or state != expected_state:
        return RedirectResponse(f"{_frontend_url()}/settings?slack=error")

    result = slack_service.handle_callback(code)
    if result is None:
        return RedirectResponse(f"{_frontend_url()}/settings?slack=error")

    if result["email"].strip().lower() != user["email"].strip().lower():
        return RedirectResponse(f"{_frontend_url()}/settings?slack=mismatch")

    slack_service.save_connection(user["email"], result["access_token"], result["scope"])
    return RedirectResponse(f"{_frontend_url()}/settings?slack=connected")


@router.get("/slack/status")
def slack_status(user: dict = Depends(require_login)) -> dict:
    return {"connected": slack_service.connect_status(user["email"])}


@router.delete("/slack")
def slack_disconnect(user: dict = Depends(require_login)) -> dict:
    slack_service.disconnect(user["email"])
    return {"success": True}
