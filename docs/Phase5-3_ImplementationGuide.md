# Phase 5-3 Implementation Guide — Knowledge から推論へ

**Phase:** 5-3  
**Focus Shift:** Writing Knowledge → Using Knowledge  
**Duration:** 2-3 weeks  

---

## Phase 5-3 の目的

AI が以下のフローで質問に対応できること：

```
質問 (ユーザー入力)
  ↓
Intent Resolver
  ├─ Analysis (データ分析)
  ├─ Monitoring (状況確認)
  └─ Reference (検索)
  ↓
Meaning Resolver
  ├─ Entity (顧客 C123)
  ├─ KPI (粗利：実際粗利)
  ├─ Time ([2026-06-01, 2026-06-30])
  ├─ Grain (顧客別)
  └─ Data Sources (sales, purchases)
  ↓
Knowledge Layer (Business Rules 適用)
  ├─ フィルタ (status IN (2,3,4,5))
  ├─ 計算ルール (粗利 = 売上 - 仕入)
  └─ 制約 (営業担当費用は顧客別分析では使用不可)
  ↓
Developer Verification (数値ではなく推論結果)
  ├─ Intent: Analysis ✓
  ├─ Meaning Payload: {entity, kpi, time, grain, data_sources} ✓
  ├─ Knowledge Applied: {rules, filters, constraints} ✓
  ├─ Unknown: [仕入テーブルのカラム構成] ⚠
  └─ Ready for Query Generation ✓
```

---

## 対象質問 (正しく解釈すること)

### Q1: 今月のOEM事業の粗利を教えて

**期待される推論:**
```
Intent: Analysis
Meaning: {
  entity: OEM事業 (product_type or name pattern),
  kpi: gross_profit,
  kpi_variant: 実際粗利 (推奨) or 概算粗利 (フォールバック),
  time: [2026-06-01, 2026-06-30],
  grain: business_segment,
  data_sources: [sales, purchases]
}
Knowledge Applied:
  - Filter: status IN (2,3,4,5), payment_method != 4
  - Calc: SUM(sales) - SUM(purchases)
  - Note: 仕入未入力分は概算粗利のまま
Unknown:
  - OEM分類の正式フィールド (project_type vs name pattern)
  - 実仕入の入力状況
Next Step: Query Generation (SQL)
```

### Q2: Fanatics案件の状況を教えて

**期待される推論:**
```
Intent: Monitoring
Meaning: {
  entity: customer_id = C_FANATICS (Entity Resolution),
  attribute: status/health,
  time: now (current state),
  grain: project,
  data_sources: [projects, sales, tasks]
}
Knowledge Applied:
  - Project State Enum: {planning, in_progress, pending_delivery, complete, ...}
  - Related Info: revenue, margin, owner, next_action
Unknown:
  - project_type column存在有無
  - tasks テーブルの参照方法
Next Step: Data Aggregation
```

### Q3: 今日優先すべき案件は？

**期待される推論:**
```
Intent: Monitoring (Priority Detection)
Meaning: {
  entity: all projects,
  filter: due_date today / at_risk status,
  time: today,
  grain: project,
  data_sources: [projects, tasks, decisions]
}
Knowledge Applied:
  - Priority Ranking: due_date + risk_flag + margin_trend
  - Grain: Project level only
Unknown:
  - tasks テーブルのスキーマ
  - Risk Flag の定義
Next Step: Ranking & Presentation
```

### Q4: 今月売上が一番大きい顧客は？

**期待される推論:**
```
Intent: Analysis
Meaning: {
  entity: all customers,
  kpi: sales_amount,
  time: [2026-06-01, 2026-06-30],
  grain: customer,
  data_sources: [sales, customers],
  ranking: DESC by sales_amount
}
Knowledge Applied:
  - Filter: status IN (2,3,4,5)
  - Agg: SUM(sales_amount) GROUP BY customer_id
  - Sort: DESC limit 1
Unknown:
  - Customer master のカラム構成
Next Step: Query Generation
```

---

## Developer Verification Template

各質問について以下を表示：

```
【Q: 今月のOEM事業の粗利を教えて】

✓ Intent: Analysis
  └─ Confidence: 0.95

✓ Meaning:
  entity: OEM (project_type or name pattern)
  kpi: gross_profit
  variant: 実際粗利 (fallback: 概算粗利)
  time: [2026-06-01, 2026-06-30]
  grain: business_segment
  data_sources: [sales, purchases]

✓ Knowledge Applied:
  - BR-SALES-STANDARD-001: status IN (2,3,4,5)
  - BR-SALES-DETAIL-003: line-item basis
  - PR-GROSS-PROFIT-LABEL-002: variant label required

⚠ Unknown:
  - OEM分類フィールド (logsys.db schema未確認)
  - 実仕入の入力状況 (purchase未入力の割合)

→ Ready for Query Generation ✓
```

---

## 実装Checklist

### Intent Resolver
- [ ] Analysis / Monitoring / Reference 判定
- [ ] Confidence score 計算
- [ ] 複数意図競合時の確認ロジック

### Meaning Resolver
- [ ] Entity extraction + resolution (canonical code化)
- [ ] KPI enum mapping
- [ ] Time phrase interpretation
- [ ] Grain determination
- [ ] Data source mapping

### Knowledge Application
- [ ] Business Rules filter適用
- [ ] Constraint enforcement (e.g., grain制約)
- [ ] Unknown 明示化

### Developer Verification Output
- [ ] Intent + confidence
- [ ] Meaning payload
- [ ] Applied rules
- [ ] Unknown fields
- [ ] Ready/Blocked status

---

## 成功基準（Phase 5-3 完了）

| 対象質問 | 正解基準 |
|---------|--------|
| Q1: OEM粗利 | Intent=Analysis, Meaning完全, Unknown≤2個 |
| Q2: Fanatics案件 | Intent=Monitoring, Entity resolved, Unknown≤2個 |
| Q3: 優先案件 | Intent=Monitoring, Ranking logic存在, Unknown≤2個 |
| Q4: 売上首位顧客 | Intent=Analysis, Grain=Customer, Unknown≤2個 |

**すべての質問で「数値」ではなく「推論結果」を返す。**

---

## 次のステップ

1. Intent Resolver 実装（1週間）
2. Meaning Resolver 実装（1.5週間）
3. Knowledge Application & Verification（0.5週間）
4. テスト & 調整

---

**Next Phase:** 5-3 — Knowledge を使って、AI が考える
