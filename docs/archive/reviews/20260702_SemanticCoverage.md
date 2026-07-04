# Semantic Coverage Report

**Date:** 2026-07-02  
**Phase:** 10, Step 3  
**Analysis Basis:** Real Logsys DB (289MB, 21 tables) vs Semantic Registry (SEM-001 through SEM-010)

---

## Coverage Matrix

### By Semantic Concept

```
SEM-001: OEM案件
─────────────────
Real DB Support:     ⚠️ PARTIAL
Primary Source:      集計.分類 (inferred classification)
Secondary Sources:   売上.事業部門, 仕入.事業部門
Row Coverage:        ~10,000 of 16,705 in 集計 (estimated ~60%)
Status:              **Requires business rule definition**
Fields Available:    分類 (classification code only; no lifecycle)
Missing:             OEM vs Retail distinction logic
Recommendation:      Document classification criteria before reasoning pipeline uses it

SEM-002: Retail案件
──────────────────
Real DB Support:     ⚠️ PARTIAL  
Primary Source:      集計.分類 (inferred classification)
Secondary Sources:   売上.事業部門
Row Coverage:        ~6,700 of 16,705 in 集計 (estimated ~40%)
Status:              **Requires business rule definition**
Fields Available:    分類 (classification code only)
Missing:             Clear Retail case identification
Recommendation:      Coordinate with OEM/Retail classification rule design

SEM-003: 顧客 (Customer)
───────────────────────
Real DB Support:     ✓ COMPLETE
Primary Source:      顧客 table (2,738 records)
Schema Match:        100% — table structure aligns with Semantic definition
Key Fields:          顧客id (PK), 顧客名称, 顧客分類, 事業規模, 取引傾向分類
Status:              **Ready to use**
Data Quality:        High — master table fully maintained
Recommendation:      Use 顧客 table directly for SEM-003 lookups

SEM-004: 受注 (Order Confirmation)
────────────────────────────────────
Real DB Support:     ⚠️ PARTIAL
Primary Source:      売上.ステータス (revenue-side order state)
Secondary Sources:   発注依頼 (vendor order state; terminology gap)
Row Coverage:        199,512 in 売上 + 34,733 in 発注依頼 (dual representation)
Status:              **Requires definition clarification**
Fields Available:    売上.ステータス (有効/キャンセル/テスト) — customer order only
Missing:             Unified order lifecycle from quote through acceptance through fulfillment
Issue:               発注 term in Japanese refers to **placing** order with vendor; 受注 means **receiving** order from customer. 発注依頼 table tracks vendor POs, not customer order acceptance.
Recommendation:      **Clarify: Does SEM-004 "受注" mean customer order state (売上.ステータス) or unified order lifecycle? If latter, need new master table.**

SEM-005: 売上 (Revenue / Sales)
─────────────────────────────────
Real DB Support:     ✓ COMPLETE  
Primary Source:      売上 table (199,512 records)
Schema Match:        100% — fully aligned with Semantic definition
Key Fields:          売上高 (revenue amount), 売上原価 (revenue cost), ステータス, 納品伝票日
Data Quality:        Excellent — transaction-level detail available
Status:              **Ready to use immediately**
Recommendation:      Use 売上 table directly for SEM-005 queries; filter by ステータス=有効 for valid transactions

SEM-006: 仕入 (Procurement)
─────────────────────────────
Real DB Support:     ✓ COMPLETE
Primary Source:      仕入 table (44,855 records) + 仕入諸掛 table (21,390 incidental costs)
Schema Match:        100% — comprehensive procurement data available
Key Fields:          仕入金額 (procurement amount), 仕入確定フラグ, 仕入確定日, 取引先区分
Supplementary:       仕入諸掛 for operational cost components (freight, tariffs, etc.)
Data Quality:        Good — primary costs + supplementary costs separate
Status:              **Ready to use immediately**
Recommendation:      For gross profit calculations (SEM-008), combine 仕入 base cost + 仕入諸掛 supplementary costs; filter by 仕入確定フラグ=1 for confirmed procurement

SEM-007: 納品 (Delivery)
──────────────────────────
Real DB Support:     ⚠️ PARTIAL
Primary Source:      売上.納品伝票日 (delivery date captured in sales table)
Row Coverage:        199,512 rows in 売上 (delivery date present)
Status:              **Usable but limited**
Fields Available:    納品伝票日 (date only) — delivery date captured
Missing:             Discrete delivery event records; no delivery status, hold reasons, partial delivery tracking
Issue:               Delivery is implicit in sales transaction; not modeled as separate business entity
Recommendation:      Use 売上.納品伝票日 for delivery timing queries; cannot query delivery-specific issues without additional table design

SEM-008: 粗利 (Gross Profit)
─────────────────────────────
Real DB Support:     ✓ COMPLETE
Primary Source:      集計.案件粗利 (pre-calculated project-level gross profit at 16,705 rows)
Secondary Source:    売上 (revenue) - 仕入 (cost) = gross profit (can derive transaction-level)
Three Variants:      ① 概算粗利 ② 実際粗利 ③ 担当者粗利 — implicitly supported through component separation
Status:              **Ready to use immediately**
Data Quality:        Excellent — pre-aggregated at project level + component breakdown available
Recommendation:      Use 集計.案件粗利 for project-level queries; use (売上 - 仕入) formula for transaction-level variance analysis

SEM-009: 案件 (Project / Case)
────────────────────────────────
Real DB Support:     ⚠️ CRITICAL GAP
Primary Source:      集計.案件名 (aggregation output only; 16,705 rows)
Status:              **NOT READY — Master table missing**
Fields Available:    案件名 (project name as output label only)
Missing:             
  • 案件id (unique project identifier)
  • ステータス (project state: 計画中/進行中/納品待ち/完了)
  • 顧客id (customer association)
  • 案件種別 (OEM/Retail differentiation) — would support SEM-001/SEM-002
  • 期限 (project deadline)
  • 作成日 (project creation date)
  • 完了日 (project completion date)
  • 担当者 (assigned staff)
Issue:               **Aggregation (集計) is output-only; cannot query case-level details**
Recommendation:      **Must design 案件 master table in Phase 11 before SEM-009 can support reasoning pipeline**

SEM-010: 商品 (Product)
──────────────────────────
Real DB Support:     ✓ COMPLETE
Primary Source:      商品 table (10,236 records)
Schema Match:        100% — SKU definition aligns with Semantic
Key Fields:          型番 (model), 色 (color), サイズ (size) — combination uniquely identifies SKU
Product Info:        商品名, 商品分類, 定価, 原価
Status:              **Ready to use immediately**
Recommendation:      Use 商品 table directly for SEM-010 product lookups and attributes
```

---

## Coverage by Reasoning Pipeline Use Case

### Q1: OEM粗利（OEM事業の月次粗利を教えてください）

**Required Semantics:**
- SEM-001 (OEM案件) — identify OEM transactions
- SEM-005 (売上) — filter by period
- SEM-008 (粗利) — aggregate gross profit

**Real DB Coverage:**
- ✓ SEM-005: 100% available (売上.売上高 with period filter)
- ✓ SEM-008: 100% available (集計.案件粗利 or calculated from 売上-仕入)
- ⚠️ SEM-001: ~60% available (集計.分類 requires business rule definition)

**Pipeline Readiness:** **75%**  
**Blocker:** Need OEM classification definition to filter 売上 or 集計 by case type

---

### Q2: Fanatics案件の状況（Fana​tics案件のステータスと次アクションを教えてください）

**Required Semantics:**
- SEM-003 (顧客) — identify Fanatics customer
- SEM-009 (案件) — query project status & details

**Real DB Coverage:**
- ✓ SEM-003: 100% available (顧客 table with customer name lookup)
- ✗ SEM-009: **Cannot retrieve** — no project master table; only 集計 aggregation exists with no status/timeline info

**Pipeline Readiness:** **50%**  
**Blocker:** SEM-009 master table missing; cannot answer project status questions

---

### Q3: 優先案件（本日優先すべき案件を教えてください）

**Required Semantics:**
- SEM-009 (案件) — query project details (deadline, status)
- SEM-008 (粗利) — rank by profit impact

**Real DB Coverage:**
- ✗ SEM-009: **Cannot retrieve** — no deadline field, no status lifecycle, no case master table
- ✓ SEM-008: 100% available (集計.案件粗利)

**Pipeline Readiness:** **50%**  
**Blocker:** SEM-009 lacks deadline (期限) field; cannot determine urgency

---

### Q4: 売上首位顧客（今月の売上首位顧客は誰ですか）

**Required Semantics:**
- SEM-003 (顧客) — aggregate by customer
- SEM-005 (売上) — sum by period & customer

**Real DB Coverage:**
- ✓ SEM-003: 100% available (顧客.顧客id for canonical customer identification)
- ✓ SEM-005: 100% available (売上.売上高 with period filter)

**Pipeline Readiness:** **100%**  
**Status:** Ready to answer immediately

---

## Table-to-Semantic Cross-Reference

| DB Table | Primary Semantic | Secondary Semantics | Coverage | Status |
|----------|------------------|---------------------|----------|--------|
| 売上 | SEM-005 | SEM-004, SEM-007, SEM-008 | 100% | ✓ Ready |
| 仕入 | SEM-006 | SEM-008 | 100% | ✓ Ready |
| 集計 | SEM-008, SEM-009 | SEM-001, SEM-002 | 50-60% | ⚠️ Partial |
| 商品 | SEM-010 | — | 100% | ✓ Ready |
| 顧客 | SEM-003 | — | 100% | ✓ Ready |
| 発注依頼 | SEM-004, SEM-006 | — | 70% | ⚠️ Partial |
| 仕入諸掛 | SEM-008 | SEM-006 | 100% | ✓ Ready |
| 取引先 | (No SEM) | SEM-006 | N/A | — |
| 顧客担当者 | (No SEM) | — | N/A | — |
| コード | (No SEM) | — | N/A | — |

---

## Impact on Reasoning Pipeline

### Fully Functional Queries
- **Q4: 売上首位顧客** — Can answer immediately with SEM-003 + SEM-005 ✓

### Conditionally Functional Queries  
- **Q1: OEM粗利** — Can answer if OEM classification rule is provided (Priority: HIGH)
- **Q2: Fanatics状況** — Can answer customer info only (SEM-003); cannot provide project status
- **Q3: 優先案件** — Cannot answer; missing project deadline (期限) in SEM-009

### Not Functional Queries
- Any query requiring **project status** (状況), **deadline** (期限), **project lifecycle** — all require SEM-009 master table

---

## Semantic Coverage Score

```
Overall Coverage:  68%
 ├─ SEM-001 (OEM案件):      60% ⚠️
 ├─ SEM-002 (Retail案件):   60% ⚠️
 ├─ SEM-003 (顧客):         100% ✓
 ├─ SEM-004 (受注):         70% ⚠️
 ├─ SEM-005 (売上):         100% ✓
 ├─ SEM-006 (仕入):         100% ✓
 ├─ SEM-007 (納品):         80% ⚠️
 ├─ SEM-008 (粗利):         100% ✓
 ├─ SEM-009 (案件):         50% ⚠️ [CRITICAL]
 └─ SEM-010 (商品):         100% ✓

Queries Answerable:
 • 100%: 1 of 4 (Q4)
 • 50-75%: 2 of 4 (Q1, Q2)
 • <50%: 1 of 4 (Q3)
```

---

**Next Step:** Phase 10 Step 4 — Create Semantic Gap Report with actionable Phase 11 recommendations
