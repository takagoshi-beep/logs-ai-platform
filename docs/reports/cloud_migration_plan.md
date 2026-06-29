# v1.1 Cloud Migration Sprint - Phase 1 Plan

## Scope and Constraints
- Goal: prepare cloud PostgreSQL support while preserving current SQLite real-data sync behavior.
- Non-goals for this phase: no implementation, no architecture redesign, no Business Layer behavior changes, no SQLite removal.
- Target model after migration: provider-selected storage with SQLite default and PostgreSQL optional.

## Current Storage/Repository Architecture (As-Is)
- Two repository stacks currently coexist:
  - `storage/*` stack for runtime ingestion/business utilities (`BaseRepository`, `SQLiteRepository`, `PostgresRepository`).
  - `database/*` stack for DB inspection/query endpoints (`DatabaseRepository`, current `SQLiteRepository` implementation).
- Runtime sync path:
  - Drive -> Ingestion -> Validation -> Storage in `ingestion/google_drive_importer.py` and `validation/runner.py`.
  - This path currently writes to SQLite through `storage.SQLiteRepository`.
- API read/query path:
  - `/tables`, `/db/*`, SQL executor use `database.get_repository(...)`, currently always SQLite.

## Where SQLite Is Directly Referenced

### A) Runtime-critical SQLite references (must be provider-aware first)
- `ingestion/google_drive_importer.py`
  - imports and instantiates `storage.SQLiteRepository` directly.
  - uses SQLite-specific metadata discovery (`sqlite_master`) and SQL assumptions.
- `business/query.py`
  - imports and opens `storage.SQLiteRepository` directly.
- `ai/explain.py`
  - imports and opens `storage.SQLiteRepository` directly for table count/catalog context.

### B) DB service layer SQLite references
- `database/repository.py`
  - `get_repository(db_path)` always returns SQLite implementation.
  - SQLite system introspection (`sqlite_master`, `PRAGMA`) is embedded.
- `database/connection.py`
  - direct `sqlite3.connect(...)` helper used by `database/repository.py`.

### C) SQLite implementation details
- `storage/sqlite.py`
  - SQLite PRAGMAs and locking setup (WAL, busy timeout) are SQLite-specific and correct for local mode.

### D) Config coupling
- `config/settings.py`
  - supports `STORAGE_PROVIDER` and `POSTGRES_URL` today.
  - current naming differs from target cloud standard `DATABASE_URL`.

## Migration Plan (Design Only, No Code Changes in Phase 1)

### Step 1: Introduce provider selection boundary
- Define one provider-resolution entrypoint for runtime storage stack:
  - `storage_provider=sqlite` -> `storage.SQLiteRepository`.
  - `storage_provider=postgres` -> `storage.PostgresRepository`.
- Keep SQLite as default and unchanged behavior for local sync.

### Step 2: Remove direct SQLite construction in runtime-critical callers
- Refactor only call-site wiring (not business logic):
  - `ingestion/google_drive_importer.py`
  - `business/query.py`
  - `ai/explain.py`
- These modules should request repository instances via provider factory instead of direct `SQLiteRepository` import.

### Step 3: Make database service layer provider-ready
- Extend `database.get_repository(...)` to be provider-aware for cloud mode.
- Keep existing SQLite schema/query behavior as default path.
- Introduce a PostgreSQL-side implementation for inspector/query operations (parallel API contract, no endpoint contract changes).

### Step 4: SQL dialect and metadata compatibility strategy
- Isolate SQLite-specific metadata queries (`sqlite_master`, `PRAGMA`) behind repository methods.
- For PostgreSQL, provide equivalent information_schema/pg_catalog-backed methods.
- Keep endpoint payload shape stable.

### Step 5: Keep ingestion architecture unchanged
- Preserve exact pipeline order: Drive -> Ingestion -> Validation -> Storage.
- Only swap repository implementation by provider config.
- Preserve current sync output contract (`files`, `rows_imported`, `table_count`, `errors`, etc.).

## Proposed Config Values
- Required defaults (local):
  - `STORAGE_PROVIDER=sqlite`
  - `DATABASE_URL=`
- Compatibility rule (for transition):
  - If `DATABASE_URL` is set, use it as PostgreSQL DSN.
  - Else fallback to existing `POSTGRES_URL` if present.
- Keep `SQLITE_PATH` as current local source-of-truth for SQLite mode.

## Tests to Add or Update (Phase 2 Implementation Gate)

### Update existing tests
- `tests/test_storage.py`
  - add provider-factory selection tests (sqlite default, postgres selection).
  - keep existing SQLite and Postgres scaffold assertions.
- `tests/test_google_drive_importer.py`
  - ensure sync still succeeds with default provider sqlite.
  - add explicit assertion that local default path remains SQLite-safe.
- `tests/test_api_sync.py`
  - ensure `/api/sync` behavior remains unchanged under `STORAGE_PROVIDER=sqlite`.

### Add new tests
- `tests/test_storage_provider_selection.py` (new)
  - verify environment/config precedence: `STORAGE_PROVIDER`, `DATABASE_URL`, `POSTGRES_URL` fallback.
- `tests/test_database_repository_provider.py` (new)
  - validate `database.get_repository(...)` provider routing contract.
- `tests/test_cloud_parity_read_contract.py` (new)
  - verify schema/list/sample API payload compatibility across providers (mocked PostgreSQL where needed).

### Regression focus
- Real-data sync regression test must explicitly prove:
  - SQLite remains default provider.
  - Full sync path still runs successfully with unchanged Business behavior.

## Risks and Guardrails
- Risk: hidden SQLite assumptions in SQL strings and metadata paths.
- Guardrail: move provider-specific SQL behind repository methods before enabling postgres in runtime paths.
- Risk: changing behavior in business endpoints.
- Guardrail: keep business functions untouched; only alter repository wiring.

## Exit Criteria for Phase 1
- SQLite coupling points identified and categorized.
- Provider migration strategy documented with no behavior changes.
- Config proposal documented (`STORAGE_PROVIDER=sqlite`, `DATABASE_URL=`).
- Test impact list defined.
