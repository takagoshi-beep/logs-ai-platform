# Query Patterns — Common Consultation Questions & AI Response Strategy

**Date:** 2026-07-01  
**Status:** v0.1 (Phase 5-2 Baseline)  
**Purpose:** Document how to interpret and respond to common business questions

---

## Overview

Query Patterns map user intent → required data → response structure.

Each pattern includes:
1. **Example Questions** (user phrasing variations)
2. **Interpretation** (what the question really means)
3. **Data Requirements** (which tables, filters)
4. **Response Strategy** (what to show, what to clarify)
5. **Common Pitfalls** (mistakes to avoid)

---

## Pattern: OEM/Product Business Analysis

### Example Questions:
- "OEM事業の粗利を知りたい" (What's the gross profit for OEM business?)
- "今月のOEM案件の状況は？" (What's the status of OEM projects this month?)
- "OEM向けの売上トレンドは？" (OEM sales trend?)

### Interpretation:
- **Entity**: OEM-classified projects/products
- **Time**: Unspecified → ask, or default to "this month"
- **KPI**: Gross profit (variant unspecified → ask or default to 実際粗利)
- **Grain**: Business segment (OEM category)
- **Question Type**: Analysis

### Data Requirements:
- **Primary**: sales table (projects classified as OEM)
- **Secondary**: purchases table (actual costs)
- **Dimension**: products table (category or project_type field, if exists)

### Processing:
```
1. Confirm time period: "Do you want this month, last month, or year-to-date?"
2. Confirm gross profit variant:
   - If purchases data is current: "actual gross profit" (実際粗利)
   - If recent orders: "estimated profit from sales data" (概算粗利)
3. Identify OEM classification:
   - If product_type field exists: filter WHERE product_type = "OEM"
   - Else: inspect project_name patterns or ask sales team
4. Aggregate: SUM(sales) - SUM(purchases) by time period
5. Note: Compare to total company profit; show margin rate
```

### Response Template:
```
"OEM business gross profit for [period]:

¥[Amount] actual gross profit
- Sales: ¥[X]
- Purchase cost: ¥[Y]
- Margin rate: [Z]%

[Breakdown]:
- [# projects]
- [# customers]
- [Top 3 customers by OEM sales]

Note: This is [actual/estimated] gross profit. 
[If estimated: once purchases are recorded, actual may differ.]
[If actual: includes all shipped and invoiced sales for OEM projects.]

Compared to total company:
- OEM is [%] of total company sales
- OEM margin [higher/lower] than company average"
```

### Common Pitfalls:
- ❌ Not asking about time period (user may expect year-to-date, not just current month)
- ❌ Not specifying profit variant (estimated vs actual difference can be 30%+)
- ❌ Mixing completed projects with still-pending (different cost status)
- ❌ Not noting that OEM classification may not be explicit in data

---

## Pattern: Customer Relationship Analysis

### Example Questions:
- "BEAMS向けの売上シェアは？" (What's BEAMS' sales share?)
- "BEAMS案件は現在どんな状況？" (What's BEAMS project status?)
- "BEAMS顧客の粗利率は？" (BEAMS customer gross profit margin?)

### Interpretation:
- **Entity**: Specific customer (BEAMS)
- **Time**: Unspecified → all time, or "recent" (default last 12 months)
- **KPI**: Sales share, project status, or gross profit
- **Grain**: Customer level
- **Question Type**: Analysis or Monitoring

### Data Requirements:
- **Primary**: projects table (customer_id filter)
- **Secondary**: sales table (revenue aggregation)
- **Tertiary**: purchases table (cost calculation)

### Processing:
```
1. Resolve customer name → canonical customer_code
   If ambiguous (e.g., "BEAMS" could match 3 records):
   → Ask: "Which BEAMS entity? [BEAMS JAPAN, BEAMS RETAIL, ...]?"
   
2. Query projects for this customer
   
3. For each project:
   - Status (on track? at risk? complete?)
   - Revenue (expected vs. actual)
   - Profitability
   
4. Aggregate metrics:
   - Total sales across all BEAMS projects
   - Average margin
   - Project count
   - Trend (growing? declining?)
```

### Response Template:
```
"BEAMS customer analysis:

Sales: ¥[Total across all projects]
- This is [X]% of total company sales
- Average project margin: [%]
- Trend: [↑ growing / ↓ declining / → stable]

Current projects: [N] active
- [Project 1]: [Status] [Expected delivery] [Margin]
- [Project 2]: [Status] [Expected delivery] [Margin]

Key observations:
- BEAMS is [top/mid/low] priority customer
- Margin trend: [improving/declining]
- Recommendation: [Continue focus / Adjust pricing / Increase investment]"
```

### Common Pitfalls:
- ❌ Not disambiguating customer aliases (BEAMS vs. BEAMS JAPAN vs. BEAMS RETAIL)
- ❌ Mixing multiple time periods (comparing last month to YTD)
- ❌ Not distinguishing between project margin and corporate margin
- ❌ Not noting that margin may change as later projects are invoiced

---

## Pattern: Project Status & Risk

### Example Questions:
- "Fanatics案件は大丈夫?" (Is Fanatics project OK?)
- "現在対応すべき案件は？" (Which projects need attention now?)
- "納期が危ない案件があれば教えて" (Which projects have at-risk delivery dates?)

### Interpretation:
- **Entity**: Single project or all projects
- **Time**: Now (current status)
- **KPI**: Health, risk, next actions
- **Question Type**: Monitoring / Alert

### Data Requirements:
- **Primary**: projects table (state, delivery_date)
- **Secondary**: sales table (revenue status)
- **Tertiary**: tasks/actions table (what needs to be done?)

### Processing:
```
1. If specific project mentioned:
   - Query projects WHERE project_name LIKE "%[input]%"
   - If ambiguous: ask for confirmation
   
2. For each project, determine health:
   - Status: on_track / at_risk / blocked / complete
   - Profitability: margin healthy?
   - Delivery: on schedule? early/late signals?
   - Next actions: what's due next?
   
3. Identify risk factors:
   - Pending purchase orders (inventory risk)
   - Late supplier deliveries (schedule risk)
   - Low margin (financial risk)
   - Changed customer requirements (scope risk)
```

### Response Template:
```
"Project status:

[Project Name]
- Customer: [Name]
- Owner: [Staff]
- Status: [On track / At risk / Blocked]
- Delivery: [Date] (in [N] days)

Health indicators:
✓ Revenue: ¥[Amount] confirmed
✓ Margin: [%] (healthy)
⚠ Purchase: Pending from [Supplier] (expected [Date])
✓ Logistics: On track

Next action required:
1. [Action 1] - Due [Date] - Owner: [Staff]
2. [Action 2] - Due [Date] - Owner: [Staff]

Risk flags:
- [If any supplier delays]
- [If margin declining]
- [If customer communication pending]"
```

### Common Pitfalls:
- ❌ Not asking which project if name is ambiguous
- ❌ Confusing project health with sales person performance
- ❌ Not highlighting actual risks vs. normal variance
- ❌ Showing data without actionable recommendations

---

## Pattern: Staff Performance & Evaluation

### Example Questions:
- "佐藤さんの先月の粗利は？" (Satoh's last month profit?)
- "今月のトップセールスパーソンは誰？" (Who's the top salesperson this month?)
- "各営業担当の粗利ランキングを知りたい" (Sales staff profit ranking?)

### Interpretation:
- **Entity**: Individual staff or staff ranking
- **Time**: Last month, this month, or YTD
- **KPI**: 担当者粗利 (staff-attributed profit; accounts for salary/expense)
- **Grain**: Staff level (DO NOT aggregate to customer/product dimension)
- **Question Type**: Analysis / Evaluation

### Data Requirements:
- **Primary**: sales table (staff_id)
- **Secondary**: purchases table (cost)
- **Tertiary**: budget_forecast category 05 (staff expense)

### Processing:
```
1. Identify staff: resolve name/ID
   If ranking: sort by 担当者粗利 DESC
   
2. For each staff member:
   - Query sales for staff_id
   - Calculate 売上金額 = SUM(sales_amount)
   - Calculate 仕入金額 = SUM(purchases) by linked projects
   - Calculate 営業担当費用 from budget_forecast(05)
   - Calculate 担当者粗利 = 売上金額 - 仕入金額 - 営業担当費用
   
3. Flag data gaps:
   - If no purchase data yet: note "Estimated margin pending purchase invoices"
   - If no expense data: note "Expense not yet recorded for this period"
```

### Response Template:
```
"[Staff Name] performance for [Period]:

Sales: ¥[Amount]
- Number of projects: [N]
- Average project size: ¥[Amount]

Profitability:
- Gross profit: ¥[Amount] (actual, from sales & purchases)
- Staff expense: ¥[Amount]
- Staff-attributed profit: ¥[Amount] ⚠ (This is used for evaluation/commission)

Comparison to team:
- Rank: [#] of [Total staff]
- Team average: ¥[Amount]
- [Above/Below] average by [%]

Trends:
- Month-over-month: [↑ / ↓ / →]
- Year-over-year: [↑ / ↓ / →]

Recommendation:
[Based on profitability trend and consistency]"
```

### Common Pitfalls:
- ❌ Confusing 売上 (sales volume) with 粗利 (profit)
- ❌ Not accounting for 営業担当費用; showing misleading "high profit" if expense not recorded
- ❌ Comparing different time periods (this month vs. last month without normalization)
- ❌ Not noting that commission should be based on 担当者粗利, not sales volume
- ❌ Trying to allocate staff expense to customer/product dimension (violates BR-STAFF-EXPENSE-GRAIN-012)

---

## Pattern: Historical Comparison & Trend

### Example Questions:
- "先月と今月の売上比較は？" (Last month vs this month sales?)
- "BEAMSの売上は成長してる？" (Is BEAMS growing?)
- "粗利率は改善してる？" (Is margin improving?)

### Interpretation:
- **Entities**: Customer (optional), product category (optional)
- **Time**: Two periods for comparison (or multi-period trend)
- **KPI**: Sales, margin, trend direction
- **Question Type**: Analysis / Insight

### Data Requirements:
- **Primary**: sales table (time-series)
- **Secondary**: purchases table (if margin trend)

### Processing:
```
1. Identify periods:
   - Period 1: [last_month_start, last_month_end]
   - Period 2: [this_month_start, this_month_end]
   
2. Calculate metrics for each period:
   - Sales: SUM(sales_amount) [with standard filters]
   - Margin: SUM(gross_profit) or (SUM(sales) - SUM(purchases))
   
3. Compute delta:
   - Delta_sales = Period2_sales - Period1_sales
   - Pct_change = (Delta_sales / Period1_sales) × 100%
   - Direction: ↑ (growing), ↓ (declining), → (stable)
```

### Response Template:
```
"Sales comparison:

[Period 1]: ¥[Amount]
[Period 2]: ¥[Amount]
Change: ¥[Delta] ([+/-]%[Percent])

Trend: [↑ Growing / ↓ Declining / → Stable]

Analysis:
- [If growing: What drove growth? New customers? Product mix?]
- [If declining: What caused decline? Lost projects? Pricing?]
- [Confidence level: Based on [N] transactions]

Margin trend:
[If available: margin also improving/declining?]

Forecast:
- If trend continues: [Expected] for next period"
```

### Common Pitfalls:
- ❌ Not asking which customer/product if comparison is broad (total company vs. segment)
- ❌ Not comparing apples-to-apples (including cancelled orders vs. excluding)
- ❌ Making strong conclusions from low-transaction-count periods
- ❌ Not accounting for seasonal variation (is decline normal for this month?)

---

## Pattern: Entity Search & Reference

### Example Questions:
- "BEAMS向けの過去提案を探して" (Find past BEAMS proposals?)
- "このブランドの商品リストは？" (What products in this brand?)
- "商品ABCの仕入先は？" (Who supplies product ABC?)

### Interpretation:
- **Entity**: Specific customer, product, brand, supplier
- **Search Type**: Historical, reference, list
- **Question Type**: Search / Reference

### Data Requirements:
- **Primary**: projects (for customer history), products (for brand/product lists), purchases (for supplier reference)

### Processing:
```
1. Resolve entity to canonical code
2. Query relevant table(s)
3. Format as list/table for easy scanning
4. Provide context (size, recency, relevance)
```

### Response Template:
```
"Projects with [Customer/Brand/Supplier]:

[Project 1]: [Date] [Status] [Revenue] [Owner]
[Project 2]: [Date] [Status] [Revenue] [Owner]
...

Total: [N] projects
- Active: [N]
- Completed: [N]
- Estimated total revenue: ¥[Amount]

Recent patterns:
- Last project: [Date] [Project name]
- Frequency: [Every N months / Irregular / Regular]
- Average project size: ¥[Amount]"
```

### Common Pitfalls:
- ❌ Not disambiguating entity (multiple customers with similar names)
- ❌ Returning too many results (limit to recent/relevant)
- ❌ Not providing enough context for selection (date, status, size)

---

## Pattern: Clarification & Scope Definition

### When Pattern Applies:
- User question is ambiguous (multiple interpretations)
- Critical entity is unspecified (which customer?)
- Time period is vague (what's "recently"?)
- KPI could mean multiple things (what kind of "profit"?)

### Strategy:
Always ask, never assume.

### Question Phrasing:
```
"I understand you're asking about [high-level interpretation].

To give you the most accurate answer, could you clarify:
1. [Entity clarification]: Did you mean [Option A] or [Option B]?
2. [Time clarification]: Did you want [Last month / This month / Year-to-date]?
3. [KPI clarification]: Are you asking about [Sales volume / Gross profit margin / Staff performance]?

Once you confirm, I can provide the data."
```

---

## Index: By Frequency

### Most Common (Phase 5-2)
- Customer relationship analysis
- Project status & risk
- Staff performance
- Historical comparison & trend

### Medium (Phase 5-3+)
- OEM business analysis
- Entity search & reference
- Clarification & scope definition

### Advanced (Phase 5-4+)
- Cost allocation by dimension
- Exception business (billing, receivables)
- Multi-dimensional drill-down
- Predictive/forecasting patterns

---

## Maintenance & Evolution

- **Owner**: Product & Analytics Team
- **Update Trigger**: New question pattern emerges, failed query, user feedback
- **Review**: Monthly (add new patterns as they appear)
- **Approval**: Product Manager

**Last Updated:** 2026-07-01  
**Next Review:** 2026-08-01
