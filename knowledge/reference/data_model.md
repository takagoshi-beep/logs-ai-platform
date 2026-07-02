# Data Model — LOGS Business Data Relationships

**Date:** 2026-07-01  
**Status:** v0.1 (Initial Structure)  
**Purpose:** Document primary data entities, their relationships, and how they combine to answer business questions

---

## Core Entity Relationship Diagram

```
Customers ─── Projects ─── Sales ─── Products
  │                           │
  │                           └─── Suppliers
  │                               (via Purchases)
  │
Suppliers ─── Purchases ─── Products
  
Staff ─── Projects
   │
   └─── Sales (sales_person_id)
   │
   └─── budget_forecast (staff_id, category 05)

Products ─── Purchases
         ─── Sales
         ─── budget_forecast (optional product dimension)
```

---

## Master Data Tables

### 顧客 (Customers)

**Primary Key:** customer_id (or customer_code)

**Key Columns:**
- customer_code (unique canonical identifier)
- customer_name (display name; may have aliases)
- customer_name_en (English name, if applicable)
- country, region
- primary_contact_name, email, phone
- payment_terms
- credit_limit, outstanding_balance
- last_project_date

**Relationships:**
- 1 Customer → Many Projects (customer_id)
- 1 Customer → Many Sales (customer_id)

**Use in Queries:**
- Customer analysis (per-customer sales, profitability, trend)
- Entity resolution (customer name → canonical customer_code)
- Risk assessment (credit limit vs. outstanding)
- Relationship management (who's the primary contact for this customer?)

**Common Issues:**
- Name variations (e.g., "BEAMS" vs. "BEAMS JAPAN" vs. "BEAMS RETAIL") → use code for certainty
- Outdated contact info → may need manual refresh
- Missing email/phone → ask sales team or reference CRM

---

### 商品 (Products)

**Primary Key:** product_id (or product_code)

**Key Columns:**
- product_code (canonical code; supplier may use different SKU)
- product_name (internal description; may be in Japanese)
- category (product classification: Bags, Apparel, Accessories, etc.)
- brand (brand ownership: own brand, licensed, OEM)
- supplier_id (default/primary supplier)
- unit_cost (standard/logical cost from supplier)
- unit_price (standard selling price)
- quality_rating (supplier quality feedback)
- reorder_point (when to reorder)
- lead_time_days (typical time from order to delivery)

**Relationships:**
- 1 Product → Many Sales (product_id)
- 1 Product → Many Purchases (product_id)

**Use in Queries:**
- Product profitability analysis (which products make money?)
- Demand trends (which products are hot?)
- Procurement planning (which products need reordering?)
- Slow mover identification (which products should we discontinue?)

**Common Issues:**
- Product name changes without code change → old names orphaned
- Multiple suppliers per product → lead_time_days may vary; need supplier-level data
- Reorder point too low → stockouts; too high → waste

---

### 担当者 (Staff)

**Primary Key:** staff_id

**Key Columns:**
- staff_id (unique ID)
- staff_name (display name in Japanese, possibly romanized variant exists)
- title (sales person, product manager, logistics, etc.)
- department
- manager_id (reporting hierarchy)
- email, phone

**Relationships:**
- 1 Staff → Many Projects (project_manager_id, sales_person_id, or both)
- 1 Staff → Many Sales (sales_person_id)
- 1 Staff → budget_forecast (category 05 expenses)

**Use in Queries:**
- Staff evaluation (profitability, sales volume, margin achievement)
- Workload assessment (how many active projects?)
- Commission calculation (based on 担当者粗利)
- Expertise mapping (who has experience with this customer/product?)

**Common Issues:**
- Name variations (full name vs. first name; kanji spelling) → use staff_id
- Promotions (title changes) → historical queries may need date filtering
- Departures (inactive staff still in data) → may need active_flag

---

### 仕入先 (Suppliers)

**Primary Key:** supplier_id

**Key Columns:**
- supplier_id
- supplier_name
- country (China, Vietnam, Indonesia, Japan, etc.)
- contact_name, email, phone
- payment_terms
- lead_time_standard (how long do orders take?)
- quality_rating (LOGS assessment of this supplier)
- minimum_order_quantity
- unit_price (may be lower than product standard_cost for volume orders)

**Relationships:**
- 1 Supplier → Many Purchases (supplier_id)

**Use in Queries:**
- Supplier performance (on-time delivery? quality? cost?)
- Sourcing analysis (which suppliers do we use for category X?)
- Cost analysis (which supplier is cheapest for this product?)
- Concentration risk (are we too dependent on one supplier?)

---

## Transactional Data Tables

### 売上 (Sales)

**Primary Key:** sale_id

**Key Columns:**
- sale_id
- sale_date (when sale was recognized; typically = ship_date)
- customer_id (foreign key → customers)
- project_id (foreign key → projects)
- product_id (foreign key → products)
- sales_person_id (foreign key → staff)
- quantity
- unit_price
- sale_amount (quantity × unit_price, before discounts)
- discount_amount (if any)
- sales_amount_after_discount
- cost_per_unit (logical cost used in estimate)
- estimated_gross_profit (sale_amount - cost_per_unit × quantity)
- status (validated, pending, returned, etc.)
- payment_method (credit, cash, wire, etc.)

**Relationships:**
- Many Sales → 1 Customer (customer_id)
- Many Sales → 1 Project (project_id)
- Many Sales → 1 Product (product_id)
- Many Sales → 1 Staff (sales_person_id)

**Derived Metrics:**
- **Total Sales** = SUM(sales_amount_after_discount)
- **Estimated Gross Profit** = SUM(estimated_gross_profit)
- **Gross Profit %** = SUM(estimated_gross_profit) / NULLIF(SUM(sales_amount), 0)

**Filters (Standard Analysis):**
- status IN (2,3,4,5) — exclude pending/error states
- payment_method != 4 — exclude hold/invalid payments
- See BR-SALES-STANDARD-001

**Use in Queries:**
- Revenue analysis (how much did we sell?)
- Profitability analysis (what was the margin?)
- Customer analytics (which customers buy what?)
- Sales person performance (who closed the most deals? highest margin?)

**Common Issues:**
- Sale amount ≠ sum of line items (may have discounts, returns) → always aggregate from detail
- Estimated profit may be wildly inaccurate if purchase not yet recorded → note assumption
- status codes not intuitive → always reference data dictionary or ask business team

---

### 仕入 (Purchases)

**Primary Key:** purchase_id

**Key Columns:**
- purchase_id
- purchase_date (invoice/receipt date)
- supplier_id (foreign key → suppliers)
- project_id (foreign key → projects, if purchase directly for specific project)
- product_id (foreign key → products)
- quantity
- unit_cost (actual cost from invoice)
- total_cost (quantity × unit_cost)
- import_surcharge_amount (freight, insurance, tariffs, etc.; already included in total_cost)
- receipt_date (when goods arrived; may differ from invoice date)
- status (received, invoiced, paid, etc.)

**Critical Note:** total_cost already includes import surcharges. Do NOT add purchase_surcharges table on top. See BR-PROCUREMENT-COMPONENT-011.

**Relationships:**
- Many Purchases → 1 Supplier (supplier_id)
- Many Purchases → 1 Project (project_id, if applicable)
- Many Purchases → 1 Product (product_id)

**Derived Metrics:**
- **Actual Gross Profit** = Sales_amount - SUM(purchase total_cost)
- **Cost of Goods Sold** = SUM(total_cost)

**Use in Queries:**
- Actual profitability (what did products actually cost us?)
- Variance analysis (estimated cost vs. actual cost; why the difference?)
- Supplier performance (which suppliers deliver on time? at best cost?)
- Cash management (when are invoices due? when should we pay?)

**Common Issues:**
- Purchase may be dated before related sale (if pre-buying for forecast) → join on project_id, not date
- Multiple shipments for one PO → multiple purchase records with same PO reference
- Exchange rate changes → cost_per_unit may vary even for same supplier/product

---

### 発注 (Purchase Orders / POs)

**Primary Key:** po_id

**Key Columns:**
- po_id
- supplier_id (foreign key)
- order_date (when we placed the order)
- expected_delivery_date
- quantity_ordered
- unit_price_quoted
- total_cost_quoted
- product_code (or product_id; may be supplier's SKU, not our product_code)
- status (open, partially_received, fully_received, invoiced, paid, cancelled)

**Relationships:**
- 1 PO → 1 Supplier (supplier_id)
- 1 PO → Many Purchases (when PO is fulfilled, purchases records created)

**Use in Queries:**
- Order fulfillment tracking (has the order arrived?)
- Procurement forecast (how much are we committed to buy?)
- Variance analysis (quoted price vs. actual invoice price; why the difference?)

---

## Dimensional/Aggregation Tables

### 予算/予定/費用 (Budget / Plan / Expense Forecast)

**Primary Key:** budget_forecast_id

**Key Columns:**
- budget_forecast_id
- category_code (01=予算, 02=予定, 05=費用; NOT 03 or 04)
- fiscal_period (YYYY-MM or Q-YYYY)
- staff_id (optional; expenses are often per-staff)
- customer_id (optional; some budgets tied to customer)
- amount (signed value; expenses typically negative)
- description
- approved_by
- notes

**Critical Rule:** Always filter by category_code. Do NOT mix 予算, 予定, and 費用 without explicitly noting which is which. See BR-BF-CATEGORY-009.

**Use in Queries:**
- Budget vs. actual comparison (predicted vs. actual expense)
- Staff-attributed profit (담당자粗利 = 실제粗利 - budget_forecast费用)
- Cash forecasting (what expenses are committed?)

---

### Projects (案件)

**Primary Key:** project_id

**Key Columns:**
- project_id
- customer_id (foreign key)
- project_name (description)
- order_date (when customer committed)
- delivery_date (when goods due)
- project_type (OEM, ODM, Retail, Campaign, etc., if tracked)
- project_manager_id (foreign key → staff)
- sales_person_id (foreign key → staff)
- state (planning, in_progress, pending_delivery, complete, on_hold, at_risk, cancelled)
- status_detail (free text reason if state is on_hold or at_risk)
- expected_sales_amount
- expected_cost_amount
- actual_sales_amount (calculated)
- actual_cost_amount (calculated)
- notes

**Relationships:**
- Many Projects → 1 Customer (customer_id)
- Many Projects → 1 Staff (project_manager_id, sales_person_id)
- 1 Project ← Many Sales (project_id)
- 1 Project ← Many Purchases (project_id)

**Use in Queries:**
- Project status dashboard (which projects are at risk?)
- Pipeline forecasting (expected sales by project)
- Team workload (how many projects per person?)
- Decision tracking (why is this project on hold? what actions needed?)

---

## Query Patterns & Data Access Flows

### Question: "今月のOEM事業の粗利を知りたい" (This month's OEM business gross profit?)

**Data Access Flow:**

```
1. Resolve Intent: Analysis / KPI = Gross Profit / Grain = Business Segment (OEM)
   
2. Meaning Resolution:
   - Time: 今月 → [first day of current month, last day of current month]
   - Entity: OEM事業 → Product category or business segment
   - KPI variant: Gross Profit → default to 実際粗利 (actual)
   
3. Data Selection:
   - Primary Source: sales table (all OEM projects)
   - Secondary Source: purchases table (actual costs)
   - Join Key: project_id (to link sales ↔ purchases)
   
4. SQL Construction:
   SELECT 
       SUM(s.sales_amount) as 売上金額,
       SUM(p.total_cost) as 仕入金額,
       SUM(s.sales_amount) - SUM(p.total_cost) as 実際粗利
   FROM sales s
   LEFT JOIN purchases p ON s.project_id = p.project_id
   WHERE s.sale_date >= [month_start]
     AND s.sale_date <= [month_end]
     AND p.purchase_date >= [month_start]
     AND p.purchase_date <= [month_end]
     AND s.status IN (2,3,4,5)
     AND s.payment_method != 4
   (Additional filter for OEM classification as needed)
   
5. Validation:
   - Is 仕入金額 = 0? If yes, warn: "Purchase data not yet entered; using estimated profit from sales table instead"
   - Is gross profit negative? Flag as risk
   - Are there multiple dates (sales month ≠ purchase month)? Clarify to user
   
6. Presentation:
   - "This month's OEM business actual gross profit is ¥X."
   - "This includes Y sales transactions and Z purchase records."
   - "Note: If purchases not yet recorded for some sales, actual profit will increase once invoices are entered."
   - "OEM business represented N% of total company sales."
```

---

### Question: "佐藤さんの先月の担当者粗利は？" (Satoh's last month staff-attributed profit?)

**Data Access Flow:**

```
1. Resolve Entity: 佐藤さん → staff_id = S123
   
2. Meaning Resolution:
   - Time: 先月 → [previous month date range]
   - KPI: 担当者粗利 (staff-attributed profit = 実際粗利 - 営業担当費用)
   - Grain: 担当者 (must NOT allocate to customer/product/factory)
   
3. Data Selection:
   - Primary: sales table (sales_person_id = S123)
   - Secondary: purchases table (for project costs)
   - Tertiary: budget_forecast (category 05, staff_id = S123, for expense)
   
4. SQL Construction:
   SELECT 
       SUM(s.sales_amount) as 売上金額,
       SUM(p.total_cost) as 仕入金額,
       SUM(s.sales_amount) - SUM(p.total_cost) as 実際粗利,
       ABS(SUM(bf.amount)) as 営業担当費用,
       SUM(s.sales_amount) - SUM(p.total_cost) - ABS(SUM(bf.amount)) as 担当者粗利
   FROM sales s
   LEFT JOIN purchases p ON s.project_id = p.project_id
   LEFT JOIN budget_forecast bf ON bf.staff_id = S123 
       AND bf.category_code = '05' 
       AND bf.fiscal_period = [previous month]
   WHERE s.sales_person_id = S123
     AND s.sale_date >= [prev_month_start]
     AND s.sale_date <= [prev_month_end]
   (Apply standard sales filters: status IN (2,3,4,5), payment_method != 4)
   
5. Validation:
   - Is 営業担当費用 found? If not, note: "No expense budget recorded for this period"
   - Ensure grain = 担当者; confirm NOT broken down by customer/product/factory
   
6. Presentation:
   - "Satoh's staff-attributed profit for [month name] is ¥X."
   - "Breakdown: Sales ¥Y - Purchases ¥Z - Staff Expense ¥E = ¥X"
   - "Commission calculation (if applicable): ¥X × [rate] = ¥[commission]"
```

---

### Question: "BEAMS向け提案書のための過去提案を探して" (Find past proposals for BEAMS customer?)

**Data Access Flow:**

```
1. Resolve Entity: BEAMS → canonical customer_code
   
2. Meaning Resolution:
   - Time: 過去（全期間） → no time filter
   - Search scope: past projects with this customer
   
3. Data Selection:
   - Primary: projects table (customer_id)
   - Secondary: sales table (for revenue context)
   - Tertiary: staff table (for project owners)
   
4. SQL Construction:
   SELECT 
       p.project_id,
       p.project_name,
       p.order_date,
       p.delivery_date,
       s.sales_person_id,
       st.staff_name,
       SUM(s.sales_amount) as 売上,
       p.state
   FROM projects p
   LEFT JOIN sales s ON p.project_id = s.project_id
   LEFT JOIN staff st ON p.sales_person_id = st.staff_id
   WHERE p.customer_id = BEAMS_CODE
   ORDER BY p.order_date DESC
   
5. Extract Context:
   - Which products did BEAMS buy before?
   - What was typical project structure? OEM? Retail?
   - Who are past project managers/sales owners?
   - Any patterns (seasonal orders, growth trends, complaints)?
   
6. Presentation:
   - List past projects with BEAMS with summary
   - Highlight staff who worked with BEAMS before
   - Extract product patterns
   - Link to proposal templates (if available)
```

---

## Data Quality Considerations

| Issue | Impact | Mitigation |
|-------|--------|-----------|
| Null purchase cost | Estimated profit inaccurate | Default to 論理原価; note assumption in answer |
| Sales date ≠ ship date | Period reconciliation complex | Ask for clarification; prefer ship_date for revenue timing |
| Purchase recorded after sale | Timing mismatch | Join on project_id, not date; aggregate separately if needed |
| Supplier SKU ≠ product code | Reconciliation errors | Use product_id as canonical; map supplier SKU separately |
| Staff name variations | Entity resolution failure | Use staff_id; support romanized/kanji lookup |
| Customer name aliases | Entity resolution failure | Maintain customer aliases table; use canonical code |
| Missing project_id on purchase | Can't link cost to project | Ask supplier/procurement to complete; flag as data quality issue |
| Negative values in budget | May be reversed or correction | Clarify with finance; use ABS() carefully |

---

## Maintenance & Evolution

- **Owner**: Data Engineering / DBA Team
- **Update Trigger**: Schema changes, new analysis need, data quality discovery
- **Review Cycle**: Annual (or when new table added)

**Last Updated:** 2026-07-01  
**Next Review:** 2026-10-01
