# Learning Layer / Policy Memory 設計提案書

**日付:** 2026-06-30  
**フェーズ:** Phase 4 準備  
**ステータス:** 設計提案

---

## 1. 既存構造の確認結果

### 1.1 既存のFeedback/Memory/Learning構造

#### A. Learning モジュール (`learning/`)
```
learning/
├── feedback.py          - 基本的なfeedback保存 (in-memory)
├── improvements.py      - improvement提案とchange request統合
├── insights.py          - 使用不明 (stub可能性)
└── query_log.py         - クエリログ記録
```

**現状:**
- `save_feedback()`: log_id, status(accepted/rejected/modified), comment を保存
- `create_improvement()`: improvement提案を生成し、change_management と連携
- **問題**: フィードバックと Business Rule の連携がない

#### B. Memory モジュール (`memory/`)
```
memory/
├── retrieval_interface.py  - メモリ検索 (stub実装)
├── store.py               - メモリストア
└── context.py             - メモリコンテキスト
```

**現状:**
- `MemoryRecord`: memory_type, title, summary, related_entities/customers/projects/staff
- `retrieve_memory()`: 型ベースで stub レコード返却
- **問題**: 実装されていない、ファイルベース

#### C. Conversation モジュール (`conversation/`)
```
conversation/
├── models.py      - ConversationTurn, ConversationState
├── resolver.py    - intent解決
└── store.py       - 会話ストア
```

**現状:**
- `ConversationTurn`: message, answer, trace_id, intent_type 記録
- **問題**: AI判断(decision/action)の記録がない

#### D. 既存データストア (`data/`)
```
data/
├── conversation/
│   ├── turns.jsonl        - 会話ターン (timestamp, user_id, message, answer, intent)
│   └── states.jsonl       - 会話状態
├── memory/
│   └── memories.jsonl     - メモリレコード (500KB+)
└── validation/
    └── reports.jsonl      - バリデーションレポート
```

#### E. ADR-0005: Human-Approved Improvement Process
```
Question Log
    ↓
Feedback (user choice: accept/reject/modify)
    ↓
Improvement Candidate (learning)
    ↓
Change Request (change_management)
    ↓
Admin Approval
    ↓
Implementation
    ↓
Test & Release
```

---

## 2. 足りない要素

### 2.1 AI Decision の記録がない
- **現在**: conversation に message/answer のみ
- **足りない**: 
  - AI が提案した decision (protect/recover/accelerate/monitor/ignore)
  - AI が提案した action 詳細
  - 3軸スコア (health/risk/opportunity) の詳細

### 2.2 Human Feedback と Decision の対応がない
- **現在**: feedback が feedback.py に保存されるが、対応するAI decisionがない
- **足りない**:
  - feedback_id ↔ project_id ↔ ai_decision_id の関係
  - Human choice vs AI proposal のdiff保存
  - feedback の reason / context 分析

### 2.3 Policy Memory がない
- **現在**: improvements.py に提案があるが、反映先がない
- **足りない**:
  - 「重要顧客なら focus=accelerate」「粗利<5%なら focus=protect」のような規則
  - これらの規則を次回 AI decision に反映する仕組み
  - 規則の priority, confidence, source_feedback_id

### 2.4 Learning Engine がない
- **現在**: feedback → improvement → change_request の流れだけ
- **足りない**:
  - AI decision vs Human choice の差分抽出
  - 差分から規則を抽出 (例: 「margin < 5% で human が protect を選んだ」→「margin < 5% なら protect」)
  - 抽出した規則の confidence/priority 計算
  - 規則の反映方法 (Business Rules へのオーバーライド)

### 2.5 Business Rule への反映パイプがない
- **現在**: evaluation_rules.py の rule classes が固定
- **足りない**:
  - Policy Memory の規則を runtime で適用
  - Weight overrides (粗利ペナルティを +5点 → +10点 へ)
  - Dynamic rule creation / composition

---

## 3. 新しい Learning Layer 設計

### 3.1 データフロー (全体)

```
[Project Data]
    ↓
[AI 3-Axis Scoring]
    ├── Health Score
    ├── Risk Score
    └── Opportunity Score
    ↓
[AI Decision & Recommendation]
    ├── Focus: protect/recover/accelerate/monitor/ignore
    ├── Today Actions (priority ordered)
    └── trace_id で全て連結
    ↓
[Human Feedback UI]
    ├── Accept / Reject / Modify
    ├── Reason text input
    └── Confidence level
    ↓
[Feedback Store]
    ├── feedback_id
    ├── project_id
    ├── trace_id
    ├── ai_decision vs human_choice diff
    ├── feedback_reason
    └── user_role / timestamp
    ↓
[Learning Engine]
    ├── Diff Analysis
    ├── Pattern Recognition
    ├── Policy Extraction
    └── Confidence Calculation
    ↓
[Policy Memory]
    ├── extracted_rules[]
    ├── priority
    ├── source_feedback_ids[]
    └── effective_at / expires_at
    ↓
[Business Rules Override]
    ├── Dynamic Weight Adjustment
    ├── Rule Priority Tuning
    └── Temporary Policies
    ↓
[Next AI Decision]
    (Policy Memory を考慮した scoring)
```

### 3.2 モジュール構成

#### A. Feedback Recording (`learning/feedback_recorder.py`) - 新規
```python
@dataclass
class AIDecision:
    decision_id: str
    project_id: str
    trace_id: str
    ai_focus: str              # protect/recover/accelerate/monitor/ignore
    ai_health_score: int
    ai_risk_score: int
    ai_opportunity_score: int
    ai_actions: list[str]      # action_id list
    confidence: float          # 0.7-1.0
    reasoning: str
    created_at: datetime

@dataclass
class HumanFeedback:
    feedback_id: str
    ai_decision_id: str
    project_id: str
    trace_id: str
    user_id: str
    user_role: str             # sales/pm/finance/ceo
    
    # Human choice
    human_focus: str           # same options as ai_focus
    human_accepted_action_ids: list[str]
    human_modified_action_ids: dict[str, str]  # action_id -> modified_action
    human_rejected_action_ids: list[str]
    
    # Feedback details
    reason: str
    confidence: float          # how confident is human in choice
    alternative_reasoning: str
    
    timestamp: datetime
    metadata: dict             # extra context

def save_ai_decision(decision: AIDecision) -> str
def save_human_feedback(feedback: HumanFeedback) -> str
def get_feedback_by_project(project_id: str) -> list[HumanFeedback]
def get_feedback_history(limit: int = 100) -> list[dict]
```

#### B. Policy Memory (`learning/policy_memory.py`) - 新規
```python
@dataclass
class PolicyRule:
    rule_id: str
    rule_type: str             # "override_score" / "adjust_weight" / "conditional_focus"
    
    # Rule definition
    condition: str             # e.g., "margin < 5 AND customer_priority == vip"
    action: str                # e.g., "focus = 'protect'"
    parameter: dict            # adjustments to apply
    
    # Metadata
    priority: int              # 1-10, higher = earlier application
    confidence: float          # how much we trust this rule (0.0-1.0)
    source_type: str           # "human_feedback" / "business_rule" / "override"
    source_feedback_ids: list[str]  # which feedbacks led to this rule
    
    effective_at: datetime
    expires_at: datetime | None
    enabled: bool
    
    # Statistics
    times_applied: int = 0
    times_benefited: int = 0   # feedback showed it helped
    times_harmed: int = 0      # feedback showed it hurt

class PolicyMemory:
    def add_rule(rule: PolicyRule) -> str
    def apply_rules(context: dict) -> dict  # modifications to apply
    def list_rules(active_only: bool = True) -> list[PolicyRule]
    def update_rule_stats(rule_id: str, benefited: bool) -> None
    def disable_rule(rule_id: str) -> None
    def get_rules_for_condition(condition: str) -> list[PolicyRule]
```

#### C. Learning Engine (`learning/learning_engine.py`) - 新規
```python
class LearningEngine:
    def analyze_feedback(feedback: HumanFeedback) -> list[dict]:
        """
        Diff AI vs Human, extract patterns
        Returns: list of suggested policies
        [
            {
                "pattern": "margin < 5% → focus should be protect not monitor",
                "confidence": 0.85,
                "evidence_count": 3,
                "suggested_rule": PolicyRule(...)
            }
        ]
        """
    
    def extract_policy_rules(feedbacks: list[HumanFeedback]) -> list[PolicyRule]:
        """Extract generalizable rules from feedback patterns"""
        
    def calculate_rule_confidence(rule: PolicyRule, feedbacks: list[HumanFeedback]) -> float:
        """How much evidence supports this rule?"""
        
    def validate_rule_before_apply(rule: PolicyRule) -> dict:
        """Check rule doesn't conflict with other policies"""
        
    def suggest_weight_adjustments(feedback_diff: dict) -> dict:
        """If AI underestimated margin risk, suggest weight increase"""
```

#### D. Integration with ProjectService (`backend/services/project_service.py`) - 修正
```python
class ProjectService:
    def __init__(self, ..., policy_memory: PolicyMemory = None):
        self.policy_memory = policy_memory
    
    def build_project_aggregate(self, project_id: str) -> ProjectAggregate:
        # 既存の3軸スコア計算
        health, risk, opportunity = self._calculate_scores(...)
        
        # Policy Memory を適用
        if self.policy_memory:
            adjustments = self.policy_memory.apply_rules({
                "project_id": project_id,
                "margin": data.profit_margin_pct,
                "customer_priority": customer_priority,
                "days_until_delivery": data.days_until_delivery,
                "billing_status": billing_status,
                # ... その他 context
            })
            
            # adjustments を score に反映
            health = self._apply_adjustments(health, adjustments.get("health"))
            risk = self._apply_adjustments(risk, adjustments.get("risk"))
            opportunity = self._apply_adjustments(opportunity, adjustments.get("opportunity"))
        
        return ProjectAggregate(...)
```

---

## 4. Policy Memory 設計

### 4.1 Policy Rule の種類

#### Type A: Score Override
```
Condition: margin < 5
Action: health_score -= 10
Type: "override_score"
Parameter: {"target": "health_score", "adjustment": -10}
```

#### Type B: Weight Adjustment
```
Condition: customer_priority == "vip"
Action: opportunity_weight *= 1.3
Type: "adjust_weight"
Parameter: {"target": "opportunity", "multiplier": 1.3}
```

#### Type C: Conditional Focus
```
Condition: (margin < 5) AND (days_until_delivery < 7)
Action: recommended_focus = "protect"
Type: "conditional_focus"
Parameter: {"target": "recommended_focus", "value": "protect"}
```

#### Type D: Action Priority Boost
```
Condition: customer_priority == "vip" AND opportunity_score > 70
Action: today_action_priority += 2
Type: "action_priority"
Parameter: {"boost": 2}
```

### 4.2 Policy Memory の保存形式

```yaml
# policy_memory.yaml
rules:
  - rule_id: "policy-001"
    name: "Low margin protection"
    condition: "margin < 5"
    action_type: "override_score"
    action: "focus = 'protect'"
    priority: 9
    confidence: 0.92
    source: "human_feedback"
    source_feedback_ids:
      - "feedback-102"
      - "feedback-103"
    effective_at: "2026-06-30T12:00:00Z"
    times_applied: 15
    times_benefited: 14
    times_harmed: 1
    enabled: true

  - rule_id: "policy-002"
    name: "VIP opportunity multiplier"
    condition: "customer_priority == 'vip'"
    action_type: "adjust_weight"
    action: "opportunity *= 1.3"
    priority: 7
    confidence: 0.78
    ...
```

---

## 5. Human Feedback モデル

### 5.1 Feedback記録の詳細構造

```python
@dataclass
class HumanFeedback:
    # Identity
    feedback_id: str                    # "feedback-20260630-001"
    
    # Context
    project_id: str
    trace_id: str                      # AI decision trace
    ai_decision_id: str               # 対応するAI decision
    
    # User
    user_id: str
    user_role: str                    # "sales" / "pm" / "finance" / "ceo" / "admin"
    user_department: str | None       # "営業1部" など
    
    # AI Proposal
    ai_proposed: {
        focus: str                    # "monitor"
        health_score: int            # 75
        risk_score: int              # 45
        opportunity_score: int       # 20
        actions: list[ProjectAction]
    }
    
    # Human Decision
    human_choice: {
        focus: str                   # "protect"  ← Different!
        health_score: int | None     # override if any
        actions_accepted: list[str]
        actions_modified: dict       # action_id -> modified version
        actions_rejected: list[str]
    }
    
    # Feedback Details
    reason: str                       # "重要顧客だから安全第一"
    confidence: float                 # 0.9 (how sure is human?)
    alternative_reasoning: str | None
    
    # Metadata
    decision_time_seconds: float      # how long human took
    review_quality: str               # "careful" / "quick" / "uncertain"
    metadata: dict
    
    # Audit
    timestamp: datetime
    modified_at: datetime | None
    reviewed_by_admin: bool
```

### 5.2 Feedback Store Format (JSONL)

```json
{
  "feedback_id": "feedback-20260630-001",
  "project_id": "102",
  "trace_id": "project-c4ca4238",
  "ai_decision_id": "decision-20260630-001",
  "user_id": "user-sales-001",
  "user_role": "sales",
  "user_department": "営業1部",
  "ai_proposed": {
    "focus": "monitor",
    "health_score": 75,
    "risk_score": 30,
    "opportunity_score": 45,
    "top_actions": 3
  },
  "human_choice": {
    "focus": "protect",
    "actions_accepted": ["act-001", "act-002"],
    "actions_rejected": ["act-003"]
  },
  "reason": "粗利5%は危険。顧客信頼より自社保護を優先",
  "confidence": 0.92,
  "timestamp": "2026-06-30T14:23:45Z"
}
```

---

## 6. 最小実装案 (Minimal Viable Loop)

### フェーズ 1: Foundation (Week 1)

**ファイル新規作成:**
1. `learning/feedback_recorder.py` (AIDecision + HumanFeedback 記録)
2. `learning/policy_memory.py` (PolicyRule + PolicyMemory in-memory)
3. `backend/api/feedback_router.py` (API endpoints)

**既存ファイル修正:**
1. `backend/services/project_service.py` (Policy Memoryの適用)
2. `backend/api/router.py` (feedback POST endpoint追加)

**最小実装内容:**
- [x] AIDecision を計算時に記録
- [x] Human Feedback を API で受け取り記録
- [x] Policy Memory に学習規則を手動追加
- [x] ProjectService で Policy Memory を参照

### フェーズ 2: Learning Engine (Week 2)

**新規作成:**
1. `learning/learning_engine.py` (差分分析、規則抽出)
2. `learning/pattern_recognizer.py` (パターン認識)

**実装:**
- [ ] Feedback vs AI proposal 差分計算
- [ ] 規則抽出アルゴリズム (簡易版: condition matching)
- [ ] 規則の confidence 計算

### フェーズ 3: UI Integration (Week 3)

**フロントエンド:**
- [ ] Feedback collection UI (accept/reject/modify buttons)
- [ ] Reason text input
- [ ] Policy memory 表示

---

## 7. テスト方針

### 7.1 Unit Tests

```python
# test_feedback_recorder.py
def test_save_and_retrieve_feedback():
    recorder = FeedbackRecorder()
    decision = AIDecision(...)
    feedback = HumanFeedback(...)
    
    feedback_id = recorder.save_human_feedback(feedback)
    retrieved = recorder.get_feedback_by_id(feedback_id)
    
    assert retrieved.human_choice.focus == "protect"

# test_policy_memory.py
def test_policy_application():
    memory = PolicyMemory()
    rule = PolicyRule(
        condition="margin < 5",
        action="focus = 'protect'",
        ...
    )
    memory.add_rule(rule)
    
    context = {"margin": 4}
    adjustments = memory.apply_rules(context)
    
    assert adjustments["focus"] == "protect"

# test_learning_engine.py
def test_extract_rule_from_feedback():
    engine = LearningEngine()
    
    # AI said "monitor" but human said "protect" for 3 projects with margin < 5
    feedbacks = [...]  # 3 feedback records
    
    rules = engine.extract_policy_rules(feedbacks)
    assert any(r.condition == "margin < 5" for r in rules)
    assert any(r.action == "focus = 'protect'" for r in rules)
```

### 7.2 Integration Tests

```python
# test_learning_loop.py
def test_minimal_feedback_loop():
    # 1. Project에서 AI decision 생성
    project = build_test_project(margin=4)
    agg = service.build_project_aggregate(project.id)
    assert agg.recommended_focus == "monitor"  # baseline
    
    # 2. Human feedback 기록
    feedback = HumanFeedback(
        ai_decision_id=agg.trace_id,
        human_choice={"focus": "protect"},
        reason="low margin"
    )
    recorder.save_human_feedback(feedback)
    
    # 3. Learning engine 분석
    engine = LearningEngine()
    rules = engine.extract_policy_rules([feedback])
    
    # 4. Policy memory 에 추가
    policy_memory.add_rule(rules[0])
    
    # 5. 같은 조건의 새 프로젝트 평가
    new_project = build_test_project(margin=4)
    service_with_policy = ProjectService(policy_memory=policy_memory)
    agg2 = service_with_policy.build_project_aggregate(new_project.id)
    
    # AI decision이 이제 "protect"로 변경되어야 함
    assert agg2.recommended_focus == "protect"  # learned!
```

### 7.3 Scenario Tests

```python
# test_scenarios_with_feedback.py
def test_margin_degradation_with_feedback():
    """
    Scenario: margin < 5% 프로젝트에서 여러 Sales manager가 "protect" 선택
    Expected: Learning engine이 규칙을 추출하고, 이후 유사 프로젝트는 
              AI도 자동으로 "protect" 추천
    """
    # Setup
    feedback_list = []
    for i in range(3):
        project = create_project(margin=4)
        decision = ai_service.build_decision(project)
        
        # Sales는 항상 "protect" 선택
        feedback = HumanFeedback(
            ai_decision_id=decision.id,
            human_choice={"focus": "protect"},
            user_role="sales"
        )
        feedback_list.append(feedback)
    
    # Learning
    rules = engine.extract_policy_rules(feedback_list)
    assert len(rules) >= 1
    
    # Verify: Policy 적용되면 다음 project도 "protect"
    policy_memory.add_rule(rules[0])
    new_project = create_project(margin=4)
    agg = service_with_policy.build_project_aggregate(new_project.id)
    assert agg.recommended_focus == "protect"
```

---

## 8. Git Status & Implementation Files

### 新規作成ファイル

```
learning/
├── feedback_recorder.py       (230 lines)
├── policy_memory.py           (180 lines)
├── learning_engine.py         (200 lines)
├── pattern_recognizer.py      (150 lines)
└── __init__.py

data/
├── feedback/
│   └── feedbacks.jsonl        (auto-created)
└── policies/
    └── policy_memory.yaml     (auto-created)

backend/api/
└── feedback_router.py         (150 lines)

tests/
└── learning/
    ├── test_feedback_recorder.py
    ├── test_policy_memory.py
    ├── test_learning_engine.py
    └── test_learning_integration.py
```

### 修正ファイル

```
backend/services/project_service.py
  - __init__に policy_memory parameter追加
  - build_project_aggregate() にPolicy Memory適用ロジック追加

backend/api/router.py
  - POST /api/feedback endpoint追加
  - GET /api/policy-memory endpoint追加

backend/api/schemas.py
  - FeedbackRequest / PolicyRuleResponse schema追加

memory/retrieval_interface.py
  - Policy Memory の retrieve 関数追加 (optional)
```

---

## 9. 今後の拡張ポイント

### Phase 4a: Feedback UI
- [ ] Accept/Reject/Modify ボタン UI
- [ ] Feedback form (reason text)
- [ ] Confidence slider

### Phase 4b: Advanced Learning
- [ ] Rule confidence自動計算
- [ ] Conflicting rules検出
- [ ] A/B test: Policy vs No Policy

### Phase 4c: Explainability
- [ ] Why did AI recommend X? (Policy rules表示)
- [ ] Which feedback led to this rule?
- [ ] Rule impact visualization

### Phase 4d: Admin Dashboard
- [ ] Active policies 表示
- [ ] Rule performance metrics
- [ ] Manual rule override
- [ ] Policy audit log

---

## Summary

**既存:** 
- Learning/Memory/Feedback の骨組みあり
- ADR-0005 で improvement process defined
- 3軸スコア計算完成

**足りない:**
- AI decision の記録と参照
- Human feedback と decision の連結
- Policy memory (実装されていない)
- Learning engine (実装されていない)

**最小実装:**
- 3つの新規モジュール (feedback_recorder, policy_memory, learning_engine)
- 2つの API endpoint (feedback POST, policy GET)
- ProjectService への policy memory 統合
- テストで最小ループ検証

**期間:** 3週間で Phase 1-3 完成可能
