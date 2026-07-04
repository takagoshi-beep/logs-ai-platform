"""Project Service - Orchestrates domain model to build complete project understanding."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from domain.project import (
    GoalEvaluation,
    GoalEvaluations,
    GoalStatus,
    ProjectAction,
    ProjectAggregate,
    ProjectData,
    ProjectDecision,
    ProjectDecisionDetail,
    ProjectEvent,
    ProjectEventType,
    ProjectEvents,
    ProjectGoal,
    ProjectState,
)
from storage.provider import create_storage_repository
from storage.repository import BaseRepository


class ProjectService:
    """Service for building complete ProjectAggregate from database."""

    def __init__(self, db_path: Path | None = None):
        """Initialize service with database connection."""
        if db_path is None:
            # Try to import app config, but fall back to default if not available
            try:
                from app import main as app_main
                db_path = app_main.DEFAULT_DB_PATH
            except (ImportError, ModuleNotFoundError, AttributeError):
                db_path = Path("data/sqlite/logsys.db")
        self.db_path = db_path

    def _open_repo(self) -> BaseRepository:
        """Open repository connection."""
        return create_storage_repository(db_path=self.db_path)

    def _generate_trace_id(self, prefix: str = "project") -> str:
        """Generate unique trace ID for this analysis."""
        return f"{prefix}-{uuid.uuid4().hex[:8]}"

    def _query_projects_from_db(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Query database to find all project candidates (Purchase Orders).
        Returns list of project records with a "project_id" key.
        """
        repo = self._open_repo()
        try:
            sql = 'SELECT DISTINCT "ID" AS project_id FROM purchase_orders ORDER BY "ID" DESC LIMIT ?'
            rows = repo.fetch_all(sql, (limit,))
            return rows or []
        except Exception as e:
            print(f"Error querying projects: {e}")
            return []
        finally:
            repo.close()

    def _build_project_data(self, project_id: str) -> ProjectData | None:
        """
        Build ProjectData by querying purchase_orders (real Supabase public schema).
        """
        repo = self._open_repo()
        try:
            po_sql = (
                'SELECT "PO_No", "仕入先ID", "仕入先名", "顧客ID", "顧客名", '
                '"PO発行日", "顧客納品日", "納品日", '
                '"合計発注金額", "合計売上原価", "合計売上金額" '
                'FROM purchase_orders WHERE "ID" = ?'
            )
            po_record = repo.fetch_one(po_sql, (project_id,))
            if not po_record:
                return None

            try:
                po_dict = po_record

                po_number = po_dict.get("PO_No", "") or ""
                supplier_id = str(po_dict.get("仕入先ID", "") or "unknown")
                supplier_name = po_dict.get("仕入先名", "") or ""
                customer_id = str(po_dict.get("顧客ID", "") or "unknown")
                customer_name = po_dict.get("顧客名", "") or ""

                def parse_date(date_val: Any) -> datetime | None:
                    if not date_val:
                        return None
                    if isinstance(date_val, datetime):
                        return date_val
                    try:
                        return datetime.fromisoformat(str(date_val).replace("Z", "+00:00"))
                    except Exception:
                        return None

                po_created = parse_date(po_dict.get("PO発行日")) or datetime.now()
                po_required_delivery = parse_date(po_dict.get("顧客納品日")) or (datetime.now() + timedelta(days=30))

                po_amount = float(po_dict.get("合計発注金額", 0) or 0) or None
                cost_amount = float(po_dict.get("合計売上原価", 0) or 0) or None
                sale_amount = float(po_dict.get("合計売上金額", 0) or 0) or None
                gross_profit = None
                gross_profit_margin = None
                if cost_amount is not None and sale_amount is not None:
                    gross_profit = sale_amount - cost_amount
                    if sale_amount:
                        # NOTE: gross_profit_margin is stored as a fraction (0.15 = 15%),
                        # matching how _determine_state/_evaluate_goals compare it below.
                        gross_profit_margin = gross_profit / sale_amount

                project_data = ProjectData(
                    project_id=project_id,
                    po_number=po_number or f"PO-{project_id}",
                    supplier_id=supplier_id,
                    supplier_name=supplier_name or "Supplier",
                    customer_id=customer_id,
                    customer_name=customer_name or "Customer",
                    po_created_date=po_created,
                    po_required_delivery_date=po_required_delivery,
                    supplier_phone=None,
                    supplier_email=None,
                    supplier_address=None,
                    customer_phone=None,
                    customer_email=None,
                    customer_address=None,
                    po_required_delivery_date_alt=None,
                    actual_delivery_date=parse_date(po_dict.get("納品日")),
                    invoice_date=None,
                    payment_due_date=None,
                    actual_payment_date=None,
                    products=[],
                    po_amount=po_amount,
                    supplier_invoice_amount=None,
                    cost_amount=cost_amount,
                    sale_amount=sale_amount,
                    gross_profit=gross_profit,
                    gross_profit_margin=gross_profit_margin,
                    cost_confirmed=cost_amount is not None,
                    profit_confirmed=gross_profit is not None,
                    delivery_status="pending",
                    payment_status="unpaid",
                    data_source_tables=["purchase_orders"],
                )
                return project_data

            except (KeyError, TypeError, ValueError) as e:
                print(f"Error parsing project data: {e}")
                # Return minimal ProjectData as fallback
                return ProjectData(
                    project_id=project_id,
                    po_number=f"PO-{project_id}",
                    supplier_id="unknown",
                    supplier_name="Supplier",
                    customer_id="unknown",
                    customer_name="Customer",
                    po_created_date=datetime.now(),
                    po_required_delivery_date=datetime.now() + timedelta(days=30),
                    delivery_status="pending",
                    payment_status="unpaid",
                    data_source_tables=["purchase_orders"],
                )
        finally:
            repo.close()

    def _generate_project_events(self, data: ProjectData, trace_id: str) -> ProjectEvents:
        """Generate project events from project data."""
        events = []
        now = datetime.now()

        # Event 1: Project created
        if data.po_created_date:
            events.append(
                ProjectEvent(
                    event_id=f"{data.project_id}-evt-001",
                    project_id=data.project_id,
                    event_type=ProjectEventType.PROJECT_CREATED,
                    event_time=data.po_created_date,
                    source_table="purchase_orders",
                    source_record_id=data.project_id,
                    before_state=None,
                    after_state=ProjectState.INITIATED,
                    business_meaning="New purchase order created",
                    impact_summary="Project initiated, awaiting delivery",
                    trace_id=trace_id,
                    source_rule="AUTO_PROJECT_INIT",
                )
            )

        # Event 2: Sales registered (if sale_amount exists)
        if data.sale_amount and data.sale_amount > 0:
            events.append(
                ProjectEvent(
                    event_id=f"{data.project_id}-evt-002",
                    project_id=data.project_id,
                    event_type=ProjectEventType.SALES_REGISTERED,
                    event_time=now,
                    source_table="purchase_orders",
                    changed_fields={"sale_amount": (None, data.sale_amount)},
                    business_meaning=f"Sales registered: {data.sale_amount}",
                    impact_summary="Revenue confirmed for this project",
                    trace_id=trace_id,
                    source_rule="AUTO_SALES_DETECT",
                )
            )

        # Event 3: Purchase registered (if cost_amount exists)
        if data.cost_amount and data.cost_amount > 0:
            events.append(
                ProjectEvent(
                    event_id=f"{data.project_id}-evt-003",
                    project_id=data.project_id,
                    event_type=ProjectEventType.PURCHASE_REGISTERED,
                    event_time=now,
                    source_table="purchase_orders",
                    changed_fields={"cost_amount": (None, data.cost_amount)},
                    business_meaning=f"Purchase cost recorded: {data.cost_amount}",
                    impact_summary="Cost of goods confirmed",
                    trace_id=trace_id,
                    source_rule="AUTO_COST_DETECT",
                )
            )

        # Event 4: Delivery completed
        if data.actual_delivery_date:
            events.append(
                ProjectEvent(
                    event_id=f"{data.project_id}-evt-004",
                    project_id=data.project_id,
                    event_type=ProjectEventType.DELIVERY_COMPLETED,
                    event_time=data.actual_delivery_date,
                    source_table="purchase_orders",
                    before_state=ProjectState.INITIATED,
                    after_state=ProjectState.DELIVERY_RECEIVED,
                    business_meaning=f"Delivery completed on {data.actual_delivery_date.date()}",
                    impact_summary="Goods received, moving to billing stage",
                    trace_id=trace_id,
                    source_rule="AUTO_DELIVERY_DETECT",
                )
            )

        # Event 5: Invoice received
        if data.invoice_date:
            events.append(
                ProjectEvent(
                    event_id=f"{data.project_id}-evt-005",
                    project_id=data.project_id,
                    event_type=ProjectEventType.INVOICE_RECEIVED,
                    event_time=data.invoice_date,
                    source_table="purchase_orders",
                    before_state=ProjectState.DELIVERY_RECEIVED,
                    after_state=ProjectState.AWAITING_PAYMENT,
                    changed_fields={"invoice_amount": (None, data.supplier_invoice_amount)},
                    business_meaning=f"Invoice received: {data.supplier_invoice_amount}",
                    impact_summary="Payment due, processing required",
                    trace_id=trace_id,
                    source_rule="AUTO_INVOICE_DETECT",
                )
            )

        # Event 6: Gross profit recalculated
        if data.gross_profit_margin is not None:
            events.append(
                ProjectEvent(
                    event_id=f"{data.project_id}-evt-006",
                    project_id=data.project_id,
                    event_type=ProjectEventType.GROSS_PROFIT_RECALCULATED,
                    event_time=now,
                    source_table="purchase_orders",
                    changed_fields={"gross_profit_margin": (None, data.gross_profit_margin)},
                    business_meaning=f"Profit margin calculated: {data.gross_profit_margin:.1%}",
                    impact_summary="Profitability analysis complete",
                    trace_id=trace_id,
                    source_rule="AUTO_MARGIN_CALC",
                )
            )

        # Event 7: Gross profit declined (if margin < 15%)
        if data.gross_profit_margin and data.gross_profit_margin < 0.15:
            events.append(
                ProjectEvent(
                    event_id=f"{data.project_id}-evt-007",
                    project_id=data.project_id,
                    event_type=ProjectEventType.GROSS_PROFIT_DECLINED,
                    event_time=now,
                    source_table="purchase_orders",
                    before_state=ProjectState.GROSS_PROFIT_UNCONFIRMED,
                    after_state=ProjectState.GROSS_PROFIT_DEGRADED,
                    changed_fields={"gross_profit_margin": (0.15, data.gross_profit_margin)},
                    business_meaning=f"Margin {data.gross_profit_margin:.1%} below 15% threshold",
                    impact_summary="ALERT: Profitability below target, review needed",
                    trace_id=trace_id,
                    source_rule="MARGIN_THRESHOLD_CHECK",
                )
            )

        # Event 8: Delivery risk detected
        if not data.actual_delivery_date and data.po_required_delivery_date:
            days_until = (data.po_required_delivery_date.date() - now.date()).days
            if days_until < 0:
                events.append(
                    ProjectEvent(
                        event_id=f"{data.project_id}-evt-008",
                        project_id=data.project_id,
                        event_type=ProjectEventType.DELIVERY_RISK_DETECTED,
                        event_time=now,
                        source_table="purchase_orders",
                        before_state=ProjectState.INITIATED,
                        after_state=ProjectState.DELIVERY_OVERDUE,
                        business_meaning=f"Delivery overdue by {-days_until} days",
                        impact_summary="ALERT: Late delivery, supplier follow-up required",
                        trace_id=trace_id,
                        source_rule="DELIVERY_SLA_CHECK",
                    )
                )

        # Event 9: Payment processed
        if data.actual_payment_date:
            events.append(
                ProjectEvent(
                    event_id=f"{data.project_id}-evt-009",
                    project_id=data.project_id,
                    event_type=ProjectEventType.PAYMENT_PROCESSED,
                    event_time=data.actual_payment_date,
                    source_table="purchase_orders",
                    before_state=ProjectState.AWAITING_PAYMENT,
                    after_state=ProjectState.COMPLETED,
                    business_meaning=f"Payment processed on {data.actual_payment_date.date()}",
                    impact_summary="Project payment settled",
                    trace_id=trace_id,
                    source_rule="AUTO_PAYMENT_DETECT",
                )
            )

        # Sort events by time
        events.sort(key=lambda e: e.event_time)

        # Build ProjectEvents
        events_dict = {}
        for event in events:
            event_type_val = event.event_type.value
            events_dict[event_type_val] = events_dict.get(event_type_val, 0) + 1

        return ProjectEvents(
            project_id=data.project_id,
            events=events,
            event_count=len(events),
            last_event_time=events[-1].event_time if events else None,
            events_by_type=events_dict,
        )

    def _determine_state(self, data: ProjectData) -> ProjectState:
        """
        Determine project state based on data.
        Checks in priority order (alert states first, then normal flow).
        """
        today = datetime.now().date()

        # Alert states (highest priority)
        if data.po_required_delivery_date.date() < today and not data.actual_delivery_date:
            return ProjectState.DELIVERY_OVERDUE

        if data.payment_due_date and data.payment_due_date.date() < today and not data.actual_payment_date:
            return ProjectState.PAYMENT_OVERDUE

        if data.cost_amount and data.po_amount and data.cost_amount > data.po_amount * 1.1:
            return ProjectState.COST_DISCREPANCY

        # Normal flow
        if not data.actual_delivery_date:
            return ProjectState.INITIATED

        if not data.invoice_date:
            return ProjectState.DELIVERY_RECEIVED

        if not data.actual_payment_date:
            return ProjectState.AWAITING_PAYMENT

        if not data.cost_confirmed:
            return ProjectState.COST_UNCONFIRMED

        if not data.profit_confirmed:
            return ProjectState.GROSS_PROFIT_UNCONFIRMED

        if data.gross_profit_margin and data.gross_profit_margin < 0.15:
            return ProjectState.GROSS_PROFIT_DEGRADED

        return ProjectState.COMPLETED

    def _evaluate_goals(self, data: ProjectData, state: ProjectState) -> GoalEvaluations:
        """Evaluate all goals against project data."""
        today = datetime.now().date()
        evaluations = {}

        # Goal 1: Meet deadline
        if data.actual_delivery_date:
            if data.actual_delivery_date.date() <= data.po_required_delivery_date.date():
                status = GoalStatus.ACHIEVED
                reason = f"Delivered on time ({data.actual_delivery_date.date()})"
            else:
                status = GoalStatus.FAILED
                reason = f"Delivered late ({data.actual_delivery_date.date()})"
            confidence = 0.99
        else:
            days_until = (data.po_required_delivery_date.date() - today).days
            if days_until < 0:
                status = GoalStatus.FAILED
                reason = f"Overdue by {-days_until} days"
                confidence = 0.99
            elif days_until < 7:
                status = GoalStatus.AT_RISK
                reason = f"Delivery due in {days_until} days"
                confidence = 0.95
            else:
                status = GoalStatus.ACHIEVED
                reason = f"On track, {days_until} days until deadline"
                confidence = 0.9

        evaluations[ProjectGoal.MEET_DEADLINE] = GoalEvaluation(
            goal=ProjectGoal.MEET_DEADLINE,
            status=status,
            reason=reason,
            confidence=confidence,
        )

        # Goal 2: Secure margin
        if data.gross_profit_margin is not None:
            if data.gross_profit_margin >= 0.15:
                status = GoalStatus.ACHIEVED
                reason = f"Margin {data.gross_profit_margin:.1%} meets target"
            else:
                status = GoalStatus.FAILED
                reason = f"Margin {data.gross_profit_margin:.1%} below target 15%"
            confidence = 0.95
        else:
            status = GoalStatus.UNKNOWN
            reason = "Profit not yet calculated"
            confidence = 0.5

        evaluations[ProjectGoal.SECURE_MARGIN] = GoalEvaluation(
            goal=ProjectGoal.SECURE_MARGIN,
            status=status,
            reason=reason,
            confidence=confidence,
        )

        # Goal 3: Confirm cost
        if data.cost_confirmed:
            status = GoalStatus.ACHIEVED
            reason = "Cost has been confirmed"
            confidence = 0.99
        elif state in [ProjectState.INITIATED, ProjectState.DELIVERY_RECEIVED]:
            status = GoalStatus.AT_RISK
            reason = "Cost confirmation pending"
            confidence = 0.9
        else:
            status = GoalStatus.UNKNOWN
            reason = "Cost status unclear"
            confidence = 0.5

        evaluations[ProjectGoal.CONFIRM_COST] = GoalEvaluation(
            goal=ProjectGoal.CONFIRM_COST,
            status=status,
            reason=reason,
            confidence=confidence,
        )

        # Goal 4: Process payment
        if data.actual_payment_date:
            status = GoalStatus.ACHIEVED
            reason = "Payment processed"
            confidence = 0.99
        elif state == ProjectState.AWAITING_PAYMENT:
            status = GoalStatus.AT_RISK
            reason = "Payment awaiting processing"
            confidence = 0.95
        else:
            status = GoalStatus.UNKNOWN
            reason = "Payment status unclear"
            confidence = 0.5

        evaluations[ProjectGoal.PROCESS_PAYMENT] = GoalEvaluation(
            goal=ProjectGoal.PROCESS_PAYMENT,
            status=status,
            reason=reason,
            confidence=confidence,
        )

        # Goal 5: Customer satisfaction
        status = GoalStatus.ACHIEVED
        reason = "No issues detected"
        confidence = 0.7

        evaluations[ProjectGoal.CUSTOMER_SATISFACTION] = GoalEvaluation(
            goal=ProjectGoal.CUSTOMER_SATISFACTION,
            status=status,
            reason=reason,
            confidence=confidence,
        )

        return GoalEvaluations(project_id=data.project_id, evaluations=evaluations)

    def _generate_decisions(
        self,
        data: ProjectData,
        state: ProjectState,
        goals: GoalEvaluations,
    ) -> list[ProjectDecisionDetail]:
        """Generate AI decisions from state and goals."""
        decisions = []

        # Decision 1: Expedite PO
        if goals.evaluations[ProjectGoal.MEET_DEADLINE].status == GoalStatus.AT_RISK:
            if state == ProjectState.INITIATED:
                decisions.append(
                    ProjectDecisionDetail(
                        decision=ProjectDecision.EXPEDITE_PO,
                        priority=1,
                        reason="Delivery deadline approaching and PO not yet delivered",
                        confidence=0.9,
                        triggered_by_goals=[ProjectGoal.MEET_DEADLINE],
                        business_rule="DELIVERY_SLA_7DAYS",
                    )
                )

        # Decision 2: Follow up supplier
        if state in [ProjectState.DELIVERY_OVERDUE]:
            decisions.append(
                ProjectDecisionDetail(
                    decision=ProjectDecision.FOLLOW_UP_SUPPLIER,
                    priority=1,
                    reason=f"Delivery overdue since {data.po_required_delivery_date.date()}",
                    confidence=0.99,
                    triggered_by_goals=[ProjectGoal.MEET_DEADLINE],
                    business_rule="DELIVERY_SLA_CRITICAL",
                )
            )

        # Decision 3: Improve margin
        if goals.evaluations[ProjectGoal.SECURE_MARGIN].status == GoalStatus.FAILED:
            if state in [ProjectState.INITIATED, ProjectState.DELIVERY_RECEIVED, ProjectState.AWAITING_PAYMENT]:
                decisions.append(
                    ProjectDecisionDetail(
                        decision=ProjectDecision.IMPROVE_MARGIN,
                        priority=2,
                        reason=f"Margin {data.gross_profit_margin:.1%} below 15% target",
                        confidence=0.92,
                        triggered_by_goals=[ProjectGoal.SECURE_MARGIN],
                        business_rule="MARGIN_TARGET_15PERCENT",
                    )
                )

        # Decision 4: Process payment
        if state == ProjectState.AWAITING_PAYMENT:
            decisions.append(
                ProjectDecisionDetail(
                    decision=ProjectDecision.PROCESS_PAYMENT,
                    priority=2,
                    reason="Invoice received, payment due",
                    confidence=0.95,
                    triggered_by_goals=[ProjectGoal.PROCESS_PAYMENT],
                    business_rule="PAYMENT_PROCESSING",
                )
            )

        # Decision 5: Request cost confirmation
        if goals.evaluations[ProjectGoal.CONFIRM_COST].status == GoalStatus.AT_RISK:
            decisions.append(
                ProjectDecisionDetail(
                    decision=ProjectDecision.REQUEST_COST_CONFIRMATION,
                    priority=2,
                    reason="Cost not yet confirmed, needed for margin calculation",
                    confidence=0.88,
                    triggered_by_goals=[ProjectGoal.CONFIRM_COST],
                    business_rule="COST_CONFIRMATION_REQUIRED",
                )
            )

        # Sort by priority
        decisions.sort(key=lambda d: d.priority)
        return decisions

    def _generate_actions(self, data: ProjectData, state: ProjectState, decisions: list[ProjectDecisionDetail], trace_id: str) -> list[ProjectAction]:
        """Generate concrete actions from decisions."""
        actions = []
        action_number = 1

        for decision in decisions:
            # Map decision to action
            if decision.decision == ProjectDecision.FOLLOW_UP_SUPPLIER:
                actions.append(
                    ProjectAction(
                        action_id=f"{data.project_id}-{action_number:03d}",
                        project_id=data.project_id,
                        action_number=action_number,
                        title=f"Follow up on overdue delivery for {data.po_number}",
                        description=f"PO {data.po_number} from {data.supplier_name} was due {data.po_required_delivery_date.date()}. "
                                    f"Not received as of {datetime.now().date()}. Contact supplier immediately.",
                        action_type="phone_call",
                        priority="high",
                        related_state=state,
                        related_goal=ProjectGoal.MEET_DEADLINE,
                        decision_source=decision.decision,
                        source_tables=["purchase_orders"],
                        source_record_ids={"po_id": data.project_id, "supplier_id": data.supplier_id},
                        condition=f"delivery_overdue AND supplier_phone={data.supplier_phone}",
                        trace_id=trace_id,
                        executed_sql=f'SELECT * FROM purchase_orders WHERE "ID"=\'{data.project_id}\'',
                        business_rule_applied="DELIVERY_SLA_CRITICAL",
                        confidence=decision.confidence,
                        created_at=datetime.now(),
                        due_date=datetime.now(),
                    )
                )
                action_number += 1

            elif decision.decision == ProjectDecision.IMPROVE_MARGIN:
                actions.append(
                    ProjectAction(
                        action_id=f"{data.project_id}-{action_number:03d}",
                        project_id=data.project_id,
                        action_number=action_number,
                        title=f"Investigate margin for {data.po_number}",
                        description=f"PO {data.po_number} has margin {data.gross_profit_margin:.1%}, below 15% target. "
                                    f"Review supplier cost and pricing. Consider alternative suppliers.",
                        action_type="data_entry",
                        priority="medium",
                        related_state=state,
                        related_goal=ProjectGoal.SECURE_MARGIN,
                        decision_source=decision.decision,
                        source_tables=["purchase_orders"],
                        source_record_ids={"po_id": data.project_id},
                        condition="margin < 0.15",
                        trace_id=trace_id,
                        executed_sql=f'SELECT * FROM purchase_orders WHERE "ID"=\'{data.project_id}\'',
                        business_rule_applied="MARGIN_TARGET_15PERCENT",
                        confidence=decision.confidence,
                        created_at=datetime.now(),
                        due_date=datetime.now() + timedelta(days=1),
                    )
                )
                action_number += 1

            elif decision.decision == ProjectDecision.PROCESS_PAYMENT:
                actions.append(
                    ProjectAction(
                        action_id=f"{data.project_id}-{action_number:03d}",
                        project_id=data.project_id,
                        action_number=action_number,
                        title=f"Process payment for {data.po_number}",
                        description=f"Invoice received for PO {data.po_number} from {data.supplier_name}. "
                                    f"Amount: {data.supplier_invoice_amount}. Due date: {data.payment_due_date.date() if data.payment_due_date else 'N/A'}",
                        action_type="data_entry",
                        priority="medium",
                        related_state=state,
                        related_goal=ProjectGoal.PROCESS_PAYMENT,
                        decision_source=decision.decision,
                        source_tables=["purchase_orders"],
                        source_record_ids={"po_id": data.project_id, "invoice_id": data.project_id},
                        condition="awaiting_payment",
                        trace_id=trace_id,
                        executed_sql=f'SELECT * FROM purchase_orders WHERE "ID"=\'{data.project_id}\'',
                        business_rule_applied="PAYMENT_PROCESSING",
                        confidence=decision.confidence,
                        created_at=datetime.now(),
                        due_date=data.payment_due_date or (datetime.now() + timedelta(days=1)),
                    )
                )
                action_number += 1

        return actions

    def build_project_aggregate(self, project_id: str) -> ProjectAggregate | None:
        """Build complete ProjectAggregate for a single project."""
        trace_id = self._generate_trace_id("project-agg")

        try:
            # Step 1: Build project data
            data = self._build_project_data(project_id)
            if not data:
                return None

            # Step 2: Generate events from data
            events = self._generate_project_events(data, trace_id)

            # Step 3: Determine state (using data + events context)
            state = self._determine_state(data)

            # Step 4: Evaluate goals
            goals = self._evaluate_goals(data, state)

            # Step 5: Generate decisions
            decisions = self._generate_decisions(data, state, goals)

            # Step 6: Generate actions
            actions = self._generate_actions(data, state, decisions, trace_id)

            # Step 7: Create aggregate
            aggregate = ProjectAggregate(
                project_id=project_id,
                po_number=data.po_number,
                trace_id=trace_id,
                events=events,
                data=data,
                state=state,
                goal_evaluations=goals,
                decisions=decisions,
                actions=actions,
                priority="high" if state in [ProjectState.DELIVERY_OVERDUE, ProjectState.PAYMENT_OVERDUE] else "medium",
            )

            return aggregate

        except Exception as e:
            print(f"Error building project aggregate: {e}")
            import traceback
            traceback.print_exc()
            return None

    def build_multiple_projects(self, limit: int = 10) -> list[ProjectAggregate]:
        """Build ProjectAggregates for multiple projects."""
        projects = self._query_projects_from_db(limit=limit)
        aggregates = []

        for project_record in projects:
            project_id = project_record.get("project_id")
            if project_id:
                agg = self.build_project_aggregate(project_id)
                if agg:
                    aggregates.append(agg)

        return aggregates