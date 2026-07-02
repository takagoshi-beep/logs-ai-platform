# Governance Framework — README

**Version:** 1.0  
**Date:** 2026-07-02  
**Status:** Official Governance Framework

---

## Purpose

Define how LOGS AI OS is developed, reviewed, and deployed.

**Not about structure. About shipping quality features fast.**

---

## Files (Authoritative Order)

### 00_ProjectPolicy.md
**Purpose:** Why and how we build this  
**Audience:** Everyone  
**Read First:** Yes

**Contains:**
- Project mission
- Core principles (5)
- Layer architecture
- Roles & responsibilities
- Governance rules

---

### 01_Blueprint.md
**Purpose:** What we cannot violate  
**Audience:** Developers  
**When to Read:** Before EVERY implementation

**Contains:**
- 4 non-negotiable Blueprint Rules
- 5 Layer architecture details
- Data provenance requirements (6 fields)
- Layer-specific content rules
- Violation severity levels

---

### 02_DeveloperWorkflow.md
**Purpose:** How to implement safely without forgetting Blueprint  
**Audience:** Developers (Claude)  
**When to Follow:** Before EVERY review request

**Contains:**
- **STEP 0: Fast Feedback Principle** (NEW - Priority!)
- STEP 1-10: 10-step workflow
- Each step documented with verification
- Evidence requirements
- Proceed/blocker conditions

---

### 03_DeveloperQualityAssurance.md
**Purpose:** What quality means  
**Audience:** Developers  
**When to Verify:** As implementing

**Contains:**
- Base Rules 1-6: Code correctness, regressions, error handling, etc.
- **NEW Rules 7-10:**
  - Rule 7: PASS requires Evidence
  - Rule 8: UI changes need screenshots (Code Complete ≠ UI Verified)
  - Rule 9: Code Verification ≠ User Verification (separate)
  - Rule 10: Review request prerequisites (all must pass)

---

### 04_ReviewChecklist.md
**Purpose:** Final verification before PO review  
**Audience:** Developers  
**When to Use:** Before requesting review

**Contains:**
- 15+ checklist items (updated)
- **NEW items:**
  - Fact証跡確認 (Provider/Table/Rows/Query/Timestamp)
  - Knowledge Candidate PENDING 表示
  - Interpretation/Fact混在チェック
  - Fact/Hypothesis混在チェック
- Evidence requirements for each
- Red flags & green lights

---

### 05_GovernanceIndex.md
**Purpose:** Where to find each rule  
**Audience:** Everyone  
**When to Use:** Looking for a specific rule

**Contains:**
- Complete rules inventory
- Cross-references between files
- Quick lookup table
- Exception handling process

---

## How to Use Governance

### For Developers: Full Workflow
```
Before implementation:
→ READ 00_ProjectPolicy.md
→ READ 01_Blueprint.md
→ READ 02_DeveloperWorkflow.md (NEW Step 0!)
→ FOLLOW Steps 1-10 in Developer Workflow
→ VERIFY QA Rules 1-10 (with Evidence!)
→ CHECK 15+ items in Review Checklist
→ ONLY THEN request Product Owner review
```

### For Product Owners: What to Review
```
When developer requests review:
→ CHECK that Developer Workflow completed
→ CHECK that Blueprint verified
→ CHECK that QA Rules satisfied
→ READ the review checklist results
→ REVIEW Knowledge Candidates
→ Approve/reject hypotheses
```

### For System: Constraints
```
What AI can do:
✓ Generate hypotheses (estimates)
✓ Mark hypotheses as PENDING candidates
✓ Request PO confirmation
✗ Auto-update Knowledge
✗ Apply hypotheses as rules
✗ Skip Blueprint checks
```

---

## Most Important: Fast Feedback Loop

**CRITICAL PRINCIPLE (Step 0 in Workflow):**

Do not optimize structure. Optimize feedback speed.

```
Add new layer/component?
→ Do NOT just add code
→ Test with REAL Logsys DB
→ Test with REAL business questions
→ Get Product Owner feedback IMMEDIATELY
→ Fix only what's needed
→ Repeat fast

Do NOT:
✗ Spend weeks building "perfect" structure
✗ Add layers that haven't been tested
✗ Wait for Product Owner feedback
✗ Over-engineer before validating
```

---

## File Status

| File | Version | Status | Last Updated |
|------|---------|--------|--------------|
| 00_ProjectPolicy.md | 1.0 | Official | 2026-07-02 |
| 01_Blueprint.md | 2.0 | Official | 2026-07-02 |
| 02_DeveloperWorkflow.md | 2.0 | Official (Step 0 added) | 2026-07-02 |
| 03_DeveloperQualityAssurance.md | 3.0 | Official (Rules 7-10 added) | 2026-07-02 |
| 04_ReviewChecklist.md | 2.0 | Official (Fact/Interpretation items added) | 2026-07-02 |
| 05_GovernanceIndex.md | 1.0 | Official | 2026-07-02 |

---

## When to Update Governance

### Add New Rule
1. Document in appropriate file (00-04)
2. Update GovernanceIndex.md
3. Notify Product Owner
4. Archive old version

### Change Existing Rule
1. Update in source file
2. Update GovernanceIndex.md
3. Get Product Owner awareness
4. Archive old version

### Never
- ✗ Add rules without documenting
- ✗ Skip GovernanceIndex update
- ✗ Delete rules without archiving
- ✗ Have multiple "correct" versions

---

## Key Changes from Previous

### Developer Workflow
- **BEFORE:** 10 steps
- **AFTER:** Step 0 (Fast Feedback) + 10 steps (total 11)
- **Why:** Remind us that structure ≠ product

### Developer QA
- **BEFORE:** 6 rules
- **AFTER:** 6 + 4 new rules (10 total)
- **Why:** Separate concerns (Code/User), require Evidence, prevent premature "complete"

### Review Checklist
- **BEFORE:** 14 items
- **AFTER:** 14 + 4 new items (18 total)
- **Why:** Verify Fact display, PENDING status, prevent layer mixing

---

## Success Metrics

You'll know Governance is working when:

✅ Developer follows STEP 0 first (Fast Feedback)  
✅ Every PASS claim has Evidence attached  
✅ Code Verification ≠ User Verification (clearly separated)  
✅ UI changes don't ship without screenshots  
✅ Blueprint violations blocked (not bypassed)  
✅ Product Owner feedback loop is < 1 day  
✅ New features work on REAL Logsys data  
✅ No "perfect structure" delays shipped

---

**Governance Status:** ✅ **OFFICIAL & ENFORCED**

Start with STEP 0: Fast Feedback Principle.
