# Business Dictionary — LOGS Business Vocabulary for AI OS

**Date:** 2026-07-01  
**Status:** v0.1 (Initial Build)  
**Purpose:** Define LOGS business terms as understood by AI OS; prevent semantic confusion in queries and responses

---

## Overview

This dictionary ensures consistent interpretation of business language across the AI OS knowledge layer. Each term has:
1. **Definition** — What it means in LOGS context
2. **Business Meaning** — How it's used operationally
3. **Data References** — Where to find it in the database
4. **Related Tables** — Which data sources contain it
5. **Common Confusions** — Where AI might misinterpret it
6. **Query Usage** — How to use in consultation responses

---

## OEM事業 (OEM Business)

**Definition:** Original Equipment Manufacturing — contracting to manufacture products under customer brand/specification.

**LOGS Context:** One of LOGS's two primary business models. OEM involves custom-built or white-label products sold under customer brand.

**Operational Use:**
- Project classification (vs. Retail, Campaign, Distribution)
- Margin analysis (OEM projects often lower margin; compensation through volume)
- Timeline management (longer lead times due to customization)
- Procurement strategy (bulk orders, lead-time management)

**Data References:**
- Project table: project_type column (if exists) or inferred from project_name pattern
- Sales records: linked via project_id to OEM classified projects
- Purchase records: OEM orders typically bulk imports

**Related Tables:**
- sales, purchases, projects, customers

**Common Confusions:**
- ❌ OEM = Wholesale (wrong; OEM is manufacturing/contracting, not just bulk sales)
- ❌ All OEM projects are high-margin (wrong; OEM can be lower margin)
- ❌ OEM = imported goods (wrong; OEM is business model, not sourcing strategy)

**Query Usage Example:**
- User: "OEM事業の粗利を知りたい" (Want to know OEM business gross profit)
- AI should: Identify projects classified as OEM, sum their gross profit, note margin expectations

**Reference:** BR-TASK-PLANNING-015 (Business Task scope), verified_business_rules.md line 1010-1015

---

## ODM (Original Design Manufacturing)

**Definition:** Original Design Manufacturing — LOGS designs and manufactures products; customer provides brand/ordering capability.

**LOGS Context:** Advanced form of OEM where LOGS contributes design/engineering, not just manufacturing.

**Operational Use:**
- Differentiated pricing (higher value than OEM due to design contribution)
- Project classification (subset of OEM, higher expertise requirement)
- Staff skill evaluation (requires design/engineering staff)

**Data References:**
- Project notes or classification system (if exists)
- May not have separate DB column; often tracked as "OEM + Design" annotation

**Related Tables:**
- projects, sales (may be distinguishable via comments/annotations)

**Common Confusions:**
- ❌ ODM = OEM (wrong; ODM is subset with design contribution)
- ❌ ODM is always more profitable (not always; depends on complexity & overhead)

**Query Usage Example:**
- User: "ODM案件の原価構成を知りたい" (Want to know ODM project cost composition)
- AI should: Flag that ODM classification may not be explicitly in data; ask for clarification or inspect project name/notes

**Reference:** reference/01_business/verified_business_rules.md (referenced in Business Concept list, line 1080)

---

## 案件 (Project/Assignment)

**Definition:** A single business engagement with a customer, spanning contract, manufacturing, delivery, and revenue recognition.

**LOGS Context:** Fundamental business unit. Everything (sales, purchases, tasks, decisions, goals) is organized under a project.

**Operational Use:**
- Primary scoping unit (all revenue/cost/risk tied to a project)
- Team coordination (project manager, sales, procurement, logistics all coordinate around project)
- Timeline tracking (project dates: order, delivery, payment)
- Profitability analysis (per-project margin, cash flow, risk assessment)

**Data References:**
- projects table (primary key: project_id)
- Linked to: sales, purchases, purchase_orders, budget_forecast, tasks, decisions, goals

**Related Tables:**
- sales (project_id foreign key)
- purchases (project_id via purchase_orders)
- purchase_orders
- projects (master table)
- staff (project_manager, sales_person)
- customers

**Common Confusions:**
- ❌ Project = Purchase Order (wrong; a project may involve multiple POs)
- ❌ Project = Sales Order (wrong; a project may involve multiple sales orders)
- ❌ Project = Product (wrong; a project is a business engagement; product is inventory)

**Query Usage Example:**
- User: "Fanatics案件の現在状況を教えて" (What's the current status of Fanatics project?)
- AI should: Query projects table for customer="Fanatics", return project_id, status, key dates, open actions, decisions

**Reference:** BP-Principle-1 (Project First), project_domain_model_report.md

---

## 顧客 (Customer)

**Definition:** External party that has contracted with LOGS for products/services; may span multiple projects.

**LOGS Context:** Business entity; link between projects, revenue recognition, risk assessment.

**Operational Use:**
- Customer master (unique customer code, standard terms, preferred contacts)
- Relationship management (which staff manage, history of projects, preferred products)
- Credit/risk assessment (payment history, outstanding balance, credit limit)
- Analytics (customer lifetime value, repeat business patterns, profitability by customer)

**Data References:**
- customers table (primary key: customer_code or customer_id)
- Linked to: projects (customer_id), sales (customer_id), purchase_orders (ship_to_customer)

**Related Tables:**
- customers (master)
- projects (customer_id)
- sales (customer_id)
- budget_forecast (customer dimension for analysis)

**Common Confusions:**
- ❌ Customer = Project (wrong; one customer may have many projects over time)
- ❌ Customer = Sales Contact (wrong; one customer may have many sales people)
- ❌ Customer Name = Canonical Customer Code (wrong; names may vary; use code for queries)

**Query Usage Example:**
- User: "BEAMS向けの売上トレンドは？" (BEAMS sales trend?)
- AI should: Resolve "BEAMS" to canonical customer_code, query sales for all projects with that customer, aggregate over time

**Entity Resolution Note:** Customer names have aliases (e.g., "BEAMS" vs. "BEAMS JAPAN" vs. "BEAMS RETAIL"). Always resolve to canonical_customer_code before querying.

**Reference:** ER-CANONICAL-001 (Entity Resolution), reference/01_business/verified_business_rules.md line 1106-1116

---

## 商品 (Product)

**Definition:** Physical goods that LOGS manufactures or resells; characterized by code, name, category, brand, supplier.

**LOGS Context:** Inventory master; basis for procurement, sales, cost calculation.

**Operational Use:**
- Inventory management (stock levels, reorder points, supplier relationships)
- Sourcing (supplier selection, lead times, quality control)
- Pricing (cost-plus, margin targets, customer-specific pricing)
- Analysis (product profitability, demand trends, slow movers)

**Data References:**
- products table (primary key: product_code or product_id)
- Columns: product_name, category, brand, supplier_code, unit_price, standard_cost, quality_rating

**Related Tables:**
- products (master)
- sales (product_id)
- purchases (product_id)
- purchase_orders (product_id)

**Common Confusions:**
- ❌ Product = SKU (partially correct; SKU may be more granular, e.g., different colors/sizes of same product)
- ❌ Product Name = Product Code (wrong; use code for joins; names can change or have aliases)
- ❌ Standard Cost = Actual Cost (wrong; actual cost depends on supplier, purchase volume, exchange rate)

**Query Usage Example:**
- User: "バッグ商品の売上シェアを知りたい" (Bag product sales share?)
- AI should: Identify product category or brand="Bags", query sales, calculate percentage of total

**Entity Resolution Note:** Product attributes (brand, category, supplier) may have mismatches between data entry. Use product_code as canonical key; infer attributes from multiple signals if name only is provided.

**Reference:** BR-MASTER-PRODUCT-004, BR-MASTER-INFERENCE-005, reference/01_business/verified_business_rules.md line 862-888

---

## 品番 (Model Number/Item Number)

**Definition:** Supplier-assigned code for a specific product specification (e.g., model, color, size variant).

**LOGS Context:** Granular procurement identifier; may differ from internal product_code.

**Operational Use:**
- Supplier communication (PO line items reference 品番)
- Quality tracking (specific 品番 may have known quality issues)
- Reorder automation ( 品番 + quantity typically used for repeat orders)

**Data References:**
- purchase_orders table: item_number or model_number column (links to specific supplier SKU)
- products table: may have supplier_sku or model_number column

**Related Tables:**
- purchase_orders
- products
- purchases

**Common Confusions:**
- ❌ 品番 = Product Code (wrong; 品番 is supplier code, product_code is internal)
- ❌ All 品番 variations are different products (wrong; may be same product, different color/size)

**Query Usage Example:**
- User: "品番ABC123の仕入原価は？" (Cost of model ABC123?)
- AI should: Resolve 品番 to product_code (if not 1:1), query purchases for that item, calculate average cost

---

## 売上 (Sales/Revenue)

**Definition:** Revenue recognized from delivery of goods/services to customer; recorded at point of sale or delivery.

**LOGS Context:** Primary KPI; basis for profitability analysis, cash forecasting, performance evaluation.

**Operational Use:**
- Revenue recognition (accrual accounting; tied to delivery date, not order/payment date)
- KPI tracking (daily/weekly/monthly sales targets, achievement tracking)
- Customer analytics (sales by customer, by product, by staff)
- Profitability (gross profit = sales - cost; used for pricing and strategy decisions)

**Data References:**
- sales table (primary key: sale_id)
- Columns: sale_date, customer_id, project_id, amount, quantity, product_id, gross_profit, cost

**Related Tables:**
- sales (detail records)
- customers, projects, products, staff (dimensions)
- purchases (cost reference)
- budget_forecast (comparison: actual vs. plan/budget)

**Common Confusions:**
- ❌ Sales = Cash Received (wrong; sales is accrual; cash may come later)
- ❌ Sales Total = Sum of Line Items (partially wrong; may have discounts, returns to reconcile)
- ❌ "売上" always means "Revenue" (sometimes means "quantity sold"; context-dependent)

**Filtering Rule:** For standard sales analysis, apply filter: status IN (2,3,4,5) AND payment_method != 4. See BR-SALES-STANDARD-001.

**Query Usage Example:**
- User: "先月の売上は？" (Last month's sales?)
- AI should: Query sales table for sales_date in [previous month], apply standard filters, SUM(amount), note filters applied

**Reference:** BR-SALES-STANDARD-001, BR-SALES-DETAIL-003, reference/01_business/verified_business_rules.md line 824-860

---

## 仕入 (Purchase/Procurement/Import)

**Definition:** Acquisition of goods from external suppliers; basis for cost of goods sold.

**LOGS Context:** Cost counterpart to sales; combines with sales to calculate profit.

**Operational Use:**
- Cost tracking (actual cost of goods delivered to customer)
- Supplier management (lead times, quality, terms)
- Cash management (purchase timing affects working capital)
- Profitability analysis (purchase cost is primary cost driver for manufacturing businesses)

**Data References:**
- purchases table (primary key: purchase_id)
- Columns: purchase_date, supplier_id, project_id, product_id, quantity, unit_cost, total_cost, import_surcharge

**Related Tables:**
- purchases (detail records)
- purchase_orders (order records; 仕入 is fulfillment of PO)
- suppliers
- projects
- products
- purchase_surcharges (import fees, freight, insurance)

**Important:** purchases includes import surcharges (輸入経費込み仕入金額); do not add purchase_surcharges separately. See BR-PROCUREMENT-COMPONENT-011.

**Common Confusions:**
- ❌ 仕入 = Purchase Order (wrong; PO is intent; 仕入 is receipt/invoice)
- ❌ 仕入 = Payment (wrong; 仕入 is accrual; payment may be deferred)
- ❌ 仕入金額 + 輸入諸掛 = Total cost (wrong; purchases already includes surcharges; see BR-PROCUREMENT-COMPONENT-011)

**Query Usage Example:**
- User: "China仕入先からの仕入金額は？" (Total purchase amount from China suppliers?)
- AI should: Query purchases for supplier_country="China", SUM(total_cost), note that amount includes import fees

**Reference:** BR-PROCUREMENT-COMPONENT-011, reference/01_business/verified_business_rules.md line 958-970

---

## 粗利 (Gross Profit)

**Definition:** Revenue minus cost of goods. But LOGS has 3 variants; always specify which.

**Variants:**
1. **概算粗利 (Estimated Gross Profit)** — Profit using logical cost (論理原価) or data entry cost estimates; used when actual purchase data not yet available
2. **実際粗利 (Actual Gross Profit)** — Profit calculated as Sales Amount - Actual Purchase Amount (from purchases table)
3. **担当者粗利 (Staff-Attributed Profit)** — Actual Gross Profit - Sales Staff Expense (budget_forecast category 05)

**LOGS Context:** Core KPI; heavily used in analytics, staff evaluation, project assessment.

**Operational Use:**
- Project evaluation (is this project healthy/profitable?)
- Staff evaluation (did sales person hit margin targets?)
- Product analysis (which products/brands have best margins?)
- Strategic decisions (should we continue this customer/product?)

**Data References:**
- sales table: gross_profit column (概算粗利, sales上の粗利)
- purchases table: used to calculate 実際粗利 = sales_amount - purchases_total_cost
- budget_forecast (category 05): used to calculate 担当者粗利

**Related Tables:**
- sales (for estimated, actual price/cost)
- purchases (for actual cost)
- budget_forecast (for staff expense)
- budget_forecast category 05 (営業担当費用: sales staff expenses)

**Critical Rule:** When answering questions about 粗利, ALWAYS specify which variant you're using. See PR-GROSS-PROFIT-LABEL-002.

**Common Confusions:**
- ❌ 粗利 = 利益 (wrong; 利益 (profit) includes all costs, not just COGS; AI OS avoids "利益" term entirely to prevent confusion)
- ❌ All 粗利 values are comparable (wrong; estimated vs actual may differ significantly if purchases not yet recorded)
- ❌ 粗利 is always positive (wrong; may be negative if cost > revenue)
- ❌ 粗利 = 粗利率 (wrong; 粗利率 is margin %; 粗利 is absolute amount)

**Calculation Rules:**
- **概算粗利**: Found in sales table; do not recalculate
- **実際粗利**: SUM(売上金額) - SUM(仕入金額 from purchases) by project/customer/product/date as needed
- **担当者粗利**: 実際粗利 - ABS(sales_staff_expense from budget_forecast category 05), where expense is typically negative value

**Query Usage Example:**
- User: "FanaticsのOEM事業の粗利は？" (Fanatics OEM project gross profit?)
- AI should:
  1. Identify which 粗利 variant is relevant (usually 実際粗利 for project assessment)
  2. Query sales for project="Fanatics" AND type="OEM", SUM(売上)
  3. Query purchases for same project, SUM(仕入金額)
  4. Calculate = Sales - Purchases
  5. Note: "This is actual gross profit. If purchases not yet recorded, estimated value from sales table would be higher/lower."

**Reference:** BR-SALES-STANDARD-001, KPI-METRIC-002, PR-GROSS-PROFIT-LABEL-002, reference/01_business/verified_business_rules.md line 1369-1401

---

## 粗利率 (Gross Profit Margin %)

**Definition:** Gross Profit as percentage of Sales: (Gross Profit / Sales) × 100

**LOGS Context:** Normalized profitability metric; used for comparing projects/products of different sizes.

**Operational Use:**
- Strategic target setting (e.g., "maintain > 30% margin on OEM")
- Competitive analysis (how does our margin compare to market?)
- Pricing review (is margin falling? do we need to raise prices or cut costs?)

**Data References:**
- Calculated from sales and cost tables, not stored directly

**Calculation Rules:**
- 粗利率 = SUM(粗利) / NULLIF(SUM(売上金額), 0)
- Always use line-item basis: SUM(明細粗利) / SUM(明細売上金額), not header values
- See BR-SALES-DETAIL-003 for precision requirements

**Common Confusions:**
- ❌ 粗利率 = 利益率 (wrong; different denominators and cost inclusions)
- ❌ 粗利率 > 50% is always good (wrong; depends on industry, business model, expense structure)

**Reference:** BR-SALES-DETAIL-003, reference/01_business/verified_business_rules.md line 846-860

---

## 論理原価 (Logical/Standard Cost)

**Definition:** Predetermined cost for a product based on standard recipe, supplier rates, or historical average; used when actual cost data not available.

**LOGS Context:** Cost estimate; used in sales profitability estimates before purchases recorded.

**Operational Use:**
- Early-stage project quoting (calculate expected margin before order placed)
- Variance analysis (actual cost vs. standard cost; variance = learning opportunity)
- Budgeting (forecast cost for period)

**Data References:**
- products table: standard_cost or cost_estimate column
- Used in sales table to calculate 概算粗利 if purchase not yet recorded

**Related Tables:**
- products (standard_cost master)
- sales (used if purchase not yet available)

**Common Confusions:**
- ❌ 論理原価 is always accurate (wrong; it's a model; actual cost may differ)
- ❌ If 論理原価 ≠ 実績原価, someone made an error (wrong; variance is normal; may indicate market changes, volume discounts, quality variations)

---

## 実績原価 (Actual Cost)

**Definition:** Cost of goods actually purchased for a project; derived from purchase invoices.

**LOGS Context:** True cost; basis for 実際粗利 calculation and post-mortem project analysis.

**Operational Use:**
- Actual profitability assessment (did we make margin we promised?)
- Variance investigation (why did actual cost differ from estimate?)
- Learning (what did we learn about this product/supplier for next project?)

**Data References:**
- purchases table: cost_total or unit_cost × quantity
- Linked to sales via project_id

**Reference:** KPI-METRIC-002 (粗利 3-variant definition), reference/01_business/verified_business_rules.md line 1388-1401

---

## 受注 (Order Received/Contract Signed)

**Definition:** Customer has committed to purchase; order is in system, may not yet be delivered or invoiced.

**LOGS Context:** Demand signal; basis for production planning, procurement triggering.

**Operational Use:**
- Pipeline tracking (what revenue is expected?)
- Production scheduling (which orders need fulfillment?)
- Procurement triggering (which 仕入 to order to fulfill?)

**Data References:**
- projects table: order_date (when customer committed)
- sales table: not yet created until delivery

**Related Tables:**
- projects (order_date)
- purchase_orders (triggered by 受注)

**Query Usage Example:**
- User: "今月の受注は？" (This month's orders received?)
- AI should: Query projects for order_date in [this month], show customer, project name, expected delivery, expected sales value

---

## 発注 (Purchase Order Issued)

**Definition:** LOGS has ordered from suppliers to fulfill customer 受注; order placed but not yet delivered.

**LOGS Context:** Procurement commitment; basis for cash flow forecast (when will we pay?), inventory expectations.

**Operational Use:**
- Supplier commitment (we've promised to buy)
- Cash management (when are we obligated to pay?)
- Inventory management (stock should arrive by when?)

**Data References:**
- purchase_orders table: primary key po_id, order_date (when ordered), expected_delivery_date

**Related Tables:**
- purchase_orders (master)
- projects (what customer orders trigger our 発注?)
- suppliers
- purchases (when 発注 is fulfilled)

**Common Confusion:**
- ❌ 発注 = 仕入 (wrong; 発注 is commitment, 仕入 is receipt/invoice)

---

## 納期 (Delivery Date/Due Date)

**Definition:** Date by which goods must be delivered to customer or completed; critical for timeline management.

**LOGS Context:** Hard constraint; missing 納期 is a business risk.

**Operational Use:**
- Production scheduling (what's the deadline?)
- Procurement timing (when must suppliers deliver to us so we can deliver to customer?)
- Risk management (early warning if 納期 may be missed)
- SLA tracking (are we meeting customer commitments?)

**Data References:**
- projects table: delivery_date or due_date column
- purchase_orders table: expected_delivery_date (internal need date, not customer date)

**Query Usage Example:**
- User: "今週中に納期を迎える案件は？" (Projects with delivery this week?)
- AI should: Query projects for delivery_date between [today] and [end of this week], return list with customer, project, owner, status, risk flags

**Reference:** reference/01_business/verified_business_rules.md (Grain Constraint, line 1363-1365)

---

## 出荷 (Shipment/Delivery)

**Definition:** Physical goods have left LOGS facility and are in transit or delivered to customer.

**LOGS Context:** Operational milestone; often triggers 売上 recognition.

**Operational Use:**
- Fulfillment tracking (is order moving as expected?)
- Logistics management (which carrier, which route, tracking number)
- 売上 recognition (accrual system: 売上 recognized at shipment, not order or payment)

**Data References:**
- sales table: ship_date (when goods left LOGS)
- logistics system: (not in logsys.db; external system)

---

## 担当者 (Staff Member/Sales Person)

**Definition:** LOGS employee responsible for customer relationship, project, or task.

**LOGS Context:** Human accountability; basis for performance evaluation, commission, task assignment.

**Operational Use:**
- Performance tracking (which sales people are hitting targets?)
- Workload balancing (is this person overloaded?)
- Commission calculation (commission based on assigned projects)
- Expertise mapping (who has skills in this area?)

**Data References:**
- staff table (or employees table): staff_id, name, title, department, manager

**Related Tables:**
- staff (master)
- projects (project_manager, sales_person)
- sales (sales_person_id)
- budget_forecast (expense allocation to staff)

**Entity Resolution Note:** Staff names may have kanji/romanized variants. Always resolve to staff_id for queries.

---

## 案件状態 (Project State/Status)

**Definition:** Current lifecycle status of project; reflects business stage and urgency.

**LOGS Context:** State machine; determines what actions are possible/expected next.

**Operational Use:**
- Workflow enforcement (what transitions are valid? who can change state?)
- Action prioritization (which projects need immediate attention?)
- Forecasting (how likely is this project to close?)

**Data References:**
- projects table: status or state column
- Typical values (may vary): Planning, In Progress, Pending Delivery, Complete, On Hold, Cancelled, At Risk

**Reference:** Blueprint v0.1 §5 (Project Aggregate Standard), project_domain_model_report.md

---

## 収支 (Cash Flow / Accounting Balance)

**Definition:** Net cash flow considering revenue and expenses; used for cash forecasting and financial planning.

**LOGS Context:** Working capital management; critical for sustainability.

**Operational Use:**
- Cash forecasting (will we have cash to pay suppliers next month?)
- Working capital management (should we adjust payment terms?)
- Financing decisions (do we need a line of credit?)

**Data References:**
- Calculated from sales (cash inflow) and purchases/budget_forecast (cash outflow)

---

## 売上計上 (Revenue Recognition)

**Definition:** Accounting principle: when to record a sale as revenue (accrual basis).

**LOGS Context:** Typically recognized at shipment; not at order or payment.

**Operational Use:**
- Financial reporting (accurate revenue numbers for P&L)
- Period close (which 売上 belongs to which fiscal period?)

**Data References:**
- sales table: recognition_date (typically = ship_date)

---

## 仕入計上 (Purchase Recognition)

**Definition:** Accounting principle: when to record a purchase as an expense (accrual basis).

**LOGS Context:** Typically recognized at receipt of invoice; not at order or payment.

**Operational Use:**
- Financial reporting (accurate cost of goods sold)
- Period close (which 仕入 belongs to which fiscal period?)

**Data References:**
- purchases table: recognition_date (typically = invoice_date)

---

## 営業担当費用 (Sales Staff Expense)

**Definition:** Cost allocated to individual sales person; used in 担当者粗利 (staff-attributed profit) calculation.

**LOGS Context:** Uniquely attributed cost; basis for staff performance evaluation and commission.

**Operational Use:**
- Staff evaluation (what's the profit after accounting for my costs?)
- Commission calculation (commission as % of 担当者粗利)
- Budget management (what's the allowable expense budget for this staff?)

**Data References:**
- budget_forecast table: category 05 (費用 variant), filtered by staff_id

**Important Rule:** See BR-STAFF-EXPENSE-GRAIN-012: Can only be used in 担当者 (Staff) grain analysis. Must NOT be allocated to customer/product/brand/factory dimensions.

**Storage Note:** Stored as negative value in database (SR-COST-NEGATIVE-001); convert to positive for display (PR-COST-DISPLAY-001).

**Query Usage Example:**
- User: "佐藤さんの担当者粗利は？" (Satoh's staff-attributed profit?)
- AI should:
  1. Resolve "佐藤さん" to staff_id
  2. Query sales for staff_id, SUM(sales_amount) = S
  3. Query purchases for projects assigned to staff, SUM(purchases_total_cost) = P
  4. Query budget_forecast category 05 for staff_id, SUM(ABS(expense)) = E
  5. Calculate: 担当者粗利 = S - P - E
  6. Note grain: "Staff-attributed profit includes only costs directly attributed to this staff member."

**Reference:** BR-STAFF-EXPENSE-GRAIN-012, KPI-METRIC-002, reference/01_business/verified_business_rules.md line 1562-1573

---

## 予算 / 予定 / 費用 (Budget / Plan / Actual Expense)

**Definition:** Three categories in budget_forecast table, identified by category code:
- **予算 (01)**: Top-down planned targets
- **予定 (02)**: Bottom-up operational plan (more detailed)
- **費用 (05)**: Actual recorded expenses (月次費用実績)

**LOGS Context:** Budget management and performance tracking.

**Data References:**
- budget_forecast table: category_code column (01/02/05)
- Do NOT expect codes 03/04; they don't exist in LOGS. See BR-BF-CATEGORY-009.

**Correct Term:** Always use 区分コード (category code) when filtering; never use display name directly in SQL. See QPR-BF-CODE-NORMALIZATION-005.

**Common Confusions:**
- ❌ Mixing 予算 and 予定 without noting which is which
- ❌ Using 費用 (05) for capital budget (wrong; 費用 is operational expense only)
- ❌ Expecting codes 03/04 to exist in budget_forecast (wrong; only 01/02/05)

**Reference:** BR-BF-CATEGORY-009, QPR-BF-CODE-NORMALIZATION-005, reference/01_business/verified_business_rules.md line 923-944

---

## 論理原価 vs. 実績原価 vs. 概算粗利 vs. 実際粗利

**Relationship Diagram:**

```
Sales Order (受注)
   ↓
Sales Record (売上記録) ← based on → Products Master (論理原価)
   ├─売上金額 (Sale Amount)
   └─概算粗利 (Estimated GP = 売上 - 論理原価)  ← Uses standard cost
   
Purchase Order (発注) → Purchase Record (仕入)  ← Actual cost from supplier
   ├─ 仕入金額 (Actual cost, including import fees)
   └─ 実績原価 (Actual cost used for final profitability)

Actual Gross Profit (実際粗利) = 売上金額 - 実績原価
   └─ Used for post-project analysis, final financials

Staff Expense (営業担当費用) from budget_forecast(05)
   └─ Staff-Attributed Profit (担当者粗利) = 実際粗利 - 営業担当費用
```

**Timeline Perspective:**

| Phase | Cost Basis | Profit Metric | Usage |
|-------|-----------|----------------|-------|
| Quote | 論理原価 | 概算粗利 | Customer proposal, early pipeline |
| Order Received | 論理原価 | 概算粗利 | Sales forecast, production planning |
| Post-Delivery | 実績原価 | 実際粗利 | Project closeout, financials, variance analysis |
| Performance Review | 実績原価 + 費用 | 担当者粗利 | Staff evaluation, commission |

**Query Usage Note:** When user asks about 粗利 without specifying which variant, ask clarifying question or default to 実際粗利 (most objective/defensible). Always note which variant in response.

---

## Terminology Maintenance

This dictionary will be updated as new terms emerge or existing definitions evolve.

**Update Process:**
1. Term is used in multiple contexts; ambiguity arises
2. Business owner or AI OS team proposes clarification
3. Definition is documented with examples
4. All stakeholders review
5. Definition is integrated into Blueprint if it becomes policy
6. Dictionary is updated with new definition and reference to Blueprint

**Owner:** AI OS Knowledge Layer Team  
**Last Updated:** 2026-07-01  
**Next Review:** 2026-10-01 (or when new term reaches adoption threshold)
