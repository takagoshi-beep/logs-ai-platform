# Phase 13 Blueprint Compliance Validation

**Date:** 2026-07-02  
**Phase:** 13 — Real DB Integration  
**Status:** Pre-Implementation Blueprint Review  
**Critical:** Ensure compliance before writing any code

---

## Blueprint Requirements vs Implementation Plan

### Rule 1: AI Must NOT Update Knowledge

**Requirement:** AIはKnowledgeを更新してはいけません

**Implementation Approach:**
- ✓ Query knowledge/semantic/ and knowledge/business_rules/ files as READ-ONLY
- ✓ Do not modify any .md files in knowledge/
- ✓ Generate Hypotheses but store in separate structure
- ✓ Mark as "Knowledge Candidate" but don't apply to actual Knowledge

**Compliance Check:**
- Will NOT modify knowledge/semantic/*.md
- Will NOT modify knowledge/business_rules/*.md
- Will NOT use Edit tool on Knowledge files
- Only use Read tool if needed for reference

**Status:** ✓ COMPLIANT

---

### Rule 2: AI Must NOT Infer Company Rules

**Requirement:** AIは会社ルールを推定で決めてはいけません

**Implementation Approach:**
- ✓ Generate Hypotheses (educated guesses)
- ✓ Mark Hypotheses that affect business logic as "Knowledge Candidate"
- ✓ Flag with Confidence score
- ✓ Ask Product Owner to confirm before treating as rule

**Example:**
```
AI sees: Sales table has delivery_date column
AI hypothesizes: "This is the official deadline field"
AI confidence: 65% (other fields might be used)
AI action: MARK AS CANDIDATE, ASK PO for confirmation
AI does NOT: Update Knowledge to use this field automatically
```

**Status:** ✓ COMPLIANT

---

### Rule 3: AI Can ONLY Generate Fact/Hypothesis/Reason/Confidence

**Requirement:** AIが生成してよいもの・Fact・Hypothesis・Reason・Confidenceのみです

**Implementation Approach:**

**Fact:**
- Direct query results from Logsys DB
- Example: "customer_name = 'Fanatics', delivery_date = 2026-07-15, sales_amount = 50000"
- No interpretation, just data

**Hypothesis:**
- Educated guess based on Facts
- Example: "This question seems to be asking about product-unit aggregation (68% confidence) because sales data is at transaction level"

**Reason:**
- Why AI formed this hypothesis
- Example: "Sales table has 199k rows at individual transaction level; question asks for monthly aggregation"

**Confidence:**
- Numeric confidence (0-100%)
- Based on: data completeness, pattern clarity, alternative interpretations

**Status:** ✓ COMPLIANT if we don't add other output types

---

### Rule 4: Only Product Owner Approval Makes It Knowledge

**Requirement:** KnowledgeになるのはProduct Owner承認後のみです

**Implementation Approach:**
- ✓ Create "Knowledge Candidate" structure
- ✓ Each Candidate has: Concept, AI Hypothesis, Confidence, Reason, Review Status = "Pending"
- ✓ Output to Reasoning screen showing "Knowledge Candidate (Pending PO Review)"
- ✓ Create docs/reviews/YYYYMMDD_KnowledgeCandidates.md with candidates list
- ✓ Wait for PO approval before updating Knowledge files

**Process:**
```
AI finds Fact → Generates Hypothesis → Creates Candidate → Flags for PO Review
                                                           → Only after PO says YES
                                                             does it become Knowledge
```

**Status:** ✓ COMPLIANT

---

## Implementation Plan (Phase 13 Scope)

### Step 1: Connect to Real Logsys DB ✓ IN SCOPE

**What:** Use LogisysProvider to query data/sqlite/logsys.db (289MB, real data)  
**Why:** Facts must come from real data, not assumptions  
**How:** Call existing LogisysProvider interface (from Phase 8)  
**Safety:** Read-only, no modifications to DB

**Status:** ✓ BLUEPRINT COMPLIANT

---

### Step 2: Extract Facts for Sample Questions ✓ IN SCOPE

**What:** Run sample queries and return raw results (no interpretation)  
**Example queries:**
```
Q: "今月のOEM粗利は?"
Facts extracted:
- Transaction count: 150 OEM-flagged transactions in 2026-07
- Revenue sum: ¥5,234,000
- Cost sum: ¥3,156,000
- Margin: ¥2,078,000
- Period: 2026-07-01 to 2026-07-31
```

**Status:** ✓ BLUEPRINT COMPLIANT

---

### Step 3: Generate Hypotheses ✓ IN SCOPE

**What:** Based on Facts, form educated guesses about business logic  
**Example:**
```
AI Hypothesis #1:
- "OEM is identified via 集計.分類 = 'OEM' (observed in data)"
- Confidence: 72%
- Reason: "集計 table has 16,705 rows; 3,400 marked as OEM; 集計.分類 field exists"

AI Hypothesis #2:
- "粗利種別: This month should use 実績原価 not 論理原価"
- Confidence: 45%
- Reason: "集計.案件粗利 pre-calculated, but can't determine which variant without PO input"
```

**Status:** ✓ BLUEPRINT COMPLIANT

---

### Step 4: Create Knowledge Candidates ✓ IN SCOPE

**What:** Extract Hypotheses that would affect Knowledge if true  
**Example:**
```
Knowledge Candidate #1:
- Concept: "OEM案件判定基準"
- AI Hypothesis: "Identified via 集計.分類 = 'OEM' flag"
- Confidence: 72%
- Reason: "Observable in real data; consistent 16k-row pattern"
- Status: CANDIDATE (awaiting PO review)
- PO Review: Not yet conducted

Knowledge Candidate #2:
- Concept: "粗利計算選択 (实績 vs 论理)"
- AI Hypothesis: "Should use 実績原価 for monthly reporting"
- Confidence: 45%
- Reason: "集計 table shows monthly aggregations; unclear which variant"
- Status: CANDIDATE (awaiting PO review)
- PO Review: Not yet conducted
```

**Status:** ✓ BLUEPRINT COMPLIANT (Candidates created but NOT applied to Knowledge)

---

### Step 5: Surface Fact→Hypothesis→Candidate in Output ✓ IN SCOPE

**What:** Modify reasoning_pipeline.py return value to show three layers  
**Why:** Transparency - show AI's reasoning process  
**How:** Return structure:
```python
{
  "question": "今月のOEM粗利は?",
  
  "facts": {
    "raw_data": [
      {"customer": "Fanatics", "sales": 50000, "cost": 30000},
      ...
    ],
    "aggregates": {
      "total_sales": 5234000,
      "total_cost": 3156000,
      "margin": 2078000,
      "record_count": 150
    },
    "sources": ["売上", "仕入", "集計"],
    "data_freshness": "2026-07-02T00:00:00Z"
  },
  
  "ai_hypotheses": [
    {
      "id": "HYP-001",
      "statement": "OEM identified via 集計.分類='OEM'",
      "confidence": 0.72,
      "reasoning": [...],
      "affects_knowledge": True
    },
    ...
  ],
  
  "knowledge_candidates": [
    {
      "concept": "OEM案件判定基準",
      "ai_hypothesis": "集計.分類='OEM' indicator",
      "confidence": 0.72,
      "reasoning": [...],
      "po_review_status": "PENDING",
      "ready_for_knowledge_update": False
    },
    ...
  ],
  
  "answer": {
    "verdict": "Pending PO confirmation of OEM definition",
    "confidence": 0.45,
    "reason": "OEM identification hypothesis at 72%; gross profit variant selection at 45%"
  }
}
```

**Safety:**
- Reasoning screen shows layers clearly separated
- Knowledge Candidates marked "PENDING" (not applied)
- Old Decision Gate still works (for backward compatibility)

**Status:** ✓ BLUEPRINT COMPLIANT

---

### Step 6: Create Knowledge Candidates Document ✓ IN SCOPE

**What:** File: docs/reviews/YYYYMMDD_KnowledgeCandidates_Phase13.md  
**Content:** List of all Candidates with PO review status  
**Safety:** For review only; doesn't affect Knowledge  

**Example Structure:**
```
# Knowledge Candidates from Phase 13 Real DB Integration

## Candidate #1: OEM案件判定基準
- AI Hypothesis: 集計.分類 = 'OEM' flag
- Confidence: 72%
- Reasoning: [...]
- PO Review Status: PENDING
- Ready for Knowledge: NO (needs PO approval)

## Candidate #2: 粗利種別選択
- AI Hypothesis: 実績原価 ベース
- Confidence: 45%
- Reasoning: [...]
- PO Review Status: PENDING
- Ready for Knowledge: NO
```

**Status:** ✓ BLUEPRINT COMPLIANT

---

### Step 7: Ask Product Owner Strategic Questions ✓ IN SCOPE

**What:** Ask only things AI truly cannot determine from data  
**Example:**
```
Q1: "売上テーブルの delivery_date は、顧客への納品日ですか?
      それとも社内の予定納期ですか? 
      データから判断できません。"

Q2: "粗利の計算で、今月のレポートでは
     実績原価と論理原価のどちらを使うべきですか?"

Q3: "キャンセルと返品の違いは何ですか?
     ステータス値での判定基準は何ですか?"
```

**NOT ask:** Things derivable from data (e.g., "What tables exist?" — we can query this)

**Status:** ✓ BLUEPRINT COMPLIANT

---

## Compliance Checklist

| Requirement | Status | Implementation |
|------------|--------|-----------------|
| No Knowledge Updates | ✓ PASS | Read-only access; no Edit on knowledge/ |
| No Rule Inference | ✓ PASS | Hypotheses only; Candidates for review |
| Only Fact/Hyp/Reason/Conf | ✓ PASS | Structure enforces these 4 types |
| Knowledge = PO Approved | ✓ PASS | Candidates mark as PENDING until review |
| Real DB Connection | ✓ PASS | Use 289MB data/sqlite/logsys.db |
| Facts from DB | ✓ PASS | Direct queries, no interpretation |
| Hypotheses Generated | ✓ PASS | Based on Facts with confidence scores |
| Candidates Created | ✓ PASS | For hypotheses affecting Knowledge |
| Screen Shows 3 Layers | ✓ PASS | Fact → Hypothesis → Candidate |
| PO-Only Questions | ✓ PASS | Ask ambiguous items only |
| No Code Violations | ✓ PASS | No Knowledge file modifications |

---

## Pre-Implementation Decision Point

**QUESTION:** Should I proceed with this implementation?

**RECOMMENDATION:** ✓ YES

**REASONING:**
1. All Blueprint rules can be satisfied by this approach
2. Real DB queries are safe (read-only)
3. Fact/Hypothesis/Candidate separation is clear
4. Knowledge protection is enforced
5. Product Owner review is explicit
6. No existing code is violated

**Risk Assessment:** LOW
- All Blueprint compliance verified
- No dangerous modifications planned
- Clear separation of concerns

**Next Step:** Proceed to implementation if approved

---

**Status:** ✓ BLUEPRINT COMPLIANT — Ready to Implement

