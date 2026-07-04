# Phase 10.5 — Concept Risk Review Request

**Date:** 2026-07-02  
**For:** Product Owner  
**Format:** YES / NO / 修正  
**Purpose:** Confirm business concept definitions before Phase 11 implementation

---

## Background

Phase 10 schema analysis revealed that real Logsys database has **multiple ambiguities** in core business concepts that could cause AI to give incorrect answers.

**Key Discovery:** Product Owner noted that 「案件」is not single concept — it has PO-unit and Product-unit granularities.

Phase 10.5 identified 20 business concepts with misunderstanding risks. This review request focuses on the **5 CRITICAL questions** that must be answered to unblock Phase 11 design.

---

## 5 Critical Review Questions

### ① 「案件」の粒度を整理する方針について

**提案:**

「案件」is not a single granularity. It should be decomposed into:

- **PO単位案件** — one Vendor PO = one case unit (purchasing/ordering granularity)
- **商品単位案件** — one Product family = one case unit (sales/planning granularity)

Additionally, depending on your business model, these may be relevant:
- 顧客単位案件 (customer-level grouping)
- 売上単位案件 (transaction-level grouping)
- 納品単位案件 (delivery event grouping)

Should AI reason about 案件 using **minimum 2 granularities (PO-unit + Product-unit)**, with additional levels optional?

**回答:**
- YES — Proceed with PO-unit + Product-unit minimum
- NO — Use single unified 案件 concept (explain how to distinguish in Logsys)
- 修正 — Use different granularities (specify which)

---

### ② 「粗利」の3種類の定義について

**提案:**

Gross profit should have three distinct variants:

1. **論理粗利 (Logical/Standard Gross Profit)**  
   = Sales Revenue × Standard Margin %  
   (Used for planning, forecasting; set at product level)

2. **実績粗利 (Actual Gross Profit)**  
   = Actual Revenue − Actual Procurement Cost (including 仕入諸掛)  
   (Used for month-end close; reflects actual costs)

3. **担当者別粗利 (Staff-Assigned Gross Profit)**  
   = Actual Gross Profit attributed to assigned sales person  
   (Used for sales staff performance; may differ if multiple staff per case)

**Additionally:** Should operational cost components (②検品 ③サンプル費用 ④販売経費 in 集計 table) be **included in or excluded from** gross profit calculation?

For monthly query like "OEM粗利は？", which variant should AI use by default?

**回答:**
- YES — All 3 variants defined as above; operational costs [INCLUDED/EXCLUDED]
- NO — Different definition needed (explain which)
- 修正 — Modify definitions as follows: [specify changes]

---

### ③ OEM案件 vs Retail案件 の分類基準について

**提案:**

OEM案件 and Retail案件 should be distinguished by:

**Primary Classifier:** 集計.分類 column

- If value = [OEM分類値]: OEM案件 (SEM-001)
- If value = [Retail分類値]: Retail案件 (SEM-002)
- If value = [Other]: [How to handle edge cases?]

**Backup Classifiers** (if primary not available):
- Customer segment (顧客.顧客分類)?
- Product type (商品.事業分類)?
- Order characteristics (inferred from transaction)?

Please provide:
1. What are the actual 集計.分類 values used in Logsys?
2. Do edge cases exist (samples, trials, test orders)? How are they classified?

**回答:**
- YES — Use 集計.分類 as primary; values are [list them]; edge cases [list handling]
- NO — Different classifier should be used (explain which)
- 修正 — Classification logic requires adjustment as follows: [specify]

---

### ④ 全テーブルのステータス定義について

**提案:**

Different Logsys tables may use different status values. To prevent AI filter errors, please standardize:

**For 売上 table:**
- 有効 (Valid transaction, included in analysis)
- キャンセル (Cancelled, should be excluded or reversed?)
- テスト (Test transaction, should be excluded?)

**For 仕入 table:**
- Values? (仕入確定フラグ=1 means confirmed? Use this or separate status field?)

**For 発注依頼 table:**
- Values?

**Required:** Please list **all valid status values** for each main transaction table (売上/仕入/発注依頼), and clarify filtering logic (include/exclude/reverse).

**回答:**
- YES — Status values are [complete list per table]; filtering logic is [specify]
- NO — Status definition is more complex (explain)
- 修正 — Status values should be revised as follows: [specify]

---

### ⑤ 実績原価 vs 論理原価 の使い分けについて

**提案:**

Two cost types should be used in different scenarios:

1. **論理原価 (Standard/Logical Cost)**  
   - Used for: Planning, forecasting, provisional calculations
   - Source: 商品.原価 or similar master cost
   - When NOT available: Fallback to? (use average? use standard?)

2. **実績原価 (Actual Cost)**  
   - Used for: Month-end actual results, variance analysis
   - Source: Actual 仕入 + 仕入諸掛 (procurement components)
   - When NOT available: Fallback to論理原価? Or mark as provisional?

**For monthly query like "OEM粗利は？":**
- Should AI always wait for 実績原価 data?
- Or provide provisional answer with 論理原価?
- If incomplete, how should AI indicate status (完全/概算)?

**回答:**
- YES — Use logic as described above; provisional answers should [specify handling]
- NO — Different cost logic should be used (explain)
- 修正 — Cost handling should be modified as follows: [specify]

---

## Additional Context

**Not requested this round** (can clarify in Phase 11 if needed):
- 受注 (order confirmation) — flagged for SEM-004 clarification
- 発注 (vendor vs customer order terminology)
- PO tracking logic
- 返品/キャンセル reversal specifics
- 納品 partial delivery handling
- Period definition (calendar vs fiscal)

---

## Deliverable from This Review

Once confirmed:
- Phase 11 Step 1: Design 案件 master table with confirmed granularities
- Phase 11 Step 2: Implement OEM/Retail classification rule
- Phase 11 Step 3-4: Implement gross profit calculation with 3 variants
- Phase 11 Step 5: Normalize status filtering across all tables
- Phase 11 Step 6: Implement cost type logic (論理 vs 実績)

---

## Please Respond

**Format:** For each question (①-⑤), provide one of:
- **YES** — Confirms proposal as-is
- **NO** — Reject proposal (explain why)
- **修正** — Approve with modifications (specify what changes)

**Additional notes:** If any question requires workshop/discussion, please indicate which topic needs discussion and estimated time needed.

---

**Submission Deadline:** (As per your schedule)  
**Next Step:** Once confirmed, Phase 11 implementation will begin with the clarified definitions.

**Response method:** Comment on this file, or email response to AI Platform team.
