# LOGS AI Platform

ログズ株式会社（ファッション雑貨の輸入・卸売business）向けの社内AI/BI
プラットフォームです。Logsysと連携した実データ（Supabase）を、Function
Callingによる自由な相談機能（chat）と、固定パターンの検証用推論エンジン
（reasoning）の2つの経路から扱います。

**2026-07-14 整理:** このREADMEは元々`app/`ディレクトリ（2026-07-06に
完全削除、14.14参照）を中心にSprintごとの開発ログとして書かれていた
ため、現在稼働しているのは`backend/`+`frontend/`の構成にも関わらず、
内容の大半が古いままになっていた。以下は現在の構成に合わせて書き直した
セクション。それ以降（`---`区切りの下）は、削除済みの`app/`時代の
Sprintログをそのまま履歴として残してある（現状を知りたいだけなら読む
必要はない）。

## ドキュメント

- **現在の状態を知りたい場合はこちら:** [docs/architecture.md](docs/architecture.md) — フェーズごとの開発記録（13以降が現行`backend/`構成、日付順）
- Blueprint（設計思想）: [docs/blueprint/AI_OS_BLUEPRINT_v0.2_DRAFT.md](docs/blueprint/AI_OS_BLUEPRINT_v0.2_DRAFT.md)
- 既知の課題: [docs/review/KNOWN_ISSUES.md](docs/review/KNOWN_ISSUES.md)
- 本番同期の設定手順: [docs/production_sync_setup.md](docs/production_sync_setup.md)
- Renderデプロイ設定: [docs/render_deployment.md](docs/render_deployment.md)

## 構成

- `backend/` — FastAPI。Supabase（Tokyo region）の実データを読む。Renderの「Root Directory: backend」設定で、このディレクトリ単体がデプロイされる（Dockerは使わない）。
- `frontend/` — Next.js。`backend/`の`/api/*`を叩く。
- `knowledge/` — 業務用語の定義（`code_master`の数値コードの意味等）を持つmarkdownファイル。`tool_registry.py`が動的に読み込む。
- `docs/architecture.md` — 開発の全記録。セッションごとにフェーズ番号（13.x、14.x、...）で追記されている。

## ローカル起動

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

ヘルスチェック: `http://localhost:8000/api/health`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

アクセス: `http://localhost:3000`

環境変数 `NEXT_PUBLIC_API_BASE`（未設定時は`http://localhost:8000`にフォールバック）でバックエンドの向き先を指定する。

### 主なページ

- `/chat` — 相談（Function Calling、chat_agent.py）
- `/reasoning` — 推論エンジン（固定Q1-Q6パターン）
- `/products`・`/products/{id}` — 商品一覧・詳細
- `/workspace`・`/workspace/{projectId}` — 案件一覧・詳細
- `/tasks` — 今日のタスク
- `/proposals` — 提案書ドラフト（Governance承認込み）
- `/history` — 実行履歴
- `/learning` — Learning Center（現状サイドメニュー未表示、直接URLでアクセス）
- `/settings` — 設定

### 環境変数（Supabase接続）

`backend/`は`SUPABASE_DB_URL`（PostgreSQL接続文字列）で本番Supabaseの
`public`スキーマに直接接続する。ローカル開発時にテストが本番へ接続する
ことを防ぐため、`tests/backend/conftest.py`の`autouse`フィクスチャが
`STORAGE_PROVIDER=sqlite`・`GOOGLE_OAUTH_ENABLED=false`を強制する。

## デプロイ

Render（Singapore region）。詳細は[docs/render_deployment.md](docs/render_deployment.md)を参照。本番同期（Logsys Excel → Supabase）の手順は[docs/production_sync_setup.md](docs/production_sync_setup.md)を参照。

---

## 履歴（`app/`時代のSprintログ、2026-07-06に`app/`削除済み・以下は参考情報として保持）

# LOGS AI Platform

LOGS AI Platform is an internal AI/data platform for using Logsys-connected Excel data as a structured business intelligence layer.

## 🚀 Quick Start — Walking Skeleton Demo (5 min)

**Want to see the AI OS in action?** Check out the [Walking Skeleton Review Guide](docs/review/FIRST_USER_REVIEW.md).

> **Important:** `app/main.py` (this section) and `backend/main.py` (used by the
> Next.js frontend for real data) are **separate servers with overlapping route
> names** (both define `/api/projects`, with different meanings — one is an
> in-memory demo sandbox, the other reads real Supabase data). Do not run both
> on the same port. Use `--port 8001` for `app/main.py` as shown below if
> `backend/main.py` is also running on 8000.

### Try the Live Demo

1. **Start Backend:**
```bash
   python -m uvicorn app.main:app --reload --port 8001
```

2. **Start Frontend:**
```bash
   cd frontend && npm run dev
```

3. **Open Demo:**
   Navigate to: **http://localhost:3000/walking-skeleton**

**What you'll see:**
- Create an OEM project with AI analysis
- View project understanding (state, goals, events)
- Get AI suggestions for next actions
- Mark actions as helpful/not helpful
- Watch the Learning system create candidates
- See Activity Feed record all events
- Inspect Debug Trace for reasoning

**Time:** 10-15 minutes  
**Learn:** How AI OS understands projects, executes decisions, learns from feedback, and maintains governance

**Full guide:** [docs/review/FIRST_USER_REVIEW.md](docs/review/FIRST_USER_REVIEW.md)  
**Known issues:** [docs/review/KNOWN_ISSUES.md](docs/review/KNOWN_ISSUES.md)  
**Feedback:** [docs/review/FEEDBACK_TEMPLATE.md](docs/review/FEEDBACK_TEMPLATE.md)

---

## 📘 Architecture & Design

**Start here:** [AI OS Blueprint v0.2 (Draft)](docs/blueprint/AI_OS_BLUEPRINT_v0.2_DRAFT.md) - Responsibility-Based Architecture

- **Blueprint:** [docs/blueprint/](docs/blueprint/) - Official AI OS specification
- **Design Documents:** [docs/architecture/design/](docs/architecture/design/) - Architectural decisions and design specs
- **Audit Reports:** [docs/architecture/audit/](docs/architecture/audit/) - Architecture verification and analysis
- **Implementation Report:** [Walking Skeleton Implementation Report](docs/blueprint/WALKING_SKELETON_IMPLEMENTATION_REPORT.md)

---

- Design constitution: [docs/philosophy.md](docs/philosophy.md)
- Architecture: [docs/architecture.md](docs/architecture.md)
- System Manifest: [docs/system_manifest.md](docs/system_manifest.md)
- Raw Data Validation: [docs/raw_data_validation.md](docs/raw_data_validation.md)
- ADRs: [docs/decisions/](docs/decisions)

## Two separate servers in this repository

This repository contains **two independent FastAPI applications** that must
not be run on the same port:

| Server | Entry point | Default port | Purpose |
|---|---|---|---|
| Full AI OS | `app/main.py` | 8001 (recommended) | The complete layered platform (Runtime/Context/Intent/Planner/Business/Knowledge/Learning). Reads real data from Supabase `public` schema via `business/` and `storage/`. Also hosts the in-memory Walking Skeleton demo under `/api/projects`. |
| Frontend API (V0.1 skeleton) | `backend/main.py` | 8000 | Serves the Next.js frontend (`frontend/`) under `/api/*`. A mix of real Supabase-backed endpoints (home KPIs, reasoning, projects, today-actions) and intentional mock endpoints (chat, tasks, proposals, history — see `backend/services/mock_store.py`). |

Both define a route also called `/api/projects`, but with **different meanings**:
`app/main.py`'s version is an in-memory demo sandbox for the Walking Skeleton
review; `backend/main.py`'s version reads real `purchase_orders` data. Keep
this in mind when testing — always check which server you're pointed at.

## Sprint 1 goal

- Create a local FastAPI app
- Import Logsys Excel sheets into SQLite
- Expose basic health/status endpoints
- Prepare a maintainable data foundation for future AI search, analytics views, and semantic retrieval

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Data placement

Place the Logsys Excel workbook under:

```text
data/excel/
```

The importer will automatically pick the newest Excel file in that directory.

## Import data into SQLite

> ⚠️ **Not used in the current configuration.** This project currently runs
> with `STORAGE_PROVIDER=supabase` and reads directly from the shared
> production `public` schema. See
> [Supabase configuration](#supabase-configuration-current-direct-public-schema-reference)
> below before using this importer.

Run the unified command below:

```bash
python database/importer.py
```

This will:

- find the latest Excel file in data/excel
- import every sheet into SQLite
- create or replace SQLite tables per sheet
- record import metadata in import_registry
- store column schema information in table_schema_registry
- run basic validation checks and store results in validation_report

## Update the database

Whenever the source Excel is updated, place the new file in data/excel and run:

```bash
python database/importer.py
```

You can also update the database via the API after placing the latest Excel workbook in `data/excel`:

```bash
curl -X POST http://127.0.0.1:8000/db/import
```

## Run the app

Start the FastAPI app:

```bash
uvicorn app.main:app --reload --port 8001
```

The API will expose:

- /chat
- /ai/chat
- /question/parse
- /health
- /version
- /tables
- /tables/{table_name}/sample
- /query
- /db/sql
- /db/status
- /db/schema
- /db/schema/{table_name}
- /db/import

Business modules are available in `business/` for domain-specific data access.

### Customer business module

The customer business module supports flexible customer data access based on schema inspection.

- `get_customer_schema(db_path)` returns the customer table and columns.
- `get_customers(db_path, limit=100)` returns customer rows.
- `get_customer(db_path, customer_code)` returns a single customer.
- `search_customers(db_path, keyword, limit=100)` searches customers by name.
- `get_top_customers_by_sales(db_path, limit=10)` reuses sales logic for customer sales ranking.

Open:

```text
http://127.0.0.1:8001
```

Then open the automatic API docs and execute the endpoints from the browser:

```text
http://127.0.0.1:8001/docs
```

## Cloud Deployment

The runtime is structured so the chat entrypoint can run as a cloud API service while keeping Business Logic and Knowledge unchanged.

- `POST /chat` is the primary chat API for web apps and future Claude-side UI clients.
- `POST /ai/chat` remains available as a compatibility alias.
- `GET /trace/{trace_id}` provides post-request observability for one execution path.
- `GET /health` and `GET /version` provide deployment checks and build metadata.
- `session/` keeps request-scoped session state separate from Memory.
- `config/` contains `dev`, `staging`, and `production` settings files.
- Storage access goes through a repository abstraction so the SQLite backend can be replaced later.

Local Docker start:

```bash
docker compose up --build
```

The container exposes the FastAPI service on port `8000`.

## Supabase configuration (current: direct `public` schema reference)

SQLite remains the default provider when `STORAGE_PROVIDER` is not set.

This project currently reuses the existing production Supabase database
(the same one used by the separate ChatGPT-driven operational tooling)
by reading directly from its `public` schema, instead of re-importing
Excel data into a separate schema. This avoids duplicating 200K+ rows
of live sales/customer/product data.

Set the following in `.env` to enable this:

```bash
STORAGE_PROVIDER=supabase
SUPABASE_DB_URL=postgresql://...
SUPABASE_SCHEMA_CORE=public
```

`.env` is loaded automatically via `python-dotenv` in `config/settings.py`;
no manual environment variable export is required.

### Important: do not re-run the Excel importer

`database/importer.py` writes into a separate SQLite database and is
**not compatible with this configuration**. It is disabled by a safety
guard when `STORAGE_PROVIDER=supabase` to avoid confusion:

```bash
python -m database.importer
# ERROR: STORAGE_PROVIDER=supabase が設定されています。... (execution blocked)
```

If Excel-based local development is genuinely needed, switch to
`STORAGE_PROVIDER=sqlite` first and be aware the resulting local data
is separate from the shared production data.

### Legacy: dedicated `ai_os_*` schemas (not currently used)

An earlier design used dedicated schemas (`ai_os_raw`, `ai_os_core`,
`ai_os_meta`) fully isolated from `public`. This is no longer the
active configuration but the bootstrap script remains available if a
future migration back to isolated schemas is needed:

```bash
python scripts/bootstrap_supabase_schemas.py
```

This script only runs `CREATE SCHEMA IF NOT EXISTS` for:

- `ai_os_raw`
- `ai_os_core`
- `ai_os_meta`

## DB schema inspection

Use the schema endpoints to inspect the database structure for AI-friendly metadata.

- `GET /db/schema`
  - returns all tables and views
  - includes table_name, row_count, column_count, columns, and sample_values

- `GET /db/schema/{table_name}`
  - returns schema details for a single table

Example response for `/db/schema`:

```json
[
  {
    "table_name": "sheet1",
    "table_type": "business",
    "row_count": 10,
    "column_count": 3,
    "columns": [
      {"name": "id", "type": "INTEGER", "sample_values": [1, 2, 3]},
      {"name": "name", "type": "TEXT", "sample_values": ["alpha", "beta"]}
    ]
  }
]
```

Example response for `/db/schema/sheet1`:

```json
{
  "table_name": "sheet1",
  "table_type": "business",
  "row_count": 10,
  "column_count": 3,
  "columns": [
    {"name": "id", "type": "INTEGER", "sample_values": [1, 2, 3]},
    {"name": "name", "type": "TEXT", "sample_values": ["alpha", "beta"]}
  ]
}
```

## Business products module

The product business module provides dynamic access to product-related tables using schema information.

- `get_product_schema(db_path)` returns the resolved product table and columns.
- `get_products(db_path, limit=50)` returns product rows.
- `get_product(db_path, product_code)` returns a single product by product code.
- `search_products(db_path, keyword, limit=50)` searches product names.

## Sprint 7: business intent and routing

The business layer now separates intent classification from execution routing so future LLM-based replacements can be introduced more easily.

- `business/intent.py` provides rule-based `classify_intent(message)` for domain/action detection.
- `business/router.py` provides `route_business_query(message, db_path)` to dispatch to existing sales/product/customer business functions.
- `POST /business/query` accepts a message and returns the detected intent together with the routed result.

## Sprint 8: enhanced intent parsing

Intent parsing now also extracts:

- `period`: `today`, `yesterday`, `this_month`, `last_month`, or `this_year`
- `count`: numeric ranking size such as `5` from `トップ5`
- `category`: normalized product categories such as `hat`, `bag`, or `sunglasses`

These fields are added to the JSON intent payload while preserving the existing `domain`, `action`, and `keywords` structure for compatibility.

## Sprint 9: system map and logic registry

The platform now exposes a simple registry of business logic so the AI layer can understand the available operations.

- `system/definitions.py` stores the logic catalog.
- `system/logic_registry.py` provides accessors for the registry and system map.
- `GET /system/map` returns a grouped overview of domains and logic names.
- `GET /system/logic` returns the full logic registry.
- `GET /system/logic/{logic_name}` returns the metadata for a specific logic.

## Sprint 34: Question Understanding layer

Question Understanding is added as a deterministic rule-based stage between Intent and Planner.

- `question/parser.py` parses the user message into structured fields.
- Extracted fields include `metric`, `operation`, `entity_type`, `period`, `limit`, and `filters`.
- Runtime trace includes a `Question` layer and normalized fields (`question_metric`, `question_operation`, `question_entity_type`, `question_period`, `question_limit`, `question_confidence`).
- `POST /question/parse` exposes parsing as a standalone API.

## Sprint 10: knowledge layer

A new knowledge layer keeps business terminology and company/brand information separate from the business logic layer.

- `knowledge/glossary.py` stores glossary items such as OEM, ODM, gross profit, logical cost, and actual cost.
- `knowledge/company.py` stores company metadata such as LOGS, 丸太屋, FOLTEK, and Arts Division.
- `knowledge/brands.py` stores brand metadata such as newhattan.
- `GET /knowledge` returns all knowledge categories.
- `GET /knowledge/{category}` returns a specific category.
- `GET /knowledge/search?q=` searches the glossary entries.

## Sprint 11: planner layer

A lightweight rule-based planner has been added to compose multi-step actions from intent, knowledge, business logic, and system metadata.

- `planner/plan.py` creates a plan from a natural-language message.
- `planner/executor.py` executes the plan step by step.
- `POST /planner/plan` returns the generated plan.
- `POST /planner/execute` executes the generated plan.

## Sprint 12: workflow layer

A new workflow layer manages how the planner's steps are executed as a structured flow.

- `workflow/models.py` defines `Workflow`, `WorkflowStep`, and `WorkflowResult` objects.
- `workflow/builder.py` converts planner steps into a workflow object.
- `workflow/engine.py` executes workflow steps while delegating to the existing knowledge, business, and system modules.
- `POST /workflow/create` creates a workflow from a plan or message.
- `POST /workflow/run` executes a workflow.

## Sprint 13: answer generation

The platform now includes a lightweight answer generator that turns workflow results into human-readable text.

- `answer/generator.py` creates a natural-language response from workflow results.
- `answer/formatter.py` provides helpers for knowledge, ranking, list, and system output formatting.
- `POST /answer` runs planning, workflow execution, and answer generation in sequence.

## Sprint 14: learning layer

A learning layer was added to capture query logs, feedback, and improvement requests without modifying business logic or definitions automatically.

- `learning/query_log.py` stores query logs with intent, plan, workflow, answer, success, error, and feedback metadata.
- `learning/feedback.py` records user feedback statuses.
- `learning/improvements.py` manages improvement items, statuses, proposed solutions, and implementation tracking.
- `learning/insights.py` summarizes learning data and suggests improvements from problematic feedback.
- `POST /answer` now saves a query log automatically and returns its `log_id`.
- Learning APIs expose logs, feedback, summaries, improvements, and improvement actions.

## Sprint 15: self-awareness layer

A self-awareness layer was added so the system can describe its own capabilities, limitations, next recommendations, and current status.

- `self_awareness/capabilities.py` exposes current capabilities, limitations, and next recommendations.
- `self_awareness/status.py` reports status metrics such as test count, logic count, knowledge count, improvement count, and active layers.
- `GET /self/capabilities`, `GET /self/limitations`, `GET /self/recommendations`, and `GET /self/status` expose this information.
- `POST /answer` also responds to questions like “何ができますか？” using the self-awareness layer.

## Sprint 16: admin dashboard layer

An admin dashboard layer was added so administrators can inspect usage, improvement backlog, and quality signals through API endpoints.

- `admin/dashboard.py` aggregates summary, health, recent improvements, and recommendations.
- `admin/metrics.py` exposes usage, improvement, and quality metrics.
- `GET /admin/dashboard`, `GET /admin/metrics/usage`, `GET /admin/metrics/improvements`, and `GET /admin/metrics/quality` provide read-only monitoring access.

## Sprint 17: change management layer

A change-management layer was added to track improvement requests through a lightweight lifecycle from draft to release.

## LOGS AI OS V0.1 Product Skeleton

### Project overview

- LOGS AI OS V0.1 Product Skeleton is the first production-oriented UI foundation.
- This is a work-entry product skeleton for end users, not a Streamlit prototype.
- Current implementation is a mock-based skeleton before full AI Runtime integration.

### Directory structure (V0.1 focus)

- `frontend`
- `backend`
- `knowledge`
- `memory`
- `capability`
- `tests/evaluation`
- `docs`

### Backend startup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Health check URL:

```text
http://localhost:8000/api/health
```

### Frontend startup

```bash
cd frontend
npm install
npm run dev
```

Access URL:

```text
http://localhost:3000
```

For screenshot-friendly preview, use a desktop browser width around `1440px` and keep the left navigation visible.

### Environment variable

- `NEXT_PUBLIC_API_BASE=http://localhost:8000`
- If not set, frontend defaults to `http://localhost:8000`.

### Preview readiness: URL list

- `http://localhost:3000/` (Home)
- `http://localhost:3000/tasks` (Task Center)
- `http://localhost:3000/proposals` (Proposal Builder)
- `http://localhost:3000/workspace/fanatics-oem` (Workspace)
- `http://localhost:3000/chat` (Chat)
- `http://localhost:3000/history` (History)
- `http://localhost:3000/debug` (Debug Trace)
- `http://localhost:8000/api/health` (Backend Health)

### Preview readiness: check order for screenshots

1. Home
2. Task Center
3. Proposal Builder
4. Workspace
5. Chat
6. History
7. Debug

### V0.1 runtime check list

- [ ] Backend health (`GET /api/health`) returns success.
- [ ] Home shows urgent cases, alerts, KPI cards, recommended actions, in-progress work, and AI proposals.
- [ ] Task Center shows priority, due, project, status, reason, AI consult, complete/hold/detail actions.
- [ ] Proposal Builder shows customer, purpose, reference data, AI structure, PowerPoint generation, review state, next action.
- [ ] Workspace shows project summary, related tasks, artifacts, AI conversation, history, next actions.
- [ ] Chat shows only concise work guidance (`Used Data`, `Confirmation`, `Next Action`) in normal view.
- [ ] History screen is displayed and records are visible.
- [ ] Debug Trace Panel is displayed for admin/developer detailed trace only.
- [ ] `POST /api/events` is accepted.
- [ ] `backend/data/events.jsonl` appends event logs.

### Preview readiness: quick verification command

```bash
curl -X GET http://localhost:8000/api/health
curl -X POST http://localhost:8000/api/events -H "Content-Type: application/json" -d "{\"event_id\":\"ev-preview-001\",\"user_id\":\"u-demo\",\"role\":\"sales\",\"screen\":\"home\",\"action\":\"view\",\"target_type\":\"screen\",\"target_id\":\"home\",\"timestamp\":\"2026-06-30T10:00:00Z\"}"
```

### Current limitations

- Real AI Runtime is not connected yet.
- Database persistence is not connected yet.
- Authentication is not implemented yet.
- PPTX file generation is not implemented yet.
- Fine-grained permission control is not implemented yet.
- Most user data is mock data.

### Next implementation steps

1. Auth and Permission
2. Runtime integration
3. Product Analytics persistence
4. Proposal Builder real artifact generation
5. Workspace real execution linkage
6. Evaluation Event conversion pipeline

### Development policy

- Keep Frontend, Backend, and Runtime loosely coupled.
- Build UI with production assumptions from the beginning.
- Do not use Streamlit as production end-user UI.
- Always capture Product Analytics events.
- Start user-facing real tests early.

- `change_management/models.py` defines the `ChangeRequest` model.
- `change_management/repository.py` manages create/list/get/update operations.
- `change_management/lifecycle.py` manages approve/reject/implement/validate/release transitions.
- `GET /change`, `GET /change/{id}`, and the corresponding POST endpoints expose this workflow.
- Improvements created in the learning layer automatically generate a change request entry for review.

## Sprint 17: AI runtime layer extension

The AI runtime layer now provides a single orchestrator entrypoint that executes planner, workflow, answer generation, and learning log recording in sequence.

- `ai/runtime.py` adds `run_chat(message)`.
- `POST /ai/chat` accepts a user message and returns the end-to-end result.
- Runtime handles stage-aware failures and returns:
  - `success=false`
  - `error`
  - `stage` (`planner`, `workflow`, `answer`, or `learning`)

Example:

```bash
curl -X POST http://127.0.0.1:8001/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"OEMとは？"}'
```

## Sprint 18: LLM gateway layer

An LLM gateway layer was added so runtime can call an external provider through a stable interface without changing Planner, Workflow, or Learning responsibilities.

- `ai/gateway.py` provides a gateway that loads prompts from `prompts/` and dispatches inference to a provider.
- `ai/providers/base.py` defines the provider interface and shared exceptions.
- `ai/providers/openai.py` implements the OpenAI provider.
- `ai/runtime.py` now calls the gateway in the answer stage.
- Prompt templates are stored in:
  - `prompts/answer_system.txt`
  - `prompts/answer_user.txt`

Environment variables:

- `LLM_PROVIDER` (default: `openai`)
- `OPENAI_API_KEY` (required for real OpenAI calls)
- `OPENAI_MODEL` (default: `gpt-4o-mini`)
- `OPENAI_TIMEOUT_SECONDS` (default: `20`)
- `OPENAI_MAX_RETRIES` (default: `2`)

The OpenAI provider includes timeout, retry, and exception handling for authentication, transient errors, and malformed responses.

## Sprint 19: tool registry layer

A tool registry layer was added so available tools can be managed through one unified contract.

- `tools/definitions.py` defines a `ToolDefinition` with:
  - `name`
  - `description`
  - `input_schema`
  - `output_schema`
  - `handler`
- `tools/registry.py` provides `ToolRegistry` and `execute(tool_name, args)`.
- `tools/executor.py` registers built-in tools and future placeholders.
- Registered core tools:
  - `business`
  - `knowledge`
  - `system`
- Future dummy tool definitions were added:
  - `calendar`
  - `mail`
  - `image`
  - `web`

Planner now returns tool-name based targets (for example `knowledge`, `business`, `system`) instead of detailed internal function paths.
Workflow execution now calls tools via `ToolRegistry.execute(...)`.
LLM tool-calling orchestration is intentionally not implemented yet in this sprint.

## Sprint 20: memory layer

A memory layer was added so LOGS AI can reference prior conversation context without introducing vector search or automatic code changes.

- `memory/store.py` manages JSONL-based memory persistence.
  - `save_memory(record)`
  - `list_memories(limit=100)`
  - `search_memories(keyword, limit=20)`
  - `get_memory(memory_id)`
- `memory/context.py` provides `build_context(message, user_id="default")`.
  - finds related memories
  - collects recent memories
  - builds a lightweight context summary

Runtime flow was extended to:

1. build memory context
2. create plan with context
3. create workflow
4. execute workflow
5. generate answer
6. save learning log
7. save memory record

New memory APIs:

- `GET /memory`
- `GET /memory/search?q=`
- `GET /memory/{memory_id}`

`POST /ai/chat` now accepts optional `user_id`.

Memory and Learning responsibilities are separated:

- Learning: improvement and quality management
- Memory: conversation context retrieval for runtime

## Sprint 21: context layer

A new context layer was added to aggregate only the information needed for the current question before planning.

- `context/models.py` defines `ContextProviderResult` and `ContextResult`, including `selection` metadata.
- `context/registry.py` provides provider registration and default-provider discovery.
- `context/selector.py` selects and prioritizes providers based on question rules.
- `context/builder.py` executes providers and aggregates their outputs.
- `context/providers/` includes:
  - `memory.py`
  - `knowledge.py`
  - `user.py`
  - `organization.py`
  - `runtime.py`

New context APIs:

- `POST /context/build`
- `GET /context/providers`

Runtime flow now starts with context aggregation:

1. build context
2. create plan with context
3. create workflow
4. execute workflow
5. generate answer
6. save learning log
7. save memory record

Context and Memory responsibilities are distinct:

- Memory: store and retrieve long-lived conversation records
- Context: aggregate working context for the current question

Context Priority / Provider Selection:

- `context/selector.py` uses rule-based matching to decide which providers should be consulted first.
- Memory is prioritized for follow-up questions such as `前回` or `続き`.
- Knowledge is prioritized for definition-style or domain-term questions such as `とは` or `OEM`.
- User, organization, and runtime providers are prioritized when the question points to the speaker, company context, or system status.
- `context/builder.py` uses selector output unless `provider_names` is explicitly provided.
- Explicit `provider_names` always overrides selector output for backward compatibility.

Context constraints:

- Context does not execute business logic.
- Context does not update DB directly.
- LLM connection is not used in the Context layer.
- External API integration is not used in the Context layer.

## Sprint 23: intent layer

A new intent layer was added after Context so the platform can determine what the user is asking for before planning execution.

- `intent/models.py` defines `IntentResult`.
- `intent/registry.py` manages the supported intent types.
- `intent/classifier.py` classifies questions with rule-based patterns only.

New intent APIs:

- `POST /intent/classify`
- `GET /intent/types`

Intent flow now sits between context aggregation and planning:

1. build context
2. classify intent
3. create plan
4. create workflow
5. execute workflow
6. generate answer
7. save learning log
8. save memory record

Intent responsibilities:

- Intent determines what the user wants.
- Intent does not call business logic directly.
- Intent does not update the database.
- Intent does not connect to LLMs or external APIs.

## Sprint 25: validation layer

A dedicated validation layer was added to separate data-quality assurance from Runtime question-answering.

- `validation/checks.py` provides lightweight structural checks for Excel, SQLite, tables, columns, row counts, and business-table candidates.
- `validation/runner.py` provides `run_validation()` with score, status, issues, and summary output.
- `validation/report.py` stores and retrieves validation reports in JSONL.

Validation APIs:

- `POST /validation/run`
- `GET /validation/report`

Validation execution policy:

- Validation is for administrator operation, post-import verification, and periodic execution.
- Runtime does not run heavy validation checks during normal `/ai/chat` requests.
- Runtime and admin surfaces can read the latest validation report metadata.

## Sprint 26: observability layer

An observability layer was added to trace AI Runtime execution without changing business or knowledge logic.

- `observability/models.py` defines `TraceRecord` and `TraceSession`.
- `observability/tracer.py` keeps in-memory trace sessions and appends records for Runtime, Validation, Context, Intent, Planner, Workflow, Business, Knowledge, and Answer stages.
- `ai/runtime.py` now returns `trace_id` with every chat response.
- `GET /trace/{trace_id}` returns the recorded trace session for inspection.

Trace records capture:

- `trace_id`
- `timestamp`
- `layer`
- `input`
- `output`
- `elapsed_ms`
- `success`
- `error`

Trace sessions keep the full sequence for one question so the runtime path can be reviewed after execution.
- Recommended run timings: Excel updates, import completion, manual admin run, and scheduled jobs.

Example:

```bash
curl -X POST http://127.0.0.1:8001/business/query \
  -H "Content-Type: application/json" \
  -d '{"message":"売上ランキングを見せて"}'
```

## Sprint 29: Storage / Connector / Ingestion foundation

This sprint adds a cloud-ready foundation so data sources and DB backends can be swapped without changing existing Business Logic, Knowledge, Context, Intent, Planner, or Workflow responsibilities.

- Storage Layer:
  - `storage/models.py` defines `StorageConfig`.
  - `storage/repository.py` defines the repository interface.
  - `storage/sqlite.py` provides the working SQLite implementation.
  - `storage/postgres.py` provides the PostgreSQL implementation (used for the shared `public` schema).

- Connector Layer:
  - `connector/google_drive/` and `connector/google_sheets.py` provide connector implementations.
  - `connector/registry.py` provides registration and retrieval of connectors.

- Ingestion Layer:
  - `ingestion/loader.py` is the entrypoint from connector data to downstream validation/storage.
  - `ingestion/sync.py` provides `sync_source(source_name)`.

External data flow (foundation):

```text
Google Drive / Spreadsheet
  -> Connector
  -> Ingestion
  -> Validation
  -> Storage
  -> Business / AI OS
```

New APIs:

- `GET /connectors`
- `GET /connectors/{name}/files`
- `POST /ingestion/sync/{source_name}`

Data governance policy:

- Google Drive / Spreadsheet are the source-of-truth raw data locations.
- DB is the structured storage location for AI OS operations.
- GitHub stores logic, tests, and documentation only.
- Raw data (`data/excel`), SQLite artifacts (`data/sqlite`), and `.env` must remain outside version control.

## Notes

- The SQLite database is created at data/sqlite/logsys.db
- Do not commit Excel, SQLite, or other confidential data files to GitHub.

## Sprint 30: Google Drive source-management preparation

Sprint 30 extends the source-management baseline for upcoming Google Drive API integration.

- Google Drive is defined as the raw source-of-truth location.
- First synchronization targets are:
  - Logsys data (sales, product, customer, purchase, order, stock candidates)
  - Sales-authored data (sales management, customer notes, estimate management, progress management)
- Current ingestion path remains:
  - Connector -> Ingestion -> Validation -> Storage -> AI OS
- Out of scope in this sprint:
  - Email
  - PDF
  - Google Docs
  - Proposal documents

Google Drive connector structure (mock-auth ready):

- `connector/google_drive/client.py`
  - Google API client/authentication abstraction (currently mock).
- `connector/google_drive/service.py`
  - Drive folder file retrieval service and connector adapter.
- `connector/google_drive/models.py`
  - Retrieval result models for Excel and Spreadsheet files.
- `connector/google_drive/config.py`
  - Folder/auth configuration loading.

Storage synchronization flow:

```text
Google Drive Folder
  -> Connector Layer
  -> Ingestion (google_drive_importer)
  -> Storage(SQLite, full refresh replace)
  -> Business Logic
  -> AI Runtime
```

New sync API:

- `POST /storage/sync`

Example:

```bash
curl -X POST http://127.0.0.1:8001/storage/sync \
  -H "Content-Type: application/json" \
  -d '{"folder_id":"your-drive-folder-id"}'
```

Response example:

```json
{
  "status": "success",
  "folder_id": "your-drive-folder-id",
  "files": 12,
  "tables": 34,
  "sync_time": "2026-06-29T00:00:00+00:00",
  "elapsed_time": 0.42
}
```

Trace for storage sync includes:

- `sync_time`
- `folder_id`
- `files`
- `table_count`
- `elapsed_time`

Required environment variables (mock auth mode):

- `GOOGLE_DRIVE_ENABLED=true`
- `GOOGLE_DRIVE_LOGSYS_FOLDER_ID=<drive-folder-id>`
- `GOOGLE_DRIVE_SALES_FOLDER_ID=<drive-folder-id>`

Google API/OAuth settings note:

- Current implementation supports real OAuth with readonly scopes and a mock fallback for tests.
- Keep `credentials.json`, `token.json`, and any OAuth secrets out of version control.

### Run commands

Initial OAuth authentication:

```bash
python scripts/google_drive_oauth.py
```

Sync execution:

```bash
curl -X POST http://127.0.0.1:8001/api/sync \
  -H "Content-Type: application/json" \
  -d '{"folder_id":"your-drive-folder-id"}'
```

Catalog check:

```bash
curl http://127.0.0.1:8001/api/catalog
```

Sync status check:

```bash
curl http://127.0.0.1:8001/api/sync/status
```

Chat API question:

```bash
curl -X POST http://127.0.0.1:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"売上トップ10は？"}'
```

Failure handling:

- `folder_id` missing: `400` with `folder_id is required`
- `credentials.json` missing: `400` with the missing credentials path
- `token.json` missing: `400` with the missing token path
- Google API permission errors: returned as sync errors with explicit messages in `errors`
- No target files found: `400` with a `No target Excel or Spreadsheet files found...` message
- Validation failure: `400` with `Validation failed after sync`

### E2E verification checklist

1. Run OAuth initial auth script.
2. Run `POST /api/sync` with a real Drive folder ID.
3. Confirm `GET /api/catalog` returns table/sheet metadata.
4. Confirm `GET /api/sync/status` returns latest sync summary.
5. Confirm `POST /api/chat` answers `売上トップ10は？`.

Governance:

- GitHub stores logic, tests, and documentation only.
- Actual data stays in Google Drive / Cloud DB.
- No real folder IDs, credentials, or OAuth secrets are committed.

## Sprint 31: Storage-backed business query flow

Sprint 31 establishes the runtime query path that reads structured data from Storage via Business Logic before full Google Drive live sync is enabled.

- Storage is the structured data reference layer at question time.
- Business Logic reads Storage through repository abstractions.
- Runtime and Planner do not write SQL directly.
- Question handling does not access Google Drive directly.
- Google Drive is a synchronization source; Storage is the query-time source.

Flow:

```text
Google Drive (sync source)
  -> Ingestion
  -> Storage
  -> Business Logic
  -> Runtime
  -> Answer
```

## Sprint 32: Business-only answers without LLM

Sprint 32 adds a deterministic Business answer path for database/table questions.

- Business layer reads SQLite storage through repository abstractions.
- If the question can be answered by Business logic alone, the runtime uses Business Formatter output directly.
- In this path, LLM is not called.
- Query-time policy remains:
  - Google Drive is sync source only.
  - Storage is the question-time reference source.

Deterministic answer path:

```text
Repository
  -> Business
  -> Business Formatter
  -> Answer
```

## Sprint 33: Business Tool Registry and Selector

Sprint 33 organizes business capabilities as selectable tools behind a dedicated Business Tool Registry.

- Business Tool Registry manages discoverable business tools.
- Business Tool Selector chooses the right business tool from message and intent using rule-based logic.
- Business features are selected through the registry rather than hard-coded function calls in planner/workflow.
- Runtime and Planner continue to avoid direct SQL handling.
- LLM-free business questions are executed through Business Tool selection and formatter output.

Selection flow:

```text
Intent
  -> Planner
  -> Business Tool Selector
  -> Business Tool Registry
  -> Business Query
  -> Formatter
  -> Answer
```