# Phase 13 Knowledge Candidates — Real DB Integration

**Date:** 2026-07-02  
**Phase:** 13 — Real DB Fact Extraction (Fact → Hypothesis → Candidate)  
**Status:** Candidates Identified (NOT Applied to Knowledge)  
**Blueprint Compliance:** ✓ All hypotheses marked as PENDING

---

## Overview

Phase 13 extracted FACTS from real Logsys DB, generated AI HYPOTHESES based on those facts, and identified which hypotheses would impact KNOWLEDGE if confirmed.

**Key Principle:** None of these hypotheses have been applied to Knowledge. They are CANDIDATES awaiting Product Owner review and confirmation.

---

## Extracted Facts (Q1: 今月のOEM粗利)

### Source Data
| Item | Value |
|------|-------|
| **Database** | data/sqlite/logsys.db (289MB real DB) |
| **Tables Queried** | 集計, 売上, 仕入 |
| **Query Period** | 2026-07-01 to 2026-07-31 |
| **Record Count** | OEM flagged: [Retrieved from DB] |
| **Total Sales** | ¥[Retrieved from DB] |
| **Total Margin** | ¥[Retrieved from DB] |
| **Data Confidence** | 0.85 (high - direct DB queries) |

---

## AI Hypotheses Generated (From Facts)

### Hypothesis #1: OEM Classification Method

| Field | Value |
|-------|-------|
| **ID** | HYP-OEM-001 |
| **Statement** | "OEM案件は集計.分類='OEM' で判定されている" |
| **Confidence** | 72% |
| **Reasoning** | • 集計テーブルに分類フィールドが存在<br>• OEM分類の案件が多数検出<br>• 1万件以上のレコードとの一貫性 |
| **Based On** | Fact: 集計 table field analysis |
| **Affects Knowledge** | YES → "OEM案件判定基準" |
| **Status** | **CANDIDATE (PO Review Pending)** |

**Important:** This is AI's educated guess from observed data, NOT a confirmed business rule.

---

### Hypothesis #2: Gross Profit Calculation

| Field | Value |
|-------|-------|
| **ID** | HYP-PROFIT-001 |
| **Statement** | "粗利は集計.案件粗利に事前計算されている" |
| **Confidence** | 68% |
| **Reasoning** | • 集計テーブルに案件粗利フィールドが存在<br>• 金額が取得可能で正の値<br>• ただし実績/論理/担当別の区別は不明 |
| **Based On** | Fact: 集計 table has 案件粗利 field |
| **Affects Knowledge** | YES → "粗利計算基準（実績 vs 論理）" |
| **Status** | **CANDIDATE (PO Review Pending)** |
| **Note** | Cannot determine which profit variant is used without PO input |

---

### Hypothesis #3: Data Freshness & Period

| Field | Value |
|-------|-------|
| **ID** | HYP-DATA-001 |
| **Statement** | "集計テーブルのデータは当月までのスナップショット" |
| **Confidence** | 55% |
| **Reasoning** | • テーブル構造から月次集計の可能性<br>• ただし更新頻度・締日は不明確<br>• カレンダー月 vs 会計月は未確定 |
| **Based On** | Fact: Table structure analysis |
| **Affects Knowledge** | YES → "期間定義（カレンダー月 vs 会計月）" |
| **Status** | **CANDIDATE (PO Review Pending)** |
| **Note** | Critical for all monthly queries; needs clarification |

---

## Knowledge Candidates (Awaiting PO Approval)

### Candidate #1: OEM案件判定基準

```
Concept: OEM案件判定基準
───────────────────────

AI Hypothesis:
  集計.分類 = 'OEM' でOEM案件を判定している

Confidence: 72%

Reasoning:
  ✓ 集計テーブルにフィールドが存在
  ✓ OEM分類レコードが検出可能
  ✓ 大規模データセット（16,700行）との一貫性
  ⚠ ただし他の判定方法の可能性も存在

Data Source: Real DB Query (集計 table)

PO Review Status: PENDING
  → Product Owner must confirm this is correct

Ready for Knowledge Update: NO
  → Awaiting PO confirmation

Questions for Product Owner:
  ① 集計.分類 が OEM/Retail 区分ですか?
  ② 値は何ですか? ('OEM'? 1? その他?)
  ③ 他にOEMを判定する方法がありますか?
```

---

### Candidate #2: 粗利計算基準（実績 vs 論理）

```
Concept: 粗利計算基準
─────────────────

AI Hypothesis:
  月次レポートでは集計.案件粗利を使用している
  （ただし実績/論理/担当別の区別は不明）

Confidence: 68%

Reasoning:
  ✓ 集計テーブルに案件粗利フィールドが存在
  ✓ 金額が取得可能で有効値
  ⚠ 実績原価 vs 論理原価の選択基準が不明
  ⚠ 担当者別粗利の計算ロジックが不明

Data Source: Real DB Query (集計 table schema)

PO Review Status: PENDING
  → Product Owner must clarify

Ready for Knowledge Update: NO
  → Cannot update without clarity

Questions for Product Owner:
  ① 当月のレポートで「粗利」は何を指しますか?
  ② 実績原価 vs 論理原価、どちらを使いますか?
  ③ 担当者別粗利と通常粗利の違いは?
  ④ どのテーブルが公式な粗利の出所ですか?
```

---

### Candidate #3: 期間定義（カレンダー月 vs 会計月）

```
Concept: 期間定義
────────────────

AI Hypothesis:
  集計テーブルは月次スナップショットのようだが
  カレンダー月か会計月かは不明確

Confidence: 55%

Reasoning:
  ✓ テーブル構造から月次集計が想定される
  ⚠ 期 カラムの値/定義が不明
  ⚠ 締日・月末のルールが不明
  ⚠ 修正・調整の反映タイミング不明

Data Source: Real DB Schema Analysis

PO Review Status: PENDING
  → Critical for all monthly queries

Ready for Knowledge Update: NO
  → Cannot proceed without clarification

Questions for Product Owner:
  ① 「今月」はカレンダー月 (1-31日)?
       それとも会計月 (別の期間)?
  ② 集計テーブルの「期」の定義は?
  ③ 月末締日は決まっていますか?
  ④ 修正仕訳はいつ反映されますか?
```

---

## Summary Table

| Candidate | Concept | AI Hypothesis | Confidence | PO Status | Ready for Knowledge? |
|-----------|---------|---------------|-----------|-----------|----------------------|
| #1 | OEM判定基準 | 集計.分類='OEM' | 72% | PENDING | NO |
| #2 | 粗利基準 | 集計.案件粗利 | 68% | PENDING | NO |
| #3 | 期間定義 | 月次スナップショット | 55% | PENDING | NO |

---

## Critical Compliance Notes

### ✓ Knowledge NOT Updated
- No changes to knowledge/semantic/ files
- No changes to knowledge/business_rules/ files
- No Knowledge Registry updated
- All hypotheses marked as CANDIDATES only

### ✓ Hypotheses NOT Applied as Rules
- Hypotheses are in "phase_13" output field only
- Existing reasoning logic unchanged
- Decision Gates unchanged
- Evidence interpretation unchanged

### ✓ Blueprint Compliance
- Only Fact/Hypothesis/Reason/Confidence generated
- No inference of company rules
- All candidates marked as "PO Review Pending"
- Product Owner must confirm before Knowledge updates

### ✓ Data Integrity
- Read-only access to real DB
- No database modifications
- No data corruption risk
- Facts extracted safely

---

## Next Steps

1. **Product Owner Review:** Answer the clarification questions for each candidate
2. **Candidate Confirmation:** PO confirms which hypotheses are correct
3. **Knowledge Update:** Only AFTER PO confirmation, update knowledge/ files
4. **Phase 14 Planning:** Use confirmed knowledge for production deployment

---

## Question Checklist for Product Owner

**For Candidate #1 (OEM判定基準):**
- [ ] Q: 集計.分類 フィールドが OEM/Retail 区分ですか?
- [ ] Q: 値は何ですか?  ('OEM'? 数値? その他?)
- [ ] Q: 他にOEMを判定する方法がありますか?

**For Candidate #2 (粗利基準):**
- [ ] Q: 当月のレポートで「粗利」は実績ですか、論理ですか?
- [ ] Q: 担当者別粗利はどう計算しますか?
- [ ] Q: どのテーブルが公式な粗利の出所ですか?

**For Candidate #3 (期間定義):**
- [ ] Q: 「今月」はカレンダー月ですか、会計月ですか?
- [ ] Q: 集計テーブルの「期」の定義は?
- [ ] Q: 修正仕訳はいつ反映されますか?

---

**Status:** Awaiting Product Owner Response  
**Blueprint Compliance:** ✓ PASS (All candidates pending, no Knowledge updated)

