"""Tests for `backend/services/project_relations.py` (docs/architecture.md 14.29)."""
from __future__ import annotations

from services import project_relations


class _FakeCursor:
    def __init__(self, rows: list[tuple]):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        pass

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class _FakeConnection:
    def __init__(self, rows: list[tuple]):
        self._cursor = _FakeCursor(rows)
        self.closed = False

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True


def test_get_related_communications_returns_unavailable_without_user_email():
    result = project_relations.get_related_communications(None, "PO-1", "c1", "Supplier")
    assert result["gmail"]["status"] == "unavailable"
    assert result["slack"]["status"] == "unavailable"


def test_get_related_communications_runs_gmail_and_slack_in_parallel(monkeypatch):
    """2026-07-10（14.74、Noritsuguが「単一のPO番号だけの検索なのに
    重い」と気づいたことから発見）: 以前はGmail検索・Slack検索を直列に
    呼んでおり、それぞれ1〜3秒かかる外部API呼び出しが単純に積み上がって
    いた。ThreadPoolExecutorで並行実行するよう修正。Slack側の呼び出しを
    わざと遅くして、Gmail側がSlackの完了を待たされていないことを
    タイミングで検証する。"""
    import time

    from services import gmail_service, slack_service

    def _slow_slack_search(user_email, query, max_results):
        time.sleep(0.2)
        return {"status": "ok", "summary": "0件", "records": []}

    monkeypatch.setattr(gmail_service, "search_messages", lambda email, query, max_results: {"status": "ok", "summary": "1件", "records": [{"subject": "test"}]})
    monkeypatch.setattr(slack_service, "search_messages", _slow_slack_search)

    start = time.perf_counter()
    result = project_relations.get_related_communications("user@logs.co.jp", "PO-1", "c1", "Supplier")
    elapsed = time.perf_counter() - start

    assert result["gmail"]["records"] == [{"subject": "test"}]
    # 直列なら合計で0.2秒以上かかるはずのところ、並行実行なら
    # Slackの0.2秒がほぼそのまま合計時間になる（Gmail分が上乗せされない）。
    assert elapsed < 0.35


def test_gmail_search_uses_po_number_only(monkeypatch):
    """2026-07-10（14.75、Noritsuguの指定）: 以前はPO番号検索が0件の
    場合、顧客担当者メールへのフォールバック検索を行っていたが、
    ①Gmail検索が直列に2回走るため応答が3〜4.5秒かかっていた、
    ②フォールバックの結果は「同じPOとは限らない」精度の低い参考情報
    だった、という2つの理由から機能ごと削除した。PO番号のみで検索する。"""
    from services import gmail_service

    calls = []

    def _fake_search(email, query, max_results):
        calls.append(query)
        return {"status": "ok", "summary": "1件", "records": [{"subject": "見積書 2091-20250602_2"}]}

    monkeypatch.setattr(gmail_service, "search_messages", _fake_search)

    result = project_relations.get_related_communications("user@logs.co.jp", "2091-20250602_2", "c1", "1064STUDIO")

    assert calls == ['"2091-20250602_2"']
    assert result["gmail"]["match_type"] == "po_number"
    assert result["gmail"]["records"] == [{"subject": "見積書 2091-20250602_2"}]


def test_gmail_search_returns_zero_records_without_extra_fallback_call(monkeypatch):
    """PO番号一致が0件でも、フォールバック検索は一切行われない
    （14.75で機能自体を削除したため）。"""
    from services import gmail_service

    calls = []

    def _fake_search(email, query, max_results):
        calls.append(query)
        return {"status": "ok", "summary": "0件", "records": []}

    monkeypatch.setattr(gmail_service, "search_messages", _fake_search)

    result = project_relations.get_related_communications("user@logs.co.jp", "2091-20250602_2", "c1", "1064STUDIO")

    assert result["gmail"]["records"] == []
    assert calls == ['"2091-20250602_2"']  # 1回だけ


def test_gmail_search_returns_unavailable_status_as_is(monkeypatch):
    """未連携の場合はそのまま'unavailable'を返す。"""
    from services import gmail_service

    monkeypatch.setattr(gmail_service, "search_messages", lambda email, query, max_results: {"status": "unavailable", "summary": "Gmail未連携です。", "records": []})

    result = project_relations.get_related_communications("user@logs.co.jp", "2091-20250602_2", "c1", "1064STUDIO")

    assert result["gmail"]["status"] == "unavailable"


def test_slack_search_uses_po_number_only_no_supplier_name_fallback(monkeypatch):
    """14.29: Slackは仕入先名へのフォールバックを行わない
    （PO発行時に必ずPO番号入りの自動通知が飛ぶ運用のため、
    フォールバックはノイズの温床になるだけで実益が薄いという判断）。"""
    from services import slack_service

    calls = []

    def _fake_search(email, query, max_results):
        calls.append(query)
        return {"status": "ok", "summary": "0件", "records": []}

    monkeypatch.setattr(slack_service, "search_messages", _fake_search)

    result = project_relations.get_related_communications("user@logs.co.jp", "2091-20250602_2", "unknown", "1064STUDIO")

    assert calls == ["2091-20250602_2"]  # 仕入先名での検索は一切呼ばれない、かつ引用符無しで送られる
    assert result["slack"]["match_type"] == "po_number"
    assert result["slack"]["records"] == []


def test_slack_search_returns_po_number_match(monkeypatch):
    from services import slack_service

    monkeypatch.setattr(
        slack_service, "search_messages",
        lambda email, query, max_results: {"status": "ok", "summary": "1件", "records": [{"text": "PO#161-20241227_1発行"}]},
    )

    result = project_relations.get_related_communications("user@logs.co.jp", "161-20241227_1", "unknown", "STP inc")

    assert result["slack"]["match_type"] == "po_number"
    assert result["slack"]["records"] == [{"text": "PO#161-20241227_1発行"}]


