"""OAuthリフレッシュトークンを保存前に暗号化するためのヘルパー
(docs/architecture.md 14.27 - Gmail/Slack連携)。

リフレッシュトークンは、その人の実際のGmail/Slackアカウントへの
長期的なアクセス権そのものなので、平文でDBに置かない。
TOKEN_ENCRYPTION_KEYは全環境（ローカルの.env・Render）で必ず設定する
urlsafe-base64のFernetキー（44文字）。一度決めたら気軽にローテー
ションしない — 変更すると既存の暗号化済みトークンが全て復号不能に
なり、全ユーザーが連携をやり直す必要が生じる。

生成方法:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
from __future__ import annotations

import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken


@lru_cache
def _fernet() -> Fernet:
    key = os.environ.get("TOKEN_ENCRYPTION_KEY", "")
    if not key:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY is not configured. Generate one with "
            '`python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"` and set it as an '
            "environment variable."
        )
    return Fernet(key.encode())


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str | None:
    """復号に失敗した場合（キー変更・データ破損等）は例外を投げずNoneを
    返す — 呼び出し側が「再連携が必要」として安全に扱えるようにするため。
    """
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, ValueError):
        return None
