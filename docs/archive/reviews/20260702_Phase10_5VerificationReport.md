# Phase 10.5 Developer Verification — Concept Risk Review

**Date:** 2026-07-02  
**Phase:** 10.5 (Investigation-Only; Preparation for Phase 11)  
**Status:** ✓ COMPLETE — Ready for Product Owner Review

---

## Executive Summary

Phase 10.5 conducted risk analysis of business concepts before Phase 11 implementation. Key finding: **「案件」is not a single concept** — it has multiple granularities (PO-unit, Product-unit, etc.) that must be carefully defined.

Investigation identified 20 business concepts with potential misunderstanding risks and prioritized 5 CRITICAL questions for Product Owner confirmation.

---

## Deliverables Completed

### ✓ Deliverable 1: Concept Risk List
**File:** docs/reviews/20260702_ConceptRiskList.md
- 20 business concepts analyzed
- Risk level assigned: 3 CRITICAL, 7 HIGH, 10 MEDIUM
- For each concept:
  - Current AI understanding documented
  - Misunderstanding risks identified
  - Logsys representation candidates listed
  - Product Owner clarification needs noted
  - Priority level assigned

**Key Findings:**
- 🔴 CRITICAL: 案件 (case/project), 粗利 (gross profit), OEM vs Retail
- 🟠 HIGH: 受注, 発注, ステータス, キャンセル, 実績原価, PO, 商品単位
- 🟡 MEDIUM: 予定, 返品, 入金, 担当者, 締め, 納品, 仕入, 顧客, 会社粗利, 粗利率

---

### ✓ Deliverable 2: Product Owner Review Request
**File:** docs/reviews/20260702_ConceptRiskReviewRequest.md
- 5 CRITICAL questions in YES/NO/修正 format
- Questions cover:
  1. 案件 granularity decomposition (PO-unit vs Product-unit)
  2. 粗利 three variants definition (論理/実績/担当者別)
  3. OEM vs Retail classification criteria
  4. ステータス standardization across tables
  5. 実績原価 vs 論理原価 usage logic
- Actionable format suitable for Product Owner workflow
- Links to Phase 11 implementation steps

---

## Verification Checklist

### Concept Analysis ✓
- [x] Identified 20 business concepts with potential risks
- [x] Categorized by risk level (3 CRITICAL, 7 HIGH, 10 MEDIUM)
- [x] Analyzed each for:
  - Current AI understanding
  - Misunderstanding scenarios
  - Logsys representation
  - PO clarification needs
- [x] Particularly decomposed 案件 into multiple granularities
- [x] Document: 20260702_ConceptRiskList.md

### Review Request ✓
- [x] Created 5 CRITICAL questions
- [x] Used YES/NO/修正 format (answerable by Product Owner)
- [x] Each question actionable for Phase 11 design
- [x] Provided context and background
- [x] Specified expected response format
- [x] Document: 20260702_ConceptRiskReviewRequest.md

### Code Integrity ✓
- [x] Did NOT modify knowledge/semantic/ files
- [x] Did NOT modify reasoning_pipeline.py
- [x] Did NOT modify any other code files
- [x] Changes are investigation-only

### Database Integrity ✓
- [x] Did NOT modify data/sqlite/logsys.db
- [x] Did NOT modify any database schema
- [x] Read-only investigation only

### Git Status ✓
- [x] Did NOT commit any changes
- [x] Ready for Product Owner review before any commits
- [x] Investigation artifacts are docs/reviews only

---

## Investigation Results

### Concept Counts
| Category | Count | Notes |
|----------|-------|-------|
| Total concepts analyzed | 20 | Including 案件 decomposed into 6+ variants |
| CRITICAL concepts | 3 | 案件, 粗利, OEM vs Retail |
| HIGH priority concepts | 7 | Blocking Phase 11 decisions |
| MEDIUM priority concepts | 10 | May surface later; lower priority |
| **New risks identified** | **7** | Not captured in Phase 9 Semantic design |

### Risk Severity Breakdown
- 🔴 CRITICAL (must clarify before Phase 11): 3 concepts
- 🟠 HIGH (should clarify for Phase 11): 7 concepts
- 🟡 MEDIUM (nice to clarify; can address later): 10 concepts

### Product Owner Review Questions
- **Total questions created:** 5 (max per request format)
- **Format:** YES/NO/修正 (answerable)
- **Topics covered:**
  1. 案件 granularity (CRITICAL)
  2. 粗利 calculation (CRITICAL)
  3. OEM/Retail classification (CRITICAL)
  4. Status normalization (HIGH)
  5. Cost type logic (HIGH)

---

## Key Discoveries

### Discovery #1: 案件 Has Multiple Granularities
**Impact:** CRITICAL

Real Logsys treats "案件" at multiple levels:
- PO単位 (vendor purchase order unit)
- 商品単位 (product family unit)
- 顧客単位 (customer account unit)
- 売上単位 (sales transaction unit)
- 納品単位 (delivery event unit)
- 発注単位 (customer order unit)

**Implication:** SEM-009 cannot be single entity; must define which granularity(ies) AI uses for reasoning.

---

### Discovery #2: Gross Profit Is Complex
**Impact:** CRITICAL

Three distinct gross profit variants exist:
1. 論理粗利 (standard, for planning)
2. 実績粗利 (actual, for results)
3. 担当者別粗利 (by staff, for performance)

**Implication:** SEM-008 implementation must specify which variant is default, and how to handle when data incomplete.

---

### Discovery #3: OEM/Retail Distinction Is Undefined
**Impact:** CRITICAL

Classification criteria in Logsys not documented:
- Likely indicator: 集計.分類 column
- Alternative sources: 商品.事業分類, 顧客.顧客分類
- Edge cases: Samples, trials, test orders — classification unclear

**Implication:** Cannot implement SEM-001/SEM-002 without explicit rule from Product Owner.

---

### Discovery #4: Status Values Are Fragmented
**Impact:** HIGH

Each transaction table may use different status encoding:
- 売上.ステータス: 有効/キャンセル/テスト (known)
- 仕入.ステータス: Unknown from schema
- 発注依頼.ステータス: Unknown from schema

**Implication:** AI filtering logic will fail if status values aren't normalized.

---

### Discovery #5: Cost Type Usage Is Ambiguous
**Impact:** HIGH

Two cost types exist but usage pattern is unclear:
- 論理原価 (standard/budgeted cost)
- 実績原価 (actual cost after procurement)

**Implication:** Gross profit calculation could use wrong cost basis if logic not clarified.

---

## Phase 11 Impact

### Blocking Issues (Requires Product Owner Input)
1. ✋ 案件 granularity definition → blocks SEM-009 master table design
2. ✋ 粗利 calculation rules → blocks SEM-008 implementation
3. ✋ OEM/Retail classification → blocks SEM-001/SEM-002 rules

### Non-Blocking Issues (Good to Clarify)
4. ✓ Status normalization → clarifies filtering logic
5. ✓ Cost type usage → clarifies gross profit calculation

### Recommendation
**All 5 questions are answerable within 1 workshop session** (2-3 hours). Once answered, Phase 11 can proceed with high confidence.

---

## Changes Made (Or NOT Made)

### ✓ No Code Changes
- reasoning_pipeline.py: **UNCHANGED**
- knowledge/semantic/*.md files: **UNCHANGED**
- backend/services/*.py files: **UNCHANGED**

### ✓ No Database Changes
- data/sqlite/logsys.db: **UNCHANGED**
- backend/data/sqlite/logsys.db: **UNCHANGED**

### ✓ Investigation Only
- Created 2 new review documents
- No modifications to existing code or data
- No commits created

---

## Compliance Checklist

| Requirement | Status | Notes |
|------------|--------|-------|
| No Semantic Catalog modifications | ✓ PASS | knowledge/semantic/ untouched |
| No Reasoning Pipeline changes | ✓ PASS | reasoning_pipeline.py untouched |
| No code commits | ✓ PASS | Investigation only |
| Investigation complete | ✓ PASS | 20 concepts analyzed |
| Review request created | ✓ PASS | 5 questions, YES/NO/修正 format |
| Product Owner ready | ✓ PASS | Docs ready for review |

---

## Next Steps

### IMMEDIATE (Next 24 hours)
1. Share Phase 10.5 deliverables with Product Owner
   - docs/reviews/20260702_ConceptRiskList.md
   - docs/reviews/20260702_ConceptRiskReviewRequest.md

2. Schedule Product Owner workshop (1-2 hours) to confirm 5 critical questions

### AFTER PRODUCT OWNER CONFIRMATION
1. Phase 11 begins with clarified requirements
2. SEM-009 master table designed with confirmed granularity
3. SEM-001/SEM-002 classification rules implemented
4. SEM-008 calculation logic finalized

### PARALLEL (Optional)
- Continue Phase 10 learnings with non-blocking concepts
- Plan Phase 12 enhancements (SEM-011 through SEM-014)

---

## Conclusions

**Phase 10.5 Investigation: POSITIVE**

Concept risk review successfully identified business definition gaps that **must be clarified before Phase 11 design**. 

- ✓ 20 business concepts analyzed
- ✓ 5 CRITICAL questions formulated (answerable)
- ✓ Review documents ready for Product Owner
- ✓ Phase 11 roadmap can proceed once questions answered

**Recommendation: PROCEED TO PRODUCT OWNER REVIEW**

---

**Prepared by:** Phase 10.5 Investigation Team  
**Status:** Ready for Product Owner Workshop  
**Duration:** Phase 10.5 investigation: ~4 hours  
**Estimated PO Workshop:** 1-2 hours  
**Next Action:** Schedule Product Owner review session
