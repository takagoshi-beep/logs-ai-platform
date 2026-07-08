"""案件に関連しそうなGmail/Slackメッセージを、実データのキーだけを
使って検索する (docs/architecture.md 14.29)。

判定に使うキー（元データ調査の結果、精度が高い順）:
  1. PO番号（purchase_orders.PO_No） — 完全一致で検索すれば誤検出がほぼ無い
  2. 顧客担当者のメールアドレス（customer_contacts.メールアドレス、
     purchase_orders.顧客ID で突合） — Gmailのfrom:/to:で高精度に絞れる

仕入先名・商品コード等は第2段階として今後追加を検討する候補
（顧客担当者のようなメールアドレスの元データが仕入先側には存在しない
ため、今回は含めていない）。

検索はあくまで「ログイン中の本人が既にGmail/Slack連携済みの場合」に
限られる。未連携の場合はgmail_service/slack_service自身が返す
'unavailable'をそのまま呼び出し元に伝える（架空の関連メッセージを
作らない）。
"""
from __future__ import annotations

from typing import Any

from services.supabase_client import get_connection


def get_customer_contact_emails(customer_id: str) -> list[str]:
    """指定した顧客IDに紐づく、顧客担当者の実在するメールアドレス一覧を返す。"""
    if not customer_id or customer_id == "unknown":
        return []

    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT DISTINCT "メールアドレス" FROM customer_contacts '
                    'WHERE "顧客ID" = %s AND "メールアドレス" IS NOT NULL AND "メールアドレス" != \'\'',
                    (customer_id,),
                )
                rows = cur.fetchall()
        finally:
            conn.close()
    except Exception as e:
        print(f"Error looking up customer contact emails: {e}")
        return []

    return [row[0] for row in rows if row[0]]


def _build_gmail_query(po_number: str, contact_emails: list[str]) -> str:
    parts = [f'"{po_number}"'] if po_number else []
    for email in contact_emails:
        parts.append(f"from:{email}")
        parts.append(f"to:{email}")
    return " OR ".join(parts)


def _build_slack_query(po_number: str, supplier_name: str) -> str:
    parts = []
    if po_number:
        parts.append(f'"{po_number}"')
    if supplier_name:
        parts.append(f'"{supplier_name}"')
    return " OR ".join(parts)


def get_related_communications(
    user_email: str | None,
    po_number: str,
    customer_id: str,
    supplier_name: str,
    max_results: int = 5,
) -> dict[str, Any]:
    """ログイン中の本人のGmail/Slackを、この案件に関連しそうなキーワード
    （PO番号・顧客担当者メールアドレス・仕入先名）で検索する。

    Gmail/Slackどちらも未連携の場合や、user_emailが無い場合は、それぞれ
    'unavailable'をそのまま返す（呼び出し側はこれを見て「連携してくだ
    さい」と案内できる）。
    """
    if not user_email:
        unavailable = {"status": "unavailable", "summary": "ログインユーザーが特定できません。", "records": []}
        return {"gmail": unavailable, "slack": unavailable}

    contact_emails = get_customer_contact_emails(customer_id)

    gmail_query = _build_gmail_query(po_number, contact_emails)
    slack_query = _build_slack_query(po_number, supplier_name)

    try:
        from services import gmail_service
        gmail_result = (
            gmail_service.search_messages(user_email, gmail_query, max_results)
            if gmail_query
            else {"status": "unavailable", "summary": "検索に使えるキーがありませんでした。", "records": []}
        )
    except Exception as e:
        gmail_result = {"status": "error", "summary": f"Gmail検索中にエラーが発生しました: {e}", "records": []}

    try:
        from services import slack_service
        slack_result = (
            slack_service.search_messages(user_email, slack_query, max_results)
            if slack_query
            else {"status": "unavailable", "summary": "検索に使えるキーがありませんでした。", "records": []}
        )
    except Exception as e:
        slack_result = {"status": "error", "summary": f"Slack検索中にエラーが発生しました: {e}", "records": []}

    return {"gmail": gmail_result, "slack": slack_result}
