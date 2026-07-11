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

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from services.supabase_client import get_connection


def _search_gmail_related(user_email: str, po_number: str, max_results: int) -> dict[str, Any]:
    """PO番号でGmailを検索する。

    2026-07-10（14.75、Noritsuguの指定）: 以前はPO番号検索が0件の場合、
    顧客担当者メールアドレス（from:/to:）へのフォールバック検索を行って
    いたが、①Gmail検索が直列に2回走るため案件詳細・商品詳細の応答が
    3〜4.5秒かかっていた、②フォールバックは「同じPOとは限らない」参考
    情報に過ぎず精度が低かった、という2つの理由から機能ごと削除した。
    顧客とのメール全般を検索したい場合は「相談」機能（またはその他の
    今後追加する機能）で行う方針とし、この関数はPO番号での検索に専念
    させる。
    """
    from services import gmail_service

    if not po_number:
        return {"status": "ok", "summary": "PO番号がありません。", "records": []}

    result = gmail_service.search_messages(user_email, f'"{po_number}"', max_results)
    result["match_type"] = "po_number"
    return result


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


def get_related_communications(
    user_email: str | None,
    po_number: str,
    customer_id: str,
    supplier_name: str,
    max_results: int = 5,
) -> dict[str, Any]:
    """ログイン中の本人のGmail/Slackを、この案件のPO番号で検索する。

    Gmail/Slackどちらも未連携の場合や、user_emailが無い場合は、それぞれ
    'unavailable'をそのまま返す（呼び出し側はこれを見て「連携してくだ
    さい」と案内できる）。

    customer_idは以前、顧客担当者メールへのフォールバック検索に使って
    いたが、14.75でその機能自体を削除した（PO番号検索が0件の場合に
    Gmail検索が直列に2回走ることで応答が3〜4.5秒かかっていた上、
    フォールバックの結果は「同じPOとは限らない」精度の低い参考情報
    だったため）。呼び出し元との互換性のため引数自体は残しているが、
    現在は使用していない。
    """
    if not user_email:
        unavailable = {"status": "unavailable", "summary": "ログインユーザーが特定できません。", "records": []}
        return {"gmail": unavailable, "slack": unavailable}

    # 2026-07-10（14.74、Noritsuguが実際の[TIMING]ログの疑問から発見）:
    # 「単一のPO番号だけの検索なのに重い」という指摘の実際の原因は、
    # ここでGmail検索とSlack検索を直列に呼んでいたこと（それぞれ1〜3秒
    # かかる外部API呼び出しが単純に積み上がっていた）。project_detail・
    # today_actions・product_detailのルーター側で「DB取得とGmail/Slack
    # 検索」を並行化した（14.70・14.72・14.73）だけでは、この関数の
    # 内側にあったGmail⇔Slack間の直列実行までは解消されなかった。
    # ThreadPoolExecutorでGmail検索・Slack検索自体を並行実行する。
    from services.timing import timed

    def _fetch_gmail():
        try:
            with timed("get_related_communications.gmail"):
                return _search_gmail_related(user_email, po_number, max_results)
        except Exception as e:
            return {"status": "error", "summary": f"Gmail検索中にエラーが発生しました: {e}", "records": []}

    def _fetch_slack():
        try:
            with timed("get_related_communications.slack"):
                return _search_slack_related(user_email, po_number, supplier_name, max_results)
        except Exception as e:
            return {"status": "error", "summary": f"Slack検索中にエラーが発生しました: {e}", "records": []}

    with ThreadPoolExecutor(max_workers=2) as executor:
        gmail_future = executor.submit(_fetch_gmail)
        slack_future = executor.submit(_fetch_slack)
        gmail_result = gmail_future.result()
        slack_result = slack_future.result()

    return {"gmail": gmail_result, "slack": slack_result}
