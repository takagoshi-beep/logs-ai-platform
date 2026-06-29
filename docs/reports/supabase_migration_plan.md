# v1.1 Supabase Migration Sprint - Phase 3 Schema-Separated Implementation

## 1) Scope and Hard Constraints
- Objective: implement schema-separated Supabase behavior so AI OS uses dedicated PostgreSQL schemas and does not interfere with existing workloads in the same Supabase project.
- Live Supabase connection is still out of scope for this phase. Implementation is local/code-level only.
- SQLite remains default runtime behavior.
- Existing public schema must remain untouched.
- Existing business data and other application tables in the Supabase project must not be overwritten, dropped, renamed, or used as dependencies.

Input context for future cloud target:
- Supabase project URL (reference only, do not connect in this phase):
  - https://smyopukrxhroewohglpi.supabase.co

## 2) Multi-Schema Isolation Model for AI OS

### 2.1 Required schemas
AI OS data is isolated into three schemas:
- ai_os_raw
- ai_os_core
- ai_os_meta

### 2.2 Data ownership by schema
- ai_os_raw:
  - raw imported Google Drive data
  - staging-level table materialization per source file/sheet
- ai_os_core:
  - normalized and business-ready tables
  - canonical read model for Business Layer
- ai_os_meta:
  - sync metadata
  - source catalog
  - schema manifest and table manifests
  - validation reports
  - traces/observability records tied to sync lifecycle

### 2.3 Public schema protection
- Do not write AI OS runtime tables into public.
- Do not alter existing tables in public.
- Do not assume any table names in public exist for AI OS.
- Do not couple AI OS reads or writes to public table structures.

## 3) Repository Access Boundaries

### 3.1 Business Layer read boundary
- Business Layer must read only from ai_os_core via Repository abstractions.
- Business logic must not query ai_os_raw, ai_os_meta, or public directly.

### 3.2 Ingestion and validation write boundaries
- Ingestion may write to:
  - ai_os_raw for raw imports
  - ai_os_meta for sync state, catalog, and manifest entries
- Validation may write to:
  - ai_os_meta for validation outputs and run metadata
- Promotion/normalization into ai_os_core is a controlled step and must remain repository-mediated.

### 3.3 API/inspection boundary
- DB inspection and status paths for AI OS should target only ai_os_raw, ai_os_core, and ai_os_meta when provider=supabase.
- Inspection must not rely on public tables.

## 4) Configuration Design (No Implementation Yet)

### 4.1 Provider and connection vars
- STORAGE_PROVIDER=sqlite | supabase
- SUPABASE_URL=
- SUPABASE_DB_URL=
- SUPABASE_SERVICE_ROLE_KEY=
- SUPABASE_ANON_KEY=
- SUPABASE_BATCH_SIZE=1000
- SUPABASE_MAX_RETRIES=5
- SUPABASE_WRITE_MODE=insert | copy

### 4.2 New schema vars (required)
- SUPABASE_SCHEMA_RAW=ai_os_raw
- SUPABASE_SCHEMA_CORE=ai_os_core
- SUPABASE_SCHEMA_META=ai_os_meta

### 4.3 Resolution rules
- With STORAGE_PROVIDER unset, default is sqlite.
- With STORAGE_PROVIDER=supabase, repository resolution requires SUPABASE_DB_URL.
- Schema names are read from SUPABASE_SCHEMA_RAW, SUPABASE_SCHEMA_CORE, and SUPABASE_SCHEMA_META.
- Supabase batch size and retry count are read from SUPABASE_BATCH_SIZE and SUPABASE_MAX_RETRIES.
- Supabase write mode is read from SUPABASE_WRITE_MODE.
- No schema name literals should be hardcoded in runtime logic once implementation starts.

## 5) Logical Data Flow with Schema Separation
1. Google Drive connectors fetch source files.
2. Raw import writes raw tabular content into ai_os_raw.
3. Validation executes against imported content and writes reports/metadata into ai_os_meta.
4. Normalization/business shaping writes canonical business-ready tables into ai_os_core.
5. Business Layer reads from ai_os_core only.
6. Sync status, catalog, manifest, and traces remain in ai_os_meta.

## 6) Impacted Components (Design Mapping)

### 6.1 Runtime storage/provider layer
- Keep provider abstraction approach.
- Add schema-aware repository behavior for Supabase mode.
- Keep sqlite behavior and defaults unchanged.
- For Supabase, prefer batch commits and checkpoint persistence over one large transaction.

### 6.2 Ingestion and validation
- Map raw writes to ai_os_raw.
- Map sync/validation metadata writes to ai_os_meta.
- Keep existing pipeline order unchanged: Drive -> Ingestion -> Validation -> Storage.
- Supabase batch ingest writes per sheet should be chunked and checkpointed so a restart can resume from the last successful batch.

### 6.3 Business layer
- Enforce repository reads from ai_os_core only.
- Preserve current output contracts and API behavior.

### 6.4 Database service layer
- Table/schema introspection should filter/target ai_os_raw, ai_os_core, ai_os_meta in Supabase mode.
- Avoid any dependence on public schema tables.

## 7) Test Strategy Updates for Schema Isolation (Future Implementation Phase)

Update existing tests:
- tests/test_storage.py
  - provider resolution plus schema-config plumbing assertions
- tests/test_google_drive_importer.py
  - verify raw writes route to ai_os_raw and metadata routes to ai_os_meta (mocked)
- tests/test_api_sync.py
  - keep sqlite-default behavior unchanged

Add/extend tests:
- tests/test_storage_provider.py
  - validate required schema config defaults/overrides in supabase mode
- tests/test_database_repository_provider.py
  - verify repository routing does not target public
- tests/test_business_provider_parity.py
  - assert business reads only from ai_os_core
- tests/test_supabase_schema_isolation.py
  - enforce no write/read dependency on public for AI OS paths

Regression gate:
- SQLite real-data sync must remain behavior-identical and green before enabling supabase mode.

## 8) Security and Coexistence Policy
- Never hardcode credentials.
- Never commit secrets.
- Keep service role key server-side only.
- Treat the Supabase project as multi-tenant at schema level for platform coexistence.
- AI OS operations must be namespaced to ai_os_raw, ai_os_core, and ai_os_meta.

## 9) Phase 3 Delivered Implementation
- Added schema config support:
  - SUPABASE_SCHEMA_RAW=ai_os_raw
  - SUPABASE_SCHEMA_CORE=ai_os_core
  - SUPABASE_SCHEMA_META=ai_os_meta
- Implemented schema-aware Supabase repository behavior for runtime and DB inspection layers.
- Added safe bootstrap script to create missing schemas:
  - scripts/bootstrap_supabase_schemas.py
  - create-only semantics (`CREATE SCHEMA IF NOT EXISTS`)
- Added transform pipeline placeholder interface:
  - ai_os_raw -> transform(pass-through) -> ai_os_core
- Enforced Business Layer read boundary to ai_os_core via repository behavior.
- Kept ingestion/validation write scope to ai_os_raw and ai_os_meta in Supabase mode.
- Preserved SQLite default behavior and local regression compatibility.

## 10) Supabase Batch Sync Safety
- Default batch size: 1000 rows.
- Supabase retries transient batch failures with exponential backoff.
- COPY write mode is available for full-sheet raw loads when SUPABASE_WRITE_MODE=copy.
- Each successful batch records a checkpoint row in ai_os_meta.gdrive_sync_checkpoints.
- Checkpoints record sync_id, source_file, sheet_name, target_table, batch_number, rows_written, last_success_at, and status.
- If Supabase disconnects, the sync stops safely and reports the last successful checkpoint.

## 11) Resume Strategy
- Future resume logic should read the latest successful checkpoint from ai_os_meta.gdrive_sync_checkpoints.
- Resume should continue with the next batch_number for the same sync_id/source_file/sheet_name/target_table combination.
- Resume should not reprocess completed batches and should not touch public schema.

## 12) Non-Destructive Guarantees
- No DROP SCHEMA operations are introduced.
- No DROP TABLE operation is introduced for public schema.
- AI OS code paths do not read/write public tables in Supabase mode.
- Existing public schema tables remain out of scope and unchanged.
