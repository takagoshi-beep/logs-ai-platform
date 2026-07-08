import os
import sys
from pathlib import Path

# `capability/` lives at the repository root, but this app is run with
# `backend/` as the working directory (see README: `cd backend && uvicorn
# main:app`). Append the repo root to sys.path (not insert at position 0)
# so top-level packages like `capability` become importable without
# shadowing backend/'s own same-named packages (business, services, etc.).
sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from api.router import router
from api.capability_router import router as capability_router
from api.governance_router import router as governance_router
from api.document_formats_router import router as document_formats_router
from api.learning_router import router as learning_router
from api.integrations_router import router as integrations_router
from api.auth_router import router as auth_router, require_login

app = FastAPI(title="LOGS AI OS Backend V0.1", version="0.1.0")

# 2026-07-08 (Web化準備、docs/architecture.md 14.25): ローカル開発では
# フロントエンド・バックエンドが同じマシン上で動くため cross-site の
# 概念が薄かったが、Renderに別々のサービスとしてデプロイすると、両者は
# 別ドメイン（例: xxx-frontend.onrender.com / xxx-backend.onrender.com）
# になり、正真正銘の cross-site 構成になる。CORSの許可オリジンと、
# セッションCookieのSameSite/Secure属性は、この1つの環境変数
# （FRONTEND_URL）から一貫して決める。
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


def _is_cross_site_https(frontend_url: str) -> bool:
    """FRONTEND_URLがhttps://で始まるか（=Renderデプロイ後のcross-site
    構成か）を判定する。ローカル開発時は常にFalse。"""
    return frontend_url.startswith("https://")


_IS_CROSS_SITE_HTTPS = _is_cross_site_https(FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# max_age を指定しない = セッションCookieとして扱われ、ブラウザを閉じると
# 自動的にログアウトになる（Noritsuguの明示的な要望どおり）。
# SESSION_SECRET_KEY は .env で必ず設定すること — 未設定時のみ開発用の
# 固定値にフォールバックする（本番運用ではこのフォールバックに頼らない）。
#
# same_site/https_only: ローカル開発(http://localhost)ではCookieに
# Secure属性を付けられない（HTTPSでないため）ので same_site="lax" +
# https_only=False。Renderデプロイ後（FRONTEND_URLがhttps://で始まる）は
# フロントエンド・バックエンドが別ドメインになるため、ブラウザに
# cross-site Cookieとして送ってもらうには same_site="none" +
# https_only=True（Secure属性必須）が必要 — この2つはセットでしか
# 意味を持たない設定のため、1つの条件分岐でまとめて決める。
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET_KEY", "dev-only-insecure-secret-change-me"),
    max_age=None,
    same_site="none" if _IS_CROSS_SITE_HTTPS else "lax",
    https_only=_IS_CROSS_SITE_HTTPS,
)

# 14.22: ログイン必須化。/api/auth/* だけは未ログインでも呼べる
# （でなければ誰もログインできなくなる）。それ以外の全ルーターに
# require_login を課す — 「アプリを開くには必ずログインが必要」という
# 明示的な選択（一部機能だけ公開、という中間案は採らないと決めている）。
app.include_router(auth_router)
app.include_router(router, dependencies=[Depends(require_login)])
app.include_router(capability_router, dependencies=[Depends(require_login)])
app.include_router(governance_router, dependencies=[Depends(require_login)])
app.include_router(document_formats_router, dependencies=[Depends(require_login)])
app.include_router(learning_router, dependencies=[Depends(require_login)])
app.include_router(integrations_router, dependencies=[Depends(require_login)])