# Supabase Cloud Sync Milestone


<!-- SNAPSHOT-BANNER -->
> **📌 Point-in-time snapshot.** This document records the state of the
> project as of the date/phase named in its title or body. It has not been
> updated since, and may not reflect the current code. Verify claims against
> the current source before relying on them. For the maintained, current
> architecture reference, see `docs/architecture.md` and `docs/system_manifest.md`.

## Scope
This milestone finalizes the Supabase cloud sync pipeline for Excel workbook ingestion while preserving SQLite as the default runtime and keeping the existing `public` schema untouched.

## Implemented
- Supabase storage provider selection via `STORAGE_PROVIDER=supabase`
- Schema-separated PostgreSQL support for:
  - `ai_os_raw`
  - `ai_os_core`
  - `ai_os_meta`
- Schema bootstrap and live connection validation scripts
- COPY-based write mode for high-volume raw table loads
- Insert-based batch fallback path with retry/backoff behavior
- Checkpoint foundation in `ai_os_meta.gdrive_sync_checkpoints`
- Metadata/catalog/status writes isolated to `ai_os_meta`
- Workbook-level validation runner for Excel sync to Supabase
- Profiling instrumentation for workbook sync stages
- Safe performance optimizations that preserve output data:
  - removed unnecessary DataFrame copy during normalization
  - removed redundant raw-table pre-refresh probe in workbook validation
  - removed redundant post-sync raw row recounts in workbook validation
  - reduced repeated settings lookups in the hot write path

## Current Status
- Supabase connection implemented: yes
- `ai_os_raw` / `ai_os_core` / `ai_os_meta` support implemented: yes
- COPY write mode implemented: yes
- Batch fallback implemented: yes
- Checkpoint/resume foundation implemented: yes
- Full Excel workbook sync validated: yes
- `public` schema unchanged during validation: yes
- SQLite default behavior preserved in focused regression tests: yes

## Validation Results
### Focused milestone suite
Command:
```bash
pytest tests/test_supabase_batching.py tests/test_supabase_schema_config.py tests/test_storage_provider.py tests/test_database_repository_provider.py tests/test_google_drive_importer.py tests/test_supabase_live_scripts.py tests/test_transform_pipeline.py tests/test_storage.py
```

Result:
- Pass

### Full test suite
Command:
```bash
pytest
```

Result:
- Fails outside the Supabase milestone scope
- Observed failing areas:
  - `tests/test_api_sync.py`
  - `tests/test_database_summary.py`
  - `tests/test_storage_sync_api.py`
- Failure pattern:
  - `test_api_sync_returns_400_when_folder_id_is_missing` returned `200` instead of `400`
  - database summary tests returned empty table/count/column results in their local setup path
  - storage sync API tests attempted a PostgreSQL connection to `example.invalid`
- These failures block a fully green repository-wide commit gate

## Workbook Validation Snapshot
Validated workbook:
- `ログシスExcels連携_v3_0813修正_20260629.xlsx`

Rows written to `ai_os_raw`:
| Table | Rows |
|---|---:|
| 売上 | 199512 |
| 顧客 | 2738 |
| 顧客担当者 | 3816 |
| 商品 | 10236 |
| 仕入 | 44855 |
| 発注依頼 | 34733 |
| 取引先 | 2148 |
| 仕入諸掛 | 21390 |
| コード | 199 |
| Total | 319627 |

Metadata snapshot:
| Table | Rows |
|---|---:|
| gdrive_source_catalog | 9 |
| gdrive_sync_checkpoints | 324 |
| gdrive_sync_registry | 1 |
| gdrive_sync_status | 1 |
| gdrive_excel_files | 0 |
| gdrive_spreadsheet_files | 0 |
| Total (`ai_os_meta`) | 335 |

Other validation points:
- `ai_os_core` remained empty
- `public` table count remained unchanged before/after validation
- Latest validation status: `ok`

## Performance Notes
Profiled workbook sync baseline:
- Runtime: 333.852 seconds
- Throughput: 957.391 rows/sec

Optimized workbook sync validation:
- Runtime: 296.707 seconds
- Throughput: 1077.248 rows/sec
- Runtime improvement: 11.13%

Top bottlenecks after optimization:
1. Excel parsing
2. DataFrame creation path tied to parsing instrumentation
3. End-to-end sheet write time on large sheets
4. PostgreSQL COPY execution
5. COPY preparation / row serialization

Largest sheet costs remain dominated by:
- `売上`
- `発注依頼`
- `仕入`

## Secrets Check
Verified before commit preparation:
- `.env` is not tracked by git
- `credentials.json` is not tracked by git
- `token.json` is not tracked by git
- No live Supabase DB credential string was found in tracked source/docs files
- The local `.env` contains the real connection string and must remain uncommitted

## Known Issues
- Full repository test suite is not green: `6 failed, 259 passed`
- Workbook validation payload still shows a reporting-only key inconsistency for `rows_written_per_table` on `発注依頼`
- Profiling currently attributes `dataframe_creation` to the same parse-created DataFrame path as `sheet_parse`, so those two metrics overlap conceptually
- Several temporary diagnostic scripts remain in the working tree and should be reviewed before a final production-facing cleanup pass

## Next Steps
- Stabilize the unrelated Google Drive API and database summary test failures so the full repository suite is green
- Decide which temporary Supabase diagnostic scripts and generated artifacts should remain tracked
- Normalize the workbook validation reporting key for `発注依頼`
- If desired, continue with a dedicated Excel parsing optimization pass, since parsing remains the dominant bottleneck
