# Governance Index — LOGS AI OS Rules & Processes

**Version:** 1.0  
**Date:** 2026-07-02  
**Status:** Authoritative reference for all governance

---

## Governance Structure

```
docs/governance/
├── 00_ProjectPolicy.md ................. Mission, principles, roles
├── 01_Blueprint.md .................... Architecture, layer rules, requirements
├── 02_DeveloperWorkflow.md ............ 10-step implementation process
├── 03_DeveloperQualityAssurance.md ... 10 QA rules with evidence requirements
├── 04_ReviewChecklist.md ............. Final pre-submission verification
└── 05_GovernanceIndex.md ............. This file (rule inventory)
```

---

## Complete Rules Inventory

### PROJECT GOVERNANCE

| Rule Set | Document | Items | Status |
|----------|----------|-------|--------|
| Project Policy | 00_ProjectPolicy.md | Mission, Principles (5), Roles, Lifecycle | ✅ Active |
| Blueprint Architecture | 01_Blueprint.md | 4 Core Rules + 5 Layers | ✅ Active |
| Workflow | 02_DeveloperWorkflow.md | 10 Steps | ✅ Active |
| QA Standards | 03_DeveloperQualityAssurance.md | 10 Rules | ✅ Active |
| Review Process | 04_ReviewChecklist.md | 15 Checklist Items | ✅ Active |

---

## BLUEPRINT RULES (Non-Negotiable)

### Rule 1: AI Must NOT Update Knowledge
- **File:** 01_Blueprint.md, Line ~150
- **Enforcement:** Code review + git diff check
- **Violation Severity:** 🔴 BLOCKER
- **Evidence Required:** `git diff knowledge/` → 0 changes

### Rule 2: AI Must NOT Infer Company Rules
- **File:** 01_Blueprint.md, Line ~170
- **Enforcement:** All hypotheses marked PENDING
- **Violation Severity:** 🔴 BLOCKER
- **Evidence Required:** `grep po_review_status: "PENDING"`

### Rule 3: Only Fact/Interpretation/Hypothesis/Confidence
- **File:** 01_Blueprint.md, Line ~190
- **Enforcement:** Output structure verification
- **Violation Severity:** 🔴 BLOCKER
- **Evidence Required:** 4 types only in phase_13

### Rule 4: Knowledge Only After PO Approval
- **File:** 01_Blueprint.md, Line ~210
- **Enforcement:** Process documentation
- **Violation Severity:** 🔴 BLOCKER
- **Evidence Required:** Candidates marked PENDING + PO questions

---

## WORKFLOW STEPS (10-Step Mandatory Process)

| Step | Name | File | Purpose |
|------|------|------|---------|
| STEP 1 | Policy Confirmation | 02_DeveloperWorkflow.md:L50 | Understand project mission |
| STEP 2 | Blueprint Confirmation | 02_DeveloperWorkflow.md:L85 | Verify compliance requirements |
| STEP 3 | QA Rule Confirmation | 02_DeveloperWorkflow.md:L130 | Understand quality standards |
| STEP 4 | Review Checklist Confirmation | 02_DeveloperWorkflow.md:L155 | Know what to verify |
| STEP 5 | Existing Structure Confirmation | 02_DeveloperWorkflow.md:L180 | Understand impact |
| STEP 6 | Implementation | 02_DeveloperWorkflow.md:L225 | Write code |
| STEP 7 | Blueprint Compliance Check | 02_DeveloperWorkflow.md:L260 | Verify Blueprint satisfied |
| STEP 8 | Screen Verification | 02_DeveloperWorkflow.md:L310 | Test in browser |
| STEP 9 | Developer QA Check | 02_DeveloperWorkflow.md:L355 | Verify quality standards |
| STEP 10 | Product Owner Review Request | 02_DeveloperWorkflow.md:L410 | Submit for review |

**Key Rule:** All steps mandatory, in order, documented with evidence.

---

## QA RULES (10 Quality Standards)

### Base Rules (1-6): General Quality

| Rule | Name | Evidence Type | File |
|------|------|---------------|------|
| Rule 1 | Code Correctness | Code review | 03_DeveloperQualityAssurance.md:L40 |
| Rule 2 | No Regressions | Test results | 03_DeveloperQualityAssurance.md:L60 |
| Rule 3 | Error Handling | grep try/except | 03_DeveloperQualityAssurance.md:L80 |
| Rule 4 | Backward Compatibility | API contracts | 03_DeveloperQualityAssurance.md:L100 |
| Rule 5 | Pattern Compliance | Code examples | 03_DeveloperQualityAssurance.md:L120 |
| Rule 6 | Local Testing | Screenshots | 03_DeveloperQualityAssurance.md:L140 |

### New Rules (7-10): Enhanced Verification

| Rule | Name | Key Requirement | File |
|------|------|-----------------|------|
| Rule 7 | Evidence Required | Every PASS needs 2+ lines of Evidence | 03_DeveloperQualityAssurance.md:L165 |
| Rule 8 | UI Verification | Screenshots required for UI changes | 03_DeveloperQualityAssurance.md:L210 |
| Rule 9 | Code vs User Split | Must separate technical and functional verification | 03_DeveloperQualityAssurance.md:L280 |
| Rule 10 | Review Prerequisites | All conditions must be met (8 items) | 03_DeveloperQualityAssurance.md:L350 |

**Key Rule:** All PASS claims must include specific, verifiable Evidence.

---

## REVIEW CHECKLIST ITEMS (15 Items)

### Architecture & Governance (4 items)

- [ ] Blueprint違反なし
- [ ] Layer責務違反なし
- [ ] 重複実装なし
- [ ] 不要Layer追加なし

### Knowledge Governance (2 items)

- [ ] 既存Knowledge更新なし
- [ ] Product Owner承認前Knowledge追加なし

### Code Quality (2 items)

- [ ] 実画面確認済み
- [ ] 表記ゆれなし

### Data Integrity (1 item)

- [ ] 実DB取得ならFact証跡あり

### Layer Content (4 items)

- [ ] Fact層: Provider/Table/Query/Rows/Timestamp/Data表示あり
- [ ] Interpretation層は意味だけ
- [ ] Hypothesis層は推定だけ
- [ ] Knowledge CandidateはPENDING

### Documentation (1 item)

- [ ] 未完了項目を列挙

**Location:** 04_ReviewChecklist.md

---

## LAYER ARCHITECTURE

```
Layer 1: Semantic Layer (SEM-001 to SEM-010)
├─ Business concepts (not DB structure)
├─ Files: knowledge/semantic/*.md
└─ Rule: Independent of data source

Layer 2: Knowledge Layer
├─ Business rules (PO-approved only)
├─ Files: knowledge/business_rules/*.md
└─ Rule: No AI updates without PO confirmation

Layer 3: Reasoning Layer
├─ AI thinking (Fact→Interpretation→Hypothesis→Candidate)
├─ Files: backend/services/reasoning_pipeline.py
└─ Sub-layers: 4 separate layers (see Blueprint)

Layer 4: Evidence Layer
├─ Real data from Providers
├─ Files: backend/services/data_providers.py
└─ Rule: Read-only + provenance required

Layer 5: UI Layer
├─ Transparent reasoning display
├─ Files: frontend/app/reasoning/page.tsx
└─ Rule: Show all layers, never hide steps
```

**Rule:** Each layer has single responsibility. No mixing concerns.

---

## PROVENANCE REQUIREMENTS

**When querying real database, Fact layer MUST include:**

1. **Provider** — "LogsysProvider"
2. **Source Table** — "集計"
3. **Query Conditions** — Full WHERE clause
4. **Rows Retrieved** — Actual count from DB
5. **Timestamp** — When retrieved (ISO format)
6. **Raw Data** — Actual values

**Missing any field = Fact rejected**

---

## STATUS KEYWORDS (Rule 8)

- ✅ "Code Complete" — Code changes done (NOT feature done)
- ⏳ "Waiting for UI Verification" — Screenshots pending
- ✅ "UI Verified" — Screenshots taken, working
- ✅ "Ready for Review" — All conditions met
- ⏳ "Incomplete" — Work in progress
- ❌ "Blocker" — Cannot proceed

**Key:** "Code Complete" ≠ "Feature Complete"

---

## VERIFICATION SEPARATION (Rule 9)

**Code Verification (Technical):**
- Does code work logically?
- Are there errors?
- Does it handle edge cases?
- Evidence: grep, code review, unit tests

**User Verification (Functional):**
- Can user see the feature?
- Does it display correctly?
- Are all elements present?
- Evidence: Screenshots, browser testing

**Both MUST pass independently.**

---

## EVIDENCE REQUIREMENTS (Rule 7)

### Invalid Evidence
- ❌ "Code looks good"
- ❌ "PASS" alone
- ❌ "Tested locally"
- ❌ "No errors"

### Valid Evidence
- ✅ "grep "timestamp" found at line 107"
- ✅ "git diff knowledge/ → 0 changes"
- ✅ "Screenshot [filename]: Feature displays 4 layers"
- ✅ "API returns: {"layer": "FACT", ...}"

---

## REVIEW REQUEST CONDITIONS (Rule 10)

**Can request review only when:**

1. ✅ Workflow complete (all 10 steps documented)
2. ✅ QA passed (Rules 1-10 with Evidence)
3. ✅ Blueprint verified (all 4 rules satisfied)
4. ✅ Checklist complete (all 15 items checked)
5. ✅ Code Verification: PASS
6. ✅ User Verification: READY FOR REVIEW
7. ✅ Evidence attached
8. ✅ Screenshots captured

**Cannot request review if:**
- ❌ Any step skipped
- ❌ Any rule failing
- ❌ Any checklist item unchecked
- ❌ Code Verification incomplete
- ❌ User Verification incomplete
- ❌ Evidence missing
- ❌ Screenshots missing

---

## ROLES & RESPONSIBILITIES

| Role | Responsibility | Reference |
|------|-----------------|-----------|
| Claude (Developer) | Follow Workflow + QA + Checklist | 00_ProjectPolicy.md / 02_DeveloperWorkflow.md |
| Product Owner | Review Knowledge Candidates | 01_Blueprint.md |
| System | Generate hypotheses (not rules) | 01_Blueprint.md |

---

## EXCEPTION HANDLING

| Situation | Process |
|-----------|---------|
| Blueprint violation unavoidable | Document + Justify + PO approval |
| Workflow step unclear | Clarify + Document rationale |
| QA evidence insufficient | Gather more + Don't proceed |
| Unmet items on checklist | Fix + Re-verify + Then submit |

---

## WHEN ADDING NEW RULES

**Process for adding governance rules:**

1. Document in appropriate file (00-04)
2. Add to this Index (05_GovernanceIndex.md)
3. Update related files if needed
4. Archive previous version
5. Get Product Owner awareness

**Never:**
- ❌ Add rules without documenting
- ❌ Skip Index update
- ❌ Forget to update related files
- ❌ Delete old rules without archiving

---

## Document Purpose Summary

| File | Purpose | Audience |
|------|---------|----------|
| 00_ProjectPolicy.md | Why we do this | Everyone |
| 01_Blueprint.md | What we cannot violate | Developers |
| 02_DeveloperWorkflow.md | How to implement safely | Developers |
| 03_DeveloperQualityAssurance.md | What quality means | Developers |
| 04_ReviewChecklist.md | What to verify before review | Developers |
| 05_GovernanceIndex.md | Where to find each rule | Everyone |

---

## Quick Reference: Rule Lookup

**Need to know...**

- ...the project mission? → `00_ProjectPolicy.md`
- ...Blueprint constraints? → `01_Blueprint.md`
- ...implementation steps? → `02_DeveloperWorkflow.md`
- ...QA requirements? → `03_DeveloperQualityAssurance.md`
- ...review checklist? → `04_ReviewChecklist.md`
- ...where a rule is? → `05_GovernanceIndex.md`

---

## Governance Maintenance

| Task | Frequency | Owner | File |
|------|-----------|-------|------|
| Review all rules | Per phase | Product Owner | All |
| Update checklist | As needed | Claude | 04_ReviewChecklist.md |
| Update Index | With any change | Claude | 05_GovernanceIndex.md |
| Archive old rules | Annually | Product Owner | Archive/ |

---

**Governance Index Version:** 1.0  
**Last Updated:** 2026-07-02  
**Status:** ✅ **ACTIVE & AUTHORITATIVE**

Use this document to find any governance rule.  
Update this document when adding new rules.
