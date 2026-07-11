"""Tests for `backend/services/gmail_service.py`'s `search_messages()`
(docs/architecture.md 14.76).

Context: search_messages() first lists matching message IDs, then fetches
each message's metadata (subject/from/date/snippet) individually. This used
to be a sequential loop — an N+1 pattern where total time scaled with the
number of matching emails (observed: 772ms for a product with few matches,
3-4s for products with more). Fixed to fetch all messages in parallel via
ThreadPoolExecutor.
"""
from __future__ import annotations

import time

from services import gmail_service


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        pass

    def json(self):
        return self._json_data


def test_search_messages_returns_unavailable_when_not_connected(monkeypatch):
    monkeypatch.setattr(gmail_service, "_get_access_token", lambda email: None)

    result = gmail_service.search_messages("user@logs.co.jp", "query", 5)

    assert result["status"] == "unavailable"
    assert result["records"] == []


def test_search_messages_fetches_message_metadata_in_parallel(monkeypatch):
    """2026-07-10（14.76、Noritsuguが実際の[TIMING]ログの商品ごとの差
    から発見）: 以前はヒットしたメール1件ごとに個別のメタデータ取得を
    直列に実行しており、ヒット件数に比例して所要時間が増えていた。
    ThreadPoolExecutorで並行実行するよう修正した。5件それぞれ0.1秒
    かかる場合、直列なら0.5秒以上かかるが、並行実行ならほぼ0.1秒で
    完了することを確認する。"""
    monkeypatch.setattr(gmail_service, "_get_access_token", lambda email: "fake-token")

    message_ids = [f"msg-{i}" for i in range(5)]

    def _fake_get(url, headers=None, params=None, timeout=None):
        if url.endswith("/messages"):
            return _FakeResponse({"messages": [{"id": mid} for mid in message_ids]})
        # 個別メッセージ取得: わざと遅くする
        time.sleep(0.1)
        mid = url.rsplit("/", 1)[-1]
        return _FakeResponse({
            "payload": {"headers": [
                {"name": "Subject", "value": f"件名{mid}"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "Date", "value": "2026-07-10"},
            ]},
            "snippet": "本文の抜粋",
        })

    monkeypatch.setattr(gmail_service.requests, "get", _fake_get)

    start = time.perf_counter()
    result = gmail_service.search_messages("user@logs.co.jp", "query", 10)
    elapsed = time.perf_counter() - start

    assert result["status"] == "ok"
    assert len(result["records"]) == 5
    assert {r["message_id"] for r in result["records"]} == set(message_ids)
    # 直列なら0.5秒以上かかるはずのところ、並行実行なら0.1秒強で完了する。
    assert elapsed < 0.3


def test_search_messages_returns_empty_records_when_no_matches(monkeypatch):
    monkeypatch.setattr(gmail_service, "_get_access_token", lambda email: "fake-token")

    def _fake_get(url, headers=None, params=None, timeout=None):
        return _FakeResponse({"messages": []})

    monkeypatch.setattr(gmail_service.requests, "get", _fake_get)

    result = gmail_service.search_messages("user@logs.co.jp", "query", 10)

    assert result["status"] == "ok"
    assert result["records"] == []


def test_search_messages_skips_individual_fetch_failures_gracefully(monkeypatch):
    """一部のメッセージ取得が失敗しても、成功した分だけ返す
    （並行実行に変更しても、個別の例外処理は維持されている）。"""
    monkeypatch.setattr(gmail_service, "_get_access_token", lambda email: "fake-token")

    message_ids = ["msg-ok", "msg-fail"]

    def _fake_get(url, headers=None, params=None, timeout=None):
        if url.endswith("/messages"):
            return _FakeResponse({"messages": [{"id": mid} for mid in message_ids]})
        if url.endswith("/msg-fail"):
            raise RuntimeError("boom")
        return _FakeResponse({
            "payload": {"headers": [{"name": "Subject", "value": "OK件名"}]},
            "snippet": "",
        })

    monkeypatch.setattr(gmail_service.requests, "get", _fake_get)

    result = gmail_service.search_messages("user@logs.co.jp", "query", 10)

    assert result["status"] == "ok"
    assert len(result["records"]) == 1
    assert result["records"][0]["message_id"] == "msg-ok"
