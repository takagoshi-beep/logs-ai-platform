# Project Policy — LOGS AI OS

**Version:** 1.0  
**Date:** 2026-07-02  
**Status:** Governance Framework Established

---

## Mission

Build an AI Operating System that:
1. **Learns business terminology** through structured Product Owner dialogue
2. **Maintains strict governance** - never updates Knowledge without explicit PO approval
3. **Separates concerns** - Facts ≠ Interpretations ≠ Hypotheses ≠ Knowledge
4. **Enables transparency** - all reasoning is explainable with evidence trails

---

## Core Principles

### Principle 1: Knowledge Governance
- ✅ AI generates hypotheses (estimates)
- ✅ AI marks hypotheses as Knowledge Candidates
- ❌ AI NEVER auto-updates Knowledge
- ✅ Only Product Owner can confirm hypotheses → Knowledge

### Principle 2: Evidence-First Reasoning
- ✅ All facts must come from real data (Logsys DB)
- ✅ All facts must include provenance (Provider/Table/Query/Rows/Timestamp)
- ✅ All interpretations must reference facts
- ✅ All hypotheses must show reasoning

### Principle 3: Layer Separation
```
Reasoning Layers (Strictly Separated):
├── Fact Layer: Raw DB observations (no interpretation)
├── Interpretation Layer: Pattern recognition (no numbers, only meaning)
├── Hypothesis Layer: AI estimates with confidence
└── Knowledge Candidate Layer: Awaiting PO review (marked PENDING)
```

### Principle 4: Quality Assurance
- ✅ Developer must verify Blueprint before implementation
- ✅ Code must pass QA checks before review request
- ✅ UI/UX must be verified with screenshots before PO review
- ✅ All verification steps must include Evidence (not just "PASS")

### Principle 5: Transparency in Operations
- ✅ Every decision is documented (Why + How + Evidence)
- ✅ Every workflow step is recorded
- ✅ Every change is traceable to requirements
- ✅ Every governance rule has clear exceptions/boundaries

---

## Architecture Principles

### Layer Responsibility
```
Semantic Layer (SEM-001 to SEM-010)
↓ (Business concepts, not DB structure)
Knowledge Layer (Business rules, decision criteria)
↓ (PO-approved only)
Reasoning Layer (Fact → Interpretation → Hypothesis → Candidate)
↓ (AI generates, PO reviews)
Evidence Layer (Data from Providers: Logsys, Gmail, etc.)
↓ (Real data with provenance)
UI Layer (Transparent display of reasoning)
```

---

## Quality Standards

### Code Quality
- ✅ No Knowledge updates without Evidence Trail
- ✅ No Rule inference without Confidence Score
- ✅ No DB queries without Provenance metadata
- ✅ No mixed concerns in output layers

### Review Quality
- ✅ Blueprint Compliance verified before commit
- ✅ User Interface verified via screenshot before PO review
- ✅ All verification includes Evidence, not just "PASS"
- ✅ Code Verification and User Verification kept separate

### Product Quality
- ✅ Features only shipped after PO approval
- ✅ Knowledge changes only after explicit PO confirmation
- ✅ Governance rules never bypassed for convenience
- ✅ Transparency is always prioritized

---

## Roles & Responsibilities

### Developer (Claude)
- ✅ Follow Developer Workflow (10 steps)
- ✅ Verify Blueprint before implementation
- ✅ Pass Developer QA before review request
- ✅ Provide Evidence for all verification claims
- ✅ Never commit before workflow completion

### Product Owner
- ✅ Review Knowledge Candidates
- ✅ Answer clarification questions
- ✅ Confirm or reject AI hypotheses
- ✅ Update Knowledge only after explicit confirmation

### System
- ✅ Generate hypotheses (not rules)
- ✅ Mark candidates as PENDING
- ✅ Provide reasoning transparency
- ✅ Never auto-update Knowledge

---

## Governance Rules

### Rule 1: Blueprint Governance
- All features must comply with Blueprint before implementation
- Blueprint violations are blocker issues
- Blueprint changes require explicit PO review

### Rule 2: Workflow Compliance
- Developer Workflow (10 steps) is mandatory before review request
- Skipping workflow steps is grounds for rejection
- Workflow must be documented in review

### Rule 3: QA Evidence Requirements
- "PASS" claims must include Evidence
- Evidence examples: git diffs, grep results, screenshots
- "PASS" without Evidence is treated as "NOT VERIFIED"

### Rule 4: UI/UX Verification
- UI changes require screenshot verification
- Screenshots must show feature working correctly
- "Code Complete" ≠ "Feature Complete" (need screenshots)

### Rule 5: Knowledge Protection
- Knowledge updates blocked during development
- Knowledge Candidates stay PENDING until PO confirms
- No bypassing Knowledge protection mechanisms

### Rule 6: Transparency Required
- All reasoning must include Why + How + Evidence
- All decisions must be documented
- All governance rules must be followed (no exceptions)

---

## Development Lifecycle

```
STEP 1: Policy Check
├─ Understand project principles
├─ Identify governance implications
└─ Plan for governance compliance

STEP 2: Design Phase
├─ Blueprint compliance review
├─ Layer responsibility verification
├─ Identify impact on existing layers
└─ Get implicit approval to proceed

STEP 3: Implementation Phase
├─ Follow Developer Workflow (10 steps)
├─ Code changes with evidence trail
├─ Pass Developer QA (Rules 1-6)
└─ UI verification with screenshots

STEP 4: Review Phase
├─ Code Verification with Evidence
├─ User Verification with screenshots
├─ Review Checklist confirmed
└─ Ready for PO review

STEP 5: PO Review Phase
├─ Product Owner reviews
├─ PO provides feedback
├─ Changes implemented
└─ Final approval

STEP 6: Deployment Phase
├─ Changes merged
├─ Governance compliance confirmed
├─ Documentation updated
└─ Archive review for reference
```

---

## Governance Index

All governance rules are documented in:
- `01_Blueprint.md` — Technical constraints
- `02_DeveloperWorkflow.md` — Step-by-step implementation
- `03_DeveloperQualityAssurance.md` — Quality standards
- `04_ReviewChecklist.md` — Pre-review verification

**Index updated:** 2026-07-02

---

## Exception Handling

### When Blueprint violations are unavoidable
1. Document the violation explicitly
2. Explain why it's necessary
3. Get explicit Product Owner approval
4. Create compliance deviation record
5. Plan remediation in next phase

### When workflow steps are unclear
1. Review documentation thoroughly
2. Ask clarifying questions before proceeding
3. Document decision rationale
4. Update governance if needed

### When QA evidence is insufficient
1. Gather additional evidence
2. Do not proceed without evidence
3. Update QA checklist if needed
4. Request clarification from Product Owner

---

## Governance Updates

This policy is authoritative. Changes require:
1. Product Owner discussion
2. Impact assessment on existing projects
3. Documentation updates (all 5 files)
4. Governance Index update
5. Archive previous version

**Last Updated:** 2026-07-02  
**Next Review:** When new phase begins

---

**Status:** ✅ **GOVERNANCE FRAMEWORK ACTIVE**
