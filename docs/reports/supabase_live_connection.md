# v1.1 Supabase Live Connection Guide


<!-- SNAPSHOT-BANNER -->
> **📌 Point-in-time snapshot.** This document records the state of the
> project as of the date/phase named in its title or body. It has not been
> updated since, and may not reflect the current code. Verify claims against
> the current source before relying on them. For the maintained, current
> architecture reference, see `docs/architecture.md` and `docs/system_manifest.md`.

## Purpose
This guide defines safe procedures for validating live Supabase PostgreSQL connectivity and preparing AI OS schemas without touching existing public schema tables.

## Safety Principles
- Do not modify, drop, rename, or depend on existing public schema tables.
- Use environment variables only. Do not hardcode secrets.
- SQLite remains default when STORAGE_PROVIDER is not set.
- Supabase paths are active only when STORAGE_PROVIDER=supabase.

## Required Environment Variables
- STORAGE_PROVIDER=supabase
- SUPABASE_DB_URL=postgresql://...
- SUPABASE_SCHEMA_RAW=ai_os_raw
- SUPABASE_SCHEMA_CORE=ai_os_core
- SUPABASE_SCHEMA_META=ai_os_meta
- SUPABASE_BATCH_SIZE=1000
- SUPABASE_MAX_RETRIES=5

Optional but commonly present:
- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY
- SUPABASE_ANON_KEY

For batch-based writes and smoke validations:
- SUPABASE_WRITE_MODE=copy
- SUPABASE_BATCH_SIZE=1000
- SUPABASE_MAX_RETRIES=5

## 1) Connection Test (Read-Only)
Script:
- scripts/check_supabase_connection.py

What it does:
- loads settings from environment
- verifies STORAGE_PROVIDER=supabase
- connects using SUPABASE_DB_URL
- executes SELECT version();
- prints success or failure

What it does not do:
- no DDL
- no DML
- no schema/table mutation

Run:

```bash
python scripts/check_supabase_connection.py
```

Expected output:
- success with PostgreSQL version string
- or clear failure reason

## 2) Schema Bootstrap (Create-Only)
Script:
- scripts/bootstrap_supabase_ai_os.py

What it does:
- loads settings from environment
- verifies STORAGE_PROVIDER=supabase
- connects using SUPABASE_DB_URL
- runs CREATE SCHEMA IF NOT EXISTS for:
  - ai_os_raw
  - ai_os_core
  - ai_os_meta

What it does not do:
- no DROP SCHEMA
- no DROP TABLE
- no operation on public schema objects

Run:

```bash
python scripts/bootstrap_supabase_ai_os.py
```

Expected output:
- success with schema list
- or clear failure reason

## Operational Notes
- Run connection test first.
- Run schema bootstrap only after connection test succeeds.
- Keep credentials in environment or secret manager.
- Never commit real connection strings.

## 3) Batch Sync Safety
- Imported raw tables write to ai_os_raw only.
- Metadata, catalog, checkpoints, and sync status write to ai_os_meta only.
- Batches default to 1000 rows and retry transient failures with exponential backoff.
- When SUPABASE_WRITE_MODE=copy, raw-table batches use PostgreSQL COPY for faster full-sheet loads.
- Each successful batch writes a checkpoint row so a later resume can continue from the last successful batch.
- The existing public schema is not targeted by the AI OS sync path.
