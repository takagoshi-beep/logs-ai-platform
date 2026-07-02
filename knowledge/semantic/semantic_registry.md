# Semantic Registry v2 — Business-Centric

Knowledge Registry（`knowledge/**/*.md`内のルール）とは別に、
「LOGS社員が業務で実際に使う用語」と「それらの業務意味定義」を対応付ける。

Reasoningの`meaning`は、DB列名ではなく、まずこのSemantic Registryを経由して業務用語を理解する。
フロー: 質問 → Semantic Resolver → Meaning（業務概念参照） → Knowledge（ルール）→ Evidence → Decision

各エントリは`####`見出しを使用。Knowledge Registryのルール抽出（`###`見出し）とは衝突しない。

---

#### SEM-001: OEM案件

**業務用語:** OEM案件  
**定義:** 顧客からの要件に基づき、LOGSが企画・設計・製造・納品する案件

**Meaningで参照される箇所:** `business_segment` （Q1）

**使用する人:** 営業企画（受注）、生産管理（製造）、営業（納期管理）、経営層（利益分析）  
**関連Semantic:** SEM-005（売上）, SEM-006（仕入）, SEM-008（粗利）, SEM-007（納品）

**確認状態:** Pending（OEM判定ルールが未確定）  
**詳細:** knowledge/semantic/oem_project.md

---

#### SEM-002: Retail案件

**業務用語:** Retail案件  
**定義:** LOGSが保有する既製品を顧客に販売する案件

**Meaningで参照される箇所:** `business_segment` （Q1フォールバック）

**使用する人:** 営業（商品提案）、在庫管理（在庫手配）、経営層（売上トレンド分析）  
**関連Semantic:** SEM-005（売上）, SEM-010（商品）, SEM-007（納品）

**確認状態:** Pending（Retail判定ルールが未確定）  
**詳細:** knowledge/semantic/retail_project.md

---

#### SEM-003: 顧客

**業務用語:** 顧客  
**定義:** LOGSと継続的な取引関係を持つ取引先企業。商品を購入し、納品・請求の相手方となる事業体

**Meaningで参照される箇所:** `entity`, `entity_type` （Q2, Q4）

**使用する人:** 営業（顧客管理）、経営層（得意先分析）、経理（請求先管理）  
**関連Semantic:** SEM-005（売上）, SEM-004（受注）

**確認状態:** Pending（顧客識別体系が未確定）  
**詳細:** knowledge/semantic/customer.md

---

#### SEM-004: 受注

**業務用語:** 受注  
**定義:** 顧客がLOGSに対して正式に発注すること。注文確定→納品→請求→入金フロー の起点

**Meaningで参照される箇所:** （今後利用予定）

**使用する人:** 営業（受注確定）、生産管理（スケジューリング）、経営層（パイプライン管理）  
**関連Semantic:** SEM-003（顧客）, SEM-005（売上）, SEM-007（納品）

**確認状態:** Pending（受注確定タイミングが未確定）  
**詳細:** knowledge/semantic/order.md

---

#### SEM-005: 売上

**業務用語:** 売上  
**定義:** 顧客への商品納品を認識し、対価を請求・収益として計上すること。およびその金額

**Meaningで参照される箇所:** `metric` （Q1, Q4）

**使用する人:** 営業（納品・請求）、経理（収益計上）、経営層（売上トレンド）  
**関連Semantic:** SEM-004（受注）, SEM-007（納品）, SEM-008（粗利）, SEM-006（仕入）

**確認状態:** Pending（売上認識タイミングが未確定）  
**詳細:** knowledge/semantic/sales.md

---

#### SEM-006: 仕入

**業務用語:** 仕入  
**定義:** 商品製造に必要な材料・部品・生産外注費などを仕入先から調達すること。およびその費用

**Meaningで参照される箇所:** （Knowledge層で使用）

**使用する人:** 生産管理（発注）、経理（原価計上）、経営層（利益分析）  
**関連Semantic:** SEM-005（売上）, SEM-008（粗利）, SEM-010（商品）

**確認状態:** Pending（仕入認識タイミングが未確定）  
**詳細:** knowledge/semantic/purchase.md

---

#### SEM-007: 納品

**業務用語:** 納品  
**定義:** 製造・調達した商品を顧客に渡すこと。顧客への物理的な引き渡し

**Meaningで参照される箇所:** `time` （Q3）

**使用する人:** 生産管理（出荷）、営業（顧客対応）、経理（売上計上）  
**関連Semantic:** SEM-004（受注）, SEM-005（売上）

**確認状態:** Pending（納期定義が未確定）  
**詳細:** knowledge/semantic/delivery.md

---

#### SEM-008: 粗利

**業務用語:** 粗利  
**定義:** 売上から直接的な製造原価を差し引いた利益。会社全体、案件別、顧客別等の複数粒度で計算される経営指標

**Meaningで参照される箇所:** `metric`, `candidate_kpi` （Q1）

**使用する人:** 経営層（経営判断）、営業（案件採算管理）、生産管理（原価低減）  
**関連Semantic:** SEM-005（売上）, SEM-006（仕入）, SEM-001（OEM案件）, SEM-002（Retail案件）

**確認状態:** Pending（概算/実際粗利の算出根拠が未確定）  
**詳細:** knowledge/semantic/gross_profit.md

---

#### SEM-009: 案件

**業務用語:** 案件  
**定義:** LOGSが対応する一連の業務活動の単位。単一の顧客への単一の納品約定から、完全納品・完金まで、一貫して追跡・管理される最小ビジネスユニット

**Meaningで参照される箇所:** `entity`, `entity_type` （Q2, Q3）

**使用する人:** 営業企画（案件管理）、生産管理（進捗管理）、経営層（ポートフォリオ管理）  
**関連Semantic:** SEM-001（OEM案件）, SEM-002（Retail案件）, SEM-003（顧客）, SEM-004（受注）

**確認状態:** Pending（案件定義と案件マスタの存在有無が未確定）  
**詳細:** knowledge/semantic/project.md

---

#### SEM-010: 商品

**業務用語:** 商品  
**定義:** LOGSが製造・販売する対象物の品目。型番・カラー・サイズなどの各バリアント単位で識別される

**Meaningで参照される箇所:** `entity` （メタ参照、今後拡張）

**使用する人:** 商品企画（商品開発）、営業（提案）、在庫管理（在庫手配）  
**関連Semantic:** SEM-001（OEM案件）, SEM-002（Retail案件）

**確認状態:** Pending（商品分類コード体系が未確定）  
**詳細:** knowledge/semantic/product.md

---

## インデックス

| SEM ID | 業務用語 | 確認状態 |
|--------|---------|---------|
| SEM-001 | OEM案件 | Pending |
| SEM-002 | Retail案件 | Pending |
| SEM-003 | 顧客 | Pending |
| SEM-004 | 受注 | Pending |
| SEM-005 | 売上 | Pending |
| SEM-006 | 仕入 | Pending |
| SEM-007 | 納品 | Pending |
| SEM-008 | 粗利 | Pending |
| SEM-009 | 案件 | Pending |
| SEM-010 | 商品 | Pending |

---

## 利用フロー

```
質問（例：「OEM粗利」）
  ↓
Semantic Resolver（質問から業務概念を抽出）
  → "OEM" → SEM-001
  → "粗利" → SEM-008
  ↓
Meaning（抽出した概念から意味を構築）
  → business_segment: "OEM案件 → SEM-001"
  → metric: "粗利 → SEM-008"
  ↓
Knowledge（ビジネスルール検索）
  → KPI-METRIC-002（粗利3種の定義）
  → BR-SALES-STANDARD-001（標準フィルタ）
  ↓
Evidence & Decision Gate
```

**Last Updated:** 2026-07-09
