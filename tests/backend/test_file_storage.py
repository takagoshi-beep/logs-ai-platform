"""Tests for `backend/services/file_storage.py`.

The Supabase client itself is always faked — no real Storage API call,
no real bucket needed in this environment.

Same reason as `test_record_store.py`: `conftest.py`'s autouse fixture
replaces `file_storage.upload_file`/`download_file` with in-memory
fakes for every other test — restore the real functions first here.
"""
from __future__ import annotations

from services import file_storage

_REAL_UPLOAD_FILE = file_storage.upload_file
_REAL_DOWNLOAD_FILE = file_storage.download_file


class _FakeBucket:
    def __init__(self):
        self.uploaded: list[tuple] = []
        self.downloaded_paths: list[str] = []
        self._files: dict[str, bytes] = {}

    def upload(self, path, data, options=None):
        self.uploaded.append((path, data, options))
        self._files[path] = data

    def download(self, path):
        self.downloaded_paths.append(path)
        return self._files[path]


class _FakeStorage:
    def __init__(self):
        self.buckets: dict[str, _FakeBucket] = {}

    def from_(self, bucket_name):
        return self.buckets.setdefault(bucket_name, _FakeBucket())


class _FakeSupabaseClient:
    def __init__(self):
        self.storage = _FakeStorage()


def test_upload_file_calls_storage_api_with_upsert(monkeypatch):
    monkeypatch.setattr(file_storage, "upload_file", _REAL_UPLOAD_FILE)
    fake_client = _FakeSupabaseClient()
    file_storage._get_client.cache_clear()
    monkeypatch.setattr(file_storage, "_get_client", lambda: fake_client)

    file_storage.upload_file("document-templates", "fmt-abc123.xlsx", b"fake excel bytes")

    bucket = fake_client.storage.buckets["document-templates"]
    path, data, options = bucket.uploaded[0]
    assert path == "fmt-abc123.xlsx"
    assert data == b"fake excel bytes"
    assert options["upsert"] == "true"


def test_download_file_returns_bytes_from_the_correct_bucket(monkeypatch):
    monkeypatch.setattr(file_storage, "upload_file", _REAL_UPLOAD_FILE)
    monkeypatch.setattr(file_storage, "download_file", _REAL_DOWNLOAD_FILE)
    fake_client = _FakeSupabaseClient()
    monkeypatch.setattr(file_storage, "_get_client", lambda: fake_client)

    file_storage.upload_file("generated-documents", "doc-xyz789.xlsx", b"generated output")
    result = file_storage.download_file("generated-documents", "doc-xyz789.xlsx")

    assert result == b"generated output"
    assert "doc-xyz789.xlsx" in fake_client.storage.buckets["generated-documents"].downloaded_paths


def test_get_client_raises_when_env_vars_missing(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    file_storage._get_client.cache_clear()
    try:
        import pytest
        with pytest.raises(RuntimeError, match="SUPABASE_URL"):
            file_storage._get_client()
    finally:
        file_storage._get_client.cache_clear()
