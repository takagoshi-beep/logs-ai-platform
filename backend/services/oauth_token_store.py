"""個人単位の外部サービス連携（Gmail/Slack等）のトークン保存
(docs/architecture.md 14.27)。

`user_oauth_tokens`テーブル(email, provider)の組で一意に管理する
— 1人のユーザーが複数プロバイダを連携できるようにするため。
リフレッシュトークンは平文では保存せず、token_crypto経由で暗号化する。
"""
from __future__ import annotations

from services.supabase_client import get_connection
from services.token_crypto import decrypt, encrypt


def save_token(email: str, provider: str, refresh_token: str, scope: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_oauth_tokens (email, provider, refresh_token_encrypted, scope, updated_at)
                VALUES (%s, %s, %s, %s, now())
                ON CONFLICT (email, provider)
                DO UPDATE SET refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
                              scope = EXCLUDED.scope,
                              updated_at = now()
                """,
                (email.strip().lower(), provider, encrypt(refresh_token), scope),
            )
        conn.commit()
    finally:
        conn.close()


def get_refresh_token(email: str, provider: str) -> str | None:
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT refresh_token_encrypted FROM user_oauth_tokens WHERE email = %s AND provider = %s",
                    (email.strip().lower(), provider),
                )
                row = cur.fetchone()
        finally:
            conn.close()
    except Exception as e:
        print(f"Error looking up OAuth token ({provider}): {e}")
        return None
    if not row:
        return None
    return decrypt(row[0])


def is_connected(email: str, provider: str) -> bool:
    return get_refresh_token(email, provider) is not None


def delete_token(email: str, provider: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_oauth_tokens WHERE email = %s AND provider = %s",
                (email.strip().lower(), provider),
            )
        conn.commit()
    finally:
        conn.close()
