"""Authentication/authorization core (docs/architecture.md 14.22).

Google Sign-In verifies *who* someone is (a real, verified Gmail
address). Whether that person is allowed to use this app at all, and
whether they're allowed to approve things, are two separate questions
answered here — deliberately kept out of `auth_router.py` so the
verification/authorization logic has its own unit-testable home,
independent of the HTTP layer.

Two-tier model, per Noritsugu's explicit scope decision: "一般" (member)
and "管理者" (admin) — not the full Blueprint Chapter 11 approval-level
ladder (Team Lead / Manager+Peer / Director+2Peers), and deliberately no
per-project access restriction (item 3 of the original ask — explicitly
declined).
"""
from __future__ import annotations

import os
from typing import Any

from services.supabase_client import get_connection


def is_valid_staff_email(email: str) -> bool:
    """指定したメールアドレスが、社員マスタ（staffテーブル）に実在するか
    確認する。社外の人物を弾くための唯一の関門。

    staffテーブルの実際の列名は、元のGoogleスプレッドシート（コード)
    の見出しをそのまま使っており、この開発環境からは正確な列名が分から
    ない（code_masterで遭遇したのと同じ制約）。列名を決め打ちして誤る
    リスクを避けるため、全列を横断的に検索し、いずれかの値がメール
    アドレスと一致するかで判定する — 列名がどうであれ安全に動作する。
    """
    if not email:
        return False
    email_lower = email.strip().lower()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM staff")
            rows = cur.fetchall()
    except Exception as e:
        print(f"Error querying staff table: {e}")
        return False
    finally:
        conn.close()

    for row in rows:
        for value in row:
            if isinstance(value, str) and value.strip().lower() == email_lower:
                return True
    return False


def get_staff_name_by_email(email: str) -> str | None:
    """ログイン中のメールアドレスから、staffテーブルの社員氏名を特定する。

    purchase_orders等の「営業担当者名」列は氏名の文字列でしか案件を
    見分けられないため、この関数がその橋渡し役になる。一致する社員が
    見つからない場合はNoneを返す — 呼び出し側は「本人の案件だけに絞る」
    処理をスキップする（表記ゆれのある名前を推測で補って絞り込むと、
    誤って他人の案件を混ぜる/本人の案件を漏らすことになるため、
    一致しない場合は絞り込み自体を諦めるのが安全側の判断）。
    """
    if not email:
        return None
    email_lower = email.strip().lower()

    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT "社員氏名" FROM staff WHERE lower("メールアドレス") = %s LIMIT 1',
                    (email_lower,),
                )
                row = cur.fetchone()
        finally:
            conn.close()
    except Exception as e:
        print(f"Error looking up staff name by email: {e}")
        return None

    if not row or not row[0]:
        return None
    return str(row[0]).strip()


def _admin_emails() -> set[str]:
    raw = os.environ.get("ADMIN_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def get_role_for_email(email: str) -> str:
    """"admin" または "member" を返す。呼び出し側は、これより先に
    is_valid_staff_email() で社員であることを確認しておくこと（社外の
    人物がADMIN_EMAILSに紛れ込んでいてもここでは弾かない設計のため）。
    """
    return "admin" if email.strip().lower() in _admin_emails() else "member"


def verify_google_id_token(credential: str) -> dict[str, Any] | None:
    """Google Identity Servicesが返したIDトークン（JWT）を検証し、
    検証済みのペイロード（email, email_verified, name等）を返す。
    署名・発行者・有効期限・audience（このアプリ向けに発行されたものか）
    が全て正しい場合のみ値を返す。改ざん・なりすましは全て弾かれる
    （Googleが提供する検証ライブラリに委ねる — 自前で検証ロジックを
    書かない）。
    """
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    if not client_id:
        print("GOOGLE_OAUTH_CLIENT_ID is not configured.")
        return None
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token

        payload = id_token.verify_oauth2_token(credential, google_requests.Request(), client_id)
    except Exception as e:
        print(f"Google ID token verification failed: {e}")
        return None

    if not payload.get("email_verified"):
        return None
    return payload


def authenticate(credential: str) -> dict[str, Any] | None:
    """ログインの一連の流れ: IDトークン検証 → 社員確認 → 権限判定。
    どこかで失敗すれば None を返す（呼び出し側は401を返す想定）。
    """
    payload = verify_google_id_token(credential)
    if payload is None:
        return None

    email = payload.get("email", "")
    if not is_valid_staff_email(email):
        return None

    return {
        "email": email,
        "name": payload.get("name", email),
        "role": get_role_for_email(email),
    }
