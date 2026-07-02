# Business Rules — LOGS Consultation Engine Decision Rules

**Date:** 2026-07-01  
**Status:** v0.1 (Phase 5-2 Foundation)  
**Purpose:** Document business rules that guide AI responses and decision-making in the consultation engine

**Source:** Extracted from reference/01_business/verified_business_rules.md; adapted for immediate consultation use.

---

## Overview

Business Rules govern:
- **What data to trust** (sources, conditions, exceptions)
- **What calculations to use** (gross profit variant, cost allocation, aggregation)
- **What to clarify** (when data is ambiguous, confirm with user)
- **What constraints to enforce** (grain/dimension rules, filter requirements)

---

## Rule Category: Sales & Revenue

### BR-SALES-STANDARD-001: Standard Sales Aggregation Filter

**Rule ID:** BR-SALES-STANDARD-001  
**Status:** Verified (user confirmed 2026-06-30)  
**Scope:** Standard sales analysis (not exception business like billing, receivables, audit)

**Statement:**
Sales aggregation applies filter: `status IN (2,3,4,5)` AND `payment_method != 4`

**When to Use:**
- Customer sales analysis
- Product sales analysis
- Sales person performance
- Revenue forecasting
- Profitability analysis

**When NOT to Use:**
- Billing/receivables management
- Audit/reconciliation
- Tax compliance
- Exception handling

**Implementation:**
```sql
WHERE status IN (2,3,4,5) AND payment_method != 4
```

**Failure Mode:** If analysis doesn't apply this filter, result may include invalid/test/cancelled sales; revenue overstated.

---

### BR-SALES-DETAIL-003: Sales Calculations Use Line-Item Basis

**Rule ID:** BR-SALES-DETAIL-003  
**Status:** Verified (user confirmed 2026-06-30)

**Statement:**
Sales amount, gross profit, and gross profit rate are calculated from line-item (detail) data, not header totals.

**Rationale:**
Header values may be pre-calculated, rounded, or inconsistent with detail. Detail is source of truth.

**Implementation:**

❌ WRONG:
```sql
SELECT sale_id, sale_header_amount, sale_header_gross_profit
```

✅ RIGHT:
```sql
SELECT 
    SUM(line_amount) as sales_total,
    SUM(line_gross_profit) as gross_profit_total,
    SUM(line_gross_profit) / NULLIF(SUM(line_amount), 0) as gross_profit_rate
```

---

### BR-SALES-RULESET-002: Exception Business Uses Different Rules

**Rule ID:** BR-SALES-RULESET-002  
**Status:** Verified (user confirmed 2026-06-30)

**Statement:**
Billing management, receivables management, audit, and data reconciliation may use different rule sets than standard sales analysis.

**When Different Rules Needed:**
- Billing → need to track partial payments, credit memos, disputes
- Receivables → need to track invoice date, payment terms, aging
- Audit → need to reconcile to GL, trace each transaction
- Reconciliation → may need to include all status codes for completeness

**Action for AI:**
- When user's question suggests exception business, ask: "Is this for [billing/receivables/audit/reconciliation] or standard sales analysis?"
- Apply appropriate rule set
- Document which rule set was used in response

---

## Rule Category: Profitability & Gross Profit

### BR-SALES-STANDARD-001 (already above)

### KPI-METRIC-002: Three Gross Profit Variants

**Rule ID:** KPI-METRIC-002  
**Status:** Verified (user confirmed 2026-06-30)

**Statement:**
Gross profit has 3 distinct variants. Always specify which variant is being used in response.

**Variants:**

1. **概算粗利 (Estimated Gross Profit)**
   - Formula: Found in sales table as pre-calculated value
   - Basis: Uses 論理原価 (logical/standard cost) or data entry estimates
   - When Available: Immediately when sale recorded, even if purchase not yet ordered
   - Use Case: Early-stage project valuation, sales forecast

2. **実際粗利 (Actual Gross Profit)**
   - Formula: SUM(Sales Amount) - SUM(Purchase Amount from purchases table)
   - Basis: Actual supplier invoices
   - When Available: After purchases recorded
   - Use Case: Final project profitability, post-mortem analysis, financials

3. **担当者粗利 (Staff-Attributed Profit)**
   - Formula: 実際粗利 - SUM(|Sales Staff Expense from budget_forecast category 05|)
   - Basis: Actual margin minus attributed staff cost
   - Grain Constraint: Only valid at staff level; cannot be allocated to customer/product/factory
   - Use Case: Staff evaluation, commission calculation

**Presentation Rule (PR-GROSS-PROFIT-LABEL-002):**
Always include label in response. Template:

```
"This gross profit is [概算/実際/担当者粗利].

If estimated:
"This uses estimated cost. Actual profit may differ once purchases are recorded."

If actual:
"This is calculated from actual sales and purchase records."

If staff-attributed:
"This accounts for sales staff expenses directly attributed to this person."
```

**Common Confusion Prevention:**
- ❌ Do NOT use "粗利" without specifying variant
- ❌ Do NOT compare estimated to actual without noting the difference
- ❌ Do NOT apply 担当者粗利 to non-staff dimensions

---

### BR-PROCUREMENT-COMPONENT-011: Purchase Amount Includes Surcharges

**Rule ID:** BR-PROCUREMENT-COMPONENT-011  
**Status:** Verified (user confirmed 2026-06-30)

**Statement:**
Purchases table `total_cost` field already includes import surcharges (freight, tariff, insurance). Do NOT add separate surcharge table.

**Why:**
- Simplicity: Avoid double-counting
- Accounting: Total cost landed is what matters for COGS

**Implementation:**

❌ WRONG:
```sql
SELECT SUM(purchases.total_cost) + SUM(purchase_surcharges.surcharge_amount)
```

✅ RIGHT:
```sql
SELECT SUM(purchases.total_cost)  -- includes surcharges already
```

**When Surcharge Detail Needed:**
If analysis requires breakdown of surcharge vs. product cost:
```sql
SELECT 
    SUM(purchases.total_cost - purchases.product_cost) as total_surcharges,
    SUM(purchases.product_cost) as product_cost,
    SUM(purchases.total_cost) as total_cost
```

---

## Rule Category: Entity Resolution

### ER-CANONICAL-001: Canonical Key Priority

**Rule ID:** ER-CANONICAL-001  
**Status:** Verified (user confirmed 2026-06-30)

**Statement:**
For all entities with formal codes (customer, product, supplier, staff), use canonical code as the unique identifier for queries. Never rely on display name alone.

**Applicable Entities:**
- Customer (use customer_code, not customer_name)
- Product (use product_code, not product_name)
- Supplier (use supplier_code)
- Staff (use staff_id, not staff_name)
- Factory/Facility (use facility_code)

**Process:**
1. User provides entity reference (name, partial code, alias)
2. Resolve to canonical code via semantic catalog
3. Use canonical code in query
4. Display result with canonical name in response

**Failure Mode:**
If canonical code not resolved:
- Check semantic catalog for aliases
- If still ambiguous, ask user: "Do you mean [Candidate A] or [Candidate B]?"
- Do NOT guess

---

### ER-NO-CODE-002: Fallback to Display Name (Rare)

**Rule ID:** ER-NO-CODE-002  
**Status:** Verified (user confirmed 2026-06-30)

**Statement:**
Only when canonical code unavailable, use display name via semantic catalog. Requires unique match.

**Conditions:**
- Canonical code not found in code table
- Display name EXACTLY matches one record in semantic catalog
- Confidence > 90%

**If Multiple Matches:**
Ask user for clarification. Do NOT pick one arbitrarily.

**If No Match:**
Suggest similar names from catalog. Ask: "Did you mean [Candidate 1] or [Candidate 2]?"

---

### ER-NO-GUESS-003: No Guessing

**Rule ID:** ER-NO-GUESS-003  
**Status:** Verified (user confirmed 2026-06-30)

**Statement:**
AI must not guess or assume entity identity. If uncertain, ask.

**Prohibited:**
- ❌ Assuming "Beams" refers to "BEAMS JAPAN" just because it's the only BEAMS customer
- ❌ Picking the highest-sales customer when multiple candidates
- ❌ Assuming timestamp refers to order date when it could be delivery date

**Required:**
- Ask user: "Which BEAMS entity did you mean?"
- Show candidates
- Wait for confirmation before proceeding

---

## Rule Category: Time & Period

### TIME-001: 「今月」はカレンダー月を指す

**Rule ID:** TIME-001  
**Status:** Verified (Product Owner confirmed 2026-07-02)

**Statement:**
「今月」はカレンダー月（当月1日〜当月末日）を指す。

**Example:**
- 2026-07-02 に質問された場合 → 今月 = 2026-07-01〜2026-07-31

**Implementation:**
```python
month_start = today.replace(day=1)
month_end = today.replace(day=monthrange(today.year, today.month)[1])
```

**Failure Mode:** 会計月・締め日ベースと混同すると期間がずれる。締め日ベースの分析が必要な場合は明示的に確認する。

---

### BR-TIME-RULESET-006: Time Period Interpretation Priority

**Rule ID:** BR-TIME-RULESET-006  
**Status:** Verified (user confirmed 2026-06-30)

**Statement:**
Time interpretation follows priority hierarchy:

1. **Explicit dates** — "2026-01-01 to 2026-03-31"
2. **Business vocabulary** — "今月", "先月", "前年同月", "直近3か月", "今年"
3. **Context from conversation** — "as we discussed last week"
4. **Ask for clarification** — If still ambiguous

**Implementation:**

```python
def resolve_time_period(user_input):
    if explicit_date_range_in_input:
        return explicit_date_range
    elif business_vocab_keyword in user_input:
        return map_keyword_to_date_range()
    elif conversation_context_available:
        return context_based_date_range
    else:
        ask_user("What time period did you mean?")
        return None
```

**Example:**
- User: "先月の売上" → This month = [prev_month_start, prev_month_end]
- User: "直近3か月" → [today - 90 days, today]
- User: "最近" → Default to 直近3か月

---

### BR-TIME-BASIS-DATE-007: Basis Date Matters

**Rule ID:** BR-TIME-BASIS-DATE-007  
**Status:** Verified (user confirmed 2026-06-30)

**Statement:**
Time period evaluation depends on basis date type:

| Analysis Type | Basis Date | Field |
|---|---|---|
| Sales revenue | Sale date (not order date) | sales.sale_date |
| Profitability | Sale date (for matching with purchases) | sales.sale_date |
| Cash flow | Payment date (when cash received) | sales.payment_date |
| Procurement | Purchase date (when invoice received) | purchases.purchase_date |
| Delivery tracking | Delivery date (when goods arrived) | sales.delivery_date |

**Action:**
- When user asks about time period, confirm: "Do you mean by sale date, delivery date, or payment date?"
- If not obvious, default to sale_date (most common)
- Document basis date choice in response

---

## Rule Category: Budget & Forecasting

### BR-BF-CATEGORY-009: Budget/Forecast Category Codes

**Rule ID:** BR-BF-CATEGORY-009  
**Status:** Verified (user confirmed 2026-06-30)

**Statement:**
Budget_forecast table has 3 categories, identified by `category_code`:
- **01** = 予算 (top-down budget)
- **02** = 予定 (operational plan)
- **05** = 費用 (actual expense)

Codes **03, 04** do NOT exist.

**When User Says:** | **Use Code:**
---|---
"予算" | 01
"予定" | 02
"費用" | 05
"発注" | NOT budget_forecast; use purchase_orders table instead
"実績" (expense context) | 05

**Implementation:**

```sql
WHERE category_code IN ('01', '02', '05')  -- Only valid codes
```

**Failure Mode:**
Querying category_code IN ('03', '04') returns no results, likely causing confusion.

---

### QPR-BF-CODE-NORMALIZATION-005: Always Use Code, Not Display Name

**Rule ID:** QPR-BF-CODE-NORMALIZATION-005  
**Status:** Verified (user confirmed 2026-06-30)

**Statement:**
SQL queries must use category_code (01/02/05), never display name (予算/予定/費用) in WHERE clauses.

**Why:**
Display names can change; codes are stable. Prevents future bugs.

❌ WRONG:
```sql
WHERE category_name = '予算'
```

✅ RIGHT:
```sql
WHERE category_code = '01'
```

---

## Rule Category: Cost Allocation & Constraints

### BR-STAFF-EXPENSE-GRAIN-012: Expense Allocation Grain Constraint

**Rule ID:** BR-STAFF-EXPENSE-GRAIN-012  
**Status:** Verified (user confirmed 2026-06-30)

**Statement:**
Sales staff expense (budget_forecast category 05) is tied to individual staff members. Can be used ONLY in staff grain analysis. Must NOT be allocated to customer, product, brand, or factory dimensions.

**Permitted:**
- 担当者粗利 (staff-attributed profit by staff member)
- Staff evaluation

**Prohibited:**
```sql
SELECT customer_id, SUM(staff_expense) -- ❌ Invalid allocation
SELECT product_id, SUM(staff_expense)   -- ❌ Invalid allocation
SELECT brand, SUM(staff_expense)         -- ❌ Invalid allocation
SELECT factory, SUM(staff_expense)       -- ❌ Invalid allocation
```

**Correct Usage:**
```sql
SELECT staff_id, SUM(staff_expense)  -- ✅ Only valid grain
```

---

## Rule Category: Data Interpretation

### IR-MASTER-CONFLICT-001: Master Data Conflicts

**Rule ID:** IR-MASTER-CONFLICT-001  
**Status:** Verified (user confirmed 2026-06-30)

**Statement:**
If product master conflicts with product name (e.g., master says category=Bags but name is "Apparel Shirt"):
1. Prioritize master data (category=Bags)
2. Reference name field for context
3. If unresolvable, escalate as Open Question

**Example:**
- Master: product_id=P123, category=Bags, brand=House Brand
- Name: "Apparel T-Shirt"
- Action: Use category=Bags (master), note discrepancy, ask: "Is this product miscategorized?"

---

### IR-NAME-RESOLUTION-003: Flexible Name Matching

**Rule ID:** IR-NAME-RESOLUTION-003  
**Status:** Verified (user confirmed 2026-06-30)

**Statement:**
Don't require exact name match. Try in this priority order:

1. **Exact code match** (e.g., customer code provided)
2. **Exact name match** (primary name)
3. **Alias match** (alternative name, abbreviation)
4. **Partial match** (substring search)
5. **Phonetic/spelling variation** (old name, transliteration)
6. **AI semantic inference** (last resort; low confidence)

**Example:**
- User: "BEAMS"
- Priority 1: Check if "BEAMS" is a code → No
- Priority 2: Check if "BEAMS" exists as exact name → Yes (BEAMS JAPAN, BEAMS RETAIL)
- → Ambiguous; ask user which one

---

## Rule Category: Response Presentation

### PR-GROSS-PROFIT-LABEL-002: Always Label Gross Profit Variant

**Rule ID:** PR-GROSS-PROFIT-LABEL-002  
**Status:** Verified (user confirmed 2026-06-30)

**Statement:**
Response must ALWAYS specify which gross profit variant is presented.

**Template:**

```
"[Customer/Project/Person] 粗利:

This is [概算/実際/担当者] gross profit.

[Variant-specific note]"
```

**Variant-Specific Notes:**

- **概算粗利**: "This uses estimated cost. Actual profit may change once purchase invoices are recorded."
- **実際粗利**: "This is calculated from actual sales and purchase records (shipped and invoiced)."
- **担当者粗利**: "This includes direct sales staff expenses, used for staff evaluation and commission."

---

### PR-MEANING-TRACE-005: Show Meaning Resolution in Response

**Rule ID:** PR-MEANING-TRACE-005  
**Status:** Verified (user confirmed 2026-06-30)

**Statement:**
Response should optionally show how the question was interpreted.

**Optional Trace Format:**

```
Interpreted as:
- Time: [This month] (based on: "先月" = previous month)
- Entity: [BEAMS JAPAN] (canonical customer code: C012)
- Metric: [Actual Gross Profit] (默认 variant)
- Grain: [By Customer] (analysis dimension)
```

**When to Include Trace:**
- Entity resolution required interpretation
- Time period required clarification
- Multiple valid interpretations existed
- User might benefit from confirmation

**When to Skip Trace:**
- Simple, unambiguous question
- Would clutter response unnecessarily

---

## Rule: Consultation Engine Decision Gate

### GATE-CONSULT-MEANING-RESOLUTION: Meaning Complete Before Response

**Gate ID:** GATE-CONSULT-MEANING-RESOLUTION  
**Status:** Verified (user confirmed 2026-06-30)

**Statement:**
Before responding to user question, consult engine must resolve:
- ✅ Entity (canonical code identified)
- ✅ Time period (start date, end date, basis date)
- ✅ KPI (which gross profit? which metric?)
- ✅ Grain (what dimension?)

**If Any Unresolved:**
→ Ask user clarifying question, do NOT guess.

**Example:**

User: "粗利を知りたい"

Unresolved:
- Entity ❌ (Which customer/project/product?)
- KPI ❌ (Gross profit variant?)
- Time ❌ (Which period?)
- Grain ❌ (What dimension?)

Response: "Could you clarify? Which of these did you mean?
- [Customer name/project/product]
- [Which time period: this month, last month, etc.]
- [For all OEM business, or a specific project?]"

---

## Index: Rules by Phase

### Phase 5-2 (Now)
- BR-SALES-STANDARD-001
- BR-SALES-DETAIL-003
- KPI-METRIC-002 (especially 実際粗利, 概算粗利)
- BR-PROCUREMENT-COMPONENT-011
- ER-CANONICAL-001, ER-NO-CODE-002, ER-NO-GUESS-003
- BR-TIME-RULESET-006, BR-TIME-BASIS-DATE-007
- BR-BF-CATEGORY-009, QPR-BF-CODE-NORMALIZATION-005
- PR-GROSS-PROFIT-LABEL-002
- GATE-CONSULT-MEANING-RESOLUTION

### Phase 5-3 (Mid-term)
- BR-STAFF-EXPENSE-GRAIN-012 (when computing 担当者粗利)
- IR-MASTER-CONFLICT-001, IR-NAME-RESOLUTION-003
- PR-MEANING-TRACE-005

### Phase 5-4+ (Future)
- BR-SALES-RULESET-002 (exception business)
- BR-COST-ALLOCATION-004+ (advanced allocation rules)
- Full Validation Suite (100+ checks per reference)

---

## Maintenance & Evolution

- **Owner**: AI OS Knowledge Team
- **Update Trigger**: New business rule, failed evaluation, user feedback
- **Review**: Quarterly or when new rule adopted
- **Approval**: Architecture Review Board

**Last Updated:** 2026-07-01  
**Next Review:** 2026-10-01
