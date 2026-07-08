"""Supabase Storage-backed file storage for document format templates
and generated documents (docs/architecture.md 14.23 — Web化 / cloud
deployment preparation).

Storage (Supabase's object storage, backed by S3-compatible storage) is
a *separate service* from the Postgres database `record_store.py`
talks to — it has its own REST API and needs the Supabase project URL
plus a service-role key, not the `SUPABASE_DB_URL` connection string
used elsewhere in this codebase. Uses the official `supabase-py`
client rather than hand-rolling REST calls.

Two buckets are used, both must be created once in the Supabase
dashboard before this works (see docs/deployment_setup.md):
`document-templates` (uploaded template files) and
`generated-documents` (filled-in output files).
"""
from __future__ import annotations

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def _get_client():
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY is not configured "
            "(needed for Supabase Storage — separate from SUPABASE_DB_URL)."
        )
    return create_client(url, key)


def upload_file(bucket: str, path: str, data: bytes) -> None:
    """指定したバケットにファイルをアップロードする。同じpathに既存の
    ファイルがあれば上書きする（upsert）— format_id/output_idは毎回
    新規のUUIDベースなので通常は衝突しないが、再試行時に安全なように。
    """
    client = _get_client()
    client.storage.from_(bucket).upload(
        path,
        data,
        {
            "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "upsert": "true",
        },
    )


def download_file(bucket: str, path: str) -> bytes:
    """指定したバケットからファイルをダウンロードする。存在しない場合は
    supabase-py側の例外がそのまま呼び出し元に伝播する（呼び出し元で
    404等に変換すること）。
    """
    client = _get_client()
    return client.storage.from_(bucket).download(path)
