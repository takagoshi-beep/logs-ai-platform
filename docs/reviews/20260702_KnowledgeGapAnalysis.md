# AI Knowledge Gap Analysis

**Date:** 2026-07-02  
**Phase:** 11 — AI Quality Review  
**Purpose:** AI identifies concepts it doesn't yet understand  
**Status:** Self-Assessment (No Changes; Learning-Only)

---

## Knowledge Gap Summary

AI OS currently operates with **partial understanding** of critical business concepts. Below are gaps ranked by priority for learning.

**Total Concepts Analyzed:** 25  
**HIGH Priority (★★★★★):** 8 concepts  
**MEDIUM Priority (★★★★):** 12 concepts  
**LOW Priority (★★★):** 5 concepts  

---

## HIGH PRIORITY GAPS — Must Learn for Production Quality

---

### ★★★★★ 案件 (Project/Case) — CRITICAL BLOCKER

**Current Understanding**
- PO単位案件 exists (vendor purchase order unit)
- 商品単位案件 exists (product family unit)  
- Unclear which to use when
- Multiple other granularities possible (customer-unit, sales-unit, etc.)

**What's Missing**
- Which granularity is primary for LOGS business?
- How do PO-unit and product-unit relate? (1:1, 1:many, many:many?)
- When user asks "Fanatics案件", what should I return?
- How should I handle ambiguous cases (multiple POs for same product)?
- What's the case lifecycle (creation → status transitions → completion)?

**Why It Matters for Answer Quality**
- Q2 (Fanatics案件状況): Cannot answer without knowing case granularity
- Q3 (優先案件): Cannot rank if don't know which unit has deadline
- Q1 (OEM粗利): May aggregate at wrong granularity
- **Impact:** 50% of sample queries blocked or returns wrong granularity

**AI's Current Behavior**
- Returns all matching aggregations (likely multiple units mixed)
- No way to disambiguate
- Confidence: 0.4 (low; substantial risk of wrong answer)

---

### ★★★★★ 粗利 (Gross Profit) — Calculation Ambiguity

**Current Understanding**
- Three variants exist: 論理粗利, 実績粗利, 担当者別粗利
- Stored in 集計.案件粗利 (one value)
- Calculated from: 売上 - 仕入 - 仕入諸掛

**What's Missing**
- **CRITICAL:** Which variant should be used by default?
- When is 論理粗利 appropriate? (planning phase? forecast?)
- When is 実績粗利 required? (month-end? final decisions?)
- How do I know which variant is available? (If 実績原価 missing, fallback to 論理?)
- Should operational cost components (②③④ in 集計) be included?
- What about 粗利率 (ratio) vs 粗利額 (amount)? Different calculations?

**Why It Matters for Answer Quality**
- Q1 (OEM粗利): Returns single number, but may be using wrong variant
- Could report 30% margin when actual is 15% (or vice versa)
- Affects all profit-related decisions and KPI tracking
- **Impact:** Q1 produces potentially 50%+ wrong answers

**AI's Current Behavior**
- Uses 集計.案件粗利 (one pre-calculated field)
- No way to distinguish which variant it is
- Confidence: 0.5 (moderate; uncertainty on interpretation)

---

### ★★★★★ OEM案件 vs Retail案件 — Classification Criteria

**Current Understanding**
- OEM = custom-designed; Retail = off-the-shelf (assumed)
- Stored in 集計.分類 (classification field)
- Classification logic not documented

**What's Missing**
- What are the actual values in 集計.分類?
- How is OEM/Retail distinction determined? (customer type? product type? order characteristics?)
- Are there edge cases? (samples, trials, test orders?)
- Can a single customer have both OEM and Retail orders? (mixed portfolio?)

**Why It Matters for Answer Quality**
- Q1 (OEM粗利): Filters entire dataset by OEM
- If classification is wrong, captures wrong cases (entire answer is wrong)
- Affects business segment analysis, KPI tracking, priority decisions
- **Impact:** Q1 may return completely wrong subset

**AI's Current Behavior**
- Looks for "OEM" in question text
- Assumes 集計.分類 indicates OEM (unverified)
- Confidence: 0.3 (very low; high risk)

---

### ★★★★★ ステータス (Status Codes) — Inconsistency

**Current Understanding**
- 売上.ステータス: 有効/キャンセル/テスト (observed)
- 仕入.ステータス: Unknown
- 発注依頼.ステータス: Unknown
- Each table may use different encoding (text vs. codes)

**What's Missing**
- What are ALL valid status values per table? (売上/仕入/発注依頼/etc.)
- Are they codes (e.g., 1, 2, 3) or text (e.g., "active", "pending")?
- Should キャンセル orders be completely excluded, kept with negative impact, or archived?
- Should テスト orders be filtered out universally?
- Are there other status values not yet observed?

**Why It Matters for Answer Quality**
- Filtering logic depends entirely on status understanding
- If status values are wrong, query returns empty or wrong results
- Affects accuracy of all financial queries (sales, profit, etc.)
- **Impact:** All queries produce wrong answers if status filtering is wrong

**AI's Current Behavior**
- Hardcodes ステータス=有効 filter
- Guesses other tables follow same pattern (risky)
- Confidence: 0.4 (low; likely to be wrong on new tables)

---

### ★★★★★ 実績原価 vs 論理原価 — When to Use Each

**Current Understanding**
- 実績原価 = actual cost after procurement (more accurate)
- 論理原価 = standard/budgeted cost (available earlier)
- Both may exist for same product

**What's Missing**
- **CRITICAL:** When should each be used?
  - Planning phase → 論理?
  - After month-close → 実績?
  - In-flight orders → which?
- If one is missing, what's the fallback? (estimate? error?)
- How do I detect which is available for a given dataset?
- What's the timing? (When does 実績原価 become available?)

**Why It Matters for Answer Quality**
- Gross profit = Revenue - Cost
- Using wrong cost basis gives completely wrong profit numbers
- Could be off by 20-50% depending on case
- **Impact:** Financial queries (Q1, Q4) produce wrong answers

**AI's Current Behavior**
- Uses whatever costs are in Logsys (doesn't know which type)
- Assumes cost basis is consistent (likely wrong)
- Confidence: 0.4 (low; high risk of wrong calculation)

---

### ★★★★★ キャンセル (Cancellation) — Handling Logic

**Current Understanding**
- 売上.ステータス = キャンセル indicates cancelled sale
- Should probably be excluded from aggregations
- But exact logic for handling is unknown

**What's Missing**
- At what stage can sales be cancelled? (at order? after shipment?)
- Is cancellation reversible? (can be un-cancelled?)
- Should キャンセル rows be excluded from ALL queries, or kept separately?
- If excluded, what about historical analytics? (does キャンセル affect month-to-date?)
- Partial cancellation possible? (cancel 500 of 1000 units?)

**Why It Matters for Answer Quality**
- Including キャンセル in profit queries inflates margins (cancelled items appear as losses)
- Excluding when should include under-reports margins
- Affects all financial KPIs and trend analysis
- **Impact:** Q1, Q4 produce wrong numbers if cancellation handling is wrong

**AI's Current Behavior**
- Probably includes キャンセル in calculations (no explicit filter)
- May report inflated or deflated margins
- Confidence: 0.3 (very low; guessing on handling)

---

### ★★★★★ 返品 (Return / Reversal) — Recognition & Reversal

**Current Understanding**
- Product returned by customer
- Should reverse revenue and cost
- But exact mechanism unknown

**What's Missing**
- When can returns be accepted? (within X days? unlimited?)
- How are returns recorded? (negative rows? separate table? flag?)
- Are returns already reflected in aggregations? (or do I need to adjust?)
- Can returns be partial? (partial quantity)
- Should returns be included in monthly KPIs or listed separately?

**Why It Matters for Answer Quality**
- If returns aren't reversed properly, profit is overstated
- Could be off by 10-20% in volatile product lines
- Affects margin trends and historical analysis
- **Impact:** Q1, Q4 may produce wrong numbers if returns not properly accounted

**AI's Current Behavior**
- Unclear if 返品 is handled at all
- Probably includes returned items in totals (wrong)
- Confidence: 0.2 (very low; likely incorrect)

---

### ★★★★★ 期限 (Deadline) — Field & Definition

**Current Understanding**
- Deadline should exist for cases
- Not found in real DB schema analysis (Phase 10)
- Critical for priority ranking queries

**What's Missing**
- Where is deadline stored? (which table?)
- Field name? (期限? 納期? 予定日?)
- Is it different from actual delivery date (納品伝票日)?
- Can deadlines change? (project pushed out?)
- Is deadline tracking per case or per PO?

**Why It Matters for Answer Quality**
- Q3 (優先案件): Ranks by deadline
- Without this field, cannot rank urgency
- May return wrong priority order
- **Impact:** Q3 blocked or returns meaningless ranking

**AI's Current Behavior**
- Assumes 期限 exists (not verified)
- Can access it (not confirmed)
- Confidence: 0.2 (very low; likely doesn't exist in real DB)

---

## MEDIUM PRIORITY GAPS — Should Learn for Business Completeness

---

### ★★★★ 受注 (Order Confirmation) — State Machine

**Current Understanding**
- Customer places order (受注)
- Different from vendor purchase order (発注)
- Lifecycle unclear

**What's Missing**
- What state machine? (quote → confirmed → production → shipped → delivered?)
- Is 受注 just a status flag, or multi-state?
- Where is it tracked? (in 売上 table? separate table?)
- Can orders be changed after confirmation?

**Why It Matters**
- Future queries like "未受注案件" (unconfirmed orders)
- Affects workflow understanding

**Priority**
- MEDIUM: Not blocking current queries, but needed for future

---

### ★★★★ 発注 (Vendor Order) — Terminology Clarity

**Current Understanding**
- 発注 = placing order with vendor
- 発注依頼 table tracks this
- Different from customer order (受注)

**What's Missing**
- Confirm 発注依頼 table is vendor-side orders?
- Customer order table is different? (or part of 売上?)
- How do they link together?

**Why It Matters**
- Prevents terminology confusion
- Affects routing of queries

**Priority**
- MEDIUM: Confusion risk, but manageable

---

### ★★★★ 予定 (Plan / Schedule) — Field & Usage

**Current Understanding**
- Planned quantities, dates, forecasts exist
- Location unknown (not in real DB schema analysis)
- Used for forecasting/planning

**What's Missing**
- Where are plans stored? (Logsys? Google Sheets only?)
- Types of plans? (demand forecast? supply plan? schedule?)
- How plans relate to actuals?

**Why It Matters**
- Future "forecast vs. actual" queries
- Variance analysis

**Priority**
- MEDIUM: Not for current queries; plan-based analysis later

---

### ★★★★ 納品 (Delivery) — Timing & Tracking

**Current Understanding**
- 売上.納品伝票日 captures delivery date
- Physical handoff to customer
- May be partial or staged

**What's Missing**
- Is this date shipped or date received by customer?
- Can delivery be partial? (split shipments)
- Can delivery be delayed? (tracked as separate event?)
- Is delivery status tracked (on-time vs. late)?

**Why It Matters**
- "On-time delivery rate" analysis
- Delivery variance tracking

**Priority**
- MEDIUM: Operational metrics, important but not critical

---

### ★★★★ 担当者 (Staff / Assignment) — Role & Allocation

**Current Understanding**
- 集計 table has 社員id, 営業事務id
- Staff assigned to projects/customers
- Used for 担当者別粗利 (profit by staff)

**What's Missing**
- How many staff per case? (can staff be reassigned mid-project?)
- How is 担当者別粗利 calculated if multiple staff?
- Is staff history tracked? (who was owner at which time?)
- Does all work go to same person, or split by stage?

**Why It Matters**
- Performance/KPI tracking by staff
- Incentive management
- Workload balancing

**Priority**
- MEDIUM: Important for HR/management but not for Q1-Q4

---

### ★★★★ 締め (Close / Month-End) — Period Definition

**Current Understanding**
- Calendar month vs. fiscal month distinction unclear
- All transactional tables have 期 column
- Meaning of 期 unknown

**What's Missing**
- Does LOGS use calendar months (1-31) or fiscal months (e.g., Feb-Jan for Japanese FY)?
- Does 期 in tables represent this? (values?)
- Are there custom periods? (rolling 4-week?)
- Consistent across all divisions?

**Why It Matters**
- All monthly queries depend on this (Q1, Q4)
- Month-end close procedures
- Reporting accuracy

**Priority**
- MEDIUM: Critical for monthly queries, but can infer

---

### ★★★★ OEM / Retail / 商品単位 — Related Classification

**Current Understanding**
- OEM = custom design, Retail = catalog (assumed)
- 商品 (product unit) is separate concept
- How they interrelate: unknown

**What's Missing**
- Can one product be both OEM and Retail? (sold both ways?)
- Is OEM/Retail a property of product, customer, or order?
- How to classify ambiguous cases?
- Do classification rules differ by product family?

**Why It Matters**
- Business segment analysis
- Margin analysis by segment

**Priority**
- MEDIUM: Important for strategy, but can work around

---

### ★★★★ 会計期間 (Accounting Period) — Calendar Alignment

**Current Understanding**
- Transactions are tagged by period (期)
- Possibly calendar month or fiscal month
- Rules for period assignment unclear

**What's Missing**
- When is transaction assigned to period? (by date? by close date?)
- Can transactions move between periods? (adjustments?)
- Are there partial periods? (mid-month cutoffs?)

**Why It Matters**
- Period-based reporting consistency
- Accrual accounting vs. cash basis

**Priority**
- MEDIUM: Operational detail, manageable

---

### ★★★★ 入金 (Payment Received) — Timing & Recognition

**Current Understanding**
- Customer payment is recognized
- Different from revenue recognition
- Used for cash flow analysis

**What's Missing**
- When is 入金 recorded? (on payment date? when cleared?)
- Partial payments possible?
- How does 入金 relate to 売上? (same transaction?)
- Can there be sales without payment? (credit terms?)

**Why It Matters**
- Cash flow forecasting
- Aging analysis

**Priority**
- MEDIUM: Financial management, important later

---

### ★★★★ 粗利率 (Margin Ratio) — Calculation Formula

**Current Understanding**
- Ratio of profit to revenue (assumed)
- Different from 粗利額 (absolute margin amount)

**What's Missing**
- Formula: 粗利 ÷ 売上 × 100%? Or different?
- Consistency of ratio definition across organization?
- Used for comparisons: product profitability? customer value? segment health?

**Why It Matters**
- Performance metrics
- Strategic decisions (which segments to grow?)

**Priority**
- MEDIUM: Analytical metric, important but derivable

---

### ★★★★ 顧客担当者 / 顧客 — Relationship Tracking

**Current Understanding**
- 顧客 (customer master) with 2,738 records
- 顧客担当者 (customer contact) with 3,816 records
- Relationship between them unclear

**What's Missing**
- 1 customer : many contacts?
- How does contact relate to case assignment?
- Can contacts change mid-project?
- Primary vs. secondary contacts?

**Why It Matters**
- Communication management
- Relationship continuity

**Priority**
- MEDIUM: CRM-related, useful but not critical

---

### ★★★★ 商品分類 / 事業分類 — Dual Classification

**Current Understanding**
- 商品 table has both 商品分類 and 事業分類 columns
- Both indicate product/business type
- Difference unknown

**What's Missing**
- What does 商品分類 represent? (product family? category? supplier?)
- What does 事業分類 represent? (business division? channel? strategy?)
- Are they hierarchical? (one is sub-type of other?)
- Which is used for OEM/Retail distinction?

**Why It Matters**
- Product portfolio analysis
- Segment reporting

**Priority**
- MEDIUM: Organizational structure, useful

---

## LOW PRIORITY GAPS — Nice to Understand, Can Work Around

---

### ★★★ 社員 (Employee) — Organization Structure

**Current Understanding**
- Staff tracked in 社員id columns
- Used for 担当者別粗利 and assignments
- Full employee data not in Logsys (references only)

**What's Missing**
- Is full employee master table available?
- Organizational hierarchy? (reporting structure?)
- Department assignments?

**Priority**
- LOW: Can reference by ID; don't need full details

---

### ★★★ 仕入先 / 取引先 — Vendor Management

**Current Understanding**
- 取引先 (trading partner / vendor) table exists
- Procurement counterparty
- Details unknown

**What's Missing**
- Vendor performance metrics?
- Vendor classification?
- Lead times?

**Priority**
- LOW: Can fetch procurement data without vendor details

---

### ★★★ 仕入 Details — Procurement Composition

**Current Understanding**
- 仕入 = material + component + external processing costs
- Breakdown mechanism unknown

**What's Missing**
- Are cost components separated? (material vs. processing vs. logistics?)
- Can I distinguish labor vs. materials?
- Is externally-processed work tracked separately?

**Priority**
- LOW: Works with aggregate; details are nice to have

---

### ★★★ コード (Code Registry) — Metadata Mapping

**Current Understanding**
- Central registry for business codes
- 199 records

**What's Missing**
- What do codes represent? (customer codes? product codes? status codes?)
- Is this used for mapping/translation?

**Priority**
- LOW: System working without full code understanding

---

### ★★★ Google Drive Sync — Data Provenance

**Current Understanding**
- Logsys is synced from Google Drive sheets
- 11 sync/import tables track this
- Details of sync logic unknown

**What's Missing**
- Sync frequency? (daily? hourly?)
- Conflict resolution? (what if both sides change?)
- Data freshness SLA?

**Priority**
- LOW: Infrastructure detail; doesn't affect query quality

---

## Knowledge Gap Priority Matrix

```
Concept              Priority  Current Confidence  Blocker?
─────────────────────────────────────────────────────────
案件 (Project)       ★★★★★    0.3                YES
粗利 (Profit)        ★★★★★    0.5                YES
OEM/Retail分類       ★★★★★    0.3                YES
ステータス           ★★★★★    0.4                YES
実績原価             ★★★★★    0.4                YES
キャンセル           ★★★★★    0.3                YES
返品                 ★★★★★    0.2                YES
期限                 ★★★★★    0.2                YES
受注                 ★★★★    0.4                NO
発注                 ★★★★    0.5                NO
予定                 ★★★★    0.2                NO
納品                 ★★★★    0.5                NO
担当者               ★★★★    0.4                NO
締め                 ★★★★    0.4                NO
商品単位             ★★★★    0.5                NO
会計期間             ★★★★    0.3                NO
入金                 ★★★★    0.2                NO
粗利率               ★★★★    0.4                NO
顧客                 ★★★★    0.7                NO
社員                 ★★★     0.5                NO
仕入先               ★★★     0.4                NO
仕入詳細             ★★★     0.6                NO
コード               ★★★     0.3                NO
GDrive Sync          ★★★     0.5                NO
```

---

## Learning Priority Recommendation

**Immediate (Before Production):**
1. 案件 (granularity: PO vs Product vs Customer?)
2. 粗利 (which variant to use when?)
3. OEM/Retail (classification criteria?)
4. ステータス (values per table?)
5. 実績原価 (when available? fallback?)

**Short-term (For robustness):**
6. キャンセル (exclusion logic?)
7. 返品 (reversal mechanism?)
8. 期限 (field location/name?)

**Medium-term (For completeness):**
9-19. Remaining concepts

---

**Ready for Product Owner Teaching Session**

