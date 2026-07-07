"""Authentication endpoints and FastAPI dependencies (docs/architecture.md
14.22).

`require_login`/`require_admin` are the actual enforcement points — every
other router in this app takes one of these as a dependency. The session
itself is a Starlette `SessionMiddleware`-signed cookie with no `max_age`
set (see `main.py`), which browsers delete when closed, per Noritsugu's
explicit choice ("ブラウザを閉じたらログアウトにしたい").
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from services.auth_service import authenticate

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    credential: str  # Google Identity ServicesのIDトークン(JWT)


@router.post("/login")
def login(req: LoginRequest, request: Request) -> dict:
    user = authenticate(req.credential)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="ログインできませんでした。社員として登録されたGoogleアカウントでログインしてください。",
        )
    request.session["user"] = user
    return {"success": True, "user": user}


@router.post("/logout")
def logout(request: Request) -> dict:
    request.session.clear()
    return {"success": True}


@router.get("/me")
def me(request: Request) -> dict:
    return {"user": request.session.get("user")}


def require_login(request: Request) -> dict:
    """ログイン済み（社員として確認済み）であることを要求する。
    未ログインなら401を返す — これがアプリ全体のログインゲート。
    """
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="ログインが必要です。")
    return user


def require_admin(request: Request) -> dict:
    """管理者であることを要求する（require_loginの上位互換）。
    承認系のエンドポイント（Governance decide、Learning review）専用。
    """
    user = require_login(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="この操作には管理者権限が必要です。")
    return user
