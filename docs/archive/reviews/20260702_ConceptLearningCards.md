# Concept Learning Cards

**Date:** 2026-07-02  
**Phase:** 11 — AI Learning Format  
**Purpose:** Simplified one-page-per-concept format for Product Owner teaching  
**Format:** Card = Concept | Current Understanding | Missing | PO Explanation | Updated Understanding

---

## How to Use These Cards

1. **Product Owner selects** which concept to explain (recommend: 案件 first)
2. **AI reads** "Current Understanding" section
3. **AI reads** "Missing" section (what AI doesn't know)
4. **Product Owner provides** explanation (fill "PO Explanation" field)
5. **AI updates** understanding (fill "Updated Understanding" field)

**One card per learning session.** Keep explanations concise (1-2 paragraphs).

---

## CRITICAL CONCEPTS — Learn First

### Card 1: 案件 (Project/Case)

| Field | Content |
|-------|---------|
| **Concept** | 案件 (Project/Case Unit) |
| **Current Understanding** | Multiple granularities exist: PO単位, 商品単位, maybe customer-unit. Don't know which is primary. Q2/Q3 queries ambiguous. |
| **Missing** | Which granularity does user expect when asking about "案件"? How do PO-unit and product-unit relate? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

### Card 2: 粗利 (Gross Profit)

| Field | Content |
|-------|---------|
| **Concept** | 粗利 — Which variant to use? |
| **Current Understanding** | Three variants exist: 論理粗利 (standard), 実績粗利 (actual), 担当者別粗利 (by staff). All stored as single value in 集計.案件粗利. Don't know which is right answer. |
| **Missing** | When should each variant be used? If one isn't available, what's fallback? Should operational costs (②③④) be included? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

### Card 3: OEM案件 vs Retail案件

| Field | Content |
|-------|---------|
| **Concept** | OEM vs Retail Classification |
| **Current Understanding** | Assumed OEM = custom, Retail = catalog. Stored in 集計.分類. No rule documented. Q1 queries may capture wrong segment. |
| **Missing** | What are actual classification values? How is OEM/Retail determined (customer? product? order type?)? Edge cases? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

### Card 4: ステータス (Status Codes)

| Field | Content |
|-------|---------|
| **Concept** | Status Values Across Tables |
| **Current Understanding** | 売上.ステータス = 有効/キャンセル/テスト (known). Other tables unknown. Filtering logic unclear. |
| **Missing** | All valid status values per table? Are they codes or text? Should キャンセル be excluded always? テスト always excluded? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

### Card 5: 実績原価 vs 論理原価

| Field | Content |
|-------|---------|
| **Concept** | Actual Cost vs. Standard Cost |
| **Current Understanding** | Both exist. 実績原価 more accurate; 論理原価 available earlier. Unclear when to use each. Affects all margin calculations. |
| **Missing** | When should each be used? If one missing, what's fallback? How do I know which is available? Timing of availability? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

### Card 6: キャンセル (Cancellation)

| Field | Content |
|-------|---------|
| **Concept** | Cancellation Handling |
| **Current Understanding** | 売上.ステータス = キャンセル flag. Probably should exclude from calculations. Exact reversal logic unknown. |
| **Missing** | Should キャンセル be excluded from ALL queries or kept separately? Can be partial? At what stage allowed? Reversible? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

### Card 7: 返品 (Return)

| Field | Content |
|-------|---------|
| **Concept** | Product Return Handling |
| **Current Understanding** | Customer returns product. Should reverse revenue/cost. Not verified. Probably not handled in calculations. |
| **Missing** | How are returns recorded? Negative rows or flag? When accepted? Can be partial? Should returns affect monthly KPIs? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

### Card 8: 期限 (Deadline/Due Date)

| Field | Content |
|-------|---------|
| **Concept** | Project Deadline Field |
| **Current Understanding** | Should exist for priority ranking (Q3). Not found in real DB schema. Critical for "優先案件" queries. Field name/location unknown. |
| **Missing** | Where is deadline stored (which table)? Field name? Is it different from 納品伝票日? Can deadlines change? Per-case or per-PO? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

## MEDIUM PRIORITY CONCEPTS — Learn After Critical

### Card 9: 受注 (Order Confirmation)

| Field | Content |
|-------|---------|
| **Concept** | Customer Order State |
| **Current Understanding** | Different from vendor PO (発注). Represents customer order from start to end. State machine unclear. |
| **Missing** | What state machine exists (quote→confirmed→production→shipped→delivered)? Is it just status flag or multi-state? Where tracked? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

### Card 10: 発注 (Vendor Purchase Order)

| Field | Content |
|-------|---------|
| **Concept** | Vendor Order Placement |
| **Current Understanding** | 発注 = placing order with vendor (opposite of 受注). 発注依頼 table tracks this. Different from customer order. |
| **Missing** | Confirm 発注依頼 is vendor-side? How does it link to customer order (受注)? Separate flow or merged? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

### Card 11: 予定 (Plan/Schedule)

| Field | Content |
|-------|---------|
| **Concept** | Planning & Scheduling |
| **Current Understanding** | Planned quantities, dates, forecasts used for planning phase. Location in Logsys unknown. Not in current DB schema. |
| **Missing** | Where are plans stored? Types of plans (demand forecast? supply schedule? delivery plan)? How do plans relate to actuals? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

### Card 12: 納品 (Delivery)

| Field | Content |
|-------|---------|
| **Concept** | Product Delivery |
| **Current Understanding** | Physical handoff to customer. Stored as 売上.納品伝票日 (delivery date). May be partial or staged. Timing and status unclear. |
| **Missing** | Is date shipped or received? Can delivery be partial (split shipments)? Can be delayed? On-time tracking? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

### Card 13: 担当者 (Staff Assignment)

| Field | Content |
|-------|---------|
| **Concept** | Staff/Owner Assignment to Projects |
| **Current Understanding** | 社員id, 営業事務id in 集計 table. Used for 担当者別粗利. Multiple staff per case possible? Unclear. |
| **Missing** | How many staff per case? Can reassign mid-project? How is 担当者別粗利 split if multiple staff? History tracked? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

### Card 14: 締め / 期間 (Month-End Close / Period)

| Field | Content |
|-------|---------|
| **Concept** | Accounting Period Definition |
| **Current Understanding** | Calendar month vs. fiscal month distinction unclear. All tables have 期 column. Values/meaning unknown. |
| **Missing** | Does LOGS use calendar or fiscal months? Does 期 represent this? Custom periods? Consistent across divisions? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

### Card 15: 商品単位 (Product Unit Granularity)

| Field | Content |
|-------|---------|
| **Concept** | How Product SKU Is Defined |
| **Current Understanding** | 商品 table has 型番, 色, サイズ. Uniqueness at model-only? model+color? model+color+size? Level unclear. |
| **Missing** | What uniquely identifies a product SKU? Is each variant (color/size) separate? Can one model have multiple cases? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

### Card 16: 会計期間 (Accounting Period / Calendar)

| Field | Content |
|-------|---------|
| **Concept** | Calendar Alignment for Reporting |
| **Current Understanding** | Transactions tagged by 期 (period). Rules for assignment unclear. Can change between periods? |
| **Missing** | When is transaction assigned to period (by date? by close date?)? Accrual vs. cash? Adjustments between periods? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

### Card 17: 入金 (Payment Received)

| Field | Content |
|-------|---------|
| **Concept** | Customer Payment Recognition |
| **Current Understanding** | Payment received from customer. Different from revenue recognition (売上). Used for cash flow. |
| **Missing** | When recorded (on payment date or when cleared)? Partial payments? How related to 売上? Can have sales without payment? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

### Card 18: 粗利率 (Margin Ratio)

| Field | Content |
|-------|---------|
| **Concept** | Profit Margin Percentage |
| **Current Understanding** | Ratio of profit to revenue (assumed). Different from 粗利額 (absolute amount). Formula unclear. |
| **Missing** | Formula: 粗利÷売上×100%? Different? Used for comparisons (product? customer? segment)? How defined organizationally? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

### Card 19: 顧客 & 顧客担当者 (Customer & Contact)

| Field | Content |
|-------|---------|
| **Concept** | Customer Entity vs. Contact Relationship |
| **Current Understanding** | 顧客 master (2,738 records) + 顧客担当者 (3,816 contacts). Relationship between them unclear. |
| **Missing** | 1 customer : many contacts? How contact relates to case? Can reassign mid-project? Primary vs. secondary? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

### Card 20: 商品分類 & 事業分類 (Product vs. Business Classification)

| Field | Content |
|-------|---------|
| **Concept** | Dual Product Classification System |
| **Current Understanding** | 商品 table has both fields. Difference unknown. Used for business segment analysis. Possible link to OEM/Retail? |
| **Missing** | What does 商品分類 represent? What does 事業分類 represent? Hierarchical? Which indicates OEM/Retail? |
| **PO Explanation** | [Product Owner fills this] |
| **Updated Understanding** | [AI updates after learning] |

---

## LOW PRIORITY CONCEPTS — Reference Only

| Concept | Current Understanding | Missing | Priority |
|---------|----------------------|---------|----------|
| 社員 (Employee) | Staff data; referenced by ID | Full org hierarchy, dept | ★★★ |
| 仕入先 (Vendor) | Procurement counterparty | Vendor performance, lead times | ★★★ |
| 仕入 Detail | Material + component + external processing | Component breakdown | ★★★ |
| コード (Code Registry) | Central code mapping (199 records) | What codes mean | ★★★ |
| GDrive Sync | Logsys synced from Sheets | Sync frequency, conflict resolution | ★★★ |

---

## Learning Session Guide

**Recommended Order:**
1. Start with **Card 1** (案件) — most critical
2. Then **Cards 2-5** (粗利, OEM/Retail, ステータス, 実績原価) — blocking queries
3. Then **Cards 6-8** (キャンセル, 返品, 期限) — accuracy risks
4. Then remaining as time/priority allows

**Each Session:**
- Duration: 15-20 minutes per card
- Format: PO fills "PO Explanation" section; AI fills "Updated Understanding"
- Document in this file for future reference
- One card per meeting is ideal

---

**Ready for Product Owner Teaching Sessions**  
**Start with:** Card 1 (案件)  
**Next:** Cards 2-5 in any order

