"""案件に関連しそうなGmail/Slackメッセージを、実データのキーだけを
使って検索する (docs/architecture.md 14.29)。

判定に使うキー（元データ調査の結果、精度が高い順）:
  1. PO番号（purchase_orders.PO_No） — 完全一致で検索すれば誤検出がほぼ無い
  2. 顧客担当者のメールアドレス（customer_contacts.メールアドレス、
     purchase_orders.顧客ID で突合） — Gmailのfrom:/to:で高精度に絞れる

Gmail: 上記2つをOR（どちらか一致すればヒット）では組み合わせない —
「PO番号は一致していないが、その顧客担当者との別件のメールならヒットする」
というノイズが実際に発生したため（2026-07-08、全く別のPO番号のメールが
表示された実例）。代わりに、まずPO番号だけで検索し、0件だった場合に限り
顧客担当者メールにフォールバックする段階的な方式にしている。フォール
バックでヒットした結果は`match_type="customer_contact"`で区別し、
呼び出し側が「PO番号そのものの一致ではない」ことを利用者に伝えられる
ようにする。

Slack: PO番号一致のみを使う（仕入先名でのフォールバックは採用しない）。
PO発行時に必ずPO番号入りの自動通知がSlackへ流れる運用のため、フォール
バックを設ける実益が薄く、Gmailと同種のノイズを持ち込むリスクの方が
大きいと判断した（2026-07-08、Noritsuguの明示的な選択）。

商品コード等は第3段階として今後追加を検討する候補。

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


def _contact_emails_query(contact_emails: list[str]) -> str:
    parts = []
    for email in contact_emails:
        parts.append(f"from:{email}")
        parts.append(f"to:{email}")
    return " OR ".join(parts)


def _search_gmail_related(
    user_email: str, po_number: str, contact_emails: list[str], max_results: int
) -> dict[str, Any]:
    from services import gmail_service

    if po_number:
        po_result = gmail_service.search_messages(user_email, f'"{po_number}"', max_results)
        if po_result.get("status") != "ok":
            # Gmail未連携・APIエラー等 — フォールバックしても意味がないので
            # そのまま呼び出し側に伝える（連携未完了なのに「担当者名で
            # 検索したら見つかりました」という矛盾した表示を避ける）。
            return po_result
        if po_result.get("records"):
            po_result["match_type"] = "po_number"
            return po_result
    else:
        po_result = {"status": "ok", "summary": "PO番号がありません。", "records": []}

    if contact_emails:
        fallback_query = _contact_emails_query(contact_emails)
        fallback_result = gmail_service.search_messages(user_email, fallback_query, max_results)
        if fallback_result.get("status") == "ok" and fallback_result.get("records"):
            fallback_result["match_type"] = "customer_contact"
            fallback_result["summary"] = (
                f"PO番号「{po_number}」に一致するメールは見つかりませんでしたが、"
                f"この顧客の担当者とのメールが{len(fallback_result['records'])}件見つかりました"
                "（同じPOとは限りません）。"
            )
            return fallback_result

    po_result["match_type"] = "po_number"
    return po_result


def _search_slack_related(
    user_email: str, po_number: str, supplier_name: str, max_results: int
) -> dict[str, Any]:
    """SlackはPO番号一致のみで検索する（仕入先名でのフォールバックは
    採用しない）。PO発行時に必ずPO番号入りの自動通知がSlackへ流れる
    運用のため、Gmailの顧客担当者メールのような「仕入先名で見つかった
    が別件だった」というノイズの温床になり得るフォールバックを設ける
    実益が薄いと判断した（2026-07-08、Noritsuguの明示的な選択）。
    supplier_nameは将来また使う可能性を考えて引数には残している。

    引用符を付けない理由（2026-07-08、実機診断で判明）: Slackの検索は
    ハイフンを含む語を引用符で囲むと一致しなくなる現象を確認した
    （実例: 商品のSample_CODE "SLG-06120" は引用符付きだと0件、
    引用符無しだと正しくヒットした）。PO番号もハイフンを含む形式
    （例: "161-20241227_1"）のため、同じ問題を避けるために引用符を
    付けない。
    """
    from services import slack_service

    if not po_number:
        return {"status": "ok", "summary": "PO番号がありません。", "records": []}

    result = slack_service.search_messages(user_email, po_number, max_results)
    if result.get("status") == "ok":
        result["match_type"] = "po_number"
    return result


def get_task_signals(user_email: str | None, po_numbers: list[str], max_results: int = 25) -> dict[str, Any]:
    """今日のタスク一覧に対して、関連しそうな未読Gmail・直近Slackメッセージの
    件数を返す (docs/architecture.md 14.34)。

    タスク数だけGmail/Slackを呼び出すと、14.28で直したのと同種の遅延
    問題（N回の外部API呼び出し）を再現してしまうため、**全PO番号を1つの
    クエリにOR結合して、Gmail・Slackそれぞれ1回だけ**呼び出す。返って
    きたメッセージの件名/本文抜粋にどのPO番号が含まれるかで、タスクごと
    に振り分ける（複数PO番号を含むメッセージは両方にカウントされうる、
    ベストエフォートの振り分け）。

    Gmail: `is:unread`で未読のみに絞る（Gmail検索構文が正式にサポート
    している）。
    Slack: 「未読」に相当する概念がsearch APIには無いため、直近の関連
    メッセージ件数として扱う（Gmailの未読件数と同じ意味ではないことを
    呼び出し側で区別できるようキー名を分けている）。またSlackは
    ハイフンを含む語を引用符で囲むと一致しなくなるため（14.31）、
    PO番号は引用符なしで検索する。

    未連携・PO番号が無い場合はゼロ件として返す（架空の件数を作らない）。

    2026-07-09（14.36修正）: タスクが0件の場合、検索する対象が無いため
    早期returnしていたが、その際にgmail_status/slack_statusを無条件で
    "unavailable"（未連携の意味）にしていたため、実際には連携済みなのに
    「未連携」と誤表示していた（Noritsuguが「自分のタスク」で0件に
    なった時に発見）。タスクが0件でも、実際の連携状況（connect_status）
    を見て正しいステータスを返すよう修正した。
    """
    if not user_email:
        return {
            "gmail_unread_total": 0, "slack_recent_total": 0,
            "gmail_status": "unavailable", "slack_status": "unavailable",
            "by_task": {},
        }

    if not po_numbers:
        from services import gmail_service, slack_service
        return {
            "gmail_unread_total": 0, "slack_recent_total": 0,
            "gmail_status": "ok" if gmail_service.connect_status(user_email) else "unavailable",
            "slack_status": "ok" if slack_service.connect_status(user_email) else "unavailable",
            "by_task": {},
        }

    by_task = {po: {"gmail_unread": 0, "slack_recent": 0} for po in po_numbers}

    try:
        from services import gmail_service
        gmail_query = "(" + " OR ".join(f'"{po}"' for po in po_numbers) + ") is:unread"
        gmail_result = gmail_service.search_messages(user_email, gmail_query, max_results)
    except Exception as e:
        gmail_result = {"status": "error", "summary": str(e), "records": []}

    try:
        from services import slack_service
        slack_query = " OR ".join(po_numbers)  # 引用符なし（14.31）
        slack_result = slack_service.search_messages(user_email, slack_query, max_results)
    except Exception as e:
        slack_result = {"status": "error", "summary": str(e), "records": []}

    if gmail_result.get("status") == "ok":
        for rec in gmail_result.get("records", []):
            text = f"{rec.get('subject', '')} {rec.get('snippet', '')}"
            for po in po_numbers:
                if po in text:
                    by_task[po]["gmail_unread"] += 1

    if slack_result.get("status") == "ok":
        for rec in slack_result.get("records", []):
            text = rec.get("text", "")
            for po in po_numbers:
                if po in text:
                    by_task[po]["slack_recent"] += 1

    return {
        "gmail_unread_total": len(gmail_result.get("records", [])) if gmail_result.get("status") == "ok" else 0,
        "slack_recent_total": len(slack_result.get("records", [])) if slack_result.get("status") == "ok" else 0,
        "gmail_status": gmail_result.get("status", "unavailable"),
        "slack_status": slack_result.get("status", "unavailable"),
        "by_task": by_task,
    }


def get_related_communications(
    user_email: str | None,
    po_number: str,
    customer_id: str,
    supplier_name: str,
    max_results: int = 5,
) -> dict[str, Any]:
    """ログイン中の本人のGmail/Slackを、この案件に関連しそうなキーワード
    （PO番号を優先し、0件ならフォールバックとして顧客担当者メールアドレス・
    仕入先名）で検索する。

    Gmail/Slackどちらも未連携の場合や、user_emailが無い場合は、それぞれ
    'unavailable'をそのまま返す（呼び出し側はこれを見て「連携してくだ
    さい」と案内できる）。
    """
    if not user_email:
        unavailable = {"status": "unavailable", "summary": "ログインユーザーが特定できません。", "records": []}
        return {"gmail": unavailable, "slack": unavailable}

    contact_emails = get_customer_contact_emails(customer_id)

    try:
        gmail_result = _search_gmail_related(user_email, po_number, contact_emails, max_results)
    except Exception as e:
        gmail_result = {"status": "error", "summary": f"Gmail検索中にエラーが発生しました: {e}", "records": []}

    try:
        slack_result = _search_slack_related(user_email, po_number, supplier_name, max_results)
    except Exception as e:
        slack_result = {"status": "error", "summary": f"Slack検索中にエラーが発生しました: {e}", "records": []}

    return {"gmail": gmail_result, "slack": slack_result}
