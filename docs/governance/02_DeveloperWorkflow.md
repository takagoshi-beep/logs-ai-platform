# Developer Workflow — 11-Step Implementation Process

**Version:** 2.0  
**Date:** 2026-07-02  
**Status:** Mandatory for all development

---

## Purpose

**Ensure Product Owner feedback loop stays < 1 day**

Every implementation must follow these 11 steps, in order, before review request.

**Skipping steps = Automatic rejection**

---

## 🚀 STEP 0: Fast Feedback Principle (NEW - PRIORITY!)

### Principle Statement

**AI OS完成 ≠ 構成完成**

New components only matter if they improve answer accuracy on REAL business questions.

Do NOT just build structure. Ship feedback loops.

### The Fast Feedback Cycle

```
New Layer/Component Added?
        ↓
Test with REAL Logsys DB
        ↓
Test with REAL Business Questions
        ↓
What's NOT working?
        ↓
Product Owner Feedback (< 24 hours)
        ↓
Fix Accuracy First (not structure)
        ↓
Knowledge Candidate updates
        ↓
Minimum structure fixes only
        ↓
Repeat
```

### DO vs DON'T

**DO:**
- ✅ Add feature → Test immediately with Logsys → Get PO feedback
- ✅ Find bugs → Fix bugs first → Clean up structure later
- ✅ PO says "answer is wrong" → Change logic, not structure
- ✅ Ship weekly with PO feedback loop

**DON'T:**
- ✗ Spend 2 weeks perfecting structure
- ✗ Add layers without testing them
- ✗ Wait for perfect code before testing
- ✗ Optimize architecture before validating

### Evidence of Fast Feedback

Before STEP 1:
- [ ] What new component are you adding?
- [ ] How will it improve answer accuracy?
- [ ] What business question will you test with?
- [ ] When is PO feedback scheduled? (should be < 24 hours)
- [ ] What does "success" look like?

### Proceed If
- ✅ Have answered all 5 questions above
- ✅ Know how to test with real data
- ✅ Have path to PO feedback

### Blocker If
- ❌ Building feature without knowing how to test it
- ❌ Adding structure without validation plan
- ❌ Cannot get PO feedback within 24 hours

---

## STEP 1: Project Policy Confirmation

### Action
Read and understand: `docs/governance/00_ProjectPolicy.md`

### Verify
- [ ] Understand project mission and principles
- [ ] Understand layer architecture
- [ ] Understand roles & responsibilities
- [ ] Understand development lifecycle

### Document
```
Policy Confirmation:
✓ Mission: Learned business terminology + strict governance
✓ Principles: Knowledge governance, Evidence-first, Layer separation
✓ Layers: Semantic → Knowledge → Reasoning → Evidence → UI
✓ Roles: Developer (Claude), Product Owner, System
```

### Proceed If
- ✅ All items understood
- ✅ No ambiguities remain

### Blocker If
- ❌ Policy conflicts with requested change
- ❌ Requested change violates principles

---

## STEP 2: Blueprint Confirmation

### Action
Read and verify: `docs/governance/01_Blueprint.md`

### Verify
- [ ] Understand Blueprint Rules 1-4
- [ ] Understand Layer Architecture (5 layers)
- [ ] Understand Data Provenance Requirements (6 fields)
- [ ] Understand Interpretation/Hypothesis/Candidate rules

### Verify Requested Change Against Blueprint
- [ ] Does change violate Rule 1? (Knowledge updates)
- [ ] Does change violate Rule 2? (Rule inference)
- [ ] Does change violate Rule 3? (Output types)
- [ ] Does change violate Rule 4? (PO approval)
- [ ] Does change require new provenance fields?
- [ ] Does change affect layer separation?

### Document
```
Blueprint Confirmation:
✓ Rule 1: AI Must NOT Update Knowledge
✓ Rule 2: AI Must NOT Infer Company Rules
✓ Rule 3: Only Fact/Interpretation/Hypothesis/Confidence
✓ Rule 4: Knowledge Only After PO Approval
✓ Provenance: All 6 fields
✓ No mixing layers
```

### Proceed If
- ✅ No violations detected
- ✅ Change aligns with Blueprint

### Blocker If
- ❌ Any Blueprint rule violated
- ❌ Layer architecture compromised

---

## STEP 3: Developer QA Rule Confirmation

### Action
Read and understand: `docs/governance/03_DeveloperQualityAssurance.md`

### Verify
- [ ] Understand QA Rules 1-10 (including NEW 7-10)
- [ ] Understand Evidence requirements (not just "PASS")
- [ ] Understand Code vs User Verification separation
- [ ] Understand UI change requirements

### Document
```
QA Rule Confirmation:
✓ Rule 1-6: Base quality standards
✓ Rule 7: Evidence required for PASS
✓ Rule 8: UI changes need screenshots (Code Complete ≠ UI Verified)
✓ Rule 9: Code Verification and User Verification separate
✓ Rule 10: Review prerequisites (all conditions must be met)
```

### Proceed If
- ✅ All rules understood
- ✅ Evidence requirements clear

---

## STEP 4: Review Checklist Confirmation

### Action
Read and prepare: `docs/governance/04_ReviewChecklist.md`

### Verify
- [ ] Understand all checklist items (now 18+ items)
- [ ] Understand Fact証跡 requirement (Provider/Table/Rows/Query/Timestamp)
- [ ] Understand PENDING display requirement
- [ ] Understand Interpretation/Fact separation

### Document
```
Review Checklist Confirmation:
□ All 18+ items understood
□ Fact証跡 items understood
□ PENDING display requirement understood
□ Layer mixing prevention understood
```

### Proceed If
- ✅ All checklist items understood
- ✅ Know what evidence to collect

---

## STEP 5: Implementation

### Action
Now implement the change

### Follow Guidelines
- ✅ Use existing patterns
- ✅ Keep changes minimal
- ✅ Add evidence trails (provenance)
- ✅ Keep layers separated
- ✅ Test locally with Logsys DB

### DO NOT Commit Yet
- ❌ Commits happen AFTER all verifications pass
- ❌ Save work locally only

---

## STEP 6: Test with Real Logsys DB

### Action
Run feature against REAL business questions

### Test Questions (Example)
```
Use real Logsys data to test:
- 今月のOEM粗利は?
- Fanatics案件の状況は?
- 優先すべき案件は?
- 売上が一番大きい顧客は?
```

### Verify
- [ ] Backend returns data from real DB
- [ ] No errors or exceptions
- [ ] Data looks reasonable
- [ ] Answer makes sense to business

### Document
```
Real DB Testing Results:
✓ Question: [question]
✓ DB response: [summary of data received]
✓ Issues found: [list or "None"]
✓ Ready for PO feedback: YES/NO
```

### Proceed If
- ✅ Feature works with real data
- ✅ Ready for Product Owner input

### Blocker If
- ❌ Errors or exceptions
- ❌ Data doesn't make sense
- ❌ Feature broken in production data

---

## STEP 7: Product Owner Feedback (< 24 hours)

### Action
Get Product Owner input IMMEDIATELY

### What to Ask
```
Product Owner Review:
- Does the answer look correct?
- Is the data quality acceptable?
- What's NOT working?
- What should we fix first?
- Confidence in approach: Y/N?
```

### Proceed If
- ✅ PO confirmed approach is sound
- ✅ Clear on what to fix next
- ✅ Have guidance for priorities

### Adjust If
- ❌ PO found issues → Go to STEP 5 (fix)
- ❌ Accuracy problems → Fix logic, not structure
- ❌ UX unclear → Improve clarity

---

## STEP 8: Knowledge Candidate Creation

### Action
Extract hypotheses as Knowledge Candidates (if applicable)

### Verify
- [ ] Candidates marked PENDING
- [ ] PO questions documented
- [ ] All candidates ready for PO review

### Document
```
Knowledge Candidates:
- Candidate 1: [concept] (PO review status: PENDING)
- Candidate 2: [concept] (PO review status: PENDING)
- [etc]
```

### Proceed If
- ✅ All candidates properly formatted
- ✅ Ready for PO confirmation

---

## STEP 9: Minimum Structure Fixes Only

### Action
Fix ONLY what's needed for accuracy

### DO NOT
- ✗ Optimize structure
- ✗ Refactor working code
- ✗ Add "future-proof" layers
- ✗ Over-engineer

### DO
- ✅ Fix bugs that hurt accuracy
- ✅ Add fields that help answers
- ✅ Change logic that's wrong
- ✅ Keep changes small

### Document
```
Structure Changes:
- What changed: [list]
- Why changed: [accuracy reason]
- What did NOT change: [what we kept simple]
```

### Proceed If
- ✅ Changes are minimal
- ✅ All changes justified by accuracy needs

---

## STEP 10: Developer Verification

### Action
Verify all governance requirements met

### Verification
- [ ] Blueprint verified (all 4 rules)
- [ ] QA verified (Rules 1-10 with Evidence)
- [ ] Checklist completed (18+ items)
- [ ] Code Verification: PASS
- [ ] User Verification: READY FOR REVIEW
- [ ] Screenshots captured (if UI change)
- [ ] Evidence documented

### Document
```
Developer Verification Complete:
✓ Blueprint: PASS
✓ QA: PASS (Rules 1-10)
✓ Checklist: PASS (18+ items)
✓ Code Verification: PASS
✓ User Verification: READY FOR REVIEW
```

### Proceed If
- ✅ All items verified
- ✅ Evidence complete

---

## STEP 11: Product Owner Review Request

### Action
Submit for Product Owner final review

### Pre-Review Verification
```
All Steps Complete?
STEP 0: ✅ Fast Feedback
STEP 1: ✅ Policy Confirmation
STEP 2: ✅ Blueprint Confirmation
STEP 3: ✅ QA Confirmation
STEP 4: ✅ Checklist Confirmation
STEP 5: ✅ Implementation
STEP 6: ✅ Real DB Testing
STEP 7: ✅ PO Feedback (< 24h)
STEP 8: ✅ Candidates Created
STEP 9: ✅ Structure Minimized
STEP 10: ✅ Verified
STEP 11: 🔄 Ready for Submit
```

### Submission Document
```
Phase [XX] Review Request

WORKFLOW RESULTS:
[Summary of STEP 0-10]

BLUEPRINT COMPLIANCE:
[All 4 rules verified with Evidence]

QA RESULTS:
Code Verification: PASS
User Verification: READY FOR REVIEW
[Rules 1-10 verified with Evidence]

CHECKLIST RESULTS:
[18+ items verified]

REAL DB TESTING:
[Questions tested, results documented]

PO FEEDBACK INCORPORATED:
[What changed based on feedback]

SCREENSHOTS:
[Attached]

UNMET ITEMS:
[List or "None"]

Ready for Final Review: YES
```

### Submit For Review
- [ ] All 11 steps documented
- [ ] All Evidence attached
- [ ] Screenshots included
- [ ] Unmet items listed
- [ ] NO COMMITS yet

---

## Critical Rules

### STEP 0 is MANDATORY
- ❌ DO NOT skip Fast Feedback Principle
- ✅ Always test with real data first
- ✅ Always get PO feedback < 24 hours

### All Steps in Order
- ❌ Cannot skip verification steps
- ✅ All steps must be documented
- ✅ Evidence required for each

### No Commits Before Complete
- ❌ Commits happen AFTER all steps
- ✅ Save locally during development
- ✅ Commit only after PO approval

---

## Why 11 Steps (Not 10)?

STEP 0 reminds us:

**Structure only matters if it ships answers.**

Do not optimize code. Optimize feedback speed.

---

**Workflow Version:** 2.0  
**Last Updated:** 2026-07-02  
**Status:** ✅ **MANDATORY - STEP 0 PRIORITY**

Start with STEP 0 every time.
