# Developer Quality Assurance Rules

**Version:** 2.0  
**Date:** 2026-07-02  
**Status:** All rules enforced

---

## Base QA Rules (Rules 1-6)

### Rule 1: Code Correctness
**Principle:** Implementation must be logically correct

**Verification:**
- [ ] Code follows language conventions
- [ ] Logic is sound
- [ ] No obvious bugs
- [ ] Edge cases handled

**Evidence Example:**
```
✅ Rule 1 PASS

Evidence:
- Code review shows correct null checks
- All branches tested locally
- Error handling in place for edge cases
```

---

### Rule 2: No Regressions
**Principle:** Changes must not break existing functionality

**Verification:**
- [ ] Existing features still work
- [ ] Tested other affected modules
- [ ] No unexpected side effects

**Evidence Example:**
```
✅ Rule 2 PASS

Evidence:
- Tested Q1/Q2/Q3/Q4 questions still work
- Backend returns expected format
- Frontend displays without errors
```

---

### Rule 3: Error Handling
**Principle:** Code must handle failure gracefully

**Verification:**
- [ ] Try-catch blocks present
- [ ] Error messages informative
- [ ] Fallback behaviors defined
- [ ] Logging in place

**Evidence Example:**
```
✅ Rule 3 PASS

Evidence:
- grep try/except: 5 blocks found
- Error messages logged to stdout
- Fallback returns default structure
```

---

### Rule 4: Backward Compatibility
**Principle:** Changes must not break existing interfaces

**Verification:**
- [ ] Old API calls still work
- [ ] Old field names supported (if applicable)
- [ ] Version compatibility maintained
- [ ] Migration path clear (if applicable)

**Evidence Example:**
```
✅ Rule 4 PASS

Evidence:
- Existing /reasoning endpoint returns old + new fields
- Old field names still supported
- No breaking changes to TypeScript interfaces
```

---

### Rule 5: Pattern Compliance
**Principle:** Follow established patterns in codebase

**Verification:**
- [ ] Similar code uses similar patterns
- [ ] No new patterns invented unnecessarily
- [ ] Naming conventions consistent
- [ ] File organization logical

**Evidence Example:**
```
✅ Rule 5 PASS

Evidence:
- _extract_facts() follows _q1_oem_gross_profit() pattern
- Naming: _verb_noun() for private functions
- Located in same file as similar functions
```

---

### Rule 6: Local Testing
**Principle:** Feature must be tested locally before submission

**Verification:**
- [ ] Tested in development environment
- [ ] Feature works as intended
- [ ] No local errors
- [ ] Screenshots captured

**Evidence Example:**
```
✅ Rule 6 PASS

Evidence:
- localhost:3000/reasoning tested
- Question submitted: "今月のOEM粗利は?"
- Phase 13 layers display correctly
- Screenshots: [list files]
```

---

## NEW QA Rules (Rules 7-10)

### Rule 7: PASS Claims Must Include Evidence

**Rule Statement:**
"PASS" だけの報告は禁止します。必ず Evidence を添付してください。

**What This Means:**
- ❌ INVALID: "Rule 1 PASS"
- ✅ VALID: "Rule 1 PASS (Evidence: ...)"

**Evidence Format:**

For Code-Related QA:
```
✅ Blueprint Rule 1 PASS

Evidence:
• git diff knowledge/ → 0 changes
• git diff knowledge/semantic/ → 0 changes
• grep "Edit.*knowledge" → 0 matches
```

For Feature-Related QA:
```
✅ Feature Display PASS

Evidence:
• Frontend renders without errors
• All 4 layers visible on screen
• PENDING badges show on candidates
• Screenshots: [list files]
```

For Data-Related QA:
```
✅ Fact Provenance Complete PASS

Evidence:
• grep timestamp: Found at line 107
• grep provider: Found "LogsysProvider"
• grep query_conditions: Full WHERE clause present
• Rows_retrieved field: Present
```

**Verification:**
- [ ] Every PASS has 2+ lines of Evidence
- [ ] Evidence is specific (not generic)
- [ ] Evidence can be independently verified
- [ ] Evidence includes exact locations or file references

**Blocker If:**
- ❌ PASS without Evidence
- ❌ Generic Evidence ("code looks good")
- ❌ Unverifiable claims

---

### Rule 8: UI Changes Require Screenshot Verification

**Rule Statement:**
UIを変更した場合、コード変更完了 ≠ Feature 完了
スクリーンショット取得まで "Completed" は禁止

**Status Keywords:**
- ✅ "Code Complete" — Code changes done
- ⏳ "Waiting for UI Verification" — Screenshots pending
- ✅ "UI Verified" — Screenshots taken, feature works
- ✅ "Ready for Review" — All verifications passed

**Timeline:**
```
Code Changes
    ↓
Local Testing (npm run dev + manual test)
    ↓
Screenshot Capture (evidence of working feature)
    ↓
Feature Complete
```

**Evidence Required:**
```
UI Changes Summary:

Code Changes:
✅ reasoning_pipeline.py: Added _interpret_facts() function
   Evidence: Lines 140-183 added

UI Display:
⏳ Phase 13 section rendering in progress
   Waiting for: Screenshot verification

Screenshots Needed:
- [ ] Layer 1: FACT (showing Provider/Table/Rows/Timestamp)
- [ ] Layer 2: INTERPRETATION (showing observations)
- [ ] Layer 3: HYPOTHESIS (showing confidence scores)
- [ ] Layer 4: KNOWLEDGE_CANDIDATE (showing PENDING badge)

Status: Waiting for UI Verification
```

**Screenshot Requirements:**
- [ ] Feature is visible and working
- [ ] No errors in browser console
- [ ] All expected elements present
- [ ] Readable quality (not blurry)
- [ ] Timestamp or context in filename

**Example Screenshot Naming:**
```
20260702_Phase13_Layer1_FACT_Detail.png
20260702_Phase13_AllLayers_Overview.png
20260702_KNOWLEDGE_CANDIDATE_PENDING_Badge.png
```

**Blocker If:**
- ❌ UI changes submitted without screenshots
- ❌ Claim "Feature Complete" without verification
- ❌ Screenshots show errors or broken display

---

### Rule 9: Code Verification vs User Verification

**Rule Statement:**
Code Verification と User Verification を必ず分けてください

**What This Means:**

Code works logically ≠ User can see it working

Both must be verified separately.

**Code Verification (Technical):**
```
Code Verification:

✅ _extract_facts() returns dict with all required fields
   Evidence: grep "timestamp\|provider\|rows_retrieved"
   
✅ _interpret_facts() takes facts, returns observations
   Evidence: Function signature verified
   
✅ _generate_hypotheses() receives both facts and interpretation
   Evidence: Line 584 shows both parameters passed
   
✅ All candidates marked po_review_status = "PENDING"
   Evidence: grep "PENDING" → 3 matches found

Status: Code Verification PASS
```

**User Verification (Functional):**
```
User Verification:

✅ Browser displays Phase 13 section
   Evidence: Screenshot shows section header

✅ Layer 1 shows Provider/Table/Query/Rows/Timestamp
   Evidence: Screenshot shows all fields

❌ Layer 2 INTERPRETATION not displaying
   Evidence: Screenshot shows missing section

⏳ Need to debug why Interpretation layer not rendering
   Next step: Check TypeScript interface definition

Status: User Verification INCOMPLETE
   Blocker: Missing INTERPRETATION layer display
   Need to fix: InterpretationLayer interface or rendering logic
```

**Template:**

```
═════════════════════════════════════════════════════
Code Verification
═════════════════════════════════════════════════════

✅ Item 1: [Verified] 
   Evidence: [How verified]

✅ Item 2: [Verified]
   Evidence: [How verified]

✅ Item 3: [Verified]
   Evidence: [How verified]

Status: Code Verification PASS / INCOMPLETE
Blockers: [List any]

═════════════════════════════════════════════════════
User Verification
═════════════════════════════════════════════════════

✅ Item 1: [Visible]
   Evidence: Screenshot [path]

⏳ Item 2: [Waiting for...]
   Evidence: [Why not ready]

❌ Item 3: [Broken]
   Evidence: Screenshot [path] shows issue

Status: User Verification READY FOR REVIEW / INCOMPLETE
Blockers: [List any]
```

**Blocker If:**
- ❌ Code Verification = User Verification
- ❌ No distinction between the two
- ❌ Claim "Verified" without both types passing

---

### Rule 10: Review Request Prerequisites

**Rule Statement:**
Product Ownerへレビュー依頼できるのは [条件] のみ

**Conditions (ALL must be met):**
1. ✅ Developer Workflow followed (all 10 steps)
2. ✅ Developer QA passed (Rules 1-10)
3. ✅ Review Checklist completed (all items)
4. ✅ Code Verification PASS
5. ✅ User Verification READY FOR REVIEW
6. ✅ All Evidence documented
7. ✅ Screenshots captured
8. ✅ Blueprint Compliance confirmed

**Status Before Review Request:**
```
Developer Workflow:
  ✅ STEP 1-10: COMPLETE

Developer QA:
  ✅ Rule 1-6: PASS (with Evidence)
  ✅ Rule 7: PASS with Evidence (all claims documented)
  ✅ Rule 8: UI Verified (screenshots captured)
  ✅ Rule 9: Code AND User verified (separated)
  ✅ Rule 10: All prerequisites met

Blueprint Compliance:
  ✅ Rule 1: PASS (Evidence: no Knowledge changes)
  ✅ Rule 2: PASS (Evidence: all PENDING)
  ✅ Rule 3: PASS (Evidence: 4 types only)
  ✅ Rule 4: PASS (Evidence: no auto-update)

Review Checklist:
  ✅ All items checked
  ✅ All evidence attached
  ✅ No blockers

STATUS: ✅ READY FOR PRODUCT OWNER REVIEW
```

**What "READY FOR REVIEW" Means:**
- Product Owner can review immediately
- No additional work needed from developer
- All governance requirements met
- All evidence provided
- Screenshots attached
- Unmet items documented (if any)

**What "NOT READY FOR REVIEW" Means:**
- Missing Code Verification results
- Missing User Verification (screenshots)
- Blueprint violations unfixed
- Unmet Review Checklist items
- Evidence incomplete or missing

**Blocker For Review Request If:**
- ❌ Any step skipped
- ❌ Any rule not verified
- ❌ Any checklist item unchecked
- ❌ Code Verification incomplete
- ❌ User Verification incomplete
- ❌ Evidence missing
- ❌ Screenshots not captured
- ❌ Blueprint violations present

---

## QA Verification Workflow

```
Phase Starts
    ↓
Developer Workflow (10 steps)
    ├─ STEP 1-5: Planning & verification
    ├─ STEP 6: Implementation
    └─ STEP 7-9: QA Checks (Rules 1-10)
    ↓
Code Verification
    ├─ Rules 1-6: General QA
    ├─ Rule 7: Evidence attached
    └─ Rule 9 Part 1: Code verified
    ↓
User Verification
    ├─ Rule 8: Screenshots captured
    └─ Rule 9 Part 2: User sees it working
    ↓
Review Checklist Complete
    ├─ All items verified
    ├─ All evidence attached
    └─ No unmet items remaining
    ↓
Rule 10 Check: All Prerequisites Met?
    ├─ If YES → Ready for PO Review
    └─ If NO → Return to appropriate step
    ↓
Product Owner Review Request (STEP 10)
    ├─ Submit all documentation
    ├─ Attach all screenshots
    └─ List any unmet items
```

---

## QA Report Template

Use for final QA submission:

```
═══════════════════════════════════════════════════════
Phase [XX] Developer Quality Assurance Report
═══════════════════════════════════════════════════════

Base QA Rules (1-6):

✅ Rule 1: Code Correctness
   Evidence: [specific details]

✅ Rule 2: No Regressions
   Evidence: [what was tested]

✅ Rule 3: Error Handling
   Evidence: [grep results or code snippets]

✅ Rule 4: Backward Compatibility
   Evidence: [API contracts verified]

✅ Rule 5: Pattern Compliance
   Evidence: [pattern examples]

✅ Rule 6: Local Testing
   Evidence: [screenshots: list files]

New QA Rules (7-10):

✅ Rule 7: Evidence Attached
   Evidence: [this report]

✅ Rule 8: UI Changes Verified
   Evidence: Screenshots show feature working
   Screenshots: [list 3+ files]

✅ Rule 9: Code vs User Verification Separated
   Code Verification: PASS
   User Verification: READY FOR REVIEW

✅ Rule 10: Prerequisites Met
   All requirements satisfied

Unmet Items: [list or "None"]

Overall Status: ✅ READY FOR PRODUCT OWNER REVIEW
═══════════════════════════════════════════════════════
```

---

**QA Rules Version:** 2.0  
**Last Updated:** 2026-07-02  
**Status:** ✅ **ALL RULES ENFORCED**

Every development must satisfy Rules 1-10 before review request.
