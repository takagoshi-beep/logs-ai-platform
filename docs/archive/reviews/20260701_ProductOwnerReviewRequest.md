# 20260701 Product Owner Review Request

**レビュー対象:** Phase 5-2 Business Knowledge Construction  
**判断依頼時間:** 7分  
**判断項目数:** 3件  

---

## 今回 AI が理解したこと

✓ **粗利の3種類を区別** — 概算粗利 vs 実際粗利 vs 担当者粗利；回答時に必ず種別を明示  
✓ **エンティティ解決ルール** — 複数候補がある場合は推測せず確認；顧客コード優先  
✓ **営業担当費用の粒度制約** — スタッフ粗利計算には使用OK；顧客/商品別分析には禁止

---

## 判断してほしいこと

### 【判断1】logsys.db スキーマ確認の優先度

**現在の理解:**
- logsys.db は 289MB で 21 テーブル
- 実ビジネスデータ（売上・仕入・顧客）のスキーマ未確認

**質問:** Phase 5-3 でクエリプランナー実装時に、logsys.db スキーマ詳細が必要になります。確認方法を用意してもらえますか？

**おすすめ:** 簡易 SQL スクリプト（PRAGMA table_info 出力）で OK

**回答:**
- [ ] YES — スクリプト/Dump 用意できます
- [ ] NO — 当面は mock-data で進めて後で確認
- [ ] 修正 — [別の方法を記載]

---

### 【判断2】OEM/ODM/Retail の分類基準

**現在の理解:**
- Frontend mock-data では project_name に "OEM" / "Retail" が含まれている
- logsys.db に project_type column があるか不明

**質問:** OEM 分類は project_type column で判定 vs project_name パターンマッチのどちらで進めますか？

**おすすめ:** 最初は name パターン（mock-data と統一）、DB 連携時に type column 確認

**回答:**
- [ ] YES — name パターン で進める
- [ ] NO — DB schema 確認後に決める
- [ ] 修正 — [別の方法を記載]

---

### 【判断3】Knowledge maintenance の権限

**現在の理解:**
- Business Dictionary / Business Rules は業務変化に応じて更新が必要
- 更新権限が未確定

**質問:** Knowledge Base 更新は高越が直接 GitHub で編集 vs AI が検出して高越がレビュー のどちらですか？

**おすすめ:** 当面は高越が直接編集（シンプル）；Phase 6 以降に AI 自動検出へ

**回答:**
- [ ] YES — 高越が直接編集（GitHub markdown）
- [ ] NO — AI が検出→高越がレビュー
- [ ] 修正 — [別の方法を記載]

---

## Knowledge Gap — High Priority Only

**内部管理中の質問（回答不要）:**
- logsys.db テーブルスキーマ詳細
- Semantic Catalog マスターデータソース
- Exception Business Rules フィルタ条件

---

## Review Verification

| 項目 | 結果 |
|------|------|
| **レビュー時間** | 7 分（目標: 5-10分） | ✓ PASS |
| **質問数** | 3 件（最大: 3件） | ✓ PASS |
| **回答形式** | YES / NO / 修正 のみ | ✓ PASS |
| **評価** | **PASS — レビューコスト最適化達成** |

---

**回答期限:** 今週中  

**回答方法:** 任意（ChatGPT / Claude / 将来の AI OS / その他）

**回答例:**
```
① YES
② 修正 — OEM案件は○○です
③ NO
```
