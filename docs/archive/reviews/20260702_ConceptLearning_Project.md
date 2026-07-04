# Concept Learning Session：案件 (Project/Case)

**Date:** 2026-07-02  
**Purpose:** AI system learns correct "案件" concept definition through dialogue with Product Owner  
**Format:** Conversational exploration (not yes/no checklist)  
**Status:** Preparation — awaiting Product Owner responses

---

## AI's Current Understanding

The AI system currently understands "案件" as a **single project/case entity** that:
- Represents a "series of business activities tracked end-to-end"
- Has a unique identifier
- Links to customer, products, sales, and delivery
- Is the unit for gross profit analysis and priority ranking

**However**, Product Owner revealed this is **incomplete**. "案件" actually has **multiple interpretations** in Logsys:

- **PO単位案件** — organizational unit at Purchase Order level
- **商品単位案件** — organizational unit at Product family level  
- **Potentially also:** customer-unit, sales-unit, delivery-unit groupings

**Current Problem:** AI doesn't know which granularity to use in different business contexts.

---

## Learning Objectives

By end of this session, AI should understand:

1. ✓ What PO単位案件 means in Logsys and when it's used
2. ✓ What 商品単位案件 means in Logsys and when it's used
3. ✓ How to choose correct granularity for business questions
4. ✓ What data fields define each granularity
5. ✓ How to represent each in Semantic system
6. ✓ How this affects reasoning pipeline behavior

---

## Part 1: PO Single Unit Case

### Q1.1: What is PO単位案件?

**AI's Current Understanding:**
- PO単位 (Purchase Order unit) is a **procurement-side organizational granule**
- One vendor PO = one case unit
- Used in procurement/ordering workflows

**Clarifying Questions for Product Owner:**

① In Logsys, what exactly defines a "PO単位案件"?
   - Is it literally one row in 発注依頼 table?
   - Or multiple 発注依頼 rows grouped by customer?
   - Or something else?

② When you manage a PO単位案件, what information do you track?
   - Vendor name?
   - Ordered quantity?
   - Ordered date?
   - Expected delivery date?
   - Status (confirmed/pending/received)?
   - Cost tracking?

③ Who typically manages PO単位案件 in your organization?
   - Procurement team?
   - Production management?
   - Both?

④ In what business scenario would someone ask "このPO単位案件の状況は?" (what's the status of this PO-level case)?
   - Example use case?

---

### Q1.2: How Does PO単位案件 Relate to Logsys Tables?

**Candidate Mapping:**

```
PO単位案件 ← 発注依頼 table (34,733 rows)
  ├─ Primary Key: 発注依頼.id (unique PO identifier?)
  ├─ Links to vendor: 発注依頼.po_no (PO number?)
  ├─ Status tracking: 発注依頼.ステータス (status field)
  ├─ Timeline: 発注依頼.po発行日時, po修正日時
  └─ Cost: 発注依頼.金額 (procurement amount)
```

**Questions for Product Owner:**

① Is my mapping above correct?

② Can a single customer order (from your perspective) map to **multiple** 発注依頼 POs?
   - Example: Customer orders 1000 units → you split into 2 vendors?
   - If yes: Do you track this as 1 customer case or 2 vendor cases?

③ Can a single 発注依頼 PO be split across **multiple** customer deliveries?
   - Example: Vendor ships 500 units now, 500 later?
   - If yes: How do you associate each shipment back to original PO?

④ When does a PO単位案件 "complete"?
   - When PO is confirmed?
   - When goods are received?
   - When goods are used in production?
   - When invoice is paid?

---

## Part 2: Product-Unit Case

### Q2.1: What is 商品単位案件?

**AI's Current Understanding:**
- 商品単位 (Product family unit) is a **sales/planning-side organizational granule**
- One product family = one case unit
- Used in sales/forecasting/margin analysis workflows
- Tracked in 集計 (aggregation) table

**Clarifying Questions for Product Owner:**

① In Logsys, what exactly defines a "商品単位案件"?
   - Is it literally one row in 集計 table?
   - Or multiple rows grouped by product?
   - What's the primary key?

② When you manage a 商品単位案件, what information do you track?
   - Product name/model?
   - Planned quantity?
   - Planned sales revenue?
   - Gross profit?
   - Sales forecast?
   - Actual vs. planned variance?

③ Who typically manages 商品単位案件 in your organization?
   - Sales team?
   - Product planning?
   - Management (for KPIs)?
   - All three?

④ In what business scenario would someone ask "この商品単位案件の粗利は?" (what's the margin of this product-level case)?
   - Example use case?

---

### Q2.2: How Does 商品単位案件 Relate to Logsys Tables?

**Candidate Mapping:**

```
商品単位案件 ← 集計 table (16,705 rows)
  ├─ Primary identifier: 集計.案件名 (case name - but is this unique?)
  ├─ Product reference: 集計.分類 or inferred from name?
  ├─ Customer reference: 集計.顧客id, 顧客名
  ├─ Sales tracking: 集計.案件売上 (project sales)
  ├─ Profit tracking: 集計.案件粗利 (project gross profit)
  ├─ Operations: 集計.①②③④ cost components
  └─ Staff: 集計.社員id (assigned person)
```

**Questions for Product Owner:**

① Is my mapping above correct?

② Why is 商品単位案件 stored in 集計 (aggregation) rather than a dedicated master table?
   - Is this temporary/aggregated output?
   - Or the official project record?

③ Can one customer order span **multiple** 商品単位案件?
   - Example: Customer orders product A AND product B → 2 product-unit cases?
   - If yes: Are they tracked separately or grouped under one case?

④ Can one 商品単位案件 span **multiple** customers?
   - Example: Product A is sold to customers X and Y → 1 case or 2?
   - If 1 case: How is revenue/margin split?

⑤ When does a 商品単位案件 "complete"?
   - When sales order is confirmed?
   - When goods are shipped?
   - When goods are received by customer?
   - When revenue is recognized?
   - When payment is received?

---

## Part 3: Choosing the Right Granularity

### Q3.1: When to Use PO単位 vs 商品単位?

**Scenario A: Business Question**

> "Fanatics案件の状況を教えてください" (Tell me the status of Fanatics case)

**Current AI Problem:** 
- Should I return PO-level status or product-level status?
- If Fanatics has 3 POs with 2 different products, what do I return?
- Should I ask for clarification?

**Questions for Product Owner:**

① When a user asks about "Fanatics案件", what are they most likely asking for?
   - All POs to Fanatics? (PO-unit aggregation)
   - All products ordered by Fanatics? (product-unit aggregation)
   - Current status across both dimensions?

② Should AI:
   - Option A: Always interpret as PO-unit (procurement-focused)
   - Option B: Always interpret as product-unit (sales-focused)
   - Option C: Ask user to clarify?
   - Option D: Return both views?

---

### Q3.2: Gross Profit Analysis

> "OEM粗利は?" (What's the gross profit for OEM business?)

**Current AI Understanding:**
- Sum all gross profit for OEM cases
- But: Which granularity (PO vs product)?

**Scenario 1: Same customer, different POs**
- Fanatics case has:
  - PO #1: Product A, ¥1000 sales, ¥600 profit
  - PO #2: Product B, ¥500 sales, ¥200 profit
- Do I report:
  - A) ¥600 profit (PO #1 only)?
  - B) ¥800 profit (both POs)?
  - C) Split by product?

**Scenario 2: Same product, different POs**
- Product A case has:
  - PO #1 to Fanatics: ¥1000 sales, ¥600 profit
  - PO #2 to Nike: ¥2000 sales, ¥1000 profit
- Do I report:
  - A) ¥600 (just Fanatics)?
  - B) ¥1600 (both customers)?
  - C) Each separately?

**Questions for Product Owner:**

① For monthly profit queries like "OEM粗利", should AI:
   - Sum at PO-unit level?
   - Sum at product-unit level?
   - Something else?

② If business model is:
   - Many customers × Many products = many combinations
   - What is "OEM粗利"?
     - All OEM POs?
     - All products sold through OEM channel?
     - All cases tagged as OEM?

---

### Q3.3: Priority Ranking

> "本日優先すべき案件を教えて" (What cases should I prioritize today?)

**Current AI Understanding:**
- Rank cases by deadline urgency
- But: Which granularity?

**Questions for Product Owner:**

① When prioritizing, are you thinking about:
   - Individual POs (vendor-side urgency)?
   - Product families (sales-side urgency)?
   - Customer account (relationship management)?
   - Something else?

② If you have:
   - Fanatics case: 3 active POs, 2 products, deadline today
   - Nike case: 1 active PO, 1 product, deadline tomorrow

   Which should rank higher, and why?

③ What fields drive priority?
   - Deadline (納期)?
   - Profit amount (粗利)?
   - Profit margin (粗利率)?
   - Risk level?
   - Customer strategic importance?
   - Multiple of above?

---

## Part 4: Semantic System Representation

### Q4.1: How Should "案件" Be Represented in AI System?

**Current Semantic Definition (SEM-009):**
```
SEM-009: 案件

定義: LOGSが対応する一連の業務活動の単位。
     単一の顧客への単一の納品約定から、
     完全納品・完金まで、一貫して追跡・管理される
     最小ビジネスユニット

確認状態: Pending
```

**Problem:** This definition doesn't account for multiple granularities.

**Candidate Restructuring:**

**Option A: Single "案件" with sub-types**
```
SEM-009: 案件 (generic unit)
  ├─ SEM-009-PO: PO単位案件 (vendor PO unit)
  ├─ SEM-009-PROD: 商品単位案件 (product unit)
  └─ [possibly more]
```

**Option B: Separate Semantics**
```
SEM-009: 案件-商品単位 (product-unit case)
SEM-011: 案件-PO単位 (PO-unit case)
[and possibly others]
```

**Option C: Context-dependent interpretation**
```
SEM-009: 案件 (generic)
  [Actual meaning depends on question context:
   - For profit analysis → product-unit
   - For procurement tracking → PO-unit
   - For customer management → customer-unit
   etc.]
```

**Questions for Product Owner:**

① Which representation makes most sense for your business?
   - Option A (single semantic with subtypes)?
   - Option B (separate semantics)?
   - Option C (context-dependent)?
   - Something else?

② For internal communication at LOGS, how do people typically refer to cases?
   - "Fanatics PO案件"?
   - "FanaticsJersey商品案件"?
   - Just "Fanatics案件" (context-dependent)?

③ Are there other case granularities beyond PO and Product that matter?
   - Customer-unit ("Fanatics全体の案件")?
   - Sales-unit ("This specific sale")?
   - Delivery-unit ("This shipment")?
   - Other?

---

## Part 5: Implementation Questions

### Q5.1: Data Structure in Logsys

**When 案件 is redesigned, what data needs to be tracked?**

**Current Logsys has:**
- 売上 (sales transactions): 199k rows
- 仕入 (procurements): 44k rows
- 集計 (aggregations): 16k rows
- 発注依頼 (vendor POs): 34k rows

**Missing from real DB:**
- Dedicated 案件 master table with:
  - 案件id (unique ID)
  - 案件名 (case name)
  - 顧客id (customer)
  - 案件種別 (case type: PO-unit? Product-unit?)
  - ステータス (status)
  - 期限 (deadline)
  - [and more]

**Questions for Product Owner:**

① Should there be ONE dedicated 案件 master table?
   - Or separate tables for PO-unit and product-unit?

② What are the **minimum required fields** for a 案件 record?
   - Which fields are always present?
   - Which are optional?
   - Which change during case lifecycle?

③ How should 案件 relate to existing Logsys tables?
   - 案件 ← 売上? (1:many)
   - 案件 ← 仕入? (1:many)
   - 案件 ← 発注依頼? (1:many)
   - All of above?

④ What's the source of truth for 案件 data?
   - Google Drive sheets?
   - SQLite Logsys?
   - Combination?

---

### Q5.2: Reasoning Pipeline Behavior

**How should AI behavior change based on 案件 definition?**

**Example Q1: OEM粗利分析**
```
User: "今月のOEM粗利は？"

Current Pipeline:
1. Recognize "OEM" (SEM-001) + "粗利" (SEM-008)
2. Query 売上 + 仕入 for OEM cases
3. Calculate gross profit
4. Return result

WITH correct 案件 definition:
1. Recognize "OEM" + "粗利"
2. Identify 案件 granularity: should use 商品単位 or PO単位?
3. Query correct 案件 table or aggregation
4. Calculate profit at correct granularity
5. Return result
```

**Questions for Product Owner:**

① For Q1 (OEM粗利):
   - Should AI sum by product-unit?
   - Or by PO-unit?
   - Or by some other grouping?

② For Q2 (Fanatics案件状況):
   - Should AI return single status?
   - Or list of multiple POs/products?
   - Or ask user to clarify?

③ For Q3 (優先案件):
   - Should AI rank by PO deadline?
   - Or by product project deadline?
   - Or by customer account urgency?

④ For Q4 (売上首位顧客):
   - Should AI use transaction-level data (sales table)?
   - Or 案件-level aggregation?
   - Or product-level aggregation?

---

## Part 6: Questions Still Unanswered

**Topics that emerged but need deeper exploration:**

- [ ] How do customer order (from Fanatics perspective) vs vendor PO (from LOGS perspective) map together?
- [ ] When does a case "belong" to one 案件 vs split across multiple?
- [ ] What's the lifecycle of a 案件? When does it start, progress, complete?
- [ ] Can cases be reassigned, merged, split, or cancelled mid-lifecycle?
- [ ] How does 予定 (plan/schedule) relate to 案件? Is it a field or separate concept?
- [ ] How should AI handle partially-complete cases (some items delivered, some in production)?

---

## Expected Output After Product Owner Response

Once Product Owner answers these questions, AI system should produce:

### 1. Updated AI Understanding Document
```
案件（Updated Understanding v1）
├─ PO単位案件: [clarified definition based on Q1 answers]
├─ 商品単位案件: [clarified definition based on Q2 answers]
├─ Logsys mapping: [confirmed table/field linkages]
└─ Implementation rules: [how to use each in reasoning]
```

### 2. Semantic System Updates (Not yet — awaiting confirmation)
```
[Will update SEM-009 definition]
[Will define representation approach (A/B/C)]
[Will add SEM-011+ if new granularities identified]
[Will update reasoning_pipeline.py logic]
```

### 3. Reasoning Pipeline Behavior Document
```
When user asks "X案件のY":
├─ If X=customer name: Use 案件-商品単位 (or PO単位?)
├─ If X=product name: Use 案件-商品単位
├─ If X=vendor name: Use 案件-PO単位
└─ [other patterns]
```

### 4. Logsys Implementation Roadmap
```
Phase 11 Task 1: Design 案件 master table
├─ Table structure
├─ Primary keys
├─ Relationships
└─ Population strategy
```

---

## Session Format Notes

**This is NOT a Yes/No/修正 questionnaire.**

This is a **learning dialogue** where:
- Product Owner teaches concept details
- AI asks exploratory questions
- Both parties clarify assumptions
- Shared understanding builds

**Expected Duration:** 60-90 minutes (1 conversation session)

**Recommended Approach:**
1. Product Owner reads AI's current understanding
2. Product Owner reads all Q sections
3. Product Owner provides narrative explanation OR answers Q's in order
4. AI system processes responses and updates understanding
5. [Iterate if gaps remain]

---

## Important Notes

**What will NOT happen today:**
- ❌ Semantic Catalog modification
- ❌ Reasoning Pipeline code changes
- ❌ Database schema modifications
- ❌ New table design (that's Phase 11)
- ❌ Any commits

**This session is LEARNING ONLY** — no implementation changes until all concepts are confirmed.

---

**Ready for Product Owner Response**  
**Format:** Narrative explanation preferred; can also answer Q numbers sequentially  
**Response Channel:** Email, meeting notes, or comment on this document
