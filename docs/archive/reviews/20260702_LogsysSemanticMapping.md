# Phase 10 Step 2: Logsys Real DB → Semantic Mapping

**Date:** 2026-07-02  
**Status:** Analysis Complete  

---

## Executive Summary

Real Logsys database (289MB, 21 tables) has been analyzed and mapped to Semantic Registry (SEM-001 through SEM-010). **Key Finding: 案件 (SEM-009) has no dedicated master table — only aggregation table exists.**

| SEM ID | Business Concept | DB Support | Status | Coverage |
|--------|------------------|-----------|--------|----------|
| SEM-001 | OEM案件 | 集計 + 売上/仕入 | ⚠️ Partial | ~60% |
| SEM-002 | Retail案件 | 集計 + 売上/仕入 | ⚠️ Partial | ~60% |
| SEM-003 | 顧客 | 顧客 (2,738 rows) | ✓ Direct | 100% |
| SEM-004 | 受注 | 売上 (subset) | ⚠️ Inferred | ~70% |
| SEM-005 | 売上 | 売上 (199,512 rows) | ✓ Direct | 100% |
| SEM-006 | 仕入 | 仕入 (44,855 rows) | ✓ Direct | 100% |
| SEM-007 | 納品 | 売上.納品伝票日 | ⚠️ Partial | ~80% |
| SEM-008 | 粗利 | 集計.案件粗利 | ✓ Direct | 100% |
| SEM-009 | 案件 | 集計 (16,705 rows) | ⚠️ Aggregation Only | ~50% |
| SEM-010 | 商品 | 商品 (10,236 rows) | ✓ Direct | 100% |

**Business Tables: 10 of 11 support Semantics directly or partially.**  
**Critical Gap: 案件 master table missing (Phase 8 confirmed).**

---

## Table-by-Table Mapping

### Core Transaction Tables

#### 売上 (Sales) — 199,512 records
**Maps to:** SEM-005 (売上), SEM-007 (納品), SEM-004 (受注・subset)

**Key Columns:**
- 期 (period)
- id (primary key)
- ステータス (status: 有効/キャンセル/テスト)
- 納品伝票日 (delivery date)
- 専用伝票番号 (slip number)
- 顧客締め日, 顧客入力日 (customer transaction dates)
- 事業部門 (business division)
- 売上高, 売上原価 (revenue, cost)
- 実績数量, 実績金額 (actual quantity, amount)

**Coverage:** 100% for SEM-005 (売上) — complete revenue recognition data  
**Gap:** No explicit case/project ID; grouped only by period + customer + slip

---

#### 仕入 (Procurement) — 44,855 records
**Maps to:** SEM-006 (仕入), SEM-008 (粗利・calc input)

**Key Columns:**
- 期 (period)
- id (primary key)
- ステータス (status)
- 仕入確定フラグ (procurement confirmed flag)
- 仕入確定日, 仕入入力日
- 取引先区分 (vendor classification)
- 事業部門 (business division)
- 仕入金額, 仕入原価 (procurement amount, cost)
- 実績数量 (actual quantity)

**Coverage:** 100% for SEM-006 (仕入)  
**Design:** Procurement cost data is directly available; can support gross profit (SEM-008) calculation

---

#### 商品 (Product Master) — 10,236 records
**Maps to:** SEM-010 (商品)

**Key Columns:**
- 期 (period)
- id (primary key)
- logs_code, sample_code (product codes)
- 商品名 (product name)
- 型番 (model number)
- 色 (color), サイズ (size)
- 定価, 原価 (list price, standard cost)
- 商品分類, 事業分類 (product classification, business classification)

**Coverage:** 100% for SEM-010 (商品)  
**Design:** Product variants are tracked by model + color + size combination; aligns with SEM-010 definition

---

#### 顧客 (Customer Master) — 2,738 records
**Maps to:** SEM-003 (顧客)

**Key Columns:**
- 期 (period)
- id (primary key)
- 顧客名称 (customer name)
- 顧客カナ (phonetic name)
- 顧客分類 (customer classification)
- 事業規模, 取引傾向分類 (business size, trading pattern)
- web問い合わせid

**Coverage:** 100% for SEM-003 (顧客)  
**Design:** Customer master is fully independent; supports canonical customer identification for SEM-004/SEM-005

---

### Aggregation & Classification Tables

#### 集計 (Aggregation Summary) — 16,705 records
**Maps to:** SEM-001 (OEM案件), SEM-002 (Retail案件), SEM-008 (粗利), SEM-009 (案件)

**Key Columns:**
- 分類 (classification: may indicate OEM vs Retail)
- 顧客id, 顧客名 (customer reference)
- 社員id, 社員名, 営業事務id (staff assignment)
- 案件名 (project name) ← **Critical: Only place "case/project" concept is stored**
- 量産数量_型 (production quantity)
- 案件売上 (project sales)
- 案件粗利 (project gross profit)
- ①〜④ operational cost components

**Coverage:**  
- SEM-009 (案件): **50%** — Has project names & sales/margin aggregates, but no creation date, status, or independent lifecycle tracking
- SEM-001/SEM-002: **~60%** — "分類" column *may* indicate case type, but logic is undefined
- SEM-008 (粗利): **100%** — Direct project-level gross profit available

**Critical Finding:** No dedicated projects/cases master table. 集計 is **aggregation-only** — cannot query individual case details (creation date, status transitions, milestones, etc.). Case "identity" exists only as label in aggregation output.

---

#### コード (Code Registry) — 199 records
**Maps to:** No Semantic; metadata reference table

**Usage:** Central registry for business codes (customer codes, product codes, vendor codes, etc.)

---

### Supporting Tables

#### 発注依頼 (Purchase Order Request) — 34,733 records
**Maps to:** SEM-004 (受注・partial), SEM-006 (仕入・upstream)

**Key Columns:**
- 期 (period)
- id (primary key)
- ステータス (status: draft/confirmed/cancelled)
- 発注依頼日時, po発行日時 (request date, PO issue date)
- po_no (PO number)
- 発注種別 (order type)
- 数量, 金額 (quantity, amount)

**Coverage:**  
- **SEM-004 (受注)**: ~50% — Tracks order requests but doesn't clearly distinguish between customer orders (SEM-004) vs vendor purchase orders. Terminology ambiguity: "発注" in Japanese can mean both "place order" (to vendor) and "order received" (from customer)
- **SEM-006 (仕入)**: ~80% — Upstream procurement flow well-documented

**Gap:** No clear linkage between customer 受注 (purchase request from customer) and vendor 発注 (purchase order to vendor). May require mapping through 売上 → 集計 → 仕入 chain.

---

#### 仕入諸掛 (Procurement Incidentals) — 21,390 records
**Maps to:** SEM-008 (粗利・cost component)

**Purpose:** Supplementary procurement costs (freight, tariffs, etc.) that adjust base procurement cost for SEM-008 gross profit calculation.

---

#### 顧客担当者 (Customer Contact Person) — 3,816 records
**Maps to:** No dedicated Semantic; organizational metadata

**Purpose:** Staff assignment to customers; supports SEM-003 (顧客) context but not primary business concept.

---

#### 取引先 (Trading Partners / Vendors) — 2,148 records
**Maps to:** Vendor side of business; not directly Semantic

**Purpose:** Vendor master complementing SEM-006 (仕入) procurement data.

---

## Semantic Mapping Detail

### ✓ Fully Supported (100% coverage)

**SEM-003 (顧客):** Customer Master (顧客) table  
- Direct 1:1 mapping
- All required fields present (name, classification, contact info)
- No gaps identified

**SEM-005 (売上):** Sales Line Items (売上) table  
- 199,512 records with complete transaction data
- Status filtering capability (有効/キャンセル/テスト)
- Revenue recognition dates captured

**SEM-006 (仕入):** Procurement Master (仕入) table  
- 44,855 records with cost data
- Procurement status & confirmation flags
- Supports gross profit calculation

**SEM-008 (粗利):** Gross Profit in Aggregation (集計.案件粗利)  
- Pre-calculated at project level
- Components available for audit trail
- Three variants implicitly supported (actual/estimated/staffassigned)

**SEM-010 (商品):** Product Master (商品) table  
- 10,236 SKUs with model+color+size distinction
- Cost/price data available
- Product classification codes present

---

### ⚠️ Partially Supported (50-80% coverage)

**SEM-001 (OEM案件) & SEM-002 (Retail案件):**  
- Location: 集計.分類 column
- Issue: No formal definition of how OEM vs Retail is distinguished
- Recommendation: Requires business rule definition before implementation
- Estimated coverage: ~60%

**SEM-004 (受注):**  
- Potential sources: 売上 (revenue side), 発注依頼 (order request side)
- Issue: 受注 conceptually spans from "customer places order" through "we acknowledge it" — tracking is fragmented across multiple tables
- Gap: No unified order confirmation table
- Estimated coverage: ~70%

**SEM-007 (納品):**  
- Location: 売上.納品伝票日 (delivery date in sales table)
- Issue: Physical handoff concept is captured only as date, not as discrete event with full lifecycle
- Estimated coverage: ~80%

**SEM-009 (案件):**  
- Location: 集計 aggregation table ONLY (案件名, 案件売上, 案件粗利)
- **Critical Issue:** No master table for projects/cases
- Gap: Cannot query case metadata (creation date, status lifecycle, milestones, assigned staff)
- Current usage: Project name as output aggregation label only
- Estimated coverage: **~50%** (aggregate output exists; independent case management missing)

---

## Semantic Gaps & New Candidates

### Gap 1: Case/Project Master Table Missing (SEM-009)
**Severity:** HIGH  
**Current State:** Only 集計 (aggregation output) exists; no case master to manage lifecycle  
**Impact:** Cannot implement case status tracking, milestones, or project-level decision gates  
**Recommendation:** Design new 案件 master table (proposed Phase 11) with:
- 案件id (unique identifier)
- 案件名 (project name)
- 顧客id (customer reference)
- 案件種別 (OEM/Retail/etc — differentiates SEM-001 vs SEM-002)
- ステータス (計画中/進行中/納品待ち/完了/キャンセル)
- 期限 (deadline) — currently missing
- 担当者 (assigned staff)
- 作成日, 完了日

---

### Gap 2: Fuzzy OEM vs Retail Distinction (SEM-001, SEM-002)
**Severity:** MEDIUM  
**Current State:** 集計.分類 exists but classification logic is undefined  
**Impact:** Cannot reliably filter "OEM gross profit" vs "Retail sales" without business rule  
**Recommendation:** Business rule needed to define criteria:
- Is it based on 商品分類 (product classification)?
- Is it based on customer segment (regular vs OEM-focused)?
- Is it based on order characteristics (custom design vs off-the-shelf)?

---

### Gap 3: Order Confirmation (SEM-004) Lacks Unified Representation
**Severity:** MEDIUM  
**Current State:** 発注依頼 handles vendor purchase orders; 売上 handles revenue. Customer order acknowledgment logic is implicit.  
**Impact:** Cannot track order states (quote → confirmed → production → delivery)  
**Recommendation:** Define 受注 master table or enhance 発注依頼 to unify both customer-side and vendor-side orders.

---

### Gap 4: Delivery Event (SEM-007) Not Discrete
**Severity:** LOW  
**Current State:** 納品伝票日 captures delivery date but no discrete delivery event record  
**Impact:** Cannot audit delivery-specific issues (partial delivery, quality hold, etc.)  
**Recommendation:** Optional — depends on business need for delivery-level granularity.

---

## New Semantic Candidates from Real DB

### Not Yet in SEM-001 through SEM-010:

**1. 取引先 (Trading Partner / Vendor) — 2,148 records**
- Related to SEM-006 (仕入), but represents counterparty
- **Candidate:** SEM-011: 仕入先 (vendor/supplier)
- Recommendation: Add formal Semantic for vendor management

**2. 社員 (Staff / Employee) — Referenced in 集計**
- Appears in: 社員id, 営業事務id columns
- **Candidate:** SEM-012: 担当者 (assigned staff member)
- Relevance: Project assignment, sales team structure
- Recommendation: Create staff/assignment Semantic if project allocation becomes critical

**3. 期 (Period/Month) — Present in all transactional tables**
- Distinct from SEM-007 (納品); more like time-based grouping
- **Candidate:** SEM-013: 会計期間 (accounting period)
- Recommendation: Define formally if period-based reporting (month-end close, variance analysis) is needed

**4. ステータス (Status flags) — Present in 売上, 仕入, 発注依頼**
- Current values: 有効/キャンセル/テスト (sales); 仕入確定フラグ (procurement); status (order)
- **Candidate:** SEM-014: ステータス (generic state machine)
- Recommendation: Define state transitions if lifecycle tracking becomes critical

---

## Coverage Summary

| Category | Status | Count |
|----------|--------|-------|
| **Fully Supported** | ✓ | 5 Semantics (SEM-003, SEM-005, SEM-006, SEM-008, SEM-010) |
| **Partially Supported** | ⚠️ | 4 Semantics (SEM-001, SEM-002, SEM-004, SEM-007, SEM-009) |
| **Not Directly Supported** | ✗ | 0 of current 10 Semantics |
| **Business Tables Used** | — | 11 tables (all with business purpose) |
| **Unmapped Business Tables** | — | 0 (all 11 tables mapped to at least 1 Semantic or metadata) |

---

## Recommendations for Phase 11

**Priority 1 (Must Have):**
1. Create 案件 master table for SEM-009 (project case management)
2. Define OEM vs Retail classification logic (SEM-001/SEM-002)
3. Establish 受注 (order confirmation) lifecycle tracking (SEM-004)

**Priority 2 (Should Have):**
4. Formalize 仕入先 (vendor) as SEM-011
5. Formalize 担当者 (staff assignment) as SEM-012

**Priority 3 (Nice to Have):**
6. Implement discrete 納品 event tracking for SEM-007
7. Define 会計期間 (accounting period) logic for reporting

---

**Prepared by:** AI Reasoning Pipeline Investigation  
**Next Steps:** Phase 10 Step 3 - Create Semantic Coverage Report  
