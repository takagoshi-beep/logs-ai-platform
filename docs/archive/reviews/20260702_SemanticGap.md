# Semantic Gap Report & Phase 11 Roadmap

**Date:** 2026-07-02  
**Phase:** 10, Step 4  
**Status:** Gap Analysis Complete; Recommendations Ready

---

## Executive Summary

Real Logsys DB supports 5 of 10 business Semantics at **100% coverage**, with 4 partially supported and 1 at **critical gap**. Gap analysis reveals:

- **3 blocking issues** prevent Project/Case queries (SEM-009)
- **2 definition gaps** prevent OEM/Retail distinction (SEM-001, SEM-002)
- **4 candidates** for new Semantics (SEM-011 through SEM-014) exist in real DB

**Impact:** 1 of 4 sample queries fully answerable; 2 answerable with conditions; 1 blocked.

---

## Critical Gaps

### Gap #1: 案件 Master Table Missing (SEM-009) — SEVERITY: CRITICAL

**What's Missing:**
Real database has **NO master table for projects/cases**. Only 集計 (aggregation summary) exists with project-level totals.

**Current State:**
```
集計 table (16,705 rows):
├─ 案件名 (project name) ← stored as OUTPUT aggregation label only
├─ 顧客id, 顧客名
├─ 案件売上, 案件粗利 (totals only)
└─ [NO: status, deadline, creation date, project type, assigned staff, lifecycle]
```

**What Should Exist (for SEM-009):**
```
案件 master table (recommended):
├─ 案件id (PK, unique project identifier)
├─ 案件名 (project name)
├─ 顧客id (FK to 顧客)
├─ 案件種別 (OEM/Retail/Gift/Wholesale/etc) ← links to SEM-001/SEM-002
├─ ステータス (計画中→進行中→納品待ち→完了) ← lifecycle tracking
├─ 期限 (project deadline) ← critical for SEM-007/priority queries
├─ 担当者id (assigned staff)
├─ 作成日 (project start date)
├─ 完了日 (project end date)
├─ 備考 (notes, risk flags, etc.)
└─ [timestamps: 作成日時, 更新日時, 作成者, 更新者]
```

**Why It Matters:**
- Query "Fanatics案件の状況" (Q2) cannot retrieve status → **Pipeline broken**
- Query "本日優先案件" (Q3) cannot retrieve deadline → **Pipeline broken**
- SEM-001/SEM-002 differentiation depends on 案件種別 field → **OEM/Retail logic blocked**

**Blocking Queries:**
- Q2: Fanatics案件状況 (needs project status)
- Q3: 優先案件 (needs deadline)
- Any project-centric reasoning query

**Recommendation:**
**CREATE 案件 master table in Phase 11 Step 1.**  
Coordinate with:
- 顧客 table (FK relationship)
- 売上 table (1:many; sales tied to project)
- 仕入 table (1:many; procurement tied to project)
- 集計 table (use as validation/audit trail)

**Phase 11 Implementation Sketch:**
```sql
CREATE TABLE 案件 (
    id TEXT PRIMARY KEY,  -- unique project ID
    顧客id TEXT NOT NULL,
    案件名 TEXT NOT NULL,
    案件種別 TEXT NOT NULL,  -- OEM/Retail/Gift/Wholesale (enum)
    ステータス TEXT NOT NULL,  -- 計画中/進行中/納品待ち/完了
    期限 DATE,
    担当者id TEXT,
    作成日時 TIMESTAMP,
    更新日時 TIMESTAMP,
    作成者 TEXT,
    更新者 TEXT,
    備考 TEXT,
    FOREIGN KEY (顧客id) REFERENCES 顧客(id),
    FOREIGN KEY (担当者id) REFERENCES 社員(id)
);
```

---

### Gap #2: OEM vs Retail Classification Logic Undefined (SEM-001, SEM-002) — SEVERITY: HIGH

**What's Missing:**
Current DB has 集計.分類 column that *might* indicate OEM vs Retail, but **no formal definition** of how to distinguish them.

**Current State:**
```
集計.分類 values observed: [unclear from schema only]
Problem: No business rule defined; AI cannot infer OEM vs Retail without explicit rule
```

**Blocking Queries:**
- Q1: OEM粗利 (needs OEM identification rule)
- Coverage falls from 100% to ~60% for gross profit queries

**Why It Matters:**
- Reasoning pipeline needs explicit rule to classify transactions
- Current semantic_registry.md lists SEM-001/SEM-002 as "Pending" — awaiting rule definition

**Questions for Product Owner:**
① How is OEM案件 differentiated from Retail案件 in current business practice?  
   - By customer segment (OEM-focused customers vs retail customers)?
   - By product type (custom-designed vs off-the-shelf)?
   - By order characteristics (custom specifications vs catalog order)?
   - By contract type (dedicated supply contract vs ad-hoc)?

② If 集計.分類 is the indicator, what are the valid values and their meanings?

③ Are there edge cases (e.g., "sample order", "trial run") that are neither pure OEM nor pure Retail?

**Recommendation:**
**DOCUMENT classification rule in Phase 11 Step 2.**  
Create decision logic mapping real DB values to SEM-001/SEM-002 before reasoning pipeline is enabled for Q1.

**Phase 11 Implementation Sketch:**
```python
def classify_case_type(case_row) -> str:
    """
    Map real DB values to SEM-001 (OEM) vs SEM-002 (Retail)
    
    Pseudo-logic pending business rule confirmation:
    - If 集計.分類 == 'OEM' → SEM-001
    - Elif 集計.分類 == 'Retail' → SEM-002
    - Else if customer.顧客分類 == 'OEM-Partner' → SEM-001
    - Else if product.商品分類 == 'Catalog' → SEM-002
    - Else → unclear (flag for human review)
    """
    pass  # await Product Owner definition
```

---

### Gap #3: Order Confirmation Concept Fragmented (SEM-004) — SEVERITY: MEDIUM

**What's Missing:**
SEM-004「受注」conceptually means "order confirmation from customer," but real DB doesn't have unified representation:
- 売上 table tracks transaction status (有効/キャンセル/テスト) — **revenue side**
- 発注依頼 table tracks vendor PO status — **procurement side**
- No table for "customer order acknowledgment" state

**Current State:**
```
Terminology Problem:
  Japanese "発注" = "place order (to vendor)"
  Japanese "受注" = "receive order (from customer)"
  
  Real DB has:
  ├─ 売上.ステータス = customer order outcome (valid/cancelled/test)
  ├─ 発注依頼 = vendor purchase order (confusing terminology)
  └─ [NO: explicit customer order acknowledgment table]
```

**Blocking Queries:**
- Not currently blocking Q1-Q4, but implicit in order lifecycle

**Why It Matters:**
- Semantic definition says SEM-004 starts fulfillment flow
- AI cannot track order states (quote → confirmed → production → delivery) without master table
- May become critical if future queries ask "未受注案件は何件ですか" (how many unconfirmed orders?)

**Recommendation:**
**CLARIFY SEM-004 definition in Phase 11 Step 3.**  
Decision: Does 受注 mean...
- Option A: Customer order status only (revenue-side in 売上)?
- Option B: Unified order lifecycle from customer through vendor (requires new master table)?

If Option B, create new table:
```sql
CREATE TABLE 受注 (
    id TEXT PRIMARY KEY,
    顧客id TEXT NOT NULL,
    案件id TEXT NOT NULL,
    注文番号 TEXT,
    受注日 DATE,
    ステータス TEXT,  -- 提案中/受注確定/生産中/出荷済/完了
    引き合い額 DECIMAL,
    受注額 DECIMAL,
    ...
    FOREIGN KEY (顧客id) REFERENCES 顧客(id),
    FOREIGN KEY (案件id) REFERENCES 案件(id)
);
```

---

## Secondary Gaps

### Gap #4: Delivery Modeled as Date Only (SEM-007) — SEVERITY: LOW

**What's Missing:**
納品 (delivery) is captured only as 売上.納品伝票日 (delivery date). No discrete delivery event table.

**Impact:**
- Cannot query delivery-specific issues (partial delivery, quality hold, etc.)
- Low priority for current Reasoning Pipeline (only Q3 references delivery implicitly)

**Recommendation:** Optional enhancement for Phase 12 if business needs granular delivery tracking.

---

### Gap #5: Limited Delivery Date Field (SEM-007) — SEVERITY: LOW

**What's Missing:**
SEM-007 definition refers to 納期 (deadline), but real DB only tracks 納品伝票日 (actual delivery date). Deadline field (expected delivery date) is in proposed 案件 table (Gap #1).

**Impact:**
- Can answer "when was it delivered?" but not "was it on-time?"
- Resolved by Gap #1 (案件 master table includes 期限)

---

## Data Quality Issues (Non-Blocking)

### Issue #1: Customer Name Variations
**Location:** 顧客.顧客名称  
**Issue:** Japanese business names may have variations (full name, abbreviated name, alternate kanji)  
**Impact:** Customer lookup (SEM-003) requires name normalization  
**Recommendation:** Use 顧客.id (PK) for canonical matching, not name text

### Issue #2: Product Classification Ambiguity
**Location:** 商品.商品分類, 商品.事業分類  
**Issue:** Two parallel classification schemes exist; unclear which indicates OEM vs Retail  
**Impact:** SEM-001/SEM-002 classification may need both fields  
**Recommendation:** Clarify with Product Owner during Gap #2 resolution

### Issue #3: Status Code Standardization
**Location:** 売上.ステータス, 仕入.ステータス, 発注依頼.ステータス  
**Issue:** Each table may have different status values and meanings  
**Impact:** Reasoning pipeline needs status normalization layer  
**Recommendation:** Create status code registry (could become SEM-014)

---

## New Semantic Candidates from Real DB

**SEM-011: 仕入先 (Vendor/Supplier)**
- Real DB Table: 取引先 (2,148 records)
- Usage: Procurement counterparty in SEM-006 transactions
- Recommendation: Add formal Semantic if vendor analysis becomes important

**SEM-012: 担当者 (Staff / Assignment)**
- Real DB Evidence: 集計.社員id, 集計.営業事務id, 顧客担当者 table
- Usage: Project and customer assignments
- Recommendation: Add if resource allocation queries become needed

**SEM-013: 会計期間 (Accounting Period)**
- Real DB Evidence: 期 column in all transaction tables
- Usage: Period-based reporting (month-end close, variance analysis)
- Recommendation: Add if compliance/period-bound reporting needed

**SEM-014: ステータス (State/Status Machine)**
- Real DB Evidence: ステータス columns across 売上, 仕入, 発注依頼
- Usage: Lifecycle state transitions
- Recommendation: Add if state-based queries needed ("何件が進行中ですか")

---

## Phase 11 Implementation Roadmap

### Phase 11 Step 1: Create 案件 Master Table (CRITICAL)
**Duration:** 3-5 days  
**Scope:**
- Design 案件 table schema
- Define case lifecycle (ステータス transitions)
- Implement FK relationships to 顧客, 売上, 仕入, 担当者
- Migrate existing project names from 集計 as seed data
- Update reasoning_pipeline.py to query 案件 master

**Verification:**
- Q2 (Fanatics案件) returns status ✓
- Q3 (優先案件) returns deadline ✓

---

### Phase 11 Step 2: Define OEM vs Retail Classification (HIGH)
**Duration:** 1-2 days  
**Scope:**
- Product Owner workshop to define classification rule
- Document rule in knowledge/semantic/oem_project.md and retail_project.md
- Create mapping logic in reasoning_pipeline.py
- Test Q1 (OEM粗利) classification accuracy

**Verification:**
- Q1 (OEM粗利) correctly filters by case type ✓

---

### Phase 11 Step 3: Clarify SEM-004 受注 Definition (MEDIUM)
**Duration:** 1-2 days  
**Scope:**
- Product Owner decision: Option A (revenue-side only) or Option B (unified order lifecycle)
- If Option B: Design 受注 master table
- Update semantic_registry.md with clarified definition

**Verification:**
- SEM-004 integration with reasoning pipeline ✓

---

### Phase 11 Step 4: Add New Semantics (OPTIONAL)
**Duration:** 2-3 days  
**Scope:**
- Create SEM-011 (仕入先), SEM-012 (担当者) if business prioritizes
- Create SEM-013, SEM-014 for reporting needs
- Update reasoning_pipeline.py if new queries require these

---

## Unmapped DB Tables

**Non-Business Tables (Metadata/Sync):**
- gdrive_* tables (Google Drive sync infrastructure)
- import_* tables (data import tracking)
- validation_* tables (data validation logs)
- schema_registry, sqlite_sequence (SQLite metadata)

**Recommendation:** Keep as-is; no Semantic mapping needed.

---

## Updated Semantic Coverage Forecast

### After Phase 11 Step 1 (案件 Master):
```
SEM-009 (案件):        50% → 100% ✓
Overall Coverage:    68% → 78%
Queries Answerable:  Q4 (100%)
                   + Q2 (100% with case status) → was 50%
                   + Q3 (100% with deadline) → was 50%
```

### After Phase 11 Step 2 (OEM/Retail Rule):
```
SEM-001 (OEM案件):    60% → 100% ✓
SEM-002 (Retail案件): 60% → 100% ✓
Overall Coverage:    78% → 88%
Queries Answerable:  Q1 (100% with classification) → was 75%
```

### After Phase 11 Step 3 (SEM-004 Clarification):
```
SEM-004 (受注):       70% → 100% ✓
Overall Coverage:    88% → 98%
Queries Answerable:  All 4 sample queries at 100%
```

---

## Blockers for Reasoning Pipeline Production Use

| Blocker | Impact | Phase 11 Step | Priority |
|---------|--------|--------------|----------|
| 案件 master missing (Gap #1) | Q2, Q3 cannot run | 1 | **CRITICAL** |
| OEM vs Retail undefined (Gap #2) | Q1 50-75% coverage | 2 | **HIGH** |
| SEM-004 unclear (Gap #3) | Future order queries | 3 | **MEDIUM** |

**Decision Point:** Phase 10 Step 5 will determine if Phase 11 is approved to proceed.

---

## Recommendations to Product Owner

**For immediate decision:**

**Q1: Should we proceed with Phase 11 implementation?**
Recommendation: YES — all three critical/high gaps are solvable within 5-7 days of Product Owner input.

**Q2: Which Phase 11 steps are highest priority?**
Recommendation:  
1. Step 1 (案件 master) — UNBLOCKS Q2 & Q3
2. Step 2 (OEM/Retail rule) — IMPROVES Q1 coverage
3. Step 3 (SEM-004) — OPTIONAL; not blocking sample queries

**Q3: Should we wait for Phase 11 before connecting reasoning pipeline to real DB?**
Recommendation: **NO** — Q4 (売上首位顧客) can run immediately on real DB (100% coverage). Can enable Q4 in reasoning_pipeline.py now while waiting for Phase 11 gaps to close.

---

**Prepared for:** Product Owner Review  
**Next Step:** Phase 10 Step 5 — Developer Verification Report & Final Recommendations
