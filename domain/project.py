"""Project AI Domain Model - Core entities and value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ProjectState(Enum):
    """All possible states a project can be in."""

    INITIATED = "initiated"                         # PO created, awaiting delivery
    DELIVERY_RECEIVED = "delivery_received"         # Delivered, awaiting invoice
    AWAITING_PAYMENT = "awaiting_payment"          # Invoiced, awaiting payment
    COST_UNCONFIRMED = "cost_unconfirmed"          # Cost not yet confirmed
    GROSS_PROFIT_UNCONFIRMED = "gp_unconfirmed"   # Profit not yet calculated
    GROSS_PROFIT_DEGRADED = "gp_degraded"          # Margin < 15%
    COMPLETED = "completed"                         # All settled

    # Alert states (highest priority)
    DELIVERY_OVERDUE = "delivery_overdue"           # Late delivery
    PAYMENT_OVERDUE = "payment_overdue"             # Late payment
    COST_DISCREPANCY = "cost_discrepancy"           # Unexpected cost
    CUSTOMER_CONFIRMATION_NEEDED = "customer_confirmation_needed"


class ProjectGoal(Enum):
    """Business goals for each project."""

    MEET_DEADLINE = "meet_deadline"
    SECURE_MARGIN = "secure_margin"
    CONFIRM_COST = "confirm_cost"
    PROCESS_PAYMENT = "process_payment"
    CUSTOMER_SATISFACTION = "customer_satisfaction"


class GoalStatus(Enum):
    """Status of a goal evaluation."""

    ACHIEVED = "achieved"
    AT_RISK = "at_risk"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ProjectDecision(Enum):
    """AI recommendations on what action to take."""

    EXPEDITE_PO = "expedite_po"
    FOLLOW_UP_SUPPLIER = "follow_up_supplier"
    IMPROVE_MARGIN = "improve_margin"
    PROCESS_PAYMENT = "process_payment"
    REQUEST_COST_CONFIRMATION = "request_cost_confirmation"
    REQUEST_CUSTOMER_CONFIRMATION = "request_customer_confirmation"
    ESCALATE_TO_MANAGER = "escalate_to_manager"


class ProjectEventType(Enum):
    """Types of business events that trigger state changes."""

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


@dataclass(frozen=True)
class ProjectData:
    """All factual data about a project - immutable value object."""

    # Identity
    project_id: str                         # Unique project identifier
    po_number: str                          # Purchase order number

    # Supplier info
    supplier_id: str
    supplier_name: str

    # Customer/Dealer info
    customer_id: str
    customer_name: str

    # Timeline
    po_created_date: datetime
    po_required_delivery_date: datetime

    # Optional supplier info
    supplier_phone: str | None = None
    supplier_email: str | None = None
    supplier_address: str | None = None

    # Optional customer info
    customer_phone: str | None = None
    customer_email: str | None = None
    customer_address: str | None = None

    # Optional timeline
    po_required_delivery_date_alt: datetime | None = None  # Alternate/backup date
    actual_delivery_date: datetime | None = None
    invoice_date: datetime | None = None
    payment_due_date: datetime | None = None
    actual_payment_date: datetime | None = None

    # Products
    products: list[dict[str, Any]] = field(default_factory=list)  # List of {id, name, qty, price}

    # Financial
    po_amount: float | None = None                  # Total PO amount
    supplier_invoice_amount: float | None = None    # What supplier invoiced
    cost_amount: float | None = None                # Confirmed cost
    sale_amount: float | None = None                # Selling price
    gross_profit: float | None = None               # Absolute profit
    gross_profit_margin: float | None = None        # Profit %
    cost_confirmed: bool = False
    profit_confirmed: bool = False

    # Status flags
    delivery_status: str | None = None      # "pending", "partial", "complete"
    payment_status: str | None = None       # "unpaid", "partial", "paid"

    # Traceability
    data_source_tables: list[str] = field(default_factory=list)
    data_retrieved_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "project_id": self.project_id,
            "po_number": self.po_number,
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier_name,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "po_created_date": self.po_created_date.isoformat() if self.po_created_date else None,
            "po_required_delivery_date": self.po_required_delivery_date.isoformat() if self.po_required_delivery_date else None,
            "actual_delivery_date": self.actual_delivery_date.isoformat() if self.actual_delivery_date else None,
            "invoice_date": self.invoice_date.isoformat() if self.invoice_date else None,
            "payment_due_date": self.payment_due_date.isoformat() if self.payment_due_date else None,
            "actual_payment_date": self.actual_payment_date.isoformat() if self.actual_payment_date else None,
            "products": self.products,
            "po_amount": self.po_amount,
            "supplier_invoice_amount": self.supplier_invoice_amount,
            "cost_amount": self.cost_amount,
            "sale_amount": self.sale_amount,
            "gross_profit": self.gross_profit,
            "gross_profit_margin": self.gross_profit_margin,
            "cost_confirmed": self.cost_confirmed,
            "profit_confirmed": self.profit_confirmed,
            "delivery_status": self.delivery_status,
            "payment_status": self.payment_status,
            "data_source_tables": self.data_source_tables,
        }


@dataclass(frozen=True)
class ProjectEvent:
    """Business event that occurred in a project - immutable audit record."""

    # Identity
    event_id: str                           # Unique event identifier
    project_id: str                         # Which project
    event_type: ProjectEventType            # Type of event

    # When and where
    event_time: datetime                    # When did this happen
    source_table: str                       # Which DB table (e.g., 仕入)

    # Business context
    business_meaning: str                   # What does this event mean?
    impact_summary: str                     # How does it impact the project?

    # Optional: State change
    before_state: ProjectState | None = None   # Previous state
    after_state: ProjectState | None = None    # New state after this event

    # Optional: Details
    source_record_id: str | None = None     # Which record in that table
    changed_fields: dict[str, tuple[Any, Any]] = field(
        default_factory=dict
    )  # {field_name: (old_value, new_value)}

    # Traceability
    trace_id: str | None = None            # Links to execution trace
    executed_sql: str | None = None        # SQL that detected this event
    source_rule: str | None = None         # Which business rule triggered this

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "project_id": self.project_id,
            "event_type": self.event_type.value,
            "event_time": self.event_time.isoformat(),
            "source_table": self.source_table,
            "source_record_id": self.source_record_id,
            "before_state": self.before_state.value if self.before_state else None,
            "after_state": self.after_state.value if self.after_state else None,
            "changed_fields": self.changed_fields,
            "business_meaning": self.business_meaning,
            "impact_summary": self.impact_summary,
            "trace_id": self.trace_id,
            "executed_sql": self.executed_sql,
            "source_rule": self.source_rule,
        }


@dataclass(frozen=True)
class ProjectEvents:
    """Complete event history for a project."""

    project_id: str
    events: list[ProjectEvent] = field(default_factory=list)
    event_count: int = 0
    last_event_time: datetime | None = None
    events_by_type: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_id": self.project_id,
            "event_count": self.event_count,
            "last_event_time": self.last_event_time.isoformat() if self.last_event_time else None,
            "events": [e.to_dict() for e in self.events],
            "events_by_type": self.events_by_type,
        }

    def get_events_by_type(self, event_type: ProjectEventType) -> list[ProjectEvent]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_recent_events(self, limit: int = 10) -> list[ProjectEvent]:
        """Get most recent events."""
        return sorted(self.events, key=lambda e: e.event_time, reverse=True)[:limit]


@dataclass(frozen=True)
class GoalEvaluation:
    """Evaluation of a single goal against project data."""

    goal: ProjectGoal
    status: GoalStatus
    reason: str                             # Why this status?
    confidence: float                       # 0.0 to 1.0


@dataclass(frozen=True)
class GoalEvaluations:
    """All goal evaluations for a project."""

    project_id: str
    evaluations: dict[ProjectGoal, GoalEvaluation] = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=datetime.now)

    def get_at_risk_goals(self) -> list[ProjectGoal]:
        """Get all goals that are at risk."""
        return [g for g, e in self.evaluations.items() if e.status in [GoalStatus.AT_RISK, GoalStatus.FAILED]]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_id": self.project_id,
            "evaluations": {
                g.value: {
                    "status": e.status.value,
                    "reason": e.reason,
                    "confidence": e.confidence,
                }
                for g, e in self.evaluations.items()
            },
            "evaluated_at": self.evaluated_at.isoformat(),
        }


@dataclass(frozen=True)
class ProjectDecisionDetail:
    """Details about a single AI decision."""

    decision: ProjectDecision
    priority: int                          # 1 = highest priority
    reason: str                            # Why this decision?
    confidence: float                      # 0.0 to 1.0
    triggered_by_goals: list[ProjectGoal] = field(default_factory=list)
    business_rule: str | None = None       # Which rule triggered this


@dataclass(frozen=True)
class ProjectAction:
    """Concrete action recommended by AI."""

    # Core identity
    action_id: str
    project_id: str
    action_number: int                     # Sequence in project

    # What to do
    title: str
    description: str
    action_type: str                       # "phone_call", "email", "data_entry", etc.
    priority: str                          # "high", "medium", "low"

    # Why (traceability)
    related_state: ProjectState
    related_goal: ProjectGoal | None
    decision_source: ProjectDecision

    # Where the data comes from
    source_tables: list[str]
    source_record_ids: dict[str, Any]      # e.g., {"po_id": "123", "supplier_id": "456"}
    condition: str                         # The condition that triggered this

    # AI traceability (explainability)
    trace_id: str
    executed_sql: str | None               # SQL used to determine action
    business_rule_applied: str             # e.g., "DELIVERY_SLA_7DAYS"
    confidence: float                      # 0.0 to 1.0

    # Timing
    created_at: datetime
    due_date: datetime | None = None
    status: str = "pending"                # "pending", "in_progress", "completed", "cancelled"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "action_id": self.action_id,
            "project_id": self.project_id,
            "action_number": self.action_number,
            "title": self.title,
            "description": self.description,
            "action_type": self.action_type,
            "priority": self.priority,
            "related_state": self.related_state.value,
            "related_goal": self.related_goal.value if self.related_goal else None,
            "decision_source": self.decision_source.value,
            "source_tables": self.source_tables,
            "source_record_ids": self.source_record_ids,
            "condition": self.condition,
            "trace_id": self.trace_id,
            "executed_sql": self.executed_sql,
            "business_rule_applied": self.business_rule_applied,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
        }


@dataclass
class ProjectAggregate:
    """Complete AI view of a single business project."""

    # Identity
    project_id: str
    po_number: str
    trace_id: str

    # The 8 core elements
    events: ProjectEvents                       # What happened (events log)
    data: ProjectData                           # What we know (current facts)
    state: ProjectState                         # What situation it's in
    goal_evaluations: GoalEvaluations           # What we want & status
    decisions: list[ProjectDecisionDetail]      # What AI recommends
    actions: list[ProjectAction]                # Concrete next steps

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    assigned_to: str | None = None              # Owner
    priority: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "project_id": self.project_id,
            "po_number": self.po_number,
            "trace_id": self.trace_id,
            "events": self.events.to_dict(),
            "data": self.data.to_dict(),
            "state": self.state.value,
            "goal_evaluations": self.goal_evaluations.to_dict(),
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
            "actions": [a.to_dict() for a in self.actions],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "assigned_to": self.assigned_to,
            "priority": self.priority,
        }

    def get_primary_action(self) -> ProjectAction | None:
        """Get the highest priority action to show in Today Actions."""
        if not self.actions:
            return None
        return sorted(self.actions, key=lambda a: (a.priority == "high", -a.confidence))[0]

    def get_at_risk_goals(self) -> list[ProjectGoal]:
        """Get all goals that are at risk."""
        return self.goal_evaluations.get_at_risk_goals()
