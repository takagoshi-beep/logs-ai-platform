"""社内利用状況（誰が・いつ・どの機能を使ったか、相談で何を聞いたか）の
記録・集計 (2026-07-16、14.116、Noritsuguの指定)。

Claude API自体の利用量・コストは`usage_tracking.py`が別途扱っている
（あちらは「AIをどれだけ使ったか」、こちらは「社員がこのアプリの
どの機能をどれだけ使ったか」という別の関心事）。

【重要】記録は必ずFastAPIの`BackgroundTasks`経由で呼び出すこと
（router.py側の責務）。レスポンスを返す前に同期的にDB書き込みを
挟むと、その分だけ画面表示が遅くなってしまう（14.90〜14.92で調査した
ように、この社内システムはただでさえRenderのDB接続に100ms前後かかる
場面があるため）。
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from services import record_store

ACCESS_LOG_TABLE = "app_access_log"

# ページ種別のラベル（フロントエンドの表示用、record_page_viewの
# `page`引数と対応させる）。
PAGE_LABELS = {
    "home": "ホーム",
    "products": "商品",
    "workspace": "案件",
    "tasks": "今日のタスク",
    "proposals": "資料作成",
    "chat": "相談",
    "reasoning": "推論エンジン",
}


def record_page_view(user_email: str, user_name: str | None, page: str) -> None:
    """ページ単位での閲覧を1件記録する（個々のAPI呼び出し・絞り込み・
    ページ送り等の細かい操作までは記録しない — 記録が増えすぎて
    見づらくなるため、「どの画面を開いたか」の単位に留める）。"""
    try:
        record_store.append_record(ACCESS_LOG_TABLE, {
            "event_type": "page_view",
            "user_email": user_email,
            "user_name": user_name,
            "page": page,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        print(f"[access_log] Failed to record page view: {e}")


def record_chat_question(user_email: str, user_name: str | None, question_text: str) -> None:
    """相談（chat）で実際に送信された質問文をそのまま記録する。

    社員の質問内容を記録するため、社内での周知・合意のもとで運用する
    こと（Noritsuguの指定で実装、2026-07-16）。
    """
    try:
        record_store.append_record(ACCESS_LOG_TABLE, {
            "event_type": "chat_question",
            "user_email": user_email,
            "user_name": user_name,
            "question_text": question_text,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        print(f"[access_log] Failed to record chat question: {e}")


def get_access_summary(recent_questions_limit: int = 20) -> dict[str, Any]:
    """ユーザーごとのページ別閲覧回数と、直近の相談内容一覧を返す。"""
    records = record_store.read_all_records(ACCESS_LOG_TABLE)

    by_user: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"user_name": None, "page_views": defaultdict(int), "chat_questions": 0}
    )
    recent_questions: list[dict[str, Any]] = []

    for r in records:
        email = r.get("user_email") or "unknown"
        entry = by_user[email]
        if r.get("user_name"):
            entry["user_name"] = r["user_name"]

        if r.get("event_type") == "page_view":
            entry["page_views"][r.get("page", "unknown")] += 1
        elif r.get("event_type") == "chat_question":
            entry["chat_questions"] += 1
            recent_questions.append({
                "user_email": email,
                "user_name": r.get("user_name"),
                "question_text": r.get("question_text"),
                "recorded_at": r.get("recorded_at"),
            })

    recent_questions.sort(key=lambda q: q.get("recorded_at") or "", reverse=True)

    users = [
        {
            "user_email": email,
            "user_name": data["user_name"],
            "page_views": dict(data["page_views"]),
            "total_page_views": sum(data["page_views"].values()),
            "chat_questions": data["chat_questions"],
        }
        for email, data in by_user.items()
    ]
    users.sort(key=lambda u: -(u["total_page_views"] + u["chat_questions"]))

    return {
        "users": users,
        "recent_chat_questions": recent_questions[:recent_questions_limit],
    }
