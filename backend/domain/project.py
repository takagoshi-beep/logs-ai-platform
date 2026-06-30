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
    GROSS_PROFIT_UNCONFIRMED = "gross_profit_unconfirmed"
    GROSS_PROFIT_DEGRADED = "gross_profit_degraded"
    COMPLETED = "completed"
    DELIVERY_OVERDUE = "delivery_overdue"
    PAYMENT_OVERDUE = "payment_overdue"
    COST_DISCREPANCY = "cost_discrepancy"
    CUSTOMER_CONFIRMATION_NEEDED = "customer_confirmation_needed"


class ProjectGoal(str, Enum):
    """Business objectives for each project."""
    MEET_DEADLINE = "meet_deadline"
    SECURE_MARGIN = "secure_margin"
    CONFIRM_COST = "confirm_cost"
    PROCESS_PAYMENT = "process_payment"
    CUSTOMER_SATISFACTION = "customer_satisfaction"


class ProjectDecision(str, Enum):
    """AI decisions triggered by state and goal failures."""
    EXPEDITE_PO = "expedite_po"
    REQUEST_COST_CONFIRMATION = "request_cost_confirmation"
    IMPROVE_MARGIN = "improve_margin"
    PROCESS_PAYMENT_IMMEDIATELY = "process_payment_immediately"
    CONTACT_CUSTOMER = "contact_customer"
    ESCALATE_TO_MANAGEMENT = "escalate_to_management"
    DOCUMENT_VARIANCE = "document_variance"


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
    before_state: Optional[ProjectState] = None
    after_state: Optional[ProjectState] = None
    changed_fields: Optional[dict[str, Any]] = None
    executed_sql: Optional[str] = None
    source_rule: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "project_id": self.project_id,
            "event_type": self.event_type.value,
            "event_time": self.event_time.isoformat(),
            "source_table": self.source_table,
            "business_meaning": self.business_meaning,
            "impact_summary": self.impact_summary,
            "before_state": self.before_state.value if self.before_state else None,
            "after_state": self.after_state.value if self.after_state else None,
            "trace_id": self.trace_id,
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

    @property
    def days_until_delivery(self) -> int:
        delta = self.po_required_delivery_date - datetime.now()
        return max(0, delta.days)

    @property
    def is_overdue(self) -> bool:
        return datetime.now() > self.po_required_delivery_date

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
