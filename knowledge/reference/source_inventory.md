# Source Inventory — Knowledge Base Foundation

**Date:** 2026-07-01  
**Status:** v0.1 (Initial Inventory)  
**Purpose:** Catalog all reference data, documentation, and business materials available for AI OS Knowledge Layer

---

## Overview

This inventory maps all data sources, reference materials, and business documents that feed the Knowledge Layer. It distinguishes between:
- **Primary Sources**: Canonical business data (logsys.db, verified rules)
- **Reference Materials**: Architecture & business design documentation
- **Structured Data**: Schemas, metadata, dimension tables
- **Operational Knowledge**: Patterns, templates, learned rules

---

## 1. Internal Database — logsys.db (289 MB)

### Source Type
- **Primary** — Production/historical business data
- **Format**: SQLite3 (encrypted/synced)
- **Freshness**: Updated via gdrive_sync_registry (last full sync: 2026-06-29)
- **Trust Level**: High (source of truth for business facts)
- **Access**: Read-only (via backend ProjectService + repository)

### Tables Present
- 21 total tables (including metadata & sync tables)
- Business data tables:
  - `仕入` (Purchases/Procurement): Import records with line-item detail
  - (Japanese table names present but encoded; actual schema needs runtime inspection)
- Metadata tables:
  - `gdrive_sync_registry`: Tracks Google Drive sync history
  - `gdrive_source_catalog`: Catalog of imported files & sheets
  - `import_registry`: Data import audit trail
  - `table_schema_registry`: Column definitions & metadata

### Key Business Entities
- Customers (顧客)
- Products (商品)
- Sales records (売上)
- Purchase records (仕入)
- Staff/Sales people (担当者)
- Suppliers (仕入先)
- Facilities/Factories (工場)

### Usage Notes
- **For AI OS**: Used by `ProjectService._query_projects_from_db()` to load real case studies
- **Current State**: Not yet connected to consultation engine; mock data (frontend/lib/mock-data.ts) used for Phase 5-1
- **Future**: Will feed real data queries once integration planned
- **Limitation**: 289 MB size requires pagination for large analyses

---

## 2. Business Rules & Knowledge — reference/01_business/

### Files
- `verified_business_rules.md` (2000+ lines)
- `README.md` (purpose statement)

### Content Scope

#### Knowledge Architecture (Layers)
- Semantic Catalog
- Knowledge Source Layer (Internal + External)
- Memory Layer (types, metadata)
- Capability Library (7 categories)
- Business Context Resolution

#### Verified Rules (70+ rules, all user-confirmed)
- **BR-SALES-STANDARD-001**: Sales aggregation filter criteria
- **BR-KNOWLEDGE-SOURCE-LAYER-027**: Internal vs External source classification
- **BR-MEMORY-LAYER-032**: Memory / Knowledge separation
- **BR-CAPABILITY-LAYER-018**: Two-layer architecture (Knowledge + Capability)
- **BR-TASK-PLANNING-015**: Business Task scope (Analysis/Proposal/Document/Monitoring/Workflow/Search/Explanation)
- **BR-CONTEXT-NORMALIZATION-014**: Business ambiguous language normalization (粗利/売上/利益 etc.)

#### Entity Resolution Rules (6 rules)
- Canonical Key priority
- No-guess policy
- Error type classification
- Fallback to display name only when Canonical Key unavailable

#### Business Concepts (40+)
- 予算 (Budget) / 予定 (Plan) / 発注 (Purchase Order) / 実績 (Actual)
- 売上実績 / 仕入実績 / 費用実績
- 粗利 (Gross Profit: estimated, actual, per-staff)
- 原価 (Cost: logical, actual)
- 担当者粗利 (Staff-attributed profit)

#### Business KPIs (7 core metrics)
- 売上 (Sales)
- 仕入金額 (Purchase Amount)
- 輸入諸掛 (Import Surcharges)
- 概算粗利 (Estimated Gross Profit)
- 実際粗利 (Actual Gross Profit)
- 営業担当費用 (Sales Staff Expense)
- 担当者粗利 (Staff-attributed Profit)

#### Business Grain (7 dimensions)
- 担当者, 商品, 顧客, ブランド, 工場, 会社, 期間

#### Analysis Purpose (5 targets)
- 担当者評価 (Staff Evaluation)
- 商品分析 (Product Analysis)
- ブランド分析 (Brand Analysis)
- 顧客分析 (Customer Analysis)
- 工場分析 (Factory Analysis)

#### Validation Rules (100+ validation checks)
- SQL generation gates
- Entity Resolution failure handling
- Meaning Resolution completeness
- Capability risk guardrails
- Gross profit type disambiguation
- Cost allocation rules

### Usage Notes
- **For AI OS**: Primary reference for all business rule enforcement, validation, and knowledge mapping
- **Trust Level**: High (all verified by user on 2026-06-30)
- **Status**: Complete for current phase; design for future expansion to Proposal/Document/Monitoring intents
- **Maintenance**: Version-controlled; adheres to Blueprint v0.1
- **Integration**: Already being used by evaluation test suite and runtime validation

---

## 3. Architecture & Blueprint — docs/blueprint/ & docs/architecture/

### Blueprint
- **File**: `AI_OS_BLUEPRINT_v0.1.md`
- **Status**: CANONICAL DESIGN STANDARD (2026-06-30)
- **Audience**: Developers, Architects, AI Engineers
- **Content**:
  - 12 Core Principles (Project First, Capability Driven, Human Governed, etc.)
  - AI OS Dictionary (30+ canonical terms)
  - Two-Axis System Architecture (Project Understanding × Business Execution)
  - Project Aggregate Standard
  - Capability Standard
  - Learning Standard (Operational vs Governed)
  - Governance Standard
  - Trace & Activity Feed Standard
  - UI Philosophy
  - Implementation Roadmap

### Architecture Audit Reports
- `FINAL_AUDIT_REPORT.md`: Comprehensive health check (2026-06-25)
- `DUPLICATION_AND_GAP_ANALYSIS.md`: Current state gaps vs Blueprint
- `MEMORY_LEARNING_GOVERNANCE_PREFERENCE_SEPARATION.md`: Layer isolation design
- `DESIGN_PRINCIPLE_REVIEW.md`: Principles compliance check
- `ARCHITECTURE_HEALTH_CHECK.md`: Technical baseline

### Design Documents
- `LEARNING_LAYER_REDESIGN.md`: Operational vs Governed distinction
- `CAPABILITY_REGISTRY_DESIGN.md`: Capability definition schema
- `LEARNING_GOVERNANCE_INTEGRATION_DESIGN.md`: Learning workflow
- `PROJECT_DOMAIN_MODEL_REPORT.md`: Project aggregate structure
- `PROJECT_EVENTS_REPORT.md`: Event taxonomy

### Usage Notes
- **For AI OS**: Normative reference; all implementation must conform to Blueprint
- **Trust Level**: Very High (architecture authority)
- **Integration**: Links to business rules; provides intent/task/capability taxonomy
- **Current State**: Phase 3-4 implementation in progress

---

## 4. Database Schema & Sync — reference/02_database/

### Files
- `README.md`: Database context & sync overview
- `sync/sync.py`: Google Drive ↔ SQLite sync orchestration

### Content
- SQLite schema documentation (generated from logsys.db PRAGMA)
- Google Drive file catalog & sync history
- Data transformation rules (Excel → SQLite)
- Import audit trail

### Usage Notes
- **For AI OS**: Reference for understanding table structure, column naming, data types
- **Status**: Schema stable; sync process ongoing
- **Limitation**: Schema documentation may lag actual schema; canonical source is PRAGMA output at runtime

---

## 5. Sample Data & Queries — reference/04_queries/ & reference/06_samples/

### Query Examples
- SQL samples for common analysis patterns
- Gross profit queries (all 3 variants: estimated, actual, staff-attributed)
- Sales aggregation with filters
- Entity matching patterns

### Sample Datasets
- Historical analysis results (reports)
- Example proposal structures
- Task templates

### Usage Notes
- **For AI OS**: Reference implementation patterns; not to be copied as-is
- **Status**: Partial coverage; being extended as new analysis patterns emerge
- **Caveat**: Sample queries must be validated against current schema before execution

---

## 6. Reference & Application — reference/03_application/

### Streamlit Debug UI
- `streamlit/app.py`: Debug dashboard with working analysis patterns
- Uses reference/01_business rules in practice
- Demonstrates Entity Resolution, Meaning Resolution, validation patterns

### UI Connection Documentation
- `docs/architecture/design/UI_CONNECTION_IMPLEMENTATION.md`: Frontend ↔ Backend API contract

### Usage Notes
- **For AI OS**: Practical reference for how rules translate to executable logic
- **Trust Level**: Medium (debug-only; not production)
- **Value**: Shows working implementations of complex rules (cost allocation, gross profit variants)

---

## 7. Product & Governance — reference/99_archive/ & docs/decisions/

### Architecture Decision Records (ADRs)
- `ADR-0001-layered-architecture.md`: Two-layer (Knowledge + Capability) justification
- `ADR-0002-memory-learning-separation.md`: Memory vs Knowledge distinction
- `ADR-0003-tool-registry.md`: Capability registry design
- `ADR-0004-llm-does-not-directly-change-business-logic.md`: Governance principle

### Usage Notes
- **For AI OS**: Historical decisions & reasoning; provides context for architecture choices
- **Status**: Immutable archive; no longer updated (evolved into Blueprint v0.1)
- **Value**: Understand "why" behind current design

---

## 8. Frontend Mock Data — frontend/lib/mock-data.ts

### Content
- 4 demo projects:
  - Fanatics OEM (id: fanatics-oem)
  - BEAMS Retail (id: beams-retail)
  - GOLDWIN Campaign (id: goldwin-campaign)
  - newhattan sales kit (id: newhattan-sales-kit)
- Task recommendations (with Japanese dates, owners, priorities)
- Past consultation history

### Usage Notes
- **For AI OS**: Sprint 4 finalized demo data; used by Phase 5-1 consultation MVP
- **Status**: Hardcoded; not persistent
- **Integration**: UI routes (workspace, chat) use this data for now
- **Future**: Will be replaced by real logsys.db data in Phase 5-2+

---

## 9. Excel/CSV Reference Data — data/excel/

### Files
- `ログシスExcels連携_v3_0813修正_20260626.xlsx`: Master data specification
  - Customer dimension
  - Product dimension
  - Staff dimension
  - Supplier dimension
  - Factory dimension

### Usage Notes
- **For AI OS**: Source of dimension tables; drives Entity Resolution semantic catalog
- **Status**: Synced to logsys.db via import process
- **Update Frequency**: Manual sync (last: 2026-06-26)
- **Use Case**: Validate entity names, canonical codes, display names

---

## 10. Conversation & Feedback Data — data/conversation/, data/memory/, data/validation/

### Conversation Logs
- Stored evaluation test cases (user input, expected output, actual output)
- Feedback corrections
- Failed cases (for regression prevention)

### Memory Records
- User corrections to system outputs
- Pattern observations (e.g., "BEAMS prefers growth focus")
- Learned templates & variations

### Validation Reports
- Compliance checks (e.g., "Gross profit type specified?" for each query)
- Schema & data quality checks

### Usage Notes
- **For AI OS**: Historical feedback & learning; used for evaluation & continuous improvement
- **Status**: Growing; populated during Phase 4-5 operations
- **Integration**: Feeds Evaluation Suite; informs Knowledge updates

---

## 11. LOGS AI OS Code — backend/services/, backend/business/, frontend/

### Implementations
- `backend/services/project_service.py`: Loads project aggregates from logsys.db
- `backend/business/today_actions.py`: Demonstrates business logic (KPI calculation, state determination)
- `backend/api/router.py`: API contract implementation
- `frontend/lib/api-client.ts`: Frontend API bindings

### Usage Notes
- **For AI OS**: Canonical runtime implementation; source of truth for capabilities
- **Status**: Phase 4 working; extending to Phase 5
- **Integration**: Direct link between Knowledge and Capability execution

---

## AI Readiness Matrix

| Source | Type | Completeness | Trust | Freshness | Integration | Priority |
|--------|------|--------------|-------|-----------|-------------|----------|
| logsys.db | Database | 70% | High | Real-time | Medium | 1 |
| Verified Rules | Rules | 90% | Very High | Static | High | 1 |
| Blueprint v0.1 | Architecture | 85% | Very High | Static | High | 1 |
| Mock Data | Demo | 100% | High | N/A | High | 2 |
| Excel Catalog | Dimensions | 80% | High | 2026-06-26 | Medium | 2 |
| Queries Reference | Patterns | 60% | Medium | Static | Medium | 3 |
| Design Docs | Context | 100% | High | Static | Low | 3 |

---

## Prioritized Integration Pipeline

### Phase 5-2 (Immediate)
- [ ] Extract Business Dictionary from verified_business_rules.md
- [ ] Map Data Model (Sales, Purchase, Budget tables → KPIs → Business Concepts)
- [ ] Create Query Patterns (common questions → SQL generation logic)
- [ ] Document Entity Resolution semantic catalog (canonical names, codes, aliases)

### Phase 5-3 (Mid-term)
- [ ] Connect logsys.db real data to consultation engine
- [ ] Implement Meaning Resolution (Entity/KPI/Time/Grain determination)
- [ ] Build Knowledge Retrieval Interface (stubs for Internal sources)
- [ ] Evaluation test suite integration

### Phase 5-4+ (Future)
- [ ] External source integration (Gmail, Slack, Spreadsheet, Web)
- [ ] Memory Layer full connection (learned patterns, corrections, proposals)
- [ ] Governance approval workflows
- [ ] Monitoring & learning feedback loops

---

## Known Gaps & Open Questions

### Data Gaps
- OQ-1: Exception business rules (billing, receivables, audit) — business rules exist but implementation incomplete
- OQ-2: Full schema for all Japanese-named tables — need runtime schema inspection
- OQ-3: Historical performance/execution data — not yet captured in logsys.db

### Integration Gaps
- OQ-4: Memory Layer runtime connection — designed but not implemented
- OQ-5: External source connectors (Gmail, Slack, Spreadsheet) — stubs exist in Blueprint, not implemented
- OQ-6: Evaluation suite integration — partial; regression test cases incomplete

### Knowledge Gaps
- OQ-7: Grain constraint enforcement — rules documented but validator not yet built
- OQ-8: Cost allocation rules per Analysis Purpose — rules defined but no executor
- OQ-9: Time basis mapping per report — framework exists but incomplete

---

## Maintenance & Evolution

- **Owner**: AI OS Architecture Team
- **Update Frequency**: Quarterly (at blueprint version bumps)
- **Review Trigger**: Architecture changes, new capability addition, failed evaluations
- **Approval**: Architecture Review Board (before Blueprint update)

**Last Updated:** 2026-07-01  
**Next Review:** 2026-10-01
