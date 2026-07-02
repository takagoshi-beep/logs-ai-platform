# Google Drive 運用設計 — Phase 6 以降

**Status:** 将来設計（未実装）  
**対象フェーズ:** Phase 6+  

---

## 目的

GitHub（開発資産）と Google Drive（レビュー・承認履歴）を分離し、役割を明確化する。

---

## 将来のフォルダ構成（実装予定）

```
AI OS/
├── 01_レビュー依頼/
│   ├── 未レビュー/
│   ├── レビュー中/
│   ├── 承認済み/
│   └── 差し戻し/
├── 02_承認履歴/
│   └── YYYY年MM月/
└── 03_議事録/
```

---

## 現在（Phase 5-2）の運用

**GitHub で完結:**
- Knowledge Base (`/knowledge/`)
- Review 資料 (`/docs/reviews/`)
- Code (`/backend/`, `/frontend/`)

**Google Drive:**
- 未使用（Phase 6 で開始予定）

---

## Phase 6 開始時の手順

1. Google Drive に `AI OS/` フォルダ作成
2. 毎回のレビュー資料をアップロード
3. 承認後、`承認済み/` フォルダへ移動
4. Drive API 連携検討

---

## 参考: 現在のレビュー流れ

```
GitHub Push
    ↓
Product Owner Review (GitHub で読む)
    ↓
YES / NO / 修正 で回答（GitHub issue / メール）
    ↓
次フェーズへ
```

**Google Drive 組み込み:** Phase 6+

---

**Design Owner:** Product Owner（高越）  
**Implementation:** Phase 6
