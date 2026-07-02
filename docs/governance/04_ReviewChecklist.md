# Review Checklist — Pre-Submission Verification

**Version:** 1.0  
**Date:** 2026-07-02  
**Status:** Mandatory before review request

---

## Purpose

Final verification before submitting to Product Owner.

**Do NOT request review without completing all items.**

---

## Checklist Items

### Architecture & Governance (Mandatory)

- [ ] **Blueprint違反なし**
  - Verification: All 4 Blueprint Rules satisfied
  - Evidence: Blueprint Compliance Report
  
- [ ] **Layer責務違反なし**
  - Verification: Each layer has single responsibility
  - Evidence: Code review of layer boundaries

- [ ] **重複実装なし**
  - Verification: No functions/classes do same thing
  - Evidence: Checked similar existing code
  
- [ ] **不要Layer追加なし**
  - Verification: No unnecessary layer created
  - Evidence: Justified each layer's existence
  
- [ ] **既存Knowledge更新なし**
  - Verification: No knowledge/ files modified
  - Evidence: `git diff knowledge/` → 0 changes

### Knowledge Governance (Mandatory)

- [ ] **Product Owner承認前Knowledge追加なし**
  - Verification: No auto-updates to Knowledge
  - Evidence: Code review shows no Knowledge updates
  
- [ ] **Knowledge CandidateはPENDING**
  - Verification: All candidates marked PENDING
  - Evidence: grep "po_review_status": "PENDING"

### Code Quality (Mandatory)

- [ ] **実画面確認済み**
  - Verification: Tested in browser
  - Evidence: Screenshots attached
  
- [ ] **表記ゆれなし**
  - Verification: Consistent naming throughout
  - Evidence: Checked provider names (Logsys not Logisys)

### Data Integrity (If Applicable)

- [ ] **実DB取得ならFact証跡あり**
  - Verification: If querying real DB, provenance included
  - Evidence: Fact layer shows Provider/Table/Query/Rows/Timestamp

### Layer Content (If Applicable)

- [ ] **Fact層: Provider/Table/Query/Rows/Timestamp/Data表示あり**
  - Provider: Data source (e.g., LogsysProvider)
  - Table: Source table (e.g., 集計)
  - Query: WHERE conditions
  - Rows: Count from DB
  - Timestamp: When retrieved
  - Data: Raw values
  - Evidence: Fact structure verified

- [ ] **Interpretation層は意味だけ**
  - Verification: No ¥ amounts, no raw counts, only patterns
  - Evidence: Code review shows observations only
  - Example VALID: "集計テーブルに『分類=OEM』フラグが存在"
  - Example INVALID: "OEM粗利: ¥456,789"

- [ ] **Hypothesis層は推定だけ**
  - Verification: All hypotheses have confidence scores
  - Evidence: Confidence values present (0.72, 0.68, 0.55)
  - Example VALID: "可能性が高い (72% confidence)"
  - Example INVALID: "確定的に..." (no confidence)

- [ ] **Knowledge CandidateはPENDING**
  - Verification: po_review_status = "PENDING"
  - Evidence: All 3+ candidates show PENDING on screen

### Documentation (Mandatory)

- [ ] **未完了項目を列挙**
  - Verification: Identified any unmet items
  - Evidence: Unmet items section in report
  - If none: Explicitly state "Unmet items: None"

---

## Pre-Submission Verification

Before submitting, verify:

```
Workflow Completion:
  ✅ STEP 1-10 of Developer Workflow completed
  Evidence: [brief summary of each step]

QA Rules:
  ✅ Rules 1-6: PASS with Evidence
  ✅ Rule 7: Evidence attached to all claims
  ✅ Rule 8: UI changes verified with screenshots
  ✅ Rule 9: Code Verification PASS + User Verification READY
  ✅ Rule 10: All prerequisites met

Blueprint Compliance:
  ✅ Rule 1: No Knowledge updates (Evidence: ...)
  ✅ Rule 2: All candidates PENDING (Evidence: ...)
  ✅ Rule 3: Only 4 output types (Evidence: ...)
  ✅ Rule 4: No auto-update logic (Evidence: ...)

All Checklist Items:
  ✅ All 15 items: CHECKED
  ✅ Evidence attached for each
  ✅ No unmet items OR unmet items listed

STATUS: ✅ READY FOR PRODUCT OWNER REVIEW
```

---

## Submission Checklist

Items to include in review request:

- [ ] **Workflow Results**
  - Summary of each STEP 1-10
  - Evidence for each step
  
- [ ] **QA Results**
  - Rules 1-6 verification (with Evidence)
  - Rules 7-10 verification (with Evidence)
  - Code Verification report
  - User Verification report

- [ ] **Blueprint Compliance**
  - All 4 rules verified (with Evidence)
  - Provenance complete (if applicable)
  - Layer separation confirmed

- [ ] **Review Checklist**
  - All 15 items checked
  - Evidence for each item
  - Unmet items listed

- [ ] **Screenshots**
  - Feature overview
  - Detail views
  - PENDING badges (if applicable)
  - Console without errors

- [ ] **Code Changes**
  - Files modified: [list]
  - New functions: [list]
  - Breaking changes: [none/list]

---

## Common Issues & Resolutions

### Issue: "Code Complete" but UI not verified
**Resolution:**
- Take screenshots showing feature working
- Add to submission
- Update status to "UI Verified"

### Issue: Evidence incomplete
**Resolution:**
- For each PASS, add 2+ lines of specific Evidence
- Include exact file names/line numbers
- Make Evidence independently verifiable

### Issue: Unmet items but submitting anyway
**Resolution:**
- Do NOT submit
- Go back to failing step
- Fix issue
- Re-verify
- Then submit

### Issue: Blueprint violations found
**Resolution:**
- Do NOT submit
- Revert violation
- Re-implement correctly
- Verify Blueprint compliance
- Then submit

---

## Red Flags (Do NOT Submit If)

- ❌ Any checklist item unchecked
- ❌ Any Evidence missing or vague
- ❌ Blueprint Rule violated
- ❌ Code Verification incomplete
- ❌ User Verification incomplete
- ❌ Screenshots not captured
- ❌ "Unmet items: [non-empty list]" without resolution
- ❌ Any step of Developer Workflow skipped
- ❌ Any QA Rule not verified

---

## Green Lights (OK to Submit If)

- ✅ All 15 checklist items checked
- ✅ All Evidence specific and verifiable
- ✅ All Blueprint Rules satisfied (with Evidence)
- ✅ Code Verification: PASS
- ✅ User Verification: READY FOR REVIEW
- ✅ Screenshots captured and attached
- ✅ "Unmet items: None" OR listed items explained
- ✅ All 10 Workflow steps documented
- ✅ All 10 QA Rules verified

---

## Submission Format

```
═══════════════════════════════════════════════════════
Phase [XX] Review Request
═══════════════════════════════════════════════════════

WORKFLOW RESULTS
────────────────
STEP 1: ✅ Policy Confirmation
STEP 2: ✅ Blueprint Confirmation
STEP 3: ✅ QA Rule Confirmation
STEP 4: ✅ Review Checklist Confirmation
STEP 5: ✅ Existing Structure Confirmation
STEP 6: ✅ Implementation Complete
STEP 7: ✅ Blueprint Compliance Check
STEP 8: ✅ Screen Verification
STEP 9: ✅ Developer QA Check
STEP 10: ✅ Ready for Submission

QA RESULTS
──────────
Code Verification: PASS
  Evidence: [list key checks]

User Verification: READY FOR REVIEW
  Evidence: Screenshots [list files]

BLUEPRINT COMPLIANCE
────────────────────
Rule 1: PASS - Evidence: git diff → 0 changes
Rule 2: PASS - Evidence: po_review_status = "PENDING"
Rule 3: PASS - Evidence: 4 types only (facts, interpretation, ai_hypotheses, knowledge_candidates)
Rule 4: PASS - Evidence: No auto-update logic found

REVIEW CHECKLIST
────────────────
✅ Blueprint違反なし
✅ Layer責務違反なし
✅ 重複実装なし
✅ 不要Layer追加なし
✅ 既存Knowledge更新なし
✅ Product Owner承認前Knowledge追加なし
✅ 実画面確認済み
✅ 表記ゆれなし
✅ 実DB取得ならFact証跡あり
✅ Fact層: Provider/Table/Query/Rows/Timestamp/Data表示あり
✅ Interpretation層は意味だけ
✅ Hypothesis層は推定だけ
✅ Knowledge CandidateはPENDING
✅ 未完了項目: None

CODE CHANGES
────────────
Files modified:
- backend/services/reasoning_pipeline.py
- frontend/app/reasoning/page.tsx

New functions:
- _interpret_facts()

Breaking changes: None

SCREENSHOTS
───────────
- [20260702_Phase13_Layer1_FACT.png]
- [20260702_Phase13_Layer2_INTERPRETATION.png]
- [20260702_Phase13_Layer3_HYPOTHESIS.png]
- [20260702_Phase13_Layer4_CANDIDATE.png]

UNMET ITEMS
───────────
None

OVERALL STATUS: ✅ READY FOR PRODUCT OWNER REVIEW

Comments:
[Any additional context]

═══════════════════════════════════════════════════════
```

---

**Checklist Version:** 1.0  
**Last Updated:** 2026-07-02  
**Status:** ✅ **MANDATORY BEFORE SUBMISSION**

Do not request review without completing this checklist.
