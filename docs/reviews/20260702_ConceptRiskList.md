# Phase 10.5 — Concept Risk List

**Date:** 2026-07-02  
**Purpose:** Identify business concepts that AI might misunderstand before Phase 11 implementation  
**Status:** Investigation Only — No Semantic Catalog or Code Changes

---

## Critical Discovery

Product Owner revealed that **「案件」is not a single concept** in Logsys:
- **PO単位** (Purchase Order Unit) — ordering/procurement granularity
- **商品単位** (Product Unit) — planning/sales granularity

This requires decomposition. Other concepts likely have similar ambiguities.

---

## Concept Risk Summary

| Concept | Risk Level | Primary Issue | Phase 11 Impact |
|---------|-----------|----------------|-----------------|
| 案件 | 🔴 CRITICAL | Multiple definitions (PO/Product/Customer/Sales) | Blocks SEM-009 design |
| 粗利 | 🔴 CRITICAL | Three variants (論理/実績/担当者別) + margin vs amount | Affects SEM-008 usage |
| OEM案件 vs Retail案件 | 🔴 CRITICAL | Classification criteria undefined | Blocks SEM-001/SEM-002 rule |
| 受注 | 🟠 HIGH | Customer order vs order state vs acknowledgment | Clarifies SEM-004 |
| 発注 | 🟠 HIGH | Terminology confusion (to vendor vs from customer) | May affect SEM-004/SEM-006 |
| ステータス | 🟠 HIGH | Different status values/meanings per table | Requires normalization |
| キャンセル | 🟠 HIGH | At what stage? Partial? Reversible? | Affects filtering rules |
| 実績原価 vs 論理原価 | 🟠 HIGH | When is each used? Calculation implications? | Affects SEM-008 calculation |
| PO (発注依頼) | 🟠 HIGH | Vendor PO vs Customer PO distinction | Affects SEM-004/SEM-006 |
| 商品単位 | 🟠 HIGH | Model vs Model+Color vs Model+Color+Size | Affects SEM-010 definition |
| 予定 | 🟡 MEDIUM | Planned quantity vs schedule vs forecast | May affect future queries |
| 返品 | 🟡 MEDIUM | Timing, reversal logic, impact on totals | Affects sales/margin queries |
| 入金 | 🟡 MEDIUM | Timing, partial payments, recognition | Affects cash flow queries |
| 担当者 | 🟡 MEDIUM | Multiple roles per project? Reassignment? | Affects SEM-012 if added |
| 締め/今月 | 🟡 MEDIUM | Calendar vs fiscal vs custom period | Affects time-based queries |
| 納品 | 🟡 MEDIUM | Partial delivery, timing, status tracking | Affects SEM-007 |
| 仕入 | 🟡 MEDIUM | Material vs component vs external processing | Affects SEM-006 details |
| 顧客 | 🟡 MEDIUM | Entity vs relationship vs account | Generally low risk (master table exists) |
| 会社粗利 | 🟡 MEDIUM | Consolidated vs by division vs by business | Reporting granularity |
| 粗利率 | 🟡 MEDIUM | Ratio vs percentage calculation | Affects interpretation |

---

## Detailed Concept Analysis

### 🔴 CRITICAL CONCEPTS

---

## 1. 案件 (Project/Case) — CRITICAL

### Current AI Understanding
- Treated as single entity per Semantic Registry (SEM-009)
- Definition: "A series of business activities tracked end-to-end from order to completion"
- Assumed to be unique project identifier

### Misunderstanding Risk
- **ACTUAL:** 案件 has multiple granularities in Logsys:
  1. **PO単位** (Purchase Order Unit) — one PO = one project?
  2. **商品単位** (Product Unit) — one product line = one project?
  3. **顧客単位** (Customer Unit) — all orders from one customer = one project?
  4. **売上単位** (Sales Unit) — one sales transaction = one project?
  5. **納品単位** (Delivery Unit) — one shipment = one project?
  6. **発注単位** (Order Unit) — one customer order = one project?

- **ERROR SCENARIO:** AI asked "Fanatics案件のステータス" and retrieves wrong aggregation level; returns company-wide results instead of specific order

### Logsys上の表現候補
- PO単位: 発注依頼.id → represents ordering-side project boundary
- 商品単位: 集計 table with product grouping → represents sales-side project boundary
- 顧客単位: 顧客.id → customer entity
- 売上単位: 売上.id → individual transaction
- 納品単位: 売上.納品伝票日 + 関連行 → delivery event grouping

### Product Ownerに確認したいこと
① When you say "案件の粗利は？", which unit do you mean?
   - PO単位 (vendor order level)
   - 商品単位 (product family level)
   - 顧客単位 (customer account level)
   - Other?

② Does each unit have independent status tracking, or is status aggregated?

③ Which granularity should AI use for priority ranking (優先案件)?

### 優先度
**🔴 CRITICAL** — Must resolve before SEM-009 master table design

---

## 2. 粗利 (Gross Profit) — CRITICAL

### Current AI Understanding
- Treated as single metric in Semantic Registry (SEM-008)
- Definition: "Revenue minus direct manufacturing cost"
- Three variants mentioned: 概算/実績/担当者別

### Misunderstanding Risk
- **VARIANT AMBIGUITY:**
  1. **論理粗利 (Logical/Standard Gross Profit):** Sales × Standard Margin %
  2. **実績粗利 (Actual Gross Profit):** Actual Revenue − Actual Procurement Cost
  3. **担当者別粗利 (Staff-Assigned Gross Profit):** Profit attributed to assigned sales person

- **CALCULATION AMBIGUITY:**
  - Include 仕入諸掛 (procurement incidentals) or not?
  - Include 返品/キャンセル or exclude?
  - Use 売上日 or 納品日 for period assignment?
  - Include operational costs (②③④ in 集計)? or pure production cost?

- **GRANULARITY AMBIGUITY:**
  - Per transaction? Per product? Per case? Per customer? Per staff member?

- **RATIO vs AMOUNT:**
  - 粗利率 (margin ratio) vs 粗利額 (margin amount) — different calculations

- **ERROR SCENARIO:** AI calculates OEM粗利 using standard margin instead of actual costs; reports 30% when actual is 15%

### Logsys上の表現候補
- 集計.案件粗利 — pre-calculated project-level (but which variant?)
- (売上.売上高 - 仕入.仕入金額) — transaction-level calculation
- 売上.売上原価 — cost side; may be standard or actual

### Product Ownerに確認したいこと
① Which gross profit variant (論理/実績/担当者別) should be default for queries?

② Should operational cost components (②③④) be included in margin calculation?

③ How are return/cancellation handled in gross profit?

④ When calculating by staff, how is multi-person projects handled?

### 優先度
**🔴 CRITICAL** — Affects SEM-008 implementation and Q1 answers

---

## 3. OEM案件 vs Retail案件 — CRITICAL

### Current AI Understanding
- Treated as two separate Semantics (SEM-001, SEM-002)
- Definition: OEM = custom design; Retail = off-the-shelf
- Classification logic: undefined

### Misunderstanding Risk
- **CLASSIFICATION CRITERIA UNDEFINED:**
  - Based on customer segment (OEM-focused vs retail)?
  - Based on product type (custom vs catalog)?
  - Based on order size (bulk vs single)?
  - Based on contract type?

- **EDGE CASES:**
  - Sample order — OEM or Retail?
  - Trial/test order — OEM or Retail?
  - Customer-specific packaging — OEM or Retail?

- **LOGSYS REPRESENTATION:**
  - Is 集計.分類 the indicator? Values are unclear from schema
  - Can it be inferred from 商品.商品分類 or 商品.事業分類?
  - Or from 顧客.顧客分類?

- **ERROR SCENARIO:** AI classifies Fanatics order as Retail because customer name looks like retailer, but it's actually custom OEM order

### Logsys上の表現候補
- 集計.分類 — most likely classifier
- 商品.事業分類 — may indicate business segment
- 顧客.顧客分類 — customer type indicator
- Order characteristics (quantity, custom specs) — inferred from transaction details

### Product Ownerに確認したいこと
① What is the primary classifier for OEM vs Retail in Logsys?
   - 集計.分類 values are? (Please list examples)
   - Customer type?
   - Product type?
   - Order characteristics?

② How are ambiguous cases (samples, trials) classified?

### 優先度
**🔴 CRITICAL** — Blocks SEM-001/SEM-002 rules and Q1 implementation

---

### 🟠 HIGH PRIORITY CONCEPTS

---

## 4. 受注 (Order Confirmation) — HIGH

### Current AI Understanding
- Semantic SEM-004 defined as "Customer order from start of fulfillment"
- Treated as order acknowledgment/confirmation state
- Assumed to be tracked in Logsys

### Misunderstanding Risk
- **REPRESENTATION FRAGMENTED:**
  - 売上.ステータス tracks revenue-side order outcome (有効/キャンセル/テスト)
  - 発注依頼 tracks vendor purchase order (confusing terminology)
  - No explicit "customer order acknowledgment" table

- **STATE MACHINE UNCLEAR:**
  - Does 受注 have states (quote → confirmed → production → delivery)?
  - Or is it binary (received/not received)?
  - Can it be unconfirmed?

- **ERROR SCENARIO:** AI tries to query "未受注案件は何件ですか" (unconfirmed orders count) but table doesn't exist

### Logsys上の表現候補
- 売上.ステータス (revenue-side order state)
- 発注依頼 (vendor order, not customer order)
- No dedicated order confirmation master currently

### Product Ownerに確認したいこと
① Does SEM-004 "受注" map to 売上.ステータス, or does it need separate table?

② Should 受注 have state transitions (quote/confirmed/production/shipped)?

### 優先度
**🟠 HIGH** — Clarifies SEM-004 but not immediately blocking Q1-Q4

---

## 5. 発注 (Order Placement) — HIGH

### Current AI Understanding
- Assumed to mean "customer places order with LOGS"
- Synonym for 受注 in some contexts

### Misunderstanding Risk
- **TERMINOLOGY CONFUSION:**
  - In Japanese, 発注 typically means "placing an order **with a vendor**"
  - But can colloquially mean "order received" (錯誤risk)
  - 発注依頼 table tracks **vendor** purchase orders, not customer orders

- **MULTIPLE MEANINGS:**
  - 発注 to vendor (procurement side) ← 発注依頼 table
  - 発注 from customer (sales side) ← unclear representation

- **ERROR SCENARIO:** AI confuses vendor PO (発注依頼) with customer order; reports procurement when asked about customer order status

### Logsys上の表現候補
- 発注依頼 (vendor purchase order, procurement side)
- 売上 (customer order outcome, revenue side)

### Product Ownerに確認したいこと
① Should AI distinguish between 発注 (to vendor) and 受注 (from customer)?

② How should these map to Logsys tables?

### 優先度
**🟠 HIGH** — Prevents terminology confusion but lower impact than other gaps

---

## 6. ステータス (Status) — HIGH

### Current AI Understanding
- Treated as generic state indicator
- Assumed to be normalized across tables

### Misunderstanding Risk
- **INCONSISTENT SCHEMAS:**
  - 売上.ステータス: 有効/キャンセル/テスト
  - 仕入.ステータス: (unknown from schema)
  - 発注依頼.ステータス: (unknown from schema)
  - Each table may have different values and meanings

- **UNKNOWN STATE VALUES:**
  - Can we query "ステータス = '進行中'"? Or does table use different encoding?
  - Are status codes or status names used?

- **FILTERING LOGIC UNCLEAR:**
  - Should 有効 orders always be included?
  - Should テスト orders always be excluded?
  - What about キャンセル — completely reversed, or partially retained for audit?

- **ERROR SCENARIO:** AI filters by ステータス=進行中, but table uses ステータス=1 or ステータス=IN_PROGRESS; returns no results

### Logsys上の表現候補
- 売上.ステータス — observed values: 有効/キャンセル/テスト
- 仕入.ステータス, 発注依頼.ステータス — values unknown

### Product Ownerに確認したいこと
① What are the standard ステータス values for each main table (売上/仕入/発注依頼)?

② Are values standardized, or does each table use different codes?

③ How should キャンセル be handled (excluded from analysis, or kept for audit)?

### 優先度
**🟠 HIGH** — Affects all filtering logic

---

## 7. キャンセル (Cancellation) — HIGH

### Current AI Understanding
- Assumed to be simple binary state (cancelled or not)
- 売上.ステータス=キャンセル indicates cancellation

### Misunderstanding Risk
- **STATE AMBIGUITY:**
  - At what stage can cancellation occur?
  - Is it reversible (can cancelled order be reactivated)?
  - Partial cancellation possible?

- **IMPACT AMBIGUITY:**
  - If cancelled, should it be excluded from all queries?
  - Should it affect historical analytics (month-to-date)?
  - Should it be counted separately for audit?

- **TIMING AMBIGUITY:**
  - When is キャンセル recorded (immediately, or at month-end)?
  - Do キャンセル rows get reversed (negative line), or just flagged?

- **ERROR SCENARIO:** AI includes キャンセル rows in月次粗利 calculation; reports inflated profit because cancelled items weren't properly reversed

### Logsys上の表現候補
- 売上.ステータス = キャンセル flag
- Logic for reversal: via negative rows, or via status flag exclusion?

### Product Ownerに確認したいこと
① How should cancelled transactions be handled in queries?
   - Completely excluded?
   - Included separately?
   - Counted as negative (reversal)?

② Is cancellation reversible?

### 優先度
**🟠 HIGH** — Affects accuracy of all financial queries

---

## 8. 実績原価 vs 論理原価 (Actual vs Standard Cost) — HIGH

### Current AI Understanding
- Assumed to both exist in Logsys
- Used for different gross profit variants
- Implementation details unclear

### Misunderstanding Risk
- **WHICH TO USE WHEN:**
  - Is 論理原価 used for planning/forecast?
  - Is 実績原価 used for actual results?
  - Can both exist for same item?
  - If one is missing, which is fallback?

- **CALCULATION TIMING:**
  - When is 実績原価 recorded (immediately or at month-end)?
  - What if it's not yet available (use 論理原価 as placeholder)?

- **IMPACT ON Q1:**
  - Q1 asks "OEM粗利" — which cost should be used?
  - If only 論理 available, is answer provisional?

- **ERROR SCENARIO:** AI calculates gross profit using standard costs when actuals should be used; variance hidden until month-end reconciliation

### Logsys上の表現候補
- 売上.売上原価 — may be standard or actual
- 仕入.仕入金額 — actual procurement cost
- Unclear which represents which variant

### Product Ownerに確認したいこと
① Where are 実績原価 and 論理原価 stored in Logsys?
   - Are they in separate columns?
   - Or replaced progressively?
   - Or calculated on-demand?

② Which should be used for monthly queries?

### 優先度
**🟠 HIGH** — Affects SEM-008 calculation logic

---

## 9. PO (発注依頼) — HIGH

### Current AI Understanding
- Assumed to track vendor purchase orders
- Semantically separate from customer orders (受注)

### Misunderstanding Risk
- **AMBIGUOUS TERMINOLOGY:**
  - "PO" colloquially can mean either purchase order (to vendor) or purchase order (from customer)
  - 発注依頼 clearly is vendor PO
  - But is there a customer PO concept?

- **RELATIONSHIP TO 案件:**
  - Is each 発注依頼 = one 案件 granule?
  - Or can multiple 発注依頼 be part of one 案件?
  - Or can one 発注依頼 split across multiple 案件?

- **LINKAGE TO 売上:**
  - How does customer PO link to 売上?
  - How does vendor PO (発注依頼) link to 仕入?

- **ERROR SCENARIO:** AI tries to match customer PO number from question to 発注依頼 table but finds no match (because 発注依頼 is vendor PO, not customer PO)

### Logsys上の表現候補
- 発注依頼 (vendor purchase order)
- 売上 (customer order, but no explicit customer PO number field?)

### Product Ownerに確認したいこと
① Should AI distinguish between:
   - Customer PO (from customer to LOGS)
   - Vendor PO (from LOGS to vendor)

② How does customer PO number map to Logsys data?

### 優先度
**🟠 HIGH** — Prevents query mismatches but lower impact than SEM-009/SEM-001

---

## 10. 商品単位 (Product Unit) — HIGH

### Current AI Understanding
- Treated as single SKU identifier (SEM-010)
- Assumed to be: Model Number + Color + Size

### Misunderstanding Risk
- **GRANULARITY QUESTION:**
  - Is product uniqueness at:
    - 型番 (model number) level only?
    - 型番 + 色 (model + color) level?
    - 型番 + 色 + サイズ (model + color + size) level?
    - Something else?

- **VARIANT MANAGEMENT:**
  - How are product variants tracked?
  - Can one model have variants (colors, sizes) grouped under single "case"?
  - Or is each variant a separate case?

- **IMPACT ON 案件:**
  - Does one 商品単位 = one 案件?
  - Or is 商品 independent from 案件?

- **ERROR SCENARIO:** AI asked "商品Aの粗利" might return wrong aggregation level; sums across all colors/sizes or only one specific variant

### Logsys上の表現候補
- 商品.id — primary key (but at what granularity?)
- 商品.型番, .色, .サイズ — variant dimensions

### Product Ownerに確認したいこと
① What is the unique identifier for a product (商品)?
   - 型番 only?
   - 型番 + 色?
   - 型番 + 色 + サイズ?
   - Something else?

② How does 商品 relate to 案件?

### 優先度
**🟠 HIGH** — Affects SEM-010 definition and product-level queries

---

### 🟡 MEDIUM PRIORITY CONCEPTS

---

## 11. 予定 (Plan/Schedule) — MEDIUM

### Current AI Understanding
- Not yet modeled in Semantic Registry
- Assumed to exist for planning purposes

### Misunderstanding Risk
- **WHAT IS "予定":**
  - Planned delivery date (納期予定)?
  - Planned production schedule?
  - Planned quantity?
  - Budget/forecast?

- **WHEN IS IT USED:**
  - Only before order confirmation?
  - Or throughout project lifecycle (can be updated)?
  - Can differ from actual?

- **NOT IN CURRENT 案件:**
  - If 案件 table is designed without 予定 field, future queries fail

- **IMPACT:**
  - May be needed for "when will Fanatics case be delivered?" type queries

### Logsys上の表現候補
- No visible "予定" field in current schema analysis
- May be in project management sheet (Google Drive), not SQLite

### Product Ownerに確認したいこと
(Optional if not critical for Phase 11)

### 優先度
**🟡 MEDIUM** — Not blocking current queries; may surface later

---

## 12. 返品 (Return) — MEDIUM

### Current AI Understanding
- Assumed to reverse sales transaction

### Misunderstanding Risk
- **TIMING:**
  - When can returns be accepted? Immediately after delivery? Within X days? Never?
  - Does return timing affect月次集計?

- **REVERSAL LOGIC:**
  - Is return recorded as negative row in 売上?
  - Or as separate table with reversal logic?
  - Can return be partial (partial quantity)?

- **IMPACT ON ANALYTICS:**
  - If Q1 asks "OEM粗利", should returns be included (negative impact)?
  - Or excluded (as exceptions)?
  - Can affect month-end reported profit

- **STATUS:**
  - Does キャンセル status apply to returns?
  - How is キャンセル different from 返品?

### Logsys上の表現候補
- Unknown if separate table or part of 売上 logic

### Product Ownerに確認したいこと
(Optional; can surface later)

### 優先度
**🟡 MEDIUM** — Important for accuracy but not immediately blocking

---

## 13. 入金 (Payment Received) — MEDIUM

### Current AI Understanding
- Not yet modeled
- Assumed to be tracked separately from revenue recognition

### Misunderstanding Risk
- **WHEN RECORDED:**
  - When is 入金 recognized (on payment date or accrual)?
  - Can orders be delivered but not yet paid?
  - Impact on月次売上?

- **PARTIAL PAYMENTS:**
  - Can customers pay in installments?
  - How is this represented?

- **NOT CRITICAL FOR PHASE 11:**
  - Current Q1-Q4 don't query payment status
  - But may be needed for future "入金予定" queries

### Logsys上の表現候補
- Unknown if in current schema

### 優先度
**🟡 MEDIUM** — May surface in future queries

---

## 14. 担当者 (Staff / Assignment) — MEDIUM

### Current AI Understanding
- Referenced in 集計 table (社員id, 営業事務id)
- Not yet formalized as Semantic (candidate SEM-012)

### Misunderstanding Risk
- **MULTIPLE ROLES:**
  - One case can have sales person + operations person + other roles?
  - How is 担当者別粗利 calculated if multiple staff?

- **REASSIGNMENT:**
  - If staff changes mid-project, which is credited?
  - Is reassignment history tracked?

- **NOT CRITICAL FOR PHASE 11:**
  - Current queries don't depend on staff dimension
  - But "担当者別粗利" is a mentioned metric

### 優先度
**🟡 MEDIUM** — Low impact on Phase 11; may surface later

---

## 15. 締め / 今月 (Close / This Month) — MEDIUM

### Current AI Understanding
- 今月 assumed to mean calendar month (1st to end of month)
- 締め assumed to mean month-end close process

### Misunderstanding Risk
- **FISCAL vs CALENDAR:**
  - Does LOGS use calendar months or fiscal months?
  - Can vary by division?

- **CUSTOM PERIODS:**
  - Can "今月" be redefined (e.g., rolling 4-week period)?

- **IMPACT:**
  - Q1 "今月の粗利" needs to know which month is "今月"
  - If fiscal month logic is wrong, all monthly queries are off

- **IMPLEMENTATION:**
  - Current 売上 table has 期 column — what does it represent?

### Logsys上の表現候補
- 売上.期 column (meaning unknown; calendar month? fiscal month?)

### Product Ownerに確認したいこと
① Does 「今月」mean calendar month or fiscal month?

② If mixed (calendar for some divisions, fiscal for others), how should AI decide?

### 優先度
**🟡 MEDIUM** — Important for temporal queries but not immediately blocking

---

## 16. 納品 (Delivery) — MEDIUM

### Current AI Understanding
- Treated as date-only field (売上.納品伝票日)
- Revenue recognition point in SEM-007

### Misunderstanding Risk
- **WHAT IS "納品":**
  - Is it the date shipped, or date received by customer, or date recorded?
  - Can delivery be partial?
  - Can delivery be delayed (split across multiple dates)?

- **STATUS TRACKING:**
  - Is delivery event itself tracked, or just date?
  - Can there be hold/delay reason?

- **IMPACT ON QUERIES:**
  - If asked "今月納品された案件", does 納品伝票日 = when shipped or when received?
  - Affects月次集計精度

### 優先度
**🟡 MEDIUM** — Affects delivery-related queries; not immediately critical

---

## 17. 仕入 (Procurement) — MEDIUM

### Current AI Understanding
- Treated as homogeneous "material + component + service" cost
- Assumed all procurements are direct product cost

### Misunderstanding Risk
- **COST TYPES:**
  - Does 仕入 include external processing (外注)?
  - Does it include logistics?
  - Does it include packaging?
  - Only direct materials?

- **IMPACT ON GROSS PROFIT:**
  - If external processing is separate from 仕入, gross profit calculation breaks
  - If logistics is included, margin looks different

- **NEED FOR CLARIFICATION:**
  - SEM-006 definition says "材料・部品・生産外注費等を仕入先から調達"
  - Should be comprehensive, but Logsys specifics unclear

### Logsys上の表現候補
- 仕入 table with cost types unclear from schema
- 仕入諸掛 (supplementary costs) — what's included?

### 優先度
**🟡 MEDIUM** — Affects SEM-008 calculation; can surface during Phase 11 testing

---

## 18. 顧客 (Customer) — MEDIUM

### Current AI Understanding
- Treated as stable master entity
- Low risk; generally supported well by 顧客 table

### Misunderstanding Risk
- **NAME VARIATIONS:**
  - Japanese business names can have variants (full name, abbreviated, alternate kanji)
  - Lookup by name might fail; should use ID

- **RELATIONSHIP vs ENTITY:**
  - Is 「顧客」the entity or the relationship?
  - Can single business entity have multiple "顧客" records?

- **IMPACT:**
  - Mostly low risk due to master table existence
  - Main issue is name-based lookup fallibility

### Logsys上の表現候補
- 顧客 table is well-maintained master

### 優先度
**🟡 MEDIUM** — Generally low risk; name normalization needed

---

## 19. 会社粗利 (Company Gross Profit) — MEDIUM

### Current AI Understanding
- Assumed to be consolidated gross profit across all business

### Misunderstanding Risk
- **LEVEL OF CONSOLIDATION:**
  - By division (OEM vs Retail)?
  - By customer segment?
  - By staff team?
  - Across entire company?

- **NOT MODELED:**
  - "会社粗利" is not in current Semantics
  - May become query target later ("会社全体の粗利は?")

- **CALCULATION:**
  - If SEM-008 calculation logic is defined per-project, company-level aggregation should follow

### 優先度
**🟡 MEDIUM** — May surface as future query target

---

## 20. 粗利率 (Margin Ratio) — MEDIUM

### Current AI Understanding
- Assumed to be 粗利 / 売上 * 100%

### Misunderstanding Risk
- **DENOMINATOR AMBIGUITY:**
  - Is it 粗利 / 売上 or 粗利 / 売上原価?
  - Different formulas = very different ratios

- **CALCULATION TIMING:**
  - When is it calculated (per transaction, per month, rolling)?

- **VS 粗利額:**
  - Not currently distinguished; may cause confusion

### 優先度
**🟡 MEDIUM** — Clarification needed if ratio queries become common

---

## Summary Statistics

| Risk Level | Count | Examples |
|-----------|-------|----------|
| 🔴 CRITICAL | 3 | 案件, 粗利, OEM vs Retail |
| 🟠 HIGH | 7 | 受注, 発注, ステータス, キャンセル, 実績原価, PO, 商品単位 |
| 🟡 MEDIUM | 10 | 予定, 返品, 入金, 担当者, 締め, 納品, 仕入, 顧客, 会社粗利, 粗利率 |
| **Total** | **20** | — |

---

**Next Step:** Create Product Owner Review Request with 5 critical questions
