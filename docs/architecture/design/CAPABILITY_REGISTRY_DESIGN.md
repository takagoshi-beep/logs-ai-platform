# Capability Registry 設計書：AI OS の第二の軸


<!-- SNAPSHOT-BANNER -->
> **📌 Point-in-time snapshot.** This document records the state of the
> project as of the date/phase named in its title or body. It has not been
> updated since, and may not reflect the current code. Verify claims against
> the current source before relying on them. For the maintained, current
> architecture reference, see `docs/architecture.md` and `docs/system_manifest.md`.

**日付:** 2026-06-30  
**バージョン:** 1.0  
**ステータス:** 設計完了

---

## 0. 概念図：2軸の AI OS

```
                     AI OS Architecture
                     
        Axis 1: Project Understanding     Axis 2: Business Execution
        (案件を理解する)               (仕事を実行する能力)
        
        Project
          ↓
        Events
          ↓
        State
          ↓
        Goal                          ←────────→  Capability Registry
          ↓                                             ↓
        Decision                                   Proposal Generation
          ↓                                        Invoice Generation
        Action                                     Quotation Generation
          ↓                                        Customer Analysis
        Output                                     Gross Profit Analysis
                                                   ...
        
        これら2軸が交差する場所で、
        「どう判断して、どう実行するか」が決まる
```

---

## 1. Capability Domain Model

### 1.1 Capability Dataclass

```python
@dataclass
class Capability:
    """業務能力を表現するドメインモデル"""
    
    # Identity
    capability_id: str                    # "cap-proposal-gen-001"
    name: str                             # "Proposal Generation"
    
    # Categorization
    category: str                         # "document_generation"
    description: str
    owner_team: str                       # "sales" / "finance" / "marketing"
    owner_user_id: str | None
    
    # Lifecycle
    status: CapabilityStatus              # design/implemented/testing/deployed/deprecated
    version: str                          # "1.0", "1.1", "2.0"
    created_at: datetime
    updated_at: datetime
    
    # Capability Definition
    supported_inputs: list[str]           # ["project_id", "customer_name", "past_sales"]
    supported_outputs: list[str]          # ["proposal_outline", "powerpoint", "pdf"]
    required_context: list[str]           # ["company_domain", "industry_knowledge"]
    
    # Dependencies & Resources
    dependencies: list[str]               # ["cap-customer-analysis", "cap-market-research"]
    templates: list[str]                  # [template_id_1, template_id_2, ...]
    mappings: list[str]                   # [field_mapping_id_1, ...]
    operational_memory: dict              # {
                                          #   "template_memory": "mem-id",
                                          #   "field_mapping_memory": "mem-id",
                                          #   "correction_memory": "mem-id",
                                          #   "output_history": "mem-id"
                                          # }
    
    # Performance Metrics
    success_rate: float                   # 0.0-1.0
    correction_rate: float                # avg corrections needed
    confidence: float                     # 0.0-1.0 (reliability)
    avg_execution_time_seconds: float
    user_satisfaction: float              # 1-5 (avg rating)
    
    # Operational Tracking
    last_used_at: datetime
    last_improved_at: datetime
    execution_count: int = 0
    success_count: int = 0
    
    # Governance & Control
    governance_level: GovernanceLevel     # low/medium/high/admin_approved_required
    team_id: str | None
    
    # Audit Trail
    trace_id: str                         # deterministic trace for capability lifecycle

class CapabilityStatus(str, Enum):
    DESIGN = "design"                     # 設計中
    IMPLEMENTED = "implemented"           # 実装完了
    TESTING = "testing"                   # テスト中
    DEPLOYED = "deployed"                 # 本番運用中
    DEPRECATED = "deprecated"             # 廃止予定

class GovernanceLevel(str, Enum):
    LOW = "low"                           # Email Draft, Meeting Summary
    MEDIUM = "medium"                     # Proposal/Invoice/Quotation Generation
    HIGH = "high"                         # 分析、スコアリング
    ADMIN_APPROVED = "admin_approved_required"  # 全社テンプレート、財務
```

### 1.2 Capability Metrics

```python
@dataclass
class CapabilityMetrics:
    """Capability の性能指標"""
    capability_id: str
    
    # Execution Stats
    execution_count: int
    success_count: int
    error_count: int
    skipped_count: int
    
    # Performance
    avg_execution_time_seconds: float
    min_execution_time_seconds: float
    max_execution_time_seconds: float
    
    # Quality
    success_rate: float                   # success_count / execution_count
    error_rate: float
    
    # User Feedback
    user_satisfaction: float              # 1-5 average
    satisfaction_count: int               # how many ratings
    
    # Operational Learning
    templates_used_count: int
    corrections_required_avg: float       # avg corrections per execution
    
    # Memory
    memory_accessed_count: int
    memory_updated_count: int
    
    # Last Updated
    last_updated_at: datetime
```

### 1.3 Capability Execution (実行履歴)

```python
@dataclass
class CapabilityExecution:
    """Capability の個別実行記録"""
    execution_id: str                     # "exec-20260630-001"
    capability_id: str
    project_id: str
    action_id: str                        # which action triggered this
    user_id: str
    
    # Input & Output
    inputs: dict                          # {"customer": "...", "sales": ...}
    outputs: dict                         # {"proposal": "...", "pdf": "..."}
    
    # Execution Details
    status: ExecutionStatus               # running/completed/failed/skipped
    execution_time_seconds: float
    error_message: str | None
    
    # Memory Management
    memory_accessed: list[str]            # memory_ids that were read
    memory_updated: list[str]             # memory_ids that were written
    
    # User Feedback
    user_feedback: str | None             # "Good quality", "Needs revision", ...
    user_rating: int | None               # 1-5
    
    # Audit
    trace_id: str
    created_at: datetime
    completed_at: datetime | None
    
    def to_trace_entry(self) -> dict:
        """Debug trace への出力用"""
        return {
            "execution_id": self.execution_id,
            "capability_id": self.capability_id,
            "capability_version": ...,  # from registry
            "project_id": self.project_id,
            "action_id": self.action_id,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "status": self.status.value,
            "execution_time": self.execution_time_seconds,
            "memory_accessed": self.memory_accessed,
            "memory_updated": self.memory_updated,
            "confidence": ...,  # from capability metrics
            "trace_id": self.trace_id,
        }

class ExecutionStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
```

---

## 2. Capability Registry 設計

### 2.1 Registry 構造

```python
class CapabilityRegistry:
    """全 Capability を管理するシングルトン"""
    
    def __init__(self):
        self._capabilities: dict[str, Capability] = {}
        self._metrics: dict[str, CapabilityMetrics] = {}
        self._executions: list[CapabilityExecution] = []
        self._execution_queue: list[CapabilityExecution] = []
    
    # ========== DISCOVERY & RETRIEVAL ==========
    
    def list_capabilities(
        self,
        category: str | None = None,
        status: CapabilityStatus | None = None,
        governance_level: GovernanceLevel | None = None,
        team_id: str | None = None,
    ) -> list[Capability]:
        """
        利用可能な Capability を一覧取得
        
        filters:
        - category: "document_generation" など
        - status: deployed のみ など
        - governance_level: low まで など
        - team_id: 特定チームの capability
        """
    
    def get_capability(self, capability_id: str) -> Capability | None:
        """Capability を ID で取得"""
    
    def search_capabilities(
        self,
        supported_inputs: list[str] | None = None,
        supported_outputs: list[str] | None = None,
    ) -> list[Capability]:
        """
        入出力形式で Capability を検索
        
        例:
        search_capabilities(
            supported_inputs=["delivery_note", "amount"],
            supported_outputs=["excel_invoice"]
        )
        → [Invoice Generation capability]
        """
    
    # ========== RECOMMENDATION ==========
    
    def recommend_capability(
        self,
        project_context: dict,      # project data
        user_request: str,          # "提案書を作成して"
        user_id: str | None = None,
    ) -> tuple[Capability, float] | None:
        """
        Project context と user request から
        最適な Capability を推奨
        
        推奨スコア計算:
        - capability_success_rate (40%)
        - user_recent_usage (30%)
        - context_match (20%)
        - governance_level (10%)
        
        returns: (Capability, confidence_score: 0-1.0)
        """
    
    # ========== LIFECYCLE MANAGEMENT ==========
    
    def register_capability(
        self,
        capability: Capability,
    ) -> str:
        """新しい Capability を登録"""
    
    def update_capability(
        self,
        capability: Capability,
        updated_by: str,
        change_reason: str,
    ) -> None:
        """Capability の情報を更新"""
    
    def promote_capability(
        self,
        capability_id: str,
        new_status: CapabilityStatus,
        approved_by: str,  # who approved
    ) -> None:
        """Capability を次のステージへ昇格"""
    
    def deprecate_capability(
        self,
        capability_id: str,
        replacement_id: str | None = None,
        reason: str = "",
    ) -> None:
        """Capability を廃止"""
    
    # ========== EXECUTION & FEEDBACK ==========
    
    def execute_capability(
        self,
        capability_id: str,
        project_id: str,
        action_id: str,
        user_id: str,
        inputs: dict,
    ) -> CapabilityExecution:
        """Capability を実行して記録"""
    
    def record_execution_result(
        self,
        execution_id: str,
        outputs: dict,
        status: ExecutionStatus = ExecutionStatus.COMPLETED,
        error_message: str | None = None,
        execution_time_seconds: float = 0.0,
    ) -> None:
        """実行結果を記録"""
    
    def record_user_feedback(
        self,
        execution_id: str,
        feedback: str,
        rating: int,  # 1-5
    ) -> None:
        """ユーザーフィードバックを記録"""
    
    # ========== MEMORY MANAGEMENT ==========
    
    def update_memory(
        self,
        execution_id: str,
        memory_accessed: list[str],
        memory_updated: list[str],
    ) -> None:
        """実行時に使用・更新したメモリを記録"""
    
    def get_capability_memory(
        self,
        capability_id: str,
        memory_type: str,  # "template", "mapping", "correction"
    ) -> dict:
        """Capability が使用するメモリを取得"""
    
    # ========== METRICS & ANALYTICS ==========
    
    def get_metrics(self, capability_id: str) -> CapabilityMetrics:
        """Capability の性能指標を取得"""
    
    def get_execution_history(
        self,
        capability_id: str,
        limit: int = 100,
        project_id: str | None = None,
        user_id: str | None = None,
    ) -> list[CapabilityExecution]:
        """実行履歴を取得"""
    
    def get_success_rate_trend(
        self,
        capability_id: str,
        days: int = 30,
    ) -> list[tuple[datetime, float]]:
        """成功率の推移を取得"""
    
    # ========== UTILITY ==========
    
    def validate_capability(self, capability: Capability) -> list[str]:
        """Capability の妥当性を検証 (error list)"""
    
    def get_capability_dependencies(
        self,
        capability_id: str,
        recursive: bool = True,
    ) -> list[str]:
        """Capability の依存関係を取得"""
```

---

## 3. Capability Lifecycle

### 3.1 ライフサイクル図

```
┌──────────┐
│  DESIGN  │
└────┬─────┘
     │ Owner: Product Team
     │ Actions: Define inputs, outputs, templates
     │ Approval: Team lead review
     │ Memory: Design notes, requirements
     │ Trace: design_trace_id_001
     ↓
┌──────────────┐
│ IMPLEMENTED  │
└────┬─────────┘
     │ Owner: Development Team
     │ Actions: Code, integrate, test locally
     │ Approval: Code review + tests pass
     │ Memory: Implementation notes, version v1.0
     │ Trace: impl_trace_id_001
     ↓
┌──────────┐
│  TESTING │
└────┬─────┘
     │ Owner: QA Team
     │ Actions: 
     │   - Unit tests (test coverage >= 80%)
     │   - Integration tests (with Projects)
     │   - User acceptance tests
     │   - Template validation
     │   - Memory consistency checks
     │ Approval: QA sign-off + test reports
     │ Memory: Test results, edge cases discovered
     │ Trace: test_trace_id_001
     ↓
┌──────────┐
│ DEPLOYED │
└────┬─────┘
     │ Owner: Operations Team
     │ Actions:
     │   - Publish to Production
     │   - Enable in Capability Registry
     │   - Create monitoring dashboards
     │   - Set up logging
     │   - Document for users
     │ Approval: Deployment approval (low gov) OR Admin approval (high gov)
     │ Memory: Deployment checklist, version v1.0 deployed
     │ Trace: deploy_trace_id_001
     ├─→ Active phase
     │   - Monitor success_rate, execution_time
     │   - Collect user feedback
     │   - Update memory dynamically
     │   - Improve templates based on usage
     ↓
┌──────────┐
│ IMPROVED │
└────┬─────┘
     │ Owner: Product / Operations
     │ Actions:
     │   - Analyze usage patterns
     │   - Identify improvement opportunities
     │   - Update templates/mappings (auto)
     │   - Improve success_rate
     │ Memory: Usage analytics, correction patterns
     │ Trace: improve_trace_id_001
     ↓
┌──────────────┐
│ VERSION UP   │
└────┬─────────┘
     │ Owner: Development
     │ Actions: Increment version (1.0 → 1.1)
     │ Approval: Code review (if logic changes)
     │ Memory: Changelog, version history
     │ Trace: version_trace_id_001
     ├─→ Redeploy as 1.1 (same process as DEPLOYED)
     │
     ├─→ Option A: Replace old version (breaking)
     │   - All new executions use v1.1
     │
     ├─→ Option B: Parallel (non-breaking)
     │   - 90% use v1.0, 10% use v1.1 (A/B test)
     │   - Monitor metrics
     │   - Gradually shift traffic
     │
     ↓ (when no longer needed)
┌──────────────┐
│ DEPRECATED   │
└──────────────┘
     │ Owner: Product
     │ Actions:
     │   - Announce deprecation (2 weeks notice)
     │   - Migrate users to replacement
     │   - Stop new executions after date
     │   - Archive execution history
     │ Approval: Management approval
     │ Memory: Deprecation notes, replacement_id
     │ Trace: deprecate_trace_id_001
     │
     └─→ Final: Archive in version history
         (可能ならば復旧できるように保管)
```

### 3.2 各ステージの詳細

#### DESIGN ステージ

```python
@dataclass
class DesignApproval:
    approved_by: str                      # team_lead_id
    requirements_checklist: dict          # {
                                          #   "inputs_defined": bool,
                                          #   "outputs_defined": bool,
                                          #   "templates_planned": bool,
                                          #   "mappings_planned": bool,
                                          #   "governance_level_defined": bool
                                          # }
    approved_at: datetime
    design_document_id: str
```

#### TESTING ステージ

```python
@dataclass
class TestingApproval:
    qa_lead: str
    
    test_results: dict                    # {
                                          #   "unit_tests": {"passed": 50, "failed": 0},
                                          #   "integration_tests": {"passed": 20, "failed": 0},
                                          #   "user_acceptance": {"passed": 5, "failed": 0}
                                          # }
    
    test_coverage: float                  # 0.0-1.0 (code coverage)
    known_issues: list[str]
    
    approved_at: datetime
    test_report_id: str
```

#### DEPLOYED ステージ

```python
@dataclass
class DeploymentApproval:
    approved_by: str
    deployment_checklist: dict            # {
                                          #   "monitoring_setup": bool,
                                          #   "logging_enabled": bool,
                                          #   "documentation": bool,
                                          #   "rollback_plan": bool
                                          # }
    
    deployment_time: datetime
    rollback_plan_id: str
    
    # Monitoring config
    alert_thresholds: dict                # {
                                          #   "success_rate": 0.85,
                                          #   "error_rate": 0.15,
                                          #   "avg_time": 5.0
                                          # }
```

---

## 4. Capability Memory 設計

### 4.1 メモリの5層構造

```
Capability → TemplateMemory
            → FieldMappingMemory
            → DocumentPatternMemory
            → UserCorrectionMemory
            → OutputHistoryMemory
            → ExecutionHistoryMemory
            → ValidationMemory
```

### 4.2 各メモリのスキーマ

#### A. TemplateMemory

```python
@dataclass
class CapabilityTemplate:
    template_id: str
    capability_id: str
    
    # Template content
    name: str                             # "Proposal Template - Tech Sector v2.1"
    template_type: str                    # "powerpoint" / "excel" / "document"
    file_path: str
    
    # Scope & Usage
    scope: str                            # "user" / "team" / "company"
    user_id: str | None
    team_id: str | None
    customer_id: str | None               # if customer-specific
    
    # Statistics
    used_count: int
    success_count: int
    user_rating: float                    # 1-5 average
    last_used_at: datetime
    
    # Version
    version: str
    is_active: bool
    confidence: float                     # 0-1.0
    
    # Traceability
    source_trace_id: str                  # which execution created/updated this
    created_at: datetime
```

#### B. FieldMappingMemory

```python
@dataclass
class CapabilityFieldMapping:
    mapping_id: str
    capability_id: str
    
    # Mapping definition
    source_type: str                      # "delivery_note" / "customer_data"
    target_type: str                      # "invoice_template" / "proposal_slide"
    
    field_mappings: dict[str, dict]       # {
                                          #   "customer_name": {
                                          #     "source": "customer_name_field",
                                          #     "target": "A2",
                                          #     "transform": "clean_name"
                                          #   }
                                          # }
    
    # Scope
    scope: str                            # "user" / "team" / "company"
    user_id: str | None
    team_id: str | None
    
    # Quality
    accuracy: float                       # how often correct
    used_count: int
    last_used_at: datetime
    
    # Traceability
    source_trace_id: str
    version: str
    confidence: float
```

#### C. DocumentPatternMemory

```python
@dataclass
class DocumentPattern:
    pattern_id: str
    capability_id: str
    
    # Pattern recognition
    document_type: str                    # "invoice" / "delivery_note"
    recognition_keywords: list[str]
    field_patterns: dict                  # regex patterns for fields
    
    # Extraction rules
    extraction_rules: dict
    
    # Statistics
    accuracy: float
    recognition_count: int
    last_used_at: datetime
    
    # Scope
    scope: str
    user_id: str | None
    
    # Traceability
    source_trace_id: str
    version: str
    confidence: float
```

#### D. UserCorrectionMemory

```python
@dataclass
class CapabilityCorrection:
    correction_id: str
    capability_id: str
    
    # Correction context
    source_execution_id: str
    template_id: str
    mapping_id: str
    
    # What was corrected
    corrections: dict[str, dict]          # {
                                          #   "A2": {
                                          #     "original": "Old Address",
                                          #     "corrected": "New Address",
                                          #     "reason": "address_update"
                                          #   }
                                          # }
    
    # User & Team
    user_id: str
    team_id: str
    
    # Pattern analysis
    is_recurring: bool
    recurring_count: int                  # how many times corrected same way
    
    # Scope
    scope: str                            # "user" / "team" / "company"
    
    # Traceability
    source_trace_id: str
    created_at: datetime
    confidence: float
```

#### E. OutputHistoryMemory

```python
@dataclass
class CapabilityOutput:
    output_id: str
    capability_id: str
    
    # Generation context
    project_id: str
    customer_id: str | None
    execution_id: str
    
    # Output
    output_filename: str
    output_format: str                    # "pdf" / "xlsx" / "pptx"
    file_path: str
    file_size: int
    
    # Metadata
    generated_at: datetime
    user_id: str
    template_used_id: str
    
    # Quality
    was_used: bool                        # did user actually use it?
    was_sent: bool                        # was it sent to customer?
    user_satisfied: bool | None           # did user accept it?
    
    # Reusability
    similar_projects: list[str]           # which other projects could reuse this?
    
    # Traceability
    source_trace_id: str
    confidence: float
```

#### F. ExecutionHistoryMemory

```python
@dataclass
class ExecutionHistory:
    execution_id: str
    capability_id: str
    project_id: str
    
    # Full execution record
    inputs: dict
    outputs: dict
    status: ExecutionStatus
    
    # Performance
    execution_time_seconds: float
    success: bool
    
    # Memory impact
    memory_accessed: list[str]
    memory_created: list[str]
    
    # User feedback
    user_satisfaction: float | None
    user_feedback: str | None
    
    # Traceability
    source_trace_id: str
    created_at: datetime
    user_id: str
```

#### G. ValidationMemory

```python
@dataclass
class ValidationRecord:
    validation_id: str
    capability_id: str
    
    # What was validated
    template_id: str | None
    mapping_id: str | None
    
    # Validation result
    is_valid: bool
    validation_errors: list[str]
    validation_warnings: list[str]
    
    # Context
    validation_context: dict
    
    # Traceability
    source_trace_id: str
    validated_at: datetime
    validated_by: str
    confidence: float
```

---

## 5. Capability Learning 設計

### 5.1 自動更新可能な項目

```python
class AutoLearningCapability:
    """自動的に改善される項目"""
    
    # ✅ 自動更新 OK
    template_priority: dict               # テンプレートの推奨順序
    # 例: 過去50回の実行で template_A が49回使われた
    #      → priority を上げて次回は最初に提案
    
    field_mapping_weights: dict           # マッピングの信頼度
    # 例: customer_name → A2 のマッピングが100回中98回成功
    #      → accuracy 0.98 に上昇
    
    customer_template_preference: dict    # 顧客別テンプレート選好
    # 例: customer_X は常に template_B を選ぶ
    #      → 次回は template_B を第一推奨に
    
    success_rate: float                   # 成功率の計算
    # 成功回数 / 実行回数 で自動計算
    
    correction_rate: float                # 修正率の計算
    # ユーザー修正が必要だった回数 / 実行回数
    
    confidence: float                     # 信頼度の計算
    # (success_rate * 0.5) + (1 - correction_rate) * 0.3) + (user_rating / 5 * 0.2)
    
    avg_execution_time: float             # 実行時間の平均
    # 前回実行時間 / 100回平均 で自動更新
    
    execution_count: int                  # 実行回数の更新
    
    user_satisfaction: float              # ユーザー満足度
    # 既存 rating + 新規 feedback の加重平均
```

### 5.2 管理者承認が必要な項目

```python
class GovernedLearningCapability:
    """管理者承認が必要な学習"""
    
    # ❌ AI は勝手に変更しない（Governed Learning）
    
    business_rule_logic: str              # 計算ロジック
    # 例: 「粗利計算式を A * B / (A + B) から A * B に変更」
    # → Admin approval 必須
    
    health_score_weight: dict             # Health スコアの重み
    # 例: 「粗利ペナルティを -25 から -40 に増加」
    # → Admin approval 必須（全社の判断基準変更）
    
    risk_score_calculation: str           # リスク計算ロジック
    # → Admin approval 必須
    
    company_template_promotion: bool      # 個人テンプレートを全社化
    # 例: user_X の template を company template に昇格
    # → Admin approval 必須（全社に影響）
    
    governance_level_upgrade: GovernanceLevel # ガバナンスレベルの昇格
    # 例: low → medium / medium → high
    # → Admin approval 必須
    
    output_format_change: bool            # 出力形式の変更
    # 例: PDF のみ → PDF + Word に変更
    # → 顧客向け正式資料なら Admin approval 必須
    
    dependency_change: list[str]          # 依存 capability の変更
    # 例: Proposal Generation が新しい Analysis Tool に依存するように
    # → Admin approval 必須（他の capability に影響）
```

### 5.3 Learning Flow

```
Capability Execution
    ↓
User Correction / Feedback 記録
    ↓
AutoLearningEngine が分析
    ├─ Success rate 更新
    ├─ Correction rate 更新
    ├─ Template priority 再計算
    ├─ FieldMapping accuracy 更新
    └─ Confidence スコア更新
    ↓ (自動反映)
    
Capability Memory Updated
    └─ 次回実行で自動適用
    
    ↓ (if significant improvement detected)
    
RecommendedImprovement
    ├─ Template を全社化？
    ├─ Governance level を上げる？
    ├─ Business rule を変更する？
    └─ 新しいバージョンをリリース？
    
    ↓
Admin Review Queue
    └─ if governance_level >= MEDIUM
        Admin が approve → Deployed
```

---

## 6. Capability Governance 設計

### 6.1 ガバナンスマトリックス

```
Low Governance
├─ Email Draft
│  └─ Template + Mapping 自動学習 OK
│     Memory 自動更新 OK
│     User 削除可能 OK
│
├─ Meeting Summary
│  └─ User 각각다른 스타일 OK
│
└─ Personal Template
   └─ 個人のみ利用
      他人との共有は Optional

Medium Governance
├─ Proposal Generation
│  ├─ Success rate が 90%未満 → warn
│  ├─ 全社 Template 昇格 → Admin approval 필수
│  └─ Business rule 변경 → Admin approval 필수
│
├─ Invoice Generation
│  ├─ 財무計算 → Audit trail 필수
│  └─ 出力フォーマット変更 → Admin approval 필수
│
└─ Quotation Generation
   └─ 顧客価格 공개 전 검토 필수

High Governance
├─ Gross Profit Analysis
│  ├─ 계산 로직 변경 → Admin + Finance approval
│  └─ 결과 발표 → Management sign-off 필수
│
├─ Health / Risk / Opportunity Scoring
│  └─ Weight 변경 → Admin approval 필수
│     (전사 판단 기준 변경)
│
└─ Business Rule Update
   └─ AI 추천 → Admin Review Queue
      → Admin 의사결정
      → Approval 후 반영

Admin Approved Required
├─ 全社テンプレート
│  └─ 顧客向け정式 자료 format
│     財務 보고서 format
│
├─ 財務計算ロジック
│  └─ 粗利 計算式
│     税金 計算
│     割引 규칙
│
└─ Policy Memory 反映
   └─ 新しい Business Rule 적용
      全프로젝트에 影響
```

### 6.2 Approval Matrix (누가 승인?)

```
┌─────────────────────┬──────────────┬───────────────┬──────────────┐
│ Capability Action   │ Low Gov      │ Medium Gov    │ High/Admin   │
├─────────────────────┼──────────────┼───────────────┼──────────────┤
│ 自動 Template 更新   │ Auto OK      │ Auto OK       │ Admin review │
│ 自動 Mapping 更新    │ Auto OK      │ Auto OK       │ Admin review │
│ 自動 success_rate   │ Auto OK      │ Auto OK       │ Auto OK      │
│                     │              │               │              │
│ Template 昇格       │ Auto OK      │ Team lead     │ Admin        │
│ Business Logic 変更 │ Not allowed  │ Admin         │ Admin+Exec   │
│ Output Format 変更   │ User OK      │ Team lead     │ Admin        │
│ Governance UP       │ Not allowed  │ Admin         │ Admin        │
│ 全社テンプレート化  │ Auto OK      │ Admin         │ Admin+Legal  │
└─────────────────────┴──────────────┴───────────────┴──────────────┘
```

---

## 7. Project Aggregate との接続設計

### 7.1 接続フロー

```
Project
  ├─ Events
  │   └─ Project state change
  │
  ├─ State
  │   └─ "delivery_completed"
  │
  ├─ Goal
  │   └─ "generate_invoice"
  │
  ├─ Decision
  │   └─ "create_invoice"
  │       (AI decision)
  │
  └─ Action
      └─ action_id: "act-invoice-001"
         action_type: "document_generation"
         title: "Invoice Generation"
         description: "Generate invoice for completed delivery"
         
         ↓ (new field)
         required_capability: "cap-invoice-gen-v1.0"
         
         ↓
         CapabilityRegistry.recommend_capability(
             project_context={
                 "state": "delivery_completed",
                 "goal": "generate_invoice",
                 "customer": "customer_X",
                 "delivery_date": "2026-06-30",
                 "amount": "¥50,000"
             },
             user_request="この納品書に基づいて伝票をExcelで発行して"
         )
         
         ↓
         Capability Recommended:
         cap-invoice-gen-v1.0 (confidence: 0.92)
         
         ↓
         CapabilityRegistry.execute_capability(
             capability_id="cap-invoice-gen-v1.0",
             project_id="proj-001",
             action_id="act-invoice-001",
             user_id="user-123",
             inputs={
                 "delivery_note": <pdf>,
                 "customer": "customer_X",
                 "amount": 50000
             }
         )
         
         ↓
         Capability Execution
         ├─ Retrieve TemplateMemory (InvoiceTemplate v2.1)
         ├─ Retrieve FieldMappingMemory
         ├─ Apply DocumentPatternMemory
         ├─ Generate Excel
         ├─ Return output
         │
         └─ memory_updated:
             ├─ OutputHistoryMemory
             ├─ ExecutionHistoryMemory
             └─ (if user correction)
                 ├─ UserCorrectionMemory
                 ├─ FieldMappingMemory
                 └─ TemplateMemory (priority update)
         
         ↓
         Output saved to:
         ├─ Project Documents
         ├─ Conversation (trace)
         ├─ Action result
         └─ Debug Trace
```

### 7.2 ProjectAggregate に追加する フィールド

```python
@dataclass
class ProjectAggregate:
    # ... 既存フィールド ...
    
    # 新規フィールド: Capability との関連
    capabilities_used: list[str]          # [cap_id_1, cap_id_2]
    capability_executions: list[dict]     # [
                                          #   {
                                          #     "execution_id": "...",
                                          #     "capability_id": "...",
                                          #     "action_id": "...",
                                          #     "status": "completed"
                                          #   }
                                          # ]
    
    def get_required_capability(self) -> str | None:
        """
        Project の現在の State/Goal/Decision から
        必要な Capability を推定
        """
        
    def execute_capability(self, capability_id: str, inputs: dict) -> dict:
        """
        指定された Capability を実行して結果を Project に反映
        """
```

---

## 8. 初期 Capability 設計

### 8.1 Proposal Generation

```python
class ProposalGenerationCapability(Capability):
    """提案資料を生成する能力"""
    
    capability_id = "cap-proposal-gen-v1.0"
    name = "Proposal Generation"
    category = "document_generation"
    owner_team = "sales"
    
    supported_inputs = [
        "project_id",
        "customer_name",
        "customer_industry",
        "product",
        "sales_amount",
        "gross_profit_rate",
        "project_context",
        "user_instruction",
        "past_proposals"  # 過去の提案資料
    ]
    
    supported_outputs = [
        "proposal_outline",     # テキスト概要
        "powerpoint",          # .pptx
        "pdf",                 # .pdf
        "talking_points",      # 営業トーク用メモ
        "summary"              # 要約ドキュメント
    ]
    
    dependencies = [
        "cap-customer-analysis",
        "cap-market-research",
        "cap-financial-analysis"
    ]
    
    operational_memory = {
        "template_memory": "mem-proposal-templates",
        "field_mapping_memory": "mem-proposal-mappings",
        "document_pattern_memory": "mem-proposal-patterns",
        "user_correction_memory": "mem-proposal-corrections",
        "output_history_memory": "mem-proposal-outputs"
    }
    
    governance_level = GovernanceLevel.MEDIUM
    
    def execute(
        self,
        project_id: str,
        customer_name: str,
        product: str,
        sales_amount: float,
        gross_profit_rate: float,
        user_instruction: str,
    ) -> dict:
        """
        実装フロー:
        1. Customer Analysis から顧客特性を取得
        2. ProposalTemplateMemory から候補テンプレートを検索
           - industry 別
           - sales_amount 別
           - customer_priority 別
           - user の過去使用テンプレート
        3. ユーザーに提案
        4. テンプレート選択後、FieldMapping を適用
        5. PowerPoint を生成
        6. PDF を生成
        7. 修正を受け取る
        8. Memory を更新
        """
        return {
            "powerpoint": "<file_path>",
            "pdf": "<file_path>",
            "talking_points": "<text>",
            "summary": "<text>"
        }
```

### 8.2 Invoice Generation

```python
class InvoiceGenerationCapability(Capability):
    """請求書/伝票を生成する能力"""
    
    capability_id = "cap-invoice-gen-v1.0"
    name = "Invoice Generation"
    category = "document_generation"
    owner_team = "finance"
    
    supported_inputs = [
        "delivery_note",       # 納品書PDF/画像
        "project_id",
        "customer_id",
        "sales_lines",         # 売上明細
        "delivery_date",
        "amount",
        "tax_rate",
        "user_instruction"
    ]
    
    supported_outputs = [
        "excel_invoice",       # .xlsx
        "pdf_invoice",         # .pdf
        "issue_log",           # 発行記録
        "proof_of_output"      # 出力証跡
    ]
    
    dependencies = []  # 単独実行可能
    
    operational_memory = {
        "template_memory": "mem-invoice-templates",
        "field_mapping_memory": "mem-invoice-mappings",
        "document_pattern_memory": "mem-invoice-patterns",
        "user_correction_memory": "mem-invoice-corrections",
        "output_history_memory": "mem-invoice-outputs"
    }
    
    governance_level = GovernanceLevel.MEDIUM
    
    def execute(
        self,
        delivery_note: bytes,  # PDF
        customer_id: str,
        sales_lines: list[dict],
        amount: float,
    ) -> dict:
        """
        実装フロー:
        1. DocumentPatternMemory で納品書タイプ判定
        2. OCR で顧客・案件・金額抽出
        3. InvoiceTemplateMemory から候補検索
           - customer_id 別
           - sales_amount 別
           - team 別
        4. FieldMapping 適用
        5. Excel 生成
        6. PDF 生成
        7. ユーザー修正受け取り
        8. Memory 更新 (修正パターン認識)
        """
        return {
            "excel_invoice": "<file_path>",
            "pdf_invoice": "<file_path>",
            "issue_log": {...},
            "proof_of_output": "<timestamp_signature>"
        }
```

---

## 9. Capability Pack 将来構想

### 9.1 Pack Definition

```python
@dataclass
class CapabilityPack:
    """複数 Capability の集合パッケージ"""
    pack_id: str
    name: str
    description: str
    capabilities: list[str]               # capability_ids
    
    # 利用可能な企業/部門
    target_organization: str              # "oem", "sales", "finance"
    
    # 前提条件
    prerequisites: list[str]              # ["cap-customer-analysis"]
    
    # Pack 内 Capability の実行順序
    workflow: dict                        # {
                                          #   "step1": "cap-proposal-gen",
                                          #   "step2": "cap-quotation-gen",
                                          #   "step3": "cap-invoice-gen"
                                          # }
    
    # 統計
    adoption_rate: float
    success_rate: float
    team_count: int
    
    # Governance
    governance_level: GovernanceLevel
    
    version: str
    released_at: datetime
```

### 9.2 OEM Pack (例)

```
OEM Pack v1.0
├─ Proposal Generation
│  └─ Input: Project, Customer, Product
│     Output: PowerPoint Proposal
│
├─ Quotation Generation
│  └─ Input: Proposal acceptance
│     Output: Excel Quote
│
├─ Invoice Generation
│  └─ Input: Delivery confirmation
│     Output: Excel Invoice + PDF
│
├─ Purchase Order Generation
│  └─ Input: Customer demand forecast
│     Output: Excel PO (to supplier)
│
├─ Specification Translation
│  └─ Input: Customer request (Japanese)
│     Output: Technical specification (English)
│
├─ Inspection Report Generation
│  └─ Input: Quality check results
│     Output: PDF Report
│
└─ Shipment Tracking
   └─ Input: Invoice, shipment data
      Output: Tracking notification

Workflow:
Customer Request
  ↓
Proposal Generation
  ↓ (customer accepts)
Quotation Generation
  ↓ (customer orders)
Purchase Order Generation (to supplier)
  ↓ (goods arrive)
Specification Translation
  ↓ (goods delivered to customer)
Invoice Generation + Shipment Tracking
  ↓ (inspection)
Inspection Report Generation
```

### 9.3 Creative Pack (例)

```
Creative Pack v1.0
├─ Proposal Generation
│  └─ Creative theme + design
│
├─ Mood Board Generation
│  └─ Reference images collection
│
├─ Brand Analysis
│  └─ Competitor + market analysis
│
└─ Presentation Generation
   └─ Visual design + storytelling
```

### 9.4 Finance Pack (例)

```
Finance Pack v1.0
├─ Gross Profit Analysis
│  └─ Margin analysis + forecasting
│
├─ Cash Flow Forecast
│  └─ 12-month cash flow prediction
│
├─ KPI Report
│  └─ Monthly KPI dashboard
│
├─ Invoice Audit
│  └─ Compliance + error detection
│
└─ Payment Follow-up
   └─ Overdue payment reminders
```

---

## 10. Capability Registry MVP 実装案

### 10.1 MVP スコープ

```
✅ In Scope (MVP 1週間で実装)
├─ Capability domain model (dataclass)
├─ CapabilityRegistry (in-memory CRUD)
├─ 2つの初期 Capability 登録
│  ├─ Proposal Generation v1.0
│  └─ Invoice Generation v1.0
├─ recommend_capability() 実装
├─ execute_capability() 記録
├─ CapabilityExecution memory update
├─ API endpoints (Flask/FastAPI)
│  ├─ GET /api/capabilities
│  ├─ GET /api/capabilities/{id}
│  ├─ POST /api/capabilities/recommend
│  ├─ POST /api/capabilities/{id}/execute
│  └─ GET /api/capabilities/{id}/metrics
├─ ProjectAction へ required_capability 追加
└─ Debug Trace に capability 情報表示

❌ Out of Scope (Phase 2 以降)
├─ Capability Pack
├─ Admin approval workflow
├─ Advanced learning engine
├─ Full governance implementation
├─ Performance monitoring dashboards
└─ Comprehensive template system
```

### 10.2 ファイル構成

```
backend/
├── capability/
│   ├── __init__.py
│   ├── domain.py              [Agent が作成した code]
│   ├── registry.py            [MVP実装]
│   ├── memory.py              [CapabilityMemory 管理]
│   └── learning.py            [AutoLearning engine 簡易版]
│
├── api/
│   ├── capability_router.py   [新規 API endpoints]
│   └── router.py              [既存に capability endpoint追加]
│
└── services/
    └── capability_service.py  [Capability 実行ロジック]

tests/
├── test_capability_registry.py
├── test_capability_execution.py
└── test_capability_learning.py

data/
├── capabilities.json          [Capability定義ストア]
├── capability_executions.jsonl [実行履歴]
└── capability_memory/         [各メモリの記録]
```

### 10.3 実装チェックリスト

```
Week 1:

Day 1-2:
  [ ] capability/registry.py 実装
      - list_capabilities()
      - get_capability()
      - register_capability()
      - recommend_capability() (簡易版: success_rate のみ)
      
  [ ] capability/memory.py 実装
      - CapabilityMemory class
      - save_execution()
      - update_memory()
      
Day 3:
  [ ] capability_router.py 実装
      - GET /api/capabilities
      - GET /api/capabilities/{id}
      - POST /api/capabilities/recommend
      - POST /api/capabilities/{id}/execute
      - GET /api/capabilities/{id}/metrics
      
Day 4:
  [ ] ProjectAction へ required_capability フィールド追加
  [ ] Debug Trace に capability 情報追加
  [ ] Proposal/Invoice Capability を JSON で定義
  
Day 5:
  [ ] テスト作成 (Test 1-6)
  [ ] Documentation
  [ ] Demo script
```

---

## 11. テスト方針

### Test 1: Registry 登録確認

```python
def test_capability_registry_has_two_capabilities():
    """Proposal Generation と Invoice Generation が登録されている"""
    registry = CapabilityRegistry.instance()
    
    capabilities = registry.list_capabilities()
    assert len(capabilities) >= 2
    
    cap_ids = [cap.capability_id for cap in capabilities]
    assert "cap-proposal-gen-v1.0" in cap_ids
    assert "cap-invoice-gen-v1.0" in cap_ids
    
    proposal_cap = registry.get_capability("cap-proposal-gen-v1.0")
    assert proposal_cap.name == "Proposal Generation"
    assert proposal_cap.status == CapabilityStatus.DEPLOYED
    assert proposal_cap.governance_level == GovernanceLevel.MEDIUM
```

### Test 2: Action → Capability 推奨

```python
def test_action_proposal_recommends_proposal_generation():
    """
    Decision: create_proposal
    Action: Proposal builder
    → Proposal Generation capability を推奨
    """
    registry = CapabilityRegistry.instance()
    
    project_context = {
        "state": "initiated",
        "goal": "create_proposal",
        "customer": "customer_A",
        "sales_amount": 1000000,
        "product": "software_license"
    }
    
    user_request = "提案資料を作成してください"
    
    capability, confidence = registry.recommend_capability(
        project_context=project_context,
        user_request=user_request
    )
    
    assert capability.capability_id == "cap-proposal-gen-v1.0"
    assert confidence > 0.8
```

### Test 3: User Request → Capability 推奨

```python
def test_invoice_request_recommends_invoice_generation():
    """
    User Request: 「この納品書に基づいて伝票をExcelで発行して」
    → Invoice Generation capability を推奨
    """
    registry = CapabilityRegistry.instance()
    
    project_context = {
        "state": "delivery_received",
        "document_type": "delivery_note",
        "customer": "customer_B",
        "amount": 500000
    }
    
    user_request = "この納品書に基づいて伝票をExcelで発行して"
    
    capability, confidence = registry.recommend_capability(
        project_context=project_context,
        user_request=user_request
    )
    
    assert capability.capability_id == "cap-invoice-gen-v1.0"
    assert confidence > 0.7
```

### Test 4: ExecutionHistory 保存

```python
def test_capability_execution_saves_history():
    """Capability 実行後、ExecutionHistory が保存される"""
    registry = CapabilityRegistry.instance()
    
    # Capability 実行
    execution = registry.execute_capability(
        capability_id="cap-invoice-gen-v1.0",
        project_id="proj-001",
        action_id="act-invoice-001",
        user_id="user-123",
        inputs={
            "delivery_note": "<file>",
            "customer": "customer_B",
            "amount": 500000
        }
    )
    
    assert execution.execution_id is not None
    assert execution.status == ExecutionStatus.RUNNING
    
    # 実行結果を記録
    registry.record_execution_result(
        execution_id=execution.execution_id,
        outputs={"excel_invoice": "<file>"},
        status=ExecutionStatus.COMPLETED,
        execution_time_seconds=2.5
    )
    
    # History から取得できる
    history = registry.get_execution_history(
        capability_id="cap-invoice-gen-v1.0",
        limit=10
    )
    
    assert len(history) > 0
    assert history[0].execution_id == execution.execution_id
    assert history[0].status == ExecutionStatus.COMPLETED
```

### Test 5: Memory 更新

```python
def test_user_correction_updates_memory():
    """
    ユーザー修正後、
    UserCorrectionMemory と FieldMappingMemory が更新される
    """
    registry = CapabilityRegistry.instance()
    
    # Execution
    execution = registry.execute_capability(...)
    registry.record_execution_result(...)
    
    # User correction
    correction = {
        "A2": {
            "original": "Old Address",
            "corrected": "New Address",
            "reason": "address_update"
        }
    }
    
    registry.update_memory(
        execution_id=execution.execution_id,
        memory_accessed=["mem-invoice-templates"],
        memory_updated=["mem-invoice-corrections", "mem-invoice-mappings"]
    )
    
    # Verify memory updated
    memory = registry.get_capability_memory(
        capability_id="cap-invoice-gen-v1.0",
        memory_type="correction"
    )
    
    assert memory is not None
    assert len(memory["corrections"]) > 0
```

### Test 6: Debug Trace 表示

```python
def test_debug_trace_shows_capability_info():
    """Debug Trace に capability 実行情報が表示される"""
    registry = CapabilityRegistry.instance()
    
    execution = registry.execute_capability(...)
    registry.record_execution_result(...)
    
    trace_entry = execution.to_trace_entry()
    
    assert trace_entry["execution_id"] is not None
    assert trace_entry["capability_id"] == "cap-invoice-gen-v1.0"
    assert trace_entry["capability_version"] == "1.0"
    assert trace_entry["project_id"] is not None
    assert trace_entry["action_id"] is not None
    assert "inputs" in trace_entry
    assert "outputs" in trace_entry
    assert "memory_accessed" in trace_entry
    assert "memory_updated" in trace_entry
    assert "confidence" in trace_entry
    assert "trace_id" in trace_entry
```

---

## 12. 既存構造への影響

### 12.1 変更対象

#### A. ProjectAggregate (backend/domain/project.py)

```python
@dataclass
class ProjectAction:
    # ... 既存フィールド ...
    
    # 新規フィールド
    required_capability: str | None       # "cap-proposal-gen-v1.0"
    capability_execution_id: str | None   # "exec-..."
    capability_metadata: dict | None      # execution詳細
```

#### B. Debug Trace (backend/api/debug page)

```python
# Debug trace entry に capability 情報を追加
trace_entry = {
    # ... 既存フィールド ...
    
    # 新規: Capability 実行情報
    "capabilities": [
        {
            "execution_id": "exec-001",
            "capability_id": "cap-invoice-gen-v1.0",
            "capability_version": "1.0",
            "status": "completed",
            "execution_time": 2.5,
            "inputs": {...},
            "outputs": {...},
            "memory_accessed": [...],
            "memory_updated": [...],
            "confidence": 0.92,
            "trace_id": "exec-trace-001"
        }
    ]
}
```

#### C. Conversation (frontend)

```python
# Conversation に Capability 実行が記録される
conversation_turn = {
    "turn_id": "turn-001",
    "user_message": "Invoice を発行してください",
    "ai_response": "Invoice を生成しました",
    
    # 新規フィールド
    "capability_used": {
        "capability_id": "cap-invoice-gen-v1.0",
        "execution_id": "exec-001",
        "output_file": "<path>",
        "user_feedback": "Good quality"
    }
}
```

### 12.2 非破壊的変更

```
✅ 追加のみ (既存フィールドに影響なし)
├─ ProjectAction.required_capability (optional)
├─ ProjectAction.capability_execution_id (optional)
├─ Debug trace に capability section (optional)
└─ Conversation に capability_used (optional)

❌ 削除や変更なし
├─ 既存の ProjectAggregate
├─ 既存の Action
├─ 既存の State/Goal/Decision
└─ 既存の Event structure
```

---

## 13. Git Status & Implementation Readiness

### 13.1 新規ファイル

```
capability/
├── __init__.py
├── domain.py             (Agent 作成済み)
├── registry.py           (MVP 実装予定)
├── memory.py             (MVP 実装予定)
└── learning.py           (簡易版)

backend/api/
├── capability_router.py  (新規)

backend/services/
├── capability_service.py (新規)

tests/
├── test_capability_registry.py
├── test_capability_execution.py
└── test_capability_learning.py

data/
├── capabilities.json
├── capability_executions.jsonl
└── capability_memory/
```

### 13.2 実装スケジュール

```
Week 1: MVP Implementation
  Day 1-2: registry + memory
  Day 3: API endpoints
  Day 4: ProjectAction integration + Debug Trace
  Day 5: Tests + Demo

Week 2: Initial Capabilities
  - Proposal Generation v1.0 fully tested
  - Invoice Generation v1.0 fully tested
  - User feedback integration

Week 3: Governance Framework (Phase 2)
  - Admin approval workflow
  - Learning engine enhancement
  - Performance monitoring

Week 4: Capability Pack (Phase 3)
  - OEM Pack
  - Creative Pack
  - Finance Pack
```

---

## Summary: 2軸の AI OS

```
        「Project 理解軸」          「Capability 実行軸」
        
Project Understanding          Business Execution
━━━━━━━━━━━━━━━━━━━━━━        ━━━━━━━━━━━━━━━━━━━━━━

Project               Events                Capability
  ↓                     ↓                       ↓
State               History              Template
  ↓                     ↓                       ↓
Goal              State Change          FieldMapping
  ↓                     ↓                       ↓
Decision           Analysis             DocumentPattern
  ↓                     ↓                       ↓
Action             Impact               UserCorrection
  ↓                     ↓                       ↓
Output            Recommendation       OutputHistory

         ↓         これら2軸が交差する場所で
         
         ┌─────────────────────────────────┐
         │ AI OS の意思決定と実行が成立する │
         │                                 │
         │ 「何をすべきか」 + 「どう実行するか」 │
         │     = AI の知性 + AI の能力      │
         │                                 │
         │ 案件を理解 ✓                      │
         │ 業務を実行 ✓                      │
         │ 経験から学習 ✓                    │
         │ 能力を成長 ✓                      │
         └─────────────────────────────────┘
```

---

**Phase 4 完成により、AI OS は真の「自律的学習エージェント」として動作開始**
