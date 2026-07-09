"""Project Domain Model - Core business concepts for AI project management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional


class ProjectState(str, Enum):
    """Project lifecycle states."""
    INITIATED = "initiated"
    DELIVERY_RECEIVED = "delivery_received"
    AWAITING_PAYMENT = "awaiting_payment"
    COST_UNCONFIRMED = "cost_unconfirmed"
    # 2026-07-09（14.39、Noritsuguの指定）: 案件は「完了」（売上・仕入とも
    # 入力済み）でなければ、売上未確定・原価未確定のどちらか、または
    # 両方が同時に成立する。同時表示に対応するため、_determine_state
    # （単一値、内部の events/actions 用）とは別に、_determine_status_
    # badges（複数可、画面表示用）を project_service.py に設けている。
    SALES_UNCONFIRMED = "sales_unconfirmed"
    GROSS_PROFIT_UNCONFIRMED = "gross_profit_unconfirmed"
    GROSS_PROFIT_DEGRADED = "gross_profit_degraded"
    COMPLETED = "completed"
    DELIVERY_OVERDUE = "delivery_overdue"
    PAYMENT_OVERDUE = "payment_overdue"
    COST_DISCREPANCY = "cost_discrepancy"
    CUSTOMER_CONFIRMATION_NEEDED = "customer_confirmation_needed"
    # 2026-07-09（14.42、Noritsuguの指定）: purchase_orders."ステータス"
    # （code_master ORDER_STATUS）が4（発注済）かどうかを示すバッジ。
    # 完了/売上未確定/原価未確定とは別軸で、常にどちらか一方が付く。
    PO_ISSUED = "po_issued"
    PO_NOT_ISSUED = "po_not_issued"


class ProjectGoal(str, Enum):
    """Business objectives for each project."""
    MEET_DEADLINE = "meet_deadline"
    SECURE_MARGIN = "secure_margin"
    CONFIRM_COST = "confirm_cost"
    PROCESS_PAYMENT = "process_payment"
    CUSTOMER_SATISFACTION = "customer_satisfaction"
    # 2026-07-09: 納品日/支払日はPOデータに実質入らないため使えない
    # （14.33、Noritsuguの指摘）。代わりに売上入力の有無で納品を確認する。
    CONFIRM_DELIVERY = "confirm_delivery"
    # 2026-07-09（14.42、Noritsuguの指定）: PO自体が発行済みかどうか。
    ISSUE_PO = "issue_po"


class ProjectDecision(str, Enum):
    """AI decisions triggered by state and goal failures."""
    EXPEDITE_PO = "expedite_po"
    REQUEST_COST_CONFIRMATION = "request_cost_confirmation"
    IMPROVE_MARGIN = "improve_margin"
    PROCESS_PAYMENT_IMMEDIATELY = "process_payment_immediately"
    CONTACT_CUSTOMER = "contact_customer"
    ESCALATE_TO_MANAGEMENT = "escalate_to_management"
    DOCUMENT_VARIANCE = "document_variance"
    # 2026-07-09（14.33）: 今日のタスクを「売上入力の必要性」「仕入入力の
    # 必要性」の2種類だけに絞り込むための決定。
    RECORD_SALES = "record_sales"
    RECORD_PURCHASE = "record_purchase"
    # 2026-07-09（14.42、Noritsuguの指定）: 今日のタスクの3種類目。
    ISSUE_PO = "issue_po"


class ProjectEventType(str, Enum):
    """15 business events that drive state changes."""
    PROJECT_CREATED = "project_created"
    SALES_REGISTERED = "sales_registered"
    PURCHASE_REGISTERED = "purchase_registered"
    ACTUAL_COST_CONFIRMED = "actual_cost_confirmed"
    LOGICAL_COST_USED = "logical_cost_used"
    GROSS_PROFIT_RECALCULATED = "gross_profit_recalculated"
    GROSS_PROFIT_DECLINED = "gross_profit_declined"
    DELIVERY_DATE_UPDATED = "delivery_date_updated"
    DELIVERY_RISK_DETECTED = "delivery_risk_detected"
    DELIVERY_COMPLETED = "delivery_completed"
    BILLING_REQUIRED = "billing_required"
    PAYMENT_PROCESSED = "payment_processed"
    CUSTOMER_CONFIRMATION_REQUIRED = "customer_confirmation_required"
    PROPOSAL_REQUIRED = "proposal_required"
    INVOICE_RECEIVED = "invoice_received"


class GoalStatus(str, Enum):
    """Evaluation status of a goal."""
    ACHIEVED = "achieved"
    AT_RISK = "at_risk"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class ProjectEvent:
    """Business event with complete traceability."""
    event_id: str
    project_id: str
    event_type: ProjectEventType
    event_time: datetime
    source_table: str
    business_meaning: str
    impact_summary: str
    trace_id: str
    event_source_type: str = "actual"  # actual | derived
    derivation_rule: Optional[str] = None
    before_state: Optional[ProjectState] = None
    after_state: Optional[ProjectState] = None
    changed_fields: Optional[dict[str, Any]] = None
    executed_sql: Optional[str] = None
    source_rule: Optional[str] = None
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "project_id": self.project_id,
            "event_type": self.event_type.value,
            "event_time": self.event_time.isoformat(),
            "event_source_type": self.event_source_type,
            "source_table": self.source_table,
            "business_meaning": self.business_meaning,
            "impact_summary": self.impact_summary,
            "before_state": self.before_state.value if self.before_state else None,
            "after_state": self.after_state.value if self.after_state else None,
            "trace_id": self.trace_id,
            "confidence": self.confidence,
        }


@dataclass
class ProjectEvents:
    """Collection of all events for a project."""
    project_id: str
    events: list[ProjectEvent] = field(default_factory=list)
    event_count: int = 0
    last_event_time: Optional[datetime] = None
    events_by_type: dict[str, int] = field(default_factory=dict)

    def add_event(self, event: ProjectEvent) -> None:
        """Add an event to the collection."""
        self.events.append(event)
        self.event_count += 1
        self.last_event_time = event.event_time
        event_type_key = event.event_type.value
        self.events_by_type[event_type_key] = self.events_by_type.get(event_type_key, 0) + 1


@dataclass
class ProjectData:
    """Immutable fact-based data about a project."""
    project_id: str
    po_number: str
    supplier_id: str
    supplier_name: str
    customer_id: str
    customer_name: str
    po_created_date: datetime
    po_required_delivery_date: datetime
    supplier_phone: Optional[str] = None
    supplier_email: Optional[str] = None
    supplier_address: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    po_required_delivery_date_alt: Optional[datetime] = None
    actual_delivery_date: Optional[datetime] = None
    invoice_date: Optional[datetime] = None
    payment_due_date: Optional[datetime] = None
    actual_payment_date: Optional[datetime] = None
    products: list[dict] = field(default_factory=list)
    po_amount: Optional[float] = None
    supplier_invoice_amount: Optional[float] = None
    cost_amount: Optional[float] = None
    sale_amount: Optional[float] = None
    gross_profit: Optional[float] = None
    gross_profit_margin: Optional[float] = None
    data_source_tables: list[str] = field(default_factory=lambda: ["仕入"])
    # 2026-07-09（14.33）: purchase_ordersのLOGS_CODE。sales/purchasesとの
    # 突合キー（14.30・14.32と同じ考え方）。has_sales/has_purchaseの判定に使う。
    logs_code: Optional[str] = None
    # 納品日/支払日はPOデータに実質入らないため（Noritsuguの指摘）、
    # 「納品済みかどうか」はhas_sales（売上入力の有無）または
    # production_closed（生産管理『量産』シートの表示フラグ=0）で判断する。
    has_sales: bool = False
    has_purchase: bool = False
    production_closed: bool = False
    # 2026-07-09（14.35）: 活動履歴の日付をnow()で埋めていた不具合の修正。
    # sales/purchasesの実際の入力日（複数行あれば直近のMAX、2026-07-09 14.38で修正）。
    sales_date: Optional[datetime] = None
    purchase_date: Optional[datetime] = None
    # 2026-07-09（14.40、Noritsuguの指定）: 案件名はPO番号だけでは分かり
    # づらいため、purchase_orders."案件名"を合わせて表示する。
    project_name: Optional[str] = None
    # 輸入経費率（1.xxという値になる比率）: 商品原価（商品単価×数量×為替）
    # に対して、諸掛込原価（商品原価＋輸入経費）がどの程度かを示す指標。
    # 予定（PO入力時点、purchase_orders."輸入経費率"）と実績（仕入登録時に
    # 確定、purchases."経費率"）を比較することで予実管理に使う。
    # 検索・チャットからも意味が分かるよう、このコメントで明記している。
    planned_import_cost_ratio: Optional[float] = None
    actual_import_cost_ratio: Optional[float] = None
    # 2026-07-09（14.42、Noritsuguの指定）: purchase_orders."ステータス"。
    # code_master(ORDER_STATUS)で4=発注済、それ以外(1=依頼,2=依頼保留,
    # 3=差戻,5=発注保留)は未発行。実データでは4が34,947件、他は合計22件
    # という圧倒的な分布（2026-07-09、実際にcode_masterで確認済み）。
    po_status: Optional[int] = None

    @property
    def days_until_delivery(self) -> int:
        """納品日までの日数。単純に納品日と現在日時を比較するだけで、
        売上・仕入の入力状況とは無関係（2026-07-09、14.43、Noritsuguの
        確認）。以前は`max(0, ...)`でフロアをかけていたため、納期を
        過ぎている案件でも常に「0日」と表示され、実際にどれだけ過ぎて
        いるかが分からなかった不具合を修正。過ぎている場合は負の値
        （例: -15）を返す — 表示側（フロントエンド）で「納期経過」に
        変換する（14.43、負の日数そのものを見せる意味は無いという
        Noritsuguの指定）。
        """
        delta = self.po_required_delivery_date - datetime.now()
        return delta.days

    @property
    def is_overdue(self) -> bool:
        return datetime.now() > self.po_required_delivery_date

    @property
    def is_delivered(self) -> bool:
        """納品済みかどうか。POの納品日は実質常に空のため、売上入力の
        有無、または生産管理『量産』シートで表示OFFにされたか（担当者が
        案件を終了済みとして扱った印）で判断する（2026-07-09、14.33）。
        """
        return self.has_sales or self.production_closed

    @property
    def is_po_issued(self) -> bool:
        """PO自体が発行済みか（purchase_orders."ステータス"=4=発注済、
        code_master ORDER_STATUS、2026-07-09・14.42）。"""
        return self.po_status == 4

    @property
    def profit_margin_pct(self) -> Optional[float]:
        if self.sale_amount and self.cost_amount:
            return ((self.sale_amount - self.cost_amount) / self.sale_amount) * 100
        return None


@dataclass
class GoalEvaluation:
    """Evaluation of a single goal."""
    goal: ProjectGoal
    status: GoalStatus
    reason: str
    confidence: float


@dataclass
class GoalEvaluations:
    """Evaluation of all goals for a project."""
    project_id: str
    evaluations: dict[ProjectGoal, GoalEvaluation] = field(default_factory=dict)


@dataclass
class ProjectDecisionDetail:
    """A decision with full context."""
    decision: ProjectDecision
    priority: int
    reason: str
    confidence: float
    triggered_by_goals: list[ProjectGoal]
    business_rule: str


@dataclass
class ProjectAction:
    """Concrete task generated from a decision."""
    action_id: str
    project_id: str
    title: str
    description: str
    priority: str
    related_state: ProjectState
    related_goal: Optional[ProjectGoal] = None
    decision_source: Optional[ProjectDecision] = None
    source_tables: list[str] = field(default_factory=list)
    source_record_ids: list[str] = field(default_factory=list)
    condition: str = ""
    trace_id: str = ""
    action_type: str = "call"
    due_date: Optional[datetime] = None
    executed_sql: Optional[str] = None
    business_rule_applied: Optional[str] = None
    confidence: float = 0.8
    required_capability: Optional[str] = None  # capability_id for AI OS execution
    capability_execution_id: Optional[str] = None  # execution_id from CapabilityRegistry


@dataclass
class ProjectHealth:
    """Project health assessment."""
    health_score: int
    health_status: str
    factors: dict[str, int]
    reason: str
    trace_id: str

    def to_dict(self) -> dict:
        return {
            "health_score": self.health_score,
            "health_status": self.health_status,
            "factors": self.factors,
            "reason": self.reason,
            "trace_id": self.trace_id,
        }


@dataclass
class ProjectAggregate:
    """Complete project understanding with 8 elements."""
    project_id: str
    po_number: str
    events: ProjectEvents
    data: ProjectData
    state: ProjectState
    goal_evaluations: GoalEvaluations
    decisions: list[ProjectDecisionDetail]
    actions: list[ProjectAction]
    trace_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    assigned_to: str = "AI"
    priority: str = "medium"
    # 2026-07-09（14.35）: health/risk/opportunity/recommended_focusは
    # POの納品日/支払日が常に空という実データの制約下では意味を成して
    # いなかった（Noritsuguの判断）ため廃止。代わりに現在日から納品日
    # までの月数だけで判定するdelivery_month_bucketに置き換えた。
    delivery_month_bucket: Optional[str] = None
    # 2026-07-09（14.39）: 完了以外の場合、売上未確定・原価未確定が
    # 同時に成立しうるため、単一のstateではなく複数可のリストで持つ。
    # 画面表示（案件一覧・案件詳細）にはこちらを使う。納期超過バッジは
    # Noritsuguの判断で廃止（実データでは常に完了/売上未確定/原価未確定
    # の3つだけで十分と判断）。
    status_badges: list[str] = field(default_factory=list)

    def get_at_risk_goals(self) -> list[ProjectGoal]:
        return [goal for goal, eval in self.goal_evaluations.evaluations.items()
                if eval.status == GoalStatus.AT_RISK]

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "po_number": self.po_number,
            "trace_id": self.trace_id,
            "state": self.state.value,
            "priority": self.priority,
            "delivery_month_bucket": self.delivery_month_bucket,
            "status_badges": self.status_badges,
            "events": {
                "count": self.events.event_count,
                "items": [e.to_dict() for e in self.events.events],
            },
            "data": {
                "project_id": self.data.project_id,
                "po_number": self.data.po_number,
                "supplier_name": self.data.supplier_name,
                "customer_name": self.data.customer_name,
                "days_until_delivery": self.data.days_until_delivery,
                "po_amount": self.data.po_amount,
                "cost_amount": self.data.cost_amount,
                "sale_amount": self.data.sale_amount,
                "gross_profit": self.data.gross_profit,
                "gross_profit_margin": self.data.gross_profit_margin,
                "project_name": self.data.project_name,
                "planned_import_cost_ratio": self.data.planned_import_cost_ratio,
                "actual_import_cost_ratio": self.data.actual_import_cost_ratio,
            },
            "goals": {
                goal.value: {
                    "status": eval.status.value,
                    "reason": eval.reason,
                    "confidence": eval.confidence,
                }
                for goal, eval in self.goal_evaluations.evaluations.items()
            },
            "decisions": [
                {
                    "decision": d.decision.value,
                    "priority": d.priority,
                    "reason": d.reason,
                    "confidence": d.confidence,
                    "triggered_by_goals": [g.value for g in d.triggered_by_goals],
                    "business_rule": d.business_rule,
                }
                for d in self.decisions
            ],
            "actions": [
                {
                    "action_id": a.action_id,
                    "title": a.title,
                    "description": a.description,
                    "condition": a.condition,
                    "priority": a.priority,
                    "related_state": a.related_state.value,
                    "related_goal": a.related_goal.value if a.related_goal else None,
                    "decision_source": a.decision_source.value if a.decision_source else None,
                    "confidence": a.confidence,
                    "due_date": a.due_date.isoformat() if a.due_date else None,
                }
                for a in self.actions
            ],
        }