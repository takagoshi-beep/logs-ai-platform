# Blueprint — LOGS AI OS Architecture

**Version:** 2.0  
**Date:** 2026-07-02  
**Status:** Authoritative Reference

---

## Blueprint Overview

The Blueprint defines the architecture, layer responsibilities, and non-negotiable rules for LOGS AI OS.

**Non-Compliance = Blocker Issue**

---

## Layer Architecture

### Layer 1: Semantic Layer (SEM-001 to SEM-010)
**Responsibility:** Business concepts (independent of DB structure)

Example: "OEM案件" (OEM Project) concept, not "project table"

**Rules:**
- ✅ Define business meanings (not DB structure)
- ✅ Independent of data source
- ✅ Human-readable definitions
- ❌ Never derive from single DB table

**Files:** `knowledge/semantic/*.md`

---

### Layer 2: Knowledge Layer
**Responsibility:** Business rules and decision criteria (PO-approved only)

Example: "OEM案件は集計.分類='OEM'で判定" (after PO confirms)

**Rules:**
- ✅ Only PO-approved hypotheses become Knowledge
- ✅ All Knowledge has PO signature
- ✅ Changes require PO re-confirmation
- ❌ AI cannot auto-update Knowledge

**Files:** `knowledge/business_rules/*.md`, `knowledge/semantic/*.md`

---

### Layer 3: Reasoning Layer
**Responsibility:** AI thinking process (Fact→Interpretation→Hypothesis→Candidate)

Structure:
```json
{
  "facts": { "layer": "FACT", "data": [...], "provenance": {...} },
  "interpretation": { "layer": "INTERPRETATION", "observations": [...] },
  "ai_hypotheses": { "layer": "HYPOTHESIS", "confidence": 0.72 },
  "knowledge_candidates": { "layer": "KNOWLEDGE_CANDIDATE", "po_review_status": "PENDING" }
}
```

**Rules:**
- ✅ Fact layer: Raw DB observations only (no interpretation)
- ✅ Interpretation layer: Pattern recognition (no numeric data)
- ✅ Hypothesis layer: AI estimates with confidence scores
- ✅ Candidate layer: Marked PENDING (not auto-applied)
- ❌ Never mix layers
- ❌ Never include numbers in Interpretation
- ❌ Never apply hypotheses directly as rules

**Files:** `backend/services/reasoning_pipeline.py`

---

### Layer 4: Evidence Layer
**Responsibility:** Real data from Providers (Logsys, Gmail, etc.)

**Rules:**
- ✅ Read-only access only
- ✅ All queries logged with provenance (Provider/Table/Query/Rows/Timestamp)
- ✅ All data validated before use
- ❌ No database modifications
- ❌ No missing provenance metadata

**Files:** `backend/services/data_providers.py`

---

### Layer 5: UI Layer
**Responsibility:** Display reasoning transparently

**Rules:**
- ✅ Show all 4 reasoning layers separately
- ✅ Display provenance for all facts
- ✅ Show confidence scores for hypotheses
- ✅ Show PENDING status for candidates
- ❌ Never hide reasoning steps
- ❌ Never display AI conclusions as facts

**Files:** `frontend/app/reasoning/page.tsx`

---

## Blueprint Rules (Non-Negotiable)

### Rule 1: AI Must NOT Update Knowledge
**Statement:** AIはKnowledgeを更新してはいけません

**Verification:**
```
git diff knowledge/ → 変更0件
git diff knowledge/semantic/ → 変更0件
grep -r "Edit.*knowledge" backend → Match 0件
```

**Violation = Blocker**

---

### Rule 2: AI Must NOT Infer Company Rules
**Statement:** AIは会社ルールを推定で決めてはいけません

**Implementation:**
- Generate hypotheses (estimates)
- Mark as "Knowledge Candidates"
- Flag with confidence score
- Require PO review before applying

**Evidence Required:**
```
All hypotheses marked: po_review_status = "PENDING"
All candidates marked: ready_for_knowledge_update = False
No hypotheses applied to Decision Gate logic
```

**Violation = Blocker**

---

### Rule 3: Only Fact/Interpretation/Hypothesis/Confidence
**Statement:** AIが生成するもの：Fact・Interpretation・Hypothesis・Confidenceのみ

**Definitions:**
- **Fact:** Raw DB query results (no interpretation)
  - Example: "集計テーブルから1234件取得"
  
- **Interpretation:** Pattern observations (no numbers)
  - Example: "OEM分類フラグが存在"
  
- **Hypothesis:** AI estimates with reasoning
  - Example: "OEM判定は分類='OEM'の可能性 (72%)"
  
- **Confidence:** Numeric score (0.0-1.0)
  - Example: 0.72, 0.68, 0.55

**Output Structure Verification:**
```
Only 4 field types in phase_13 output:
✓ facts
✓ interpretation
✓ ai_hypotheses (with confidence)
✓ knowledge_candidates
```

**Violation = Blocker**

---

### Rule 4: Knowledge Only After PO Approval
**Statement:** KnowledgeになるのはProduct Owner承認後のみ

**Process:**
```
Fact → Interpretation → Hypothesis → Knowledge Candidate
                                            ↓
                                   PO Review (Questions)
                                            ↓
                                    PO Confirms
                                            ↓
                                   Knowledge Update
```

**Evidence Required:**
```
All candidates marked: po_review_status = "PENDING"
All candidates marked: ready_for_knowledge_update = False
PO Questions documented in separate file
No automatic Knowledge updates implemented
```

**Violation = Blocker**

---

## Data Provenance Requirements

### Fact Layer Must Include

1. **Provider** — Where data came from
   - Example: "LogsysProvider"

2. **Source Table** — Specific table queried
   - Example: "集計"

3. **Query Conditions** — Full WHERE clause
   - Example: `{"分類": "OEM", "顧客名": "NOT NULL", "period": "2026-07-01〜2026-07-31"}`

4. **Rows Retrieved** — Count from DB
   - Example: 1234

5. **Timestamp** — When retrieved
   - Example: "2026-07-02T15:30:45.123456Z"

6. **Raw Data** — Actual values
   - Example: `{"oem_record_count": 1234, "oem_total_sales": 1234567, ...}`

### No Fact Without Provenance = Invalid
All 6 fields required or fact is rejected.

---

## Interpretation Layer Requirements

### Must Contain
- ✅ Pattern observations (what we noticed)
- ✅ Metadata references (data source, quality, etc.)

### Must NOT Contain
- ❌ Numeric calculations (¥ amounts, counts, etc.)
- ❌ Conclusions (that's for Hypothesis)
- ❌ Questions (that's for PO)

### Example Valid Interpretation
```json
{
  "layer": "INTERPRETATION",
  "observations": [
    "集計テーブルに『分類=OEM』というフラグが存在し、レコードがマッチしました",
    "売上と粗利の金額が集計テーブルに事前計算されています",
    "データ取得日時: 2026-07-02T15:30:45、推定精度: 95%"
  ]
}
```

### Example Invalid Interpretation
```json
{
  "layer": "INTERPRETATION",
  "observations": [
    "OEM粗利: ¥456,789",  ← ❌ Numbers not allowed
    "1234件マッチ"         ← ❌ Raw count not allowed
  ]
}
```

---

## Hypothesis Layer Requirements

### Must Include
- ✅ ID (HYP-xxx-###)
- ✅ Statement (AI's estimate)
- ✅ Confidence (0.0-1.0)
- ✅ Reasoning (array of facts that led to this)
- ✅ Affects Knowledge (which concept)

### Example Valid Hypothesis
```json
{
  "layer": "HYPOTHESIS",
  "id": "HYP-OEM-001",
  "statement": "OEM案件は集計.分類='OEM' で判定されている可能性が高い",
  "confidence": 0.72,
  "reasoning": [
    "Fact: 集計テーブルに『分類』フィールドが存在する",
    "Fact: OEM分類が一貫してマッチしている",
    "Interpretation: 複数の関連フィールドで同じパターン"
  ],
  "affects_knowledge": true,
  "knowledge_concept": "OEM案件判定基準"
}
```

---

## Knowledge Candidate Layer Requirements

### Must Include
- ✅ Layer: "KNOWLEDGE_CANDIDATE"
- ✅ Concept: Business concept name
- ✅ AI Hypothesis: The hypothesis text
- ✅ Confidence: Score (0.0-1.0)
- ✅ Reasoning: Array of reasoning steps
- ✅ PO Review Status: "PENDING"
- ✅ Ready for Knowledge Update: False
- ✅ Note: Warning about PO review needed

### Example Valid Candidate
```json
{
  "layer": "KNOWLEDGE_CANDIDATE",
  "concept": "OEM案件判定基準",
  "ai_hypothesis": "集計.分類='OEM' で判定される可能性が高い",
  "confidence": 0.72,
  "reasoning": [...],
  "hypothesis_id": "HYP-OEM-001",
  "po_review_status": "PENDING",
  "ready_for_knowledge_update": false,
  "note": "⚠️ Product Owner確認待ち - AIの推定であり、会社ルールとして確定していません"
}
```

### All Candidates MUST Show PENDING Badge on Screen

---

## Blueprint Violations & Resolution

| Violation | Severity | Resolution | Timeline |
|-----------|----------|-----------|----------|
| Knowledge updated without PO approval | 🔴 BLOCKER | Revert + redesign | Immediate |
| Hypotheses marked as rules (not candidates) | 🔴 BLOCKER | Revert + restructure | Immediate |
| Mixed layer concerns (numbers in interpretation) | 🟡 HIGH | Fix + re-test | Same phase |
| Missing provenance metadata | 🟡 HIGH | Add evidence + verify | Same phase |
| Interpretation includes ¥ amounts | 🟡 HIGH | Move to facts layer | Same phase |
| Missing PENDING badge on candidates | 🟡 HIGH | Add UI display | Same phase |

---

## Blueprint Verification Checklist

Use this before submitting for PO review:

- [ ] **Rule 1**: No Knowledge files modified (git diff knowledge/ → 0件)
- [ ] **Rule 2**: All hypotheses marked PENDING (grep po_review_status)
- [ ] **Rule 3**: Only 4 types in output (grep phase_13)
- [ ] **Rule 4**: No auto-update logic (grep update Knowledge)
- [ ] **Provenance**: All 6 fields present (Provider/Table/Query/Rows/Timestamp/Data)
- [ ] **Interpretation**: No numbers (grep ¥ or digits)
- [ ] **Hypothesis**: All have confidence (grep confidence)
- [ ] **Candidates**: All show PENDING on screen (screenshot)
- [ ] **Layer Separation**: Each layer has "layer": field
- [ ] **UI Display**: All 4 layers visible on reasoning page

---

**Blueprint Version:** 2.0  
**Last Updated:** 2026-07-02  
**Status:** ✅ **AUTHORITATIVE & ENFORCED**

All development must comply with this Blueprint.  
Violations are blocker issues.
