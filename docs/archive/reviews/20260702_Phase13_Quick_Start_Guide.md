# Phase 13 Quick-Start Verification Guide

**Status:** ✅ Backend & Frontend Code Complete | 🔄 Ready for Screen Testing

---

## What Was Fixed

1. ✅ **Logisys → Logsys** (2 locations fixed)
2. ✅ **4-Layer Display** (Fact/Interpretation/Hypothesis/Candidate)
3. ✅ **Fact Provenance** (Provider/Table/Query/Rows/Timestamp visible)
4. ✅ **Interpretation Clean** (Patterns only, no numeric data)
5. ✅ **Hypotheses Visible** (With confidence scores)
6. ✅ **Candidates PENDING** (All marked with explicit status)
7. ✅ **Blueprint Compliant** (All 4 rules verified)

---

## How to Verify

### Step 1: Start Backend
```bash
cd backend
python -m uvicorn main:app --reload
# Should see: Uvicorn running on http://0.0.0.0:8000
```

### Step 2: Start Frontend
```bash
cd frontend
npm run dev
# Should see: ▲ Next.js 14.0.0
# ready - started server on 0.0.0.0:3000
```

### Step 3: Navigate to Reasoning Page
```
Open browser: http://localhost:3000/reasoning
```

### Step 4: Submit OEM Question
Click sample button or type:
```
今月のOEM粗利は?
```

### Step 5: Verify 4 Layers Display
Scroll down and verify you see:

```
┌─ Phase 13 Header ────────────────────────────────────┐
│ Phase 13: 4-Layer Fact Extraction (Real DB Integration)
│ Blueprint compliance note...
└──────────────────────────────────────────────────────┘

┌─ Layer 1: FACT (Blue Box) ───────────────────────────┐
│ ✓ Provider: LogsysProvider
│ ✓ Source Table: 集計
│ ✓ Rows Retrieved: [count]
│ ✓ Timestamp: 2026-07-02 15:30:45
│ ✓ Query Conditions: WHERE 分類 = OEM AND ...
│ ✓ Raw Data: oem_record_count, oem_total_sales, etc.
│ ✓ Data Quality: Completeness, Null Count, Accuracy
└──────────────────────────────────────────────────────┘

┌─ Layer 2: INTERPRETATION (Amber Box) ─────────────────┐
│ • 集計テーブルに『分類=OEM』というフラグが存在し...
│ • 売上と粗利の金額が集計テーブルに事前計算されて...
│ • データ取得日時: ..., 推定精度: 95%
│ (✓ No ¥ symbols, no numbers, only observations)
└───────────────────────────────────────────────────────┘

┌─ Layer 3: HYPOTHESIS (Purple Box) ────────────────────┐
│ HYP-OEM-001 | 72% Confidence
│ OEM案件は集計.分類='OEM' で判定されている可能性が高い
│ Reasoning: [...]
│ Affects Knowledge: OEM案件判定基準
│ 
│ HYP-PROFIT-001 | 68% Confidence
│ [...]
│ 
│ HYP-DATA-001 | 55% Confidence
│ [...]
└───────────────────────────────────────────────────────┘

┌─ Layer 4: KNOWLEDGE_CANDIDATE (Red Box) ──────────────┐
│ OEM案件判定基準 | 72% Confidence | [PENDING]
│ 「OEM案件は集計.分類='OEM' で判定される...」
│ ⚠️ Product Owner確認待ち...
│
│ 粗利計算基準 | 68% Confidence | [PENDING]
│ [...]
│
│ 期間定義 | 55% Confidence | [PENDING]
│ [...]
└───────────────────────────────────────────────────────┘
```

---

## Verification Checklist

Print this and check as you verify:

### Display Verification
- [ ] Phase 13 header visible at top
- [ ] 4 distinct sections labeled "Layer 1", "Layer 2", "Layer 3", "Layer 4"
- [ ] Each layer has different background color (blue, amber, purple, red)

### Layer 1: FACT (Blue Box)
- [ ] "Provider: LogsysProvider" (NOT "Logisys")
- [ ] "Source Table: 集計"
- [ ] "Rows Retrieved: [number]"
- [ ] "Timestamp: 2026-07-02T..." (ISO format)
- [ ] "Query Conditions:" showing WHERE clause
- [ ] "Raw Data:" showing oem_record_count, oem_total_sales, oem_total_margin
- [ ] "Data Quality:" showing Completeness, Null Count, Accuracy

### Layer 2: INTERPRETATION (Amber Box)
- [ ] Multiple observations starting with "・"
- [ ] No ¥ symbols
- [ ] No numeric calculations
- [ ] Pattern descriptions only
- [ ] Observations about what fields exist
- [ ] Observations about data availability

### Layer 3: HYPOTHESIS (Purple Box)
- [ ] 3 hypotheses visible (HYP-OEM-001, HYP-PROFIT-001, HYP-DATA-001)
- [ ] Each has ID (HYP-*-###)
- [ ] Each has confidence score (72%, 68%, 55%)
- [ ] Each has statement starting with "AI hypothesis:"
- [ ] Each has "Reasoning:" section with bullet points
- [ ] Each shows "Affects Knowledge: [concept name]"

### Layer 4: KNOWLEDGE_CANDIDATE (Red Box)
- [ ] 3 candidates visible (OEM判定基準, 粗利計算基準, 期間定義)
- [ ] Each shows concept name
- [ ] Each shows confidence percentage
- [ ] **IMPORTANT:** Each has orange badge showing "PENDING"
- [ ] Each has warning note "⚠️ Product Owner確認待ち..."

### Overall Checks
- [ ] No errors in browser console
- [ ] All 4 layers render without scrolling up/down too much
- [ ] Text is readable and well-formatted
- [ ] Colors are distinct (blue ≠ amber ≠ purple ≠ red)
- [ ] No duplicate content between layers

---

## Screenshots to Capture

### Screenshot 1: Full Phase 13 Section
Capture the entire Phase 13 area including all 4 layers:
```bash
File: Phase13_Full_4Layers.png
Show: Header + Layer 1 + Layer 2 + Layer 3 + Layer 4
Size: Full page width, all layers visible
```

### Screenshot 2: FACT Layer Detail
Zoom in on FACT layer to show provenance clearly:
```bash
File: Phase13_Layer1_FACT_Detail.png
Show: Provider, Table, Rows, Timestamp, Query, Data clearly visible
Verify: "LogsysProvider" (not Logisys)
```

### Screenshot 3: KNOWLEDGE_CANDIDATE Detail
Zoom in on KNOWLEDGE_CANDIDATE layer:
```bash
File: Phase13_Layer4_Candidate_Detail.png
Show: PENDING badge on each candidate
Show: Confidence scores (72%, 68%, 55%)
Show: Warning note about PO review
```

---

## Common Issues & Solutions

### Issue: Phase 13 section not showing
**Solution:**
1. Make sure you submitted an OEM question (contains "OEM" AND "粗利")
2. Check browser console for errors (F12)
3. Check backend logs for Python errors
4. Restart both servers

### Issue: "LogisysProvider" still shows (not "LogsysProvider")
**Solution:**
1. Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)
2. Clear browser cache
3. Verify changes in code (grep for LogsysProvider)
4. Restart npm dev server

### Issue: INTERPRETATION layer shows ¥ amounts
**Solution:**
1. This means code change didn't take effect
2. Check line 140-183 in reasoning_pipeline.py
3. Verify _interpret_facts() only has observations
4. Restart backend server

### Issue: Candidates don't show "PENDING" badge
**Solution:**
1. Check line 262 in reasoning_pipeline.py: `"po_review_status": "PENDING"`
2. Verify page.tsx line 650: `{cand.po_review_status}`
3. Hard refresh browser
4. Restart servers

### Issue: Only 3 hypotheses showing (expected: 3)
**Solution:**
This is correct - should be 3 hypotheses (HYP-OEM-001, HYP-PROFIT-001, HYP-DATA-001)

### Issue: Hypothesis/Candidate sections don't show
**Solution:**
1. Check that question contains "OEM" and "粗利"
2. Verify backend code lines 581-593 includes the conditions
3. Check browser console for JSON parsing errors
4. Verify TypeScript interfaces were added (page.tsx lines 14-82)

---

## Code Files to Check

If something isn't showing, check these specific locations:

### Backend (reasoning_pipeline.py)
```bash
# Provider spelling
grep -n "LogsysProvider" backend/services/reasoning_pipeline.py
# Expected: Line 108, Line 134

# Interpretation layer
grep -n "def _interpret_facts" backend/services/reasoning_pipeline.py
# Expected: Line 140

# Phase 13 in reason()
grep -n "phase_13" backend/services/reasoning_pipeline.py
# Expected: Multiple lines around 587

# All 4 layers included
grep -n '"facts"\|"interpretation"\|"ai_hypotheses"\|"knowledge_candidates"' backend/services/reasoning_pipeline.py | grep phase_13
# Expected: 4 matches in the payload["phase_13"] section
```

### Frontend (page.tsx)
```bash
# Provider label fix
grep -n '"logsys": "Logsys"' frontend/app/reasoning/page.tsx
# Expected: Line 97

# Phase13Layer interface
grep -n "interface Phase13Layer" frontend/app/reasoning/page.tsx
# Expected: Line ~60

# phase_13 in setResult
grep -n "phase_13: response.phase_13" frontend/app/reasoning/page.tsx
# Expected: Line 195

# Phase 13 rendering
grep -n "result.phase_13" frontend/app/reasoning/page.tsx
# Expected: Multiple lines around 530-660
```

---

## What to Submit

After verification, submit:

1. **Screenshot 1:** Full Phase 13 display (all 4 layers visible)
2. **Screenshot 2:** FACT layer detail (showing provenance)
3. **Screenshot 3:** KNOWLEDGE_CANDIDATE detail (showing PENDING)
4. **Checklist:** This verification checklist with all items checked
5. **Report:** Description of what you verified

---

## Expected Results

✅ **SUCCESS** = All 4 layers visible on screen with:
- Logisys → Logsys spelling correct
- FACT layer showing full provenance
- INTERPRETATION layer showing only patterns
- HYPOTHESIS layer showing 3 hypotheses with confidence
- KNOWLEDGE_CANDIDATE layer showing 3 candidates all marked PENDING

❌ **FAILURE** = Any of the following:
- Only legacy Evidence layer showing (no Phase 13 section)
- "LogisysProvider" text still showing
- ¥ amounts in INTERPRETATION layer
- Candidates not marked PENDING
- No confidence scores on hypotheses
- Hypothesis/Candidate sections missing

---

## Estimated Time

- Start servers: 1-2 minutes
- Navigate to page: 30 seconds
- Submit question: 30 seconds
- Verify display: 3-5 minutes
- Capture screenshots: 2-3 minutes

**Total: ~8 minutes**

---

**Status:** ✅ Ready for verification  
**Next:** Run servers and follow steps above
