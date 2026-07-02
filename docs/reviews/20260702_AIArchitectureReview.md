# AI OS Architecture Self-Review

**Date:** 2026-07-02  
**Phase:** 11 — AI Quality Review  
**Purpose:** AI evaluates own architecture and identifies structural issues  
**Status:** Self-Assessment (No Changes; Learning-Only)

---

## Architecture Component Evaluation

### Layer 1: INTENT — Question Classification

**Role & Responsibility**
- Classify user question: type (KPI分析/案件確認/タスク判定) and category (Analysis/Monitoring/...)
- Route to appropriate reasoning path

**Scope**
- Keyword matching on question text
- Pattern matching against ~4 hardcoded question types (OEM粗利/Fanatics/優先案件/売上首位顧客)

**Overlap with Other Layers**
- ⚠️ Intent + Meaning both classify/interpret questions
- Redundancy: Intent does keyword matching, Meaning also processes semantics

**Gaps Identified**
- ❌ Only 4 hardcoded questions supported; new questions cause fallback
- ❌ No handling of question variations or rephrasing
- ❌ No confidence scoring on classification
- ❌ No feedback if classification was wrong

**Dependencies**
- Depends on: Meaning (to refine classification)
- Used by: Routing logic (Q1/Q2/Q3/Q4 functions)

**Maintainability**
- Low: Adding questions requires code changes to reasoning_pipeline.py
- Hardcoded pattern matching is brittle

**Completeness**
- **40/100** — Handles sample cases only; not extensible

**Improvement Suggestion**
- Refactor Intent to work **with** Semantic (not before it)
- Move keyword→SEM mapping here instead of scattered in functions
- Use Semantic ID in routing decision, not text patterns

---

### Layer 2: MEANING — Business Context Assembly

**Role & Responsibility**
- Translate question into business concept dictionary
- Extract: entity, metric, aggregation, time, candidate_kpi, ranking criteria

**Scope**
- Calls Semantic Registry to resolve business terms
- Returns meaning with confidence scores
- Structured as JSON with labeled fields

**Overlap with Other Layers**
- ⚠️ Overlaps with Intent (both classify questions)
- ⚠️ Overlaps with Semantic (Meaning just references Semantic)
- Meaning is mostly a "wrapper" that calls _semantic_ref()

**Gaps Identified**
- ❌ Cannot handle questions that reference undefined Semantics
- ❌ No handling of quantifiers (all, top 5, average, etc.)
- ❌ No extraction of implicit constraints (e.g., "recent" = last 30 days?)
- ❌ Confidence scores are hardcoded, not learned

**Dependencies**
- Depends on: Semantic Registry (via _semantic_ref)
- Used by: Knowledge layer (consumes meaning)

**Maintainability**
- Medium: Adding Semantics requires knowledge/semantic/*.md changes (manageable)
- Structured approach is good

**Completeness**
- **65/100** — Works for modeled questions; lacks flexibility for new patterns

**Improvement Suggestion**
- Separate "explicit meaning" (what user said) from "inferred context" (assumptions)
- Add quantifier extraction
- Track which Semantics are "confident" vs "uncertain"

---

### Layer 3: SEMANTIC — Business Concept Registry

**Role & Responsibility**
- Define LOGS business terminology (SEM-001 through SEM-010)
- Map business language to Semantic ID
- Serve as single source of truth for business concept meaning

**Scope**
- 10 Semantics defined (SEM-001: OEM案件 through SEM-010: 商品)
- Each has: definition, usage context, related concepts, confirmation status
- Stored in knowledge/semantic/semantic_registry.md

**Overlap with Other Layers**
- ⚠️ Potential overlap with Knowledge layer (both define business concepts)
- Semantic = "what the word means" (business definition)
- Knowledge = "business rules about concepts" (how to use them)
- Distinction is somewhat blurry

**Gaps Identified**
- ❌ **CRITICAL**: 案件 concept is incomplete (multiple granularities not modeled)
- ❌ **CRITICAL**: OEM vs Retail classification undefined
- ❌ **HIGH**: Gross profit (粗利) has 3 variants, but which to use when is unclear
- ❌ **HIGH**: No concept for 予定 (plan/schedule)
- ❌ **HIGH**: No concept for 担当者 (staff assignment)
- ❌ Concepts are "Pending" (await Product Owner confirmation)

**Dependencies**
- Depends on: Nothing (root-level reference)
- Used by: Meaning layer, reasoning_pipeline.py

**Maintainability**
- Good: Separated from code; easy to update docs
- Problem: Updates are frozen until Product Owner confirms

**Completeness**
- **55/100** — 50% of concepts defined; 50% marked "Pending"; critical ones undefined

**Improvement Suggestion**
- Complete 案件 definition with confirmed granularities
- Add OEM/Retail classification rule
- Define gross profit usage logic
- Expand to SEM-011 through SEM-014 for missing concepts

---

### Layer 4: KNOWLEDGE — Business Rules Registry

**Role & Responsibility**
- Capture business decision rules and constraints
- Define filtering logic, calculations, state transitions
- Examples: "exclude invalid sales", "include operational costs in margin", etc.

**Scope**
- ~20 knowledge rules defined (KPI-METRIC-002, BR-SALES-STANDARD-001, etc.)
- Stored in knowledge/business_rules/*.md
- Each rule has: name, condition, action, references to Semantics

**Overlap with Other Layers**
- ⚠️ Light overlap with Semantic (both define business concepts)
- ⚠️ Overlap with Provider (both manage data access logic)
- Rule "BR-SALES-DETAIL-003: Use detail rows, not headers" is really a Data Access rule

**Gaps Identified**
- ❌ **CRITICAL**: OEM vs Retail classification rule missing
- ❌ **CRITICAL**: Gross profit calculation (论理 vs 实績 vs 担当) rules undefined
- ❌ **HIGH**: Status filtering rules not standardized across tables
- ❌ **HIGH**: Cancellation/return reversal logic not documented
- ❌ No rules for: period definition (calendar vs fiscal), partial delivery handling
- ❌ No rules for: deadline-based priority calculation
- ❌ Confidence levels of rules not specified (some assumptions, some firm)

**Dependencies**
- Depends on: Semantic (references SEM-001, etc.)
- Used by: Evidence layer (applies rules to data)

**Maintainability**
- Medium: Rules are scattered across multiple files
- Good: Naming convention (BR-*, KPI-*, etc.) helps organization
- Problem: Rules reference undefined Semantics (e.g., OEM classification)

**Completeness**
- **50/100** — Basic rules defined; critical decision rules missing

**Improvement Suggestion**
- Add decision rules for 3 CRITICAL gaps (case granularity, gross profit, classification)
- Standardize status values across all tables
- Define cancellation/return reversal logic explicitly
- Assign confidence/priority to rules (assumption vs. verified)

---

### Layer 5: PROVIDER — Data Access Abstraction

**Role & Responsibility**
- Abstract data source (SQLite, Gmail, Sheets, Slack)
- Provide unified fetch() interface
- Handle connection, query, transformation

**Scope**
- LogisysProvider: SQLite queries (currently demo DB; Phase 11 → real DB)
- GmailProvider: Email search/retrieval
- ProjectSheetProvider: Google Sheets queries
- SlackProvider: Slack message search

**Overlap with Other Layers**
- ⚠️ Overlap with Knowledge (data access rules live here, but some rules live in Knowledge layer)
- ⚠️ Overlap with Evidence (both deal with raw data transformation)

**Gaps Identified**
- ❌ LogisysProvider still uses 36KB demo DB (Phase 10 found 289MB real DB)
- ❌ No error handling for missing data fields
- ❌ No handling of partial/incomplete data gracefully
- ❌ No connection pooling or caching
- ❌ No filtering logic (some filtering should happen here, not later)
- ❌ No validation of fetched data (wrong type, out of range, etc.)

**Dependencies**
- Depends on: Database schema (couples to implementation)
- Used by: Evidence layer

**Maintainability**
- Low: Adding new Provider requires new class + interface
- Problem: Schema changes break queries

**Completeness**
- **60/100** — Works for current 4 questions; not robust for edge cases

**Improvement Suggestion**
- Migrate LogisysProvider from demo DB to real 289MB DB (Phase 10 prerequisite)
- Add error handling and partial data strategies
- Add filtering logic that respects business rules
- Add data validation layer

---

### Layer 6: EVIDENCE — Data Integration & Interpretation

**Role & Responsibility**
- Integrate multiple data sources
- Deduplicate, time-sort, prioritize by source reliability
- Interpret evidence to extract facts (not samples, full dataset)

**Scope**
- Deduplication: Merge overlapping data from multiple providers
- Time-sorting: Sort by timestamp for temporal analysis
- Prioritization: Rank sources by reliability
- Interpretation: Extract facts from full dataset (avoid sampling bias)

**Overlap with Other Layers**
- ⚠️ Overlap with Provider (both handle data transformation)
- ⚠️ Overlap with Knowledge (some rules belong here)

**Gaps Identified**
- ❌ Deduplication logic is simplistic (same row from multiple sources only)
- ❌ No handling of conflicting data (same field, different values from different sources)
- ❌ Prioritization is hardcoded (no learning from reliability over time)
- ❌ Interpretation assumes data is complete; no strategies for missing data
- ❌ No feedback mechanism (what if interpretation was wrong?)
- ❌ No annotation of data quality/confidence

**Dependencies**
- Depends on: Provider, Knowledge
- Used by: Decision layer

**Maintainability**
- Medium: Logic is documented but not tested for edge cases
- Problem: Assumptions aren't explicit

**Completeness**
- **70/100** — Good structure; gaps in edge case handling

**Improvement Suggestion**
- Add conflict resolution rules (which source wins?)
- Track data quality metrics over time
- Explicitly mark: "this field was missing, so we used assumption X"
- Add confidence scoring for evidence quality

---

### Layer 7: DECISION — Gate & Verdict

**Role & Responsibility**
- Evaluate: Can we answer this question with confidence?
- Determine: Do we have enough data/rules/clarity?
- Return: verdict (回答可/追加確認が必要/回答不可) + reasoning

**Scope**
- Checks: Required data available? Rules clear? Assumptions reasonable?
- Returns: verdict + reason + proceed_conditions + confidence

**Overlap with Other Layers**
- ⚠️ Overlap with Knowledge (Decision uses rules to evaluate readiness)
- ⚠️ Overlap with Evidence (Decision depends on data quality assessment)

**Gaps Identified**
- ❌ **CRITICAL**: Decision logic is hardcoded per question (not generalizable)
- ❌ **CRITICAL**: Cannot evaluate "confidence in classification" (no uncertainty quantification)
- ❌ Decision thresholds are arbitrary (0.8 confidence = OK? Why?)
- ❌ No learning from past decisions (was this verdict correct?)
- ❌ No explanation of what additional data would improve confidence
- ❌ Proceed_conditions are sometimes unclear (will they be met?)

**Dependencies**
- Depends on: Knowledge, Evidence, Meaning
- Used by: Output/Communication

**Maintainability**
- Low: Decision logic is buried in Q1/Q2/Q3/Q4 functions
- Brittle: Cannot easily add new questions

**Completeness**
- **65/100** — Works for 4 sample cases; not generalizable

**Improvement Suggestion**
- Generalize Decision logic (not hardcoded per question)
- Define decision thresholds explicitly (what confidence is "good enough"?)
- Track accuracy of past decisions
- Learn which conditions are actually bottlenecks (data vs. rules vs. clarity?)

---

### Layer 8: NATURAL ANSWER — Communication (FUTURE)

**Role & Responsibility**
- Translate Decision + Evidence into natural language
- Make answer accessible to business users
- Include: verdict, summary, caveats, next steps

**Scope**
- Not yet implemented
- Placeholder in reasoning_pipeline.py
- Needed for production deployment

**Current State**
- Returns raw JSON (Decision Gate output)
- Visible in frontend via /reasoning page

**Gaps Identified**
- ❌ No natural language generation
- ❌ No personalization (same answer for all users?)
- ❌ No adaptation (simple vs. detailed explanation?)
- ❌ No citations (where did this data come from?)
- ❌ No interactive clarification (ask follow-up questions?)

**Dependencies**
- Depends on: All layers below

**Completeness**
- **0/100** — Not implemented

**Improvement Suggestion**
- Design output format (simple answer + evidence summary + caveats)
- Plan for Phase 12+ if needed

---

## Cross-Layer Architecture Assessment

### Duplications Identified

| Layer Pair | Duplication | Impact | Fix |
|-----------|------------|--------|-----|
| Intent ↔ Meaning | Both classify questions | Confusing responsibility | Merge or clarify boundary |
| Semantic ↔ Knowledge | Both define concepts | Overlapping definitions | Semantic = "definition", Knowledge = "rules" |
| Provider ↔ Evidence | Both transform data | Code duplication | Clear separation: Provider = raw, Evidence = integrated |
| Knowledge ↔ Evidence | Both apply business logic | Unclear where rules live | Rules belong in Knowledge; Evidence applies them |

### Gaps Identified

| Gap | Severity | Layer | Impact |
|-----|----------|-------|--------|
| OEM vs Retail classification logic | 🔴 CRITICAL | Semantic + Knowledge | Q1 blocked |
| 案件 granularity handling | 🔴 CRITICAL | Semantic + Decision | Q2, Q3 blocked |
| Gross profit calculation rules | 🔴 CRITICAL | Knowledge | Q1 produces wrong answer |
| Generalized Decision logic | 🟠 HIGH | Decision | Not scalable |
| Confidence thresholds | 🟠 HIGH | Decision | Arbitrary verdicts |
| Error handling | 🟠 HIGH | Provider | Fails on missing data |
| Status standardization | 🟠 HIGH | Knowledge | Filtering logic varies |
| Feedback mechanism | 🟠 HIGH | All | No learning from mistakes |

### Ambiguities Identified

| Ambiguity | Layers Involved | Issue |
|-----------|-----------------|-------|
| When to use Semantic vs Knowledge? | Semantic, Knowledge | Both describe business concepts |
| How much confidence is "enough"? | Decision | Thresholds are implicit |
| What counts as complete data? | Evidence | Definition varies per question |
| Which data source is authoritative? | Provider, Evidence | Conflicts not resolved |
| When should we ask for clarification? | Intent, Decision | Rules not documented |

### Unclear Responsibilities

| Component | Intended Responsibility | Actual Behavior | Problem |
|-----------|------------------------|-----------------|---------|
| Intent | Route to Q1/Q2/Q3/Q4 | Pattern matches keywords | Doesn't generalize |
| Meaning | Build business context | Mostly calls _semantic_ref() | Just a wrapper |
| Semantic | Define terms | Only 10 defined; many "Pending" | Incomplete |
| Knowledge | Apply business rules | Rules are incomplete/conflicting | Decisions are uncertain |
| Provider | Abstract data source | Knows too much (SQL schema) | Couples to implementation |
| Evidence | Integrate data | Handles 4 questions only | Not general |
| Decision | Evaluate readiness | Hardcoded per question | Not scalable |

---

## Overall AI OS Assessment

### Completeness Scores by Layer

```
Layer                    Score    Status
─────────────────────────────────────────
1. Intent               40/100   ⚠️  Hardcoded, not extensible
2. Meaning              65/100   ✓   OK, but just wrapper
3. Semantic             55/100   ⚠️  50% incomplete ("Pending")
4. Knowledge            50/100   ⚠️  Critical rules missing
5. Provider             60/100   ⚠️  Demo DB only; limited error handling
6. Evidence             70/100   ✓   Good structure, gaps at edges
7. Decision             65/100   ⚠️  Works but not generalizable
8. Natural Answer        0/100   ✗   Not implemented
─────────────────────────────────────────
Average:                57/100
```

### Architecture Health

| Dimension | Assessment |
|-----------|-----------|
| **Duplication** | Medium (Intent↔Meaning, Semantic↔Knowledge, Provider↔Evidence) |
| **Gaps** | High (3 CRITICAL, 7 HIGH gaps in Knowledge/Semantic) |
| **Ambiguity** | Medium (overlapping responsibilities, implicit thresholds) |
| **Maintainability** | Low (hardcoded patterns, scattered logic) |
| **Scalability** | Low (cannot handle new questions without code changes) |
| **Testability** | Low (no feedback mechanism, no test cases) |

### Critical Path Blockers

1. 🔴 **OEM vs Retail classification rule** → Blocks Q1 (OEM粗利)
2. 🔴 **案件 granularity decision** → Blocks Q2, Q3 (status, priority)
3. 🔴 **Gross profit calculation rules** → Affects Q1 accuracy

---

## Recommended Improvements (Phase 11 Priority)

### Priority 1: Complete Critical Knowledge Gaps
- [ ] Confirm 案件 granularities and update Semantic
- [ ] Define OEM vs Retail classification rule
- [ ] Document gross profit variant selection logic
- **Impact:** Unblocks 3 of 4 sample questions

### Priority 2: Generalize Decision Logic
- [ ] Refactor Q1/Q2/Q3/Q4 decision functions
- [ ] Create general decision framework (not hardcoded per question)
- **Impact:** Enables new questions

### Priority 3: Standardize Rules Across Layers
- [ ] Merge Intent + Meaning responsibility
- [ ] Clarify Semantic vs Knowledge boundary
- [ ] Move Provider data logic to Evidence
- **Impact:** Improves maintainability

### Priority 4: Add Learning Feedback
- [ ] Track decision accuracy over time
- [ ] Learn which conditions actually matter
- [ ] Adapt thresholds based on outcomes
- **Impact:** Improves quality

---

**Architecture Summary:**
- Current: 57/100 (functional for sample cases, not production-ready)
- Main issues: Incomplete Semantics, missing rules, hardcoded patterns
- Path forward: Complete knowledge gaps, generalize logic, add feedback

