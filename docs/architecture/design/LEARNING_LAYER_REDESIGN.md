# Learning Layer 再設計：Governed Learning vs Operational Learning


<!-- SNAPSHOT-BANNER -->
> **📌 Point-in-time snapshot.** This document records the state of the
> project as of the date/phase named in its title or body. It has not been
> updated since, and may not reflect the current code. Verify claims against
> the current source before relying on them. For the maintained, current
> architecture reference, see `docs/architecture.md` and `docs/system_manifest.md`.

**日付:** 2026-06-30  
**バージョン:** 2.0  
**重要:** 2つの学習系統を混同しないこと

---

## 1. 概念の明確化

### Governed Learning (会社の判断基準)
```
会社のビジネス判断に関わる学習

特徴：
- Business Rule (3軸スコア、フォーカス推奨) に関わる
- 他のプロジェクト / 顧客 / 部門へ影響が大きい
- 誤った学習 = 全社的な判断ズレ
- AIが勝手に反映してはいけない

例：
「粗利5%のプロジェクトは常にfocus=protectすべき」
→ この規則が会社全体に適用される
→ 間違えると大損

管理：
✓ 管理者承認必須
✓ Version control
✓ Rollback可能
✓ 適用履歴記録
✓ 影響範囲分析
```

### Operational Learning (作業効率化)
```
個々のタスク効率化のための学習

特徴：
- ユーザーの作業パターン、修正履歴、テンプレート選好
- 各ユーザー / チーム / 顧客ごとに異なる
- 誤った学習 = そのユーザーの作業効率低下
- 再利用して OK、削除 / 共有制限も OK

例：
「〇〇顧客への請求書は、このExcelフォーマットを使う」
「項目マッピングはこう修正する」
→ 次回は同じ形式を提案
→ ユーザー体験向上

管理：
✓ 自動保存
✓ ユーザー / チーム / 会社スコープ
✓ 削除 / 上書き可能
✓ 共有範囲制御
✓ バージョン管理
```

---

## 2. Governed Learning 設計

### 2.1 アーキテクチャ

```
┌─────────────────────────────────────────────────┐
│ USER FEEDBACK                                   │
│ (AI decision vs human choice)                   │
└────────────────┬────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│ LEARNING QUEUE (in-memory + persistence)        │
│ - feedback_id                                   │
│ - project_id, trace_id                          │
│ - ai_proposal vs human_choice                   │
│ - confidence_level                              │
│ - status: "pending_review"                      │
└────────────────┬────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│ AI ANALYZER (Learning Engine)                   │
│ - Pattern recognition                           │
│ - Rule extraction                               │
│ - Recommended policy rule                       │
│ - Confidence calculation                        │
│ - Conflict detection                            │
└────────────────┬────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│ ADMIN REVIEW INTERFACE                          │
│ - Display AI recommendation                     │
│ - Show evidence (supporting feedbacks)          │
│ - Impact simulation (affected projects)         │
│ - Approve / Reject / Modify                     │
└────────────────┬────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│ APPROVAL GATE (必須)                            │
│ - Admin decision: approve / reject / modify     │
│ - Reason / justification                        │
│ - Effective date                                │
│ - Rollback plan                                 │
└────────────────┬────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│ RULE REPOSITORY (persistent)                    │
│ - Add new rule or update existing                 │
│ - Mark as "approved" with version                 │
│ - Keep approval metadata                         │
│ - Maintain audit trail                           │
└────────────────┬────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│ BUSINESS RULE VERSION CONTROL                   │
│ - Version increment (1.0 → 1.1)                 │
│ - Changelog generation                          │
│ - A/B test setup (optional)                     │
│ - Gradual rollout (phased)                       │
│ - Rollback trigger setup                        │
└────────────────┬────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│ NEXT AI DECISION (改善された scoring)           │
│ - Business Rule v1.1 を使用                    │
│ - New projects apply updated rules              │
└─────────────────────────────────────────────────┘
```

### 2.2 Data Model

```python
@dataclass
class GovernedFeedback:
    """Governed learning に関わる user feedback"""
    feedback_id: str
    project_id: str
    trace_id: str
    
    # AI Proposal
    ai_decision: {
        focus: str                    # "monitor"
        health_score: int
        risk_score: int
        opportunity_score: int
    }
    
    # Human Feedback
    human_choice: {
        focus: str                    # "protect" ← different
        confidence: float             # 0.9
    }
    
    # Why different?
    reason: str                       # "粗利5%なら常に保護する"
    category: str                     # "margin_rule" / "vip_priority" / ...
    
    # Metadata
    user_role: str                    # "sales" / "ceo" / "finance"
    timestamp: datetime
    status: str                       # "pending_review" / "approved" / "rejected"

@dataclass
class PolicyRecommendation:
    """AI が生成する Policy recommendation"""
    recommendation_id: str
    source_feedbacks: list[str]       # feedback_ids
    
    # Recommended rule
    rule_definition: {
        condition: str                # "margin < 5"
        action: str                   # "focus = 'protect'"
        priority: int                 # 1-10
    }
    
    # Analysis
    supporting_evidence: int          # feedback count
    confidence: float                 # 0.85
    affected_project_count: int       # How many projects this affects
    
    # Status
    status: str                       # "pending_admin_review"
    created_at: datetime
    expires_at: datetime              # Auto-cleanup if not reviewed

@dataclass
class AdminApproval:
    """Admin による承認/拒否"""
    approval_id: str
    recommendation_id: str
    admin_user_id: str
    
    # Decision
    decision: str                     # "approved" / "rejected" / "modified"
    
    if decision == "modified":
        modified_rule: dict
        modification_reason: str
    
    # Metadata
    impact_analysis: {
        projects_affected: int
        teams_affected: list[str]
        estimated_impact: str
    }
    
    effective_date: datetime
    rollback_plan: str | None
    
    approved_at: datetime

@dataclass
class BusinessRuleVersion:
    """Business Rule の versioned record"""
    version_id: str                   # "rule-v1.1"
    rule_id: str
    version_number: str               # "1.1"
    
    # Rule content
    condition: str
    action: str
    priority: int
    
    # Approval info
    approved_by: str
    approval_id: str
    approved_at: datetime
    effective_at: datetime
    
    # Metadata
    changelog: str
    previous_version_id: str | None
    rollback_to: str | None           # if rolled back
    
    # Impact tracking
    times_applied: int = 0
    positive_feedback_count: int = 0
    negative_feedback_count: int = 0
```

### 2.3 Admin Review Interface 要件

```
┌──────────────────────────────────────────┐
│ AI RECOMMENDATION REVIEW PORTAL          │
│                                          │
│ Recommendation ID: policy-rec-001        │
│ Status: Pending Admin Review             │
│                                          │
│ ┌──────────────────────────────────────┐ │
│ │ RECOMMENDED POLICY                   │ │
│ │                                      │ │
│ │ Condition: margin < 5%               │ │
│ │ Action: focus = 'protect'            │ │
│ │ Priority: 9/10                       │ │
│ │ Confidence: 85%                      │ │
│ └──────────────────────────────────────┘ │
│                                          │
│ ┌──────────────────────────────────────┐ │
│ │ SUPPORTING EVIDENCE                  │ │
│ │                                      │ │
│ │ 5 user feedbacks confirm this:       │ │
│ │ • feedback-001: sales mgr            │ │
│ │ • feedback-003: finance dept         │ │
│ │ • feedback-007: project manager      │ │
│ │ • feedback-010: ceo review           │ │
│ │ • feedback-015: sales mgr            │ │
│ └──────────────────────────────────────┘ │
│                                          │
│ ┌──────────────────────────────────────┐ │
│ │ IMPACT ANALYSIS                      │ │
│ │                                      │ │
│ │ Affected projects: 127               │ │
│ │ Teams impacted: Sales, Finance       │ │
│ │ Estimated impact: High               │ │
│ │ Affected monthly actions: ~200       │ │
│ │                                      │ │
│ │ Preview: If approved, these          │ │
│ │ projects will get "protect" focus:   │ │
│ │ • PO-2024-102 (margin: 3.5%)        │ │
│ │ • PO-2024-105 (margin: 4.2%)        │ │
│ │ • PO-2024-112 (margin: 4.8%)        │ │
│ └──────────────────────────────────────┘ │
│                                          │
│ ┌──────────────────────────────────────┐ │
│ │ ADMIN DECISION                       │ │
│ │                                      │ │
│ │ ○ Approve                            │ │
│ │ ○ Reject                             │ │
│ │ ○ Modify and Approve                │ │
│ │                                      │ │
│ │ Reason:                              │ │
│ │ ☑ Agree with recommendation         │ │
│ │                                      │ │
│ │ Effective Date: [date picker]        │ │
│ │                                      │ │
│ │ Rollback Plan: [text]                │ │
│ │                                      │ │
│ │ [APPROVE] [REJECT] [MODIFY]         │ │
│ └──────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

---

## 3. Operational Learning 設計

### 3.1 アーキテクチャ

```
┌─────────────────────────────────────────────────┐
│ USER TASK                                       │
│ "この納品書に基づいて伝票をExcelで発行して"   │
└────────────────┬────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│ 1. DOCUMENT PATTERN RECOGNITION                 │
│    - 文書タイプ判定 (納書 / 請求書 / 発注)    │
│    - Data extraction (顧客ID, 案件ID, 金額)   │
│    - Search DocumentPatternMemory              │
└────────────────┬────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│ 2. TEMPLATE SEARCH & RECOMMENDATION             │
│    - TemplateMemory検索                         │
│    - 過去に使ったフォーマット候補表示           │
│    - 顧客別 / チーム別の推奨                  │
│    User: "OK、前回のフォーマットで"             │
└────────────────┬────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│ 3. FIELD MAPPING RETRIEVAL                      │
│    - FieldMappingMemory から項目マッピング     │
│    - 納書フィールド → Excelセル mapping        │
│    - ユーザー修正履歴を参照                     │
└────────────────┬────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│ 4. EXCEL GENERATION                             │
│    - テンプレートからExcelファイル生成          │
│    - マッピングに従ってデータ投入              │
│    - 前回のユーザー修正も適用                   │
└────────────────┬────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│ 5. USER CORRECTION (if any)                    │
│    - ユーザーが項目を修正                       │
│    - 金額の調整、住所の修正など                 │
│    - "保存して次回も使用"ボタン               │
└────────────────┬────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│ 6. SAVE TO OPERATIONAL MEMORY                   │
│    - UserCorrectionMemory: 修正内容保存        │
│    - FieldMappingMemory: 新しいマッピング      │
│    - OutputHistoryMemory: 出力ファイル記録     │
│    - Last_used_at, confidence update            │
└────────────────┬────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│ 7. NEXT TASK RECOMMENDATION                     │
│    - 類似の次のタスク検出                       │
│    - 「前回と同じテンプレートを使いますか？」  │
│    - 効率化提案                                 │
└─────────────────────────────────────────────────┘
```

### 3.2 Operational Memory モデル

#### A. DocumentPatternMemory

```python
@dataclass
class DocumentPattern:
    """文書タイプの認識パターン"""
    pattern_id: str
    
    # Document type
    document_type: str                # "invoice" / "delivery_note" / "po"
    document_type_ja: str             # "請求書" / "納品書" / "発注書"
    
    # Recognition criteria
    keywords: list[str]               # ["請求", "invoice"]
    field_patterns: dict              # {"金額": "JPY \d+", ...}
    
    # Extraction rules
    data_fields: dict[str, str]       # {"customer_id": "location", ...}
    
    # Metadata
    used_count: int
    accuracy: float                   # 0.95
    scope: str                        # "company" / "team" / "user"
    team_id: str | None
    user_id: str | None
    created_by: str
    created_at: datetime
    last_used_at: datetime
    
    # Versioning
    version: str                      # "1.0"
    is_active: bool

class DocumentPatternMemory:
    def recognize_document(file) -> tuple[DocumentPattern, dict]:
        """ファイルから文書タイプとデータを抽出"""
        
    def search_patterns(query: dict) -> list[DocumentPattern]:
        """条件に合うパターンを検索"""
        
    def save_pattern(pattern: DocumentPattern) -> str:
        """新しいパターンを保存"""
        
    def update_stats(pattern_id: str, used: bool, accurate: bool) -> None:
        """使用統計を更新"""
```

#### B. TemplateMemory

```python
@dataclass
class ExcelTemplate:
    """Excelテンプレート"""
    template_id: str
    
    # Template info
    name: str                         # "顧客〇〇向け請求書"
    document_type: str                # "invoice"
    file_path: str | None             # where stored
    
    # Structure
    sheet_layout: dict                # {"columns": [...], "rows": [...]}
    header_rows: int
    data_start_row: int
    
    # Customization
    company_name: str
    company_address: str
    logo_position: dict | None
    
    # Usage scope
    customer_id: str | None           # if customer-specific
    team_id: str | None
    user_id: str | None
    created_by: str
    
    # Statistics
    used_count: int
    last_used_at: datetime
    user_rating: float | None         # 1-5 stars
    
    # Version management
    version: str                      # "1.0"
    parent_template_id: str | None    # if derived
    is_active: bool
    is_deleted: bool
    deleted_at: datetime | None
    can_restore: bool                 # ロールバック可能か

class TemplateMemory:
    def search_templates(document_type: str, context: dict) -> list[ExcelTemplate]:
        """
        context = {
            "customer_id": "cust-001",
            "team_id": "team-sales",
            "user_id": "user-123"
        }
        """
        
    def get_template(template_id: str) -> ExcelTemplate:
        """テンプレート取得"""
        
    def save_template(template: ExcelTemplate) -> str:
        """新しいテンプレート保存"""
        
    def update_template(template_id: str, updates: dict) -> None:
        """テンプレート更新"""
        
    def mark_for_deletion(template_id: str) -> None:
        """削除マーク（ロールバック可能）"""
        
    def restore_template(template_id: str) -> None:
        """削除から復元"""
        
    def share_template(template_id: str, target_scope: str) -> None:
        """テンプレート共有"""
```

#### C. FieldMappingMemory

```python
@dataclass
class FieldMapping:
    """項目マッピング（ソース → Excel）"""
    mapping_id: str
    
    # Mapping definition
    source_type: str                  # "invoice" / "delivery_note"
    target_template_id: str
    
    # Field mappings
    mappings: dict[str, dict]         # {
                                      #   "customer_name": {
                                      #     "source_field": "customer_name",
                                      #     "target_cell": "A2",
                                      #     "transform": None
                                      #   },
                                      #   "total_amount": {
                                      #     "source_field": "amount",
                                      #     "target_cell": "C10",
                                      #     "transform": "convert_to_jpy"
                                      #   }
                                      # }
    
    # Validation
    validation_rules: dict            # cell validation rules
    
    # Scope
    team_id: str | None
    user_id: str | None
    customer_id: str | None
    
    # Statistics
    used_count: int
    accuracy: float                   # errors / uses
    manual_corrections_count: int
    
    # Version
    version: str
    created_at: datetime
    last_modified_at: datetime
    last_used_at: datetime
    created_by: str
    is_active: bool

class FieldMappingMemory:
    def get_mapping(source_type: str, template_id: str, context: dict) -> FieldMapping:
        """マッピング検索"""
        
    def save_mapping(mapping: FieldMapping) -> str:
        """マッピング保存"""
        
    def apply_mapping(mapping: FieldMapping, source_data: dict) -> dict:
        """マッピングを適用"""
        
    def update_accuracy(mapping_id: str, was_correct: bool) -> None:
        """精度統計更新"""
```

#### D. UserCorrectionMemory

```python
@dataclass
class UserCorrection:
    """ユーザーが加えた修正"""
    correction_id: str
    
    # Context
    source_output_id: str             # 修正対象のoutput
    document_type: str
    customer_id: str | None
    template_id: str
    
    # Correction detail
    corrections: dict[str, dict]      # {
                                      #   "A2": {
                                      #     "original": "Old Address",
                                      #     "corrected": "New Address",
                                      #     "reason": "address_updated"
                                      #   },
                                      #   "C10": {
                                      #     "original": 100000,
                                      #     "corrected": 105000,
                                      #     "reason": "discount_applied"
                                      #   }
                                      # }
    
    # Metadata
    user_id: str
    user_department: str
    timestamp: datetime
    correction_time_seconds: float    # how long did user take?
    
    # Frequency analysis
    is_recurring: bool                # same correction pattern?
    recurring_pattern_id: str | None
    
    # Suggestions for improvement
    suggested_field_mapping_update: dict | None
    suggested_template_update: dict | None

class UserCorrectionMemory:
    def save_correction(correction: UserCorrection) -> str:
        """修正記録を保存"""
        
    def find_recurring_corrections(context: dict) -> list[UserCorrection]:
        """繰り返し修正を検索"""
        
    def suggest_improvements(corrections: list[UserCorrection]) -> list[dict]:
        """
        改善提案を生成
        例：「〇〇顧客への請求書は、常に住所を修正しています。
             テンプレートの方を更新しませんか？」
        """
        
    def get_correction_pattern(pattern_id: str) -> dict:
        """修正パターンを取得"""
```

#### E. OutputHistoryMemory

```python
@dataclass
class OutputHistory:
    """生成されたExcelファイルの履歴"""
    output_id: str
    
    # Generation context
    source_document_id: str           # 元のファイル
    template_id: str
    field_mapping_id: str
    
    # Output info
    output_filename: str
    output_format: str                # "xlsx" / "csv"
    output_path: str                  # saved location
    file_hash: str                    # for dedup
    
    # Data
    generated_data: dict              # what was filled in
    user_corrections: list[str]       # correction_ids that were applied
    
    # Metadata
    generated_by: str                 # ai_system / user
    generated_at: datetime
    user_id: str | None               # who requested
    
    # Reusability
    can_be_reused: bool               # similar projects exist?
    similar_projects: list[str]
    
    # Audit
    was_sent: bool
    sent_to: str | None
    sent_at: datetime | None
    
    # Version info
    template_version: str
    mapping_version: str

class OutputHistoryMemory:
    def save_output(history: OutputHistory) -> str:
        """出力履歴を保存"""
        
    def find_similar_projects(context: dict, limit: int = 5) -> list[OutputHistory]:
        """類似プロジェクトの過去出力を検索"""
        
    def get_reuse_suggestion(new_task: dict) -> tuple[OutputHistory, float]:
        """
        Returns: (most_similar_output, similarity_score)
        例：「PO-2024-101 の時は同じテンプレートで対応しました」
        """
        
    def get_efficiency_stats(user_id: str, period: str) -> dict:
        """ユーザーの効率化統計"""
```

---

## 4. 伝票Excel発行ユースケース設計

### 4.1 ユーザーのリクエスト

```
ユーザー (Sales Manager):
「この納品書に基づいて、伝票をExcelで発行して」
```

### 4.2 AI OS の処理フロー

#### ステップ 1: 文書読み取り & タイプ判定

```
Input: 納品書ファイル (PDF/画像)

処理:
1. DocumentPatternMemory で文書タイプ判定
   → "delivery_note" (納品書) 判定

2. OCR / データ抽出
   顧客名: 〇〇株式会社
   案件: PO-2024-001
   商品: ネジ M8 100個
   金額: ¥50,000
   納品日: 2026-06-30

3. 信頼度スコア
   document_type_confidence: 0.98
   data_extraction_confidence: 0.92
```

#### ステップ 2: テンプレート候補の提示

```
TemplateMemory 検索条件:
- document_type: "delivery_note"
- customer_id: "cust-001" (〇〇株式会社)
- team_id: "team-sales" (営業チーム)
- user_id: "user-123"

検索結果:
1. 「〇〇顧客向け請求書 v2.1」
   - used_count: 47
   - last_used_at: 2026-06-28
   - user_rating: 4.8/5.0
   - scope: customer-specific

2. 「標準請求書 v1.0」
   - used_count: 152
   - last_used_at: 2026-06-29
   - user_rating: 4.2/5.0
   - scope: company-wide

3. 「営業チーム様式」
   - used_count: 89
   - last_used_at: 2026-06-30
   - user_rating: 4.5/5.0
   - scope: team

AI 推奨:
★ #1 (過去47回使用、同じ顧客、最近利用)
  + ユーザーが前回これを使ったから確率高い

UI 提示:
┌────────────────────────────┐
│ テンプレート選択           │
│                            │
│ 候補1: 〇〇顧客向け請求書│ ← 推奨
│ ☑ このテンプレートを使う  │
│                            │
│ 候補2: 標準請求書         │
│ ☐ このテンプレートを使う  │
│                            │
│ 候補3: 営業チーム様式     │
│ ☐ このテンプレートを使う  │
│                            │
│ [OK] [キャンセル]          │
└────────────────────────────┘

ユーザー: OK クリック
```

#### ステップ 3: フィールドマッピング適用

```
FieldMappingMemory から該当マッピングを取得:

source_type: "delivery_note"
template_id: "template-cust001-v2.1"

マッピング内容:
{
  "customer_name": {
    "source_field": "customer_name",
    "target_cell": "A2",
    "transform": None
    ← 過去に修正されたか確認
  },
  "amount": {
    "source_field": "total_amount",
    "target_cell": "D10",
    "transform": "format_currency",
    ← ユーザーが前回追加した修正
  },
  "address": {
    "source_field": "customer_address",
    "target_cell": "A4",
    "transform": "clean_address",
    ← UserCorrectionMemory に記録あり
    "manual_correction_history": [
      {
        "corrected_to": "新住所",
        "correction_date": "2026-06-20",
        "count": 3
      }
    ]
  }
}

前回のユーザー修正を適用:
- "address" を前回の "新住所" に初期設定
- "amount" の通貨フォーマットは前回と同じ形式
```

#### ステップ 4: Excel ファイル生成

```
処理:
1. テンプレート (〇〇顧客向け請求書 v2.1) をロード
2. フィールドマッピングに従ってデータ投入
   A2: 〇〇株式会社
   D10: ¥50,000
   A4: (前回の修正住所)
3. Excelファイル生成
   - ファイル名: "請求書_〇〇_20260630.xlsx"
   - 出力先: /output/

Output:
┌────────────────────────────┐
│ 〇〇株式会社 様             │
│ 請求書                     │
│                            │
│ 日付: 2026-06-30          │
│ 金額: ¥50,000              │
│ 摘要: ネジ M8 100個        │
│                            │
│ (前回のユーザー修正も反映) │
└────────────────────────────┘
```

#### ステップ 5: ユーザー修正 (if any)

```
ユーザーが Excelを開いて修正:

修正内容:
- 金額を ¥51,000 に修正 (消費税計上忘れ)
- 摘要を "ネジ M8 100個 + 配送料" に修正

修正完了後、UI で:
┌─────────────────────────────┐
│ 修正を保存しますか？        │
│                            │
│ ☑ 次回以降もこの形式を    │
│   使用する                  │
│                            │
│ [保存] [破棄]              │
└─────────────────────────────┘

ユーザー: [保存] クリック
```

#### ステップ 6: Operational Memory へ保存

```python
# 1. UserCorrectionMemory に記録
correction = UserCorrection(
    source_output_id="output-20260630-001",
    corrections={
        "D10": {
            "original": 50000,
            "corrected": 51000,
            "reason": "tax_adjustment"
        },
        "A3": {
            "original": "ネジ M8 100個",
            "corrected": "ネジ M8 100個 + 配送料",
            "reason": "description_update"
        }
    }
)
correction_memory.save_correction(correction)

# 2. FieldMappingMemory を更新
mapping.used_count += 1
mapping.last_used_at = now()
if len(correction.corrections) == 0:
    mapping.accuracy_score += 0.01  # 修正なし = accuracy UP
else:
    mapping.accuracy_score -= 0.02  # 修正あり = accuracy DOWN
field_mapping_memory.update_mapping(mapping)

# 3. OutputHistoryMemory に記録
output = OutputHistory(
    template_id="template-cust001-v2.1",
    field_mapping_id=mapping.id,
    generated_data={...},
    user_corrections=[correction.id],
    generated_at=now(),
    was_sent=False
)
output_history_memory.save_output(output)

# 4. 改善提案を生成
recurring_patterns = user_correction_memory.find_recurring_corrections({
    "customer_id": "cust-001",
    "field": "amount",
    "correction_type": "tax_adjustment"
})

if len(recurring_patterns) >= 3:
    # 繰り返しパターンなら提案
    suggestion = {
        "type": "template_update",
        "message": "〇〇顧客への請求書は、いつも消費税を追加しています。テンプレートのデフォルト計算式を更新しませんか？",
        "suggested_change": "D10: =C10 * 1.1 (tax included)"
    }
    template_memory.suggest_update("template-cust001-v2.1", suggestion)
```

#### ステップ 7: 次タスクの推奨

```
ユーザーが次のタスクを依頼:

ユーザー: 「同じ〇〇顧客からの納品書がもう一件あります」

AI OS の対応:
1. OutputHistoryMemory から過去の出力を検索
2. 類似度計算:
   - 同じ顧客: ✓
   - 同じテンプレート使用: ✓
   - 類似度: 0.95

3. 推奨を提示:
┌────────────────────────────────┐
│ 効率化のご提案                 │
│                               │
│ 「前回と同じ流れでよろしい   │
│  でしょうか？」              │
│                               │
│ テンプレート: 〇〇顧客向け   │
│ 前回修正: ¥51,000 + 配送料   │
│                               │
│ [OK] [変更] [新規]            │
└────────────────────────────────┘
```

---

## 5. Business Rule 更新の承認フロー

### 5.1 承認フロー図

```
┌──────────────────────────┐
│ ① USER FEEDBACK          │
│ AI: monitor              │
│ Human: protect           │
│ (Reason: margin < 5%)    │
└────────┬─────────────────┘
         ↓
┌──────────────────────────┐
│ ② FEEDBACK QUEUE         │
│ Status: pending_analysis │
└────────┬─────────────────┘
         ↓
┌──────────────────────────────────┐
│ ③ AI LEARNING ENGINE             │
│ - Pattern matching: margin < 5%   │
│ - Evidence: 5+ user feedbacks     │
│ - Recommendation: focus='protect' │
│ - Confidence: 0.85                │
│ - Affected projects: 127          │
└────────┬─────────────────────────┘
         ↓
┌────────────────────────────────────────┐
│ ④ ADMIN REVIEW (MANDATORY)              │
│                                        │
│ Status: pending_admin_review           │
│                                        │
│ Admin: CEO / CTO / Finance Manager     │
│ - Review recommendation                │
│ - Analyze impact                       │
│ - Approve / Reject / Modify            │
│                                        │
│ [APPROVE]  [REJECT]  [MODIFY]         │
└────────┬───────────────────────────────┘
         ↓
    ┌────────────────┐
    │ ADMIN DECISION │
    └────┬───────────┘
         ├─→ APPROVED
         │   Status: approved
         │   Effective Date: 2026-07-01
         │   Rollback Plan: Keep previous v1.0
         │
         ├─→ REJECTED
         │   Status: rejected
         │   Reason: "Too aggressive change"
         │   Feedback: "Please wait for Q3 review"
         │
         └─→ MODIFIED
             Condition: margin < 5% AND customer_priority != 'vip'
             (VIP顧客は除外)
             Status: pending_reanalysis
             → 再度 ③ へ
         ↓ (APPROVED or MODIFIED passed)
┌──────────────────────────────┐
│ ⑤ RULE REPOSITORY UPDATE     │
│                              │
│ Previous: v1.0               │
│ New: v1.1                    │
│                              │
│ Rule content:                │
│ Condition: margin < 5%       │
│ Action: focus='protect'      │
│ Priority: 9                  │
│ Approved by: ceo@company.jp  │
│ Approved at: 2026-06-30      │
│ Effective: 2026-07-01        │
│                              │
│ Changelog:                   │
│ "Based on 5 user feedbacks"  │
│ "Affects 127 projects"       │
└────────┬─────────────────────┘
         ↓
┌──────────────────────────────┐
│ ⑥ DEPLOYMENT STRATEGY        │
│                              │
│ Option A: Immediate           │
│ → All new projects use v1.1   │
│                              │
│ Option B: Phased              │
│ → 10% pilot → 50% → 100%     │
│ → Monitor impact metrics      │
│                              │
│ Option C: A/B Test            │
│ → Half use v1.0, half v1.1   │
│ → Compare results             │
│                              │
│ Admin chooses: Phased (10%)   │
└────────┬─────────────────────┘
         ↓
┌──────────────────────────────┐
│ ⑦ BUSINESS RULES VERSION     │
│                              │
│ Rule Repository v1.1         │
│ Active users: 10%             │
│ Monitor metrics:              │
│ - AI decision changes         │
│ - User satisfaction           │
│ - Business impact             │
│                              │
│ If successful: → 50% → 100%   │
│ If negative: → ROLLBACK to v1.0
└────────┬─────────────────────┘
         ↓
┌──────────────────────────────┐
│ ⑧ NEXT AI DECISIONS          │
│ (Using Business Rule v1.1)    │
│                              │
│ For margin < 5% projects:    │
│ → focus changed to "protect" │
│                              │
│ Impact: 127 affected project │
│ Monthly actions: ~200 changed │
└──────────────────────────────┘
```

### 5.2 Approval Gate 要件

```python
@dataclass
class ApprovalGate:
    """AI による自動反映を絶対に許さない"""
    
    # ① AI は提案のみ
    can_ai_approve: bool = False      # ❌ NEVER
    can_ai_apply_directly: bool = False # ❌ NEVER
    
    # ② Admin 承認が必須
    requires_human_approval: bool = True
    approval_roles: list[str] = ["ceo", "cto", "finance_director"]
    min_approval_count: int = 1       # at least 1 admin
    
    # ③ 記録・監査
    audit_trail: bool = True          # Who approved, when, why
    version_control: bool = True      # Keep all versions
    rollback_capability: bool = True  # Can revert
    
    # ④ 透明性
    impact_analysis: bool = True      # Show affected projects
    changelog: bool = True             # Keep changelog
    
    # ⑤ 安全性
    canary_deployment: bool = True    # Test with small subset first
    gradual_rollout: bool = True      # Phased approach
    monitoring: bool = True           # Track metrics during rollout
```

---

## 6. 既存 Learning / Memory 構造との差分

### 現在 (Phase 3)

```
learning/
├── feedback.py (基本的なfeedback保存のみ)
├── improvements.py (improvement提案)
├── insights.py
└── query_log.py

memory/
├── retrieval_interface.py (stub実装)
├── store.py
└── context.py

data/
├── conversation/
├── memory/
└── validation/
```

**問題:**
- ❌ Governed vs Operational を区別していない
- ❌ Admin approval workflow がない
- ❌ Policy memory (Business Rule に関わる) がない
- ❌ Operational memory (作業効率化) がない
- ❌ Template/Mapping/Correction メモリがない

### 新しい設計 (Phase 4)

```
learning/
├── governed/
│   ├── feedback_queue.py          [新規]
│   ├── learning_engine.py         [新規]
│   ├── policy_recommendation.py   [新規]
│   └── approval_gate.py           [新規]
│
├── operational/
│   ├── document_pattern_memory.py [新規]
│   ├── template_memory.py         [新規]
│   ├── field_mapping_memory.py    [新規]
│   ├── user_correction_memory.py  [新規]
│   └── output_history_memory.py   [新規]
│
├── feedback.py (拡張)
├── improvements.py (modified)
├── insights.py
└── query_log.py

memory/
├── governed/
│   ├── policy_repository.py       [新規]
│   └── rule_versioning.py         [新規]
│
├── operational/
│   ├── template_store.py          [新規]
│   ├── mapping_store.py           [新規]
│   └── correction_store.py        [新規]
│
├── retrieval_interface.py (拡張)
├── store.py
└── context.py

data/
├── governed/
│   ├── feedback_queue.jsonl       [新規]
│   ├── policy_recommendations.jsonl [新規]
│   ├── approvals.jsonl            [新規]
│   └── rule_versions.jsonl        [新規]
│
├── operational/
│   ├── templates/                 [新規]
│   ├── mappings.jsonl             [新規]
│   ├── corrections.jsonl          [新規]
│   └── output_history.jsonl       [新規]
│
├── conversation/
├── memory/
└── validation/

backend/api/
├── governed_router.py             [新規]
├── operational_router.py          [新規]
└── router.py (existing)

backend/services/
├── governed_learning_service.py   [新規]
├── operational_learning_service.py [新規]
└── project_service.py (修正: Policy Memory 適用)
```

---

## 7. 最小実装案

### 🎯 推奨: **Operational Template Memory を先に実装**

#### 理由

```
1. 即座の実用価値
   ✓ 手作業を削減できる (今日から使える)
   ✓ ユーザーの作業効率向上 (UX improvement)
   ✗ Governed Learning は基盤工事的 (長期効果)

2. 実装の複雑性
   ✓ Operational は単純 (CRUD + マッチング)
   ✓ Governed は複雑 (Admin workflow + versioning)

3. リスク
   ✓ Operational は局所的 (個別テンプレート)
   ✗ Governed は全社的 (Business Rule変更)
   ✗ Governed は承認フロー未構築

4. フィードバック ループ
   ✓ Operational: ユーザーがすぐ反応 ("効率いい!")
   ✗ Governed: Admin承認待ち (遅い)

5. プロダクト開発サイクル
   - MVP 1: Template Memory (1週間)
     → 顧客実績作る
     → 満足度測定
   - MVP 2: Governed Learning (2週間)
     → Governance 構築
     → Admin 承認 workflow
```

### 実装戦略

#### **Phase 4a: Operational Template Memory MVP** (1週間)

**ファイル新規作成:**
```
learning/operational/
├── __init__.py
├── template_memory.py         (150 lines)
├── field_mapping_memory.py    (120 lines)
├── user_correction_memory.py  (100 lines)
└── output_history_memory.py   (80 lines)

backend/services/
├── operational_learning_service.py (200 lines)

backend/api/
├── operational_router.py      (150 lines)

tests/operational/
├── test_template_memory.py
├── test_field_mapping.py
└── test_user_correction.py
```

**API Endpoints:**
```
GET  /api/templates?document_type=invoice&customer_id=cust-001
POST /api/templates (save new template)
PUT  /api/templates/{id} (update)
DELETE /api/templates/{id}

GET  /api/mappings?source_type=delivery_note&template_id=...
POST /api/mappings

GET  /api/corrections?template_id=...
POST /api/corrections

GET  /api/outputs/recent?customer_id=...
GET  /api/outputs/{id}/reuse-suggestion
```

**最小テストケース:**
```python
def test_template_search():
    # 過去に使ったテンプレート検索
    
def test_field_mapping_apply():
    # データをマッピングに従ってExcelに投入
    
def test_user_correction_save():
    # ユーザー修正を記録
    
def test_next_task_suggestion():
    # 類似タスクで前のテンプレート提案
```

#### **Phase 4b: Governed Learning Queue** (2週間, その後)

**ファイル新規作成:**
```
learning/governed/
├── __init__.py
├── feedback_queue.py          (150 lines)
├── learning_engine.py         (250 lines)
├── policy_recommendation.py   (120 lines)
└── approval_gate.py           (180 lines)

memory/governed/
├── __init__.py
├── policy_repository.py       (150 lines)
└── rule_versioning.py         (100 lines)

backend/api/
├── governed_router.py         (200 lines)

tests/governed/
├── test_learning_engine.py
├── test_approval_gate.py
└── test_policy_repository.py
```

**Admin Portal (UI要件):**
```
GET  /api/governed/queue (admin dashboard)
POST /api/governed/approve/{recommendation_id}
GET  /api/governed/policies (version history)
GET  /api/governed/impact-analysis/{recommendation_id}
```

---

## 8. Git Status & Next Steps

```bash
$ git status
On branch main
Changes not staged for commit:
  LEARNING_LAYER_DESIGN.md (Phase 3)

Ready for:
  - LEARNING_LAYER_REDESIGN.md (this document)
  - Implementation planning
```

### 実装スケジュール案

```
Week 1 (Phase 4a):
└─ Operational Template Memory MVP
   ├─ Day 1-2: template_memory.py + field_mapping_memory.py
   ├─ Day 3: user_correction_memory.py + output_history_memory.py
   ├─ Day 4-5: operational_router.py + tests
   └─ Demo: ユーザーがテンプレート再利用

Week 2-3 (Phase 4b):
└─ Governed Learning Queue
   ├─ Day 6-8: learning_engine.py + pattern analysis
   ├─ Day 9-10: approval_gate.py + policy_recommendation.py
   ├─ Day 11-12: governed_router.py + admin portal UI
   └─ Demo: Admin が Business Rule 承認

Week 4:
└─ Integration & E2E Test
   ├─ Full user scenario testing
   ├─ Admin approval workflow testing
   └─ Performance optimization
```

### 成果物チェックリスト

- [ ] LEARNING_LAYER_REDESIGN.md (this document)
- [ ] Governed Learning flow diagram
- [ ] Operational Learning flow diagram
- [ ] Data model definitions (5 Operational Memory types)
- [ ] Use case: Excel invoice generation
- [ ] Approval gate requirements
- [ ] Implementation roadmap
- [ ] Git commit with design documents
