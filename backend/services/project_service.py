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
        """Query database to find all project candidates (Purchase Orders with related data)."""
        repo = self._open_repo()
        try:
            sql = "SELECT * FROM 仕入 LIMIT ?"
            rows = repo.fetch_all(sql, (limit,))
            return rows or []
        except Exception as e:
            print(f"Error querying projects: {e}")
            return []
        finally:
            repo.close()

    def _build_project_data(self, project_id: str) -> ProjectData | None:
        """Build ProjectData by querying related information from database."""
        repo = self._open_repo()
        try:
            po_sql = "SELECT * FROM 仕入 WHERE id = ?"
            po_record = repo.fetch_one(po_sql, (project_id,))
            if not po_record:
                return None

            po_dict = dict(po_record) if hasattr(po_record, 'items') else po_record

            def parse_date(date_val: Any) -> datetime | None:
                if not date_val:
                    return None
                if isinstance(date_val, datetime):
                    return date_val
                try:
                    return datetime.fromisoformat(str(date_val).replace("Z", "+00:00"))
                except:
                    return None

            po_number = po_dict.get("po", "") or ""
            supplier_id = str(po_dict.get("仕入先id", "") or "unknown")
            supplier_name = po_dict.get("仕入先名", "") or ""
            customer_id = str(po_dict.get("客先id", "") or "unknown")
            customer_name = po_dict.get("客先名", "") or ""
            po_created = parse_date(po_dict.get("仕入日", None)) or datetime.now()
            po_required_delivery = parse_date(po_dict.get("仕入期日", None)) or (datetime.now() + timedelta(days=30))

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
                actual_delivery_date=parse_date(po_dict.get("納品日", None)),
                invoice_date=None,
                payment_due_date=None,
                actual_payment_date=None,
                products=[],
                po_amount=float(po_dict.get("仕入金額", 0) or 0),
                supplier_invoice_amount=None,
                cost_amount=float(po_dict.get("原価", 0) or 0),
                sale_amount=float(po_dict.get("売上", 0) or 0),
                gross_profit=None,
                gross_profit_margin=None,
            )

            if project_data.cost_amount and project_data.sale_amount:
                project_data.gross_profit = project_data.sale_amount - project_data.cost_amount
                project_data.gross_profit_margin = project_data.profit_margin_pct

            return project_data
        except Exception as e:
            print(f"Error building project data: {e}")
            return None
        finally:
            repo.close()

    def _generate_project_events(self, data: ProjectData, trace_id: str) -> ProjectEvents:
        """Generate business events from project data."""
        events = ProjectEvents(project_id=data.project_id)

        event_id = 1
        now = datetime.now()

        events.add_event(ProjectEvent(
            event_id=f"evt-{event_id}",
            project_id=data.project_id,
            event_type=ProjectEventType.PROJECT_CREATED,
            event_time=data.po_created_date,
            source_table="仕入",
            business_meaning="PO作成 - 新規案件始動",
            impact_summary="プロジェクト開始、納期管理開始",
            trace_id=trace_id,
            after_state=ProjectState.INITIATED,
        ))
        event_id += 1

        if data.sale_amount and data.sale_amount > 0:
            events.add_event(ProjectEvent(
                event_id=f"evt-{event_id}",
                project_id=data.project_id,
                event_type=ProjectEventType.SALES_REGISTERED,
                event_time=now,
                source_table="売上",
                business_meaning="売上登録 - 収入確定",
                impact_summary="売上が確定し、粗利を計算可能に",
                trace_id=trace_id,
                before_state=ProjectState.INITIATED,
                after_state=ProjectState.AWAITING_PAYMENT,
            ))
            event_id += 1

        if data.cost_amount and data.cost_amount > 0:
            events.add_event(ProjectEvent(
                event_id=f"evt-{event_id}",
                project_id=data.project_id,
                event_type=ProjectEventType.PURCHASE_REGISTERED,
                event_time=now,
                source_table="仕入",
                business_meaning="仕入登録 - 原価確定",
                impact_summary="原価が確定し、粗利を計算可能に",
                trace_id=trace_id,
                before_state=ProjectState.INITIATED,
                after_state=ProjectState.COST_UNCONFIRMED,
            ))
            event_id += 1

        if data.actual_delivery_date:
            events.add_event(ProjectEvent(
                event_id=f"evt-{event_id}",
                project_id=data.project_id,
                event_type=ProjectEventType.DELIVERY_COMPLETED,
                event_time=data.actual_delivery_date,
                source_table="仕入",
                business_meaning="納品完了 - 納期達成",
                impact_summary="納期目標達成",
                trace_id=trace_id,
                before_state=ProjectState.INITIATED,
                after_state=ProjectState.DELIVERY_RECEIVED,
            ))
            event_id += 1

        if data.actual_payment_date:
            events.add_event(ProjectEvent(
                event_id=f"evt-{event_id}",
                project_id=data.project_id,
                event_type=ProjectEventType.PAYMENT_PROCESSED,
                event_time=data.actual_payment_date,
                source_table="支払",
                business_meaning="支払完了 - 現金化",
                impact_summary="全資金回収完了",
                trace_id=trace_id,
                before_state=ProjectState.AWAITING_PAYMENT,
                after_state=ProjectState.COMPLETED,
            ))
            event_id += 1

        if data.gross_profit_margin and data.gross_profit_margin >= 15:
            events.add_event(ProjectEvent(
                event_id=f"evt-{event_id}",
                project_id=data.project_id,
                event_type=ProjectEventType.GROSS_PROFIT_RECALCULATED,
                event_time=now,
                source_table="仕入",
                business_meaning="粗利再計算 - 目標達成",
                impact_summary="粗利15%以上確保",
                trace_id=trace_id,
            ))
            event_id += 1
        elif data.gross_profit_margin and data.gross_profit_margin < 15:
            events.add_event(ProjectEvent(
                event_id=f"evt-{event_id}",
                project_id=data.project_id,
                event_type=ProjectEventType.GROSS_PROFIT_DECLINED,
                event_time=now,
                source_table="仕入",
                business_meaning="粗利低下 - リスク検知",
                impact_summary="粗利が15%未満に低下",
                trace_id=trace_id,
                after_state=ProjectState.GROSS_PROFIT_DEGRADED,
            ))
            event_id += 1

        if data.days_until_delivery < 7 and not data.actual_delivery_date:
            events.add_event(ProjectEvent(
                event_id=f"evt-{event_id}",
                project_id=data.project_id,
                event_type=ProjectEventType.DELIVERY_RISK_DETECTED,
                event_time=now,
                source_table="仕入",
                business_meaning="納期リスク検知 - 7日以内",
                impact_summary="納期まで時間が少ない - 急ぎ対応必要",
                trace_id=trace_id,
                after_state=ProjectState.INITIATED,
            ))
            event_id += 1

        return events

    def _determine_state(self, data: ProjectData) -> ProjectState:
        """Determine project state based on data."""
        now = datetime.now()

        if now > data.po_required_delivery_date and not data.actual_delivery_date:
            return ProjectState.DELIVERY_OVERDUE

        if data.actual_delivery_date and data.po_amount and not data.actual_payment_date:
            return ProjectState.AWAITING_PAYMENT

        if data.cost_amount and not data.actual_delivery_date:
            return ProjectState.COST_UNCONFIRMED

        if data.sale_amount and data.cost_amount:
            margin = data.profit_margin_pct
            if margin and margin < 15:
                return ProjectState.GROSS_PROFIT_DEGRADED

        if data.actual_delivery_date and data.actual_payment_date:
            return ProjectState.COMPLETED

        return ProjectState.INITIATED

    def _evaluate_goals(self, data: ProjectData, state: ProjectState) -> GoalEvaluations:
        """Evaluate all business goals for a project."""
        evals = GoalEvaluations(project_id=data.project_id)

        days_until = data.days_until_delivery
        if days_until < 7:
            evals.evaluations[ProjectGoal.MEET_DEADLINE] = GoalEvaluation(
                goal=ProjectGoal.MEET_DEADLINE,
                status=GoalStatus.AT_RISK,
                reason=f"Delivery in {days_until} days (< 7 days)",
                confidence=0.95,
            )
        elif data.actual_delivery_date:
            evals.evaluations[ProjectGoal.MEET_DEADLINE] = GoalEvaluation(
                goal=ProjectGoal.MEET_DEADLINE,
                status=GoalStatus.ACHIEVED,
                reason="Delivery completed",
                confidence=1.0,
            )
        else:
            evals.evaluations[ProjectGoal.MEET_DEADLINE] = GoalEvaluation(
                goal=ProjectGoal.MEET_DEADLINE,
                status=GoalStatus.UNKNOWN,
                reason="Delivery pending",
                confidence=0.5,
            )

        if data.profit_margin_pct and data.profit_margin_pct >= 15:
            evals.evaluations[ProjectGoal.SECURE_MARGIN] = GoalEvaluation(
                goal=ProjectGoal.SECURE_MARGIN,
                status=GoalStatus.ACHIEVED,
                reason=f"Margin {data.profit_margin_pct:.1f}% >= 15%",
                confidence=1.0,
            )
        elif data.profit_margin_pct and data.profit_margin_pct < 15:
            evals.evaluations[ProjectGoal.SECURE_MARGIN] = GoalEvaluation(
                goal=ProjectGoal.SECURE_MARGIN,
                status=GoalStatus.FAILED,
                reason=f"Margin {data.profit_margin_pct:.1f}% < 15%",
                confidence=0.9,
            )
        else:
            evals.evaluations[ProjectGoal.SECURE_MARGIN] = GoalEvaluation(
                goal=ProjectGoal.SECURE_MARGIN,
                status=GoalStatus.UNKNOWN,
                reason="Cost/sale data incomplete",
                confidence=0.5,
            )

        if data.cost_amount:
            evals.evaluations[ProjectGoal.CONFIRM_COST] = GoalEvaluation(
                goal=ProjectGoal.CONFIRM_COST,
                status=GoalStatus.ACHIEVED,
                reason="Cost confirmed",
                confidence=0.9,
            )
        else:
            evals.evaluations[ProjectGoal.CONFIRM_COST] = GoalEvaluation(
                goal=ProjectGoal.CONFIRM_COST,
                status=GoalStatus.AT_RISK,
                reason="Cost not yet confirmed",
                confidence=0.9,
            )

        if data.actual_payment_date:
            evals.evaluations[ProjectGoal.PROCESS_PAYMENT] = GoalEvaluation(
                goal=ProjectGoal.PROCESS_PAYMENT,
                status=GoalStatus.ACHIEVED,
                reason="Payment completed",
                confidence=1.0,
            )
        else:
            evals.evaluations[ProjectGoal.PROCESS_PAYMENT] = GoalEvaluation(
                goal=ProjectGoal.PROCESS_PAYMENT,
                status=GoalStatus.UNKNOWN,
                reason="Payment pending",
                confidence=0.5,
            )

        evals.evaluations[ProjectGoal.CUSTOMER_SATISFACTION] = GoalEvaluation(
            goal=ProjectGoal.CUSTOMER_SATISFACTION,
            status=GoalStatus.UNKNOWN,
            reason="No customer feedback",
            confidence=0.5,
        )

        return evals

    def _generate_decisions(self, data: ProjectData, state: ProjectState, goals: GoalEvaluations) -> list[ProjectDecisionDetail]:
        """Generate decisions from state and goal failures."""
        decisions = []

        goal_dict = goals.evaluations
        meet_deadline_eval = goal_dict.get(ProjectGoal.MEET_DEADLINE)
        secure_margin_eval = goal_dict.get(ProjectGoal.SECURE_MARGIN)
        confirm_cost_eval = goal_dict.get(ProjectGoal.CONFIRM_COST)

        if meet_deadline_eval and meet_deadline_eval.status == GoalStatus.AT_RISK:
            decisions.append(ProjectDecisionDetail(
                decision=ProjectDecision.EXPEDITE_PO,
                priority=1,
                reason="Delivery within 7 days - expedite required",
                confidence=0.95,
                triggered_by_goals=[ProjectGoal.MEET_DEADLINE],
                business_rule="DELIVERY_SLA_7DAYS",
            ))

        if confirm_cost_eval and confirm_cost_eval.status == GoalStatus.AT_RISK:
            decisions.append(ProjectDecisionDetail(
                decision=ProjectDecision.REQUEST_COST_CONFIRMATION,
                priority=2,
                reason="Cost not yet confirmed",
                confidence=0.9,
                triggered_by_goals=[ProjectGoal.CONFIRM_COST],
                business_rule="COST_CONFIRMATION_REQUIRED",
            ))

        if secure_margin_eval and secure_margin_eval.status == GoalStatus.FAILED:
            decisions.append(ProjectDecisionDetail(
                decision=ProjectDecision.IMPROVE_MARGIN,
                priority=3,
                reason=f"Margin below 15% threshold",
                confidence=0.85,
                triggered_by_goals=[ProjectGoal.SECURE_MARGIN],
                business_rule="MARGIN_THRESHOLD_15PCT",
            ))

        return decisions

    def _generate_actions(self, data: ProjectData, state: ProjectState, decisions: list[ProjectDecisionDetail], trace_id: str) -> list[ProjectAction]:
        """Generate concrete actions from decisions."""
        actions = []
        action_id = 1

        for decision in decisions:
            if decision.decision == ProjectDecision.EXPEDITE_PO:
                actions.append(ProjectAction(
                    action_id=f"act-{action_id}",
                    project_id=data.project_id,
                    title=f"仕入先へ納期急ぎ連絡: {data.po_number}",
                    description=f"納期まで{data.days_until_delivery}日。{data.supplier_name}に急ぎ対応を依頼してください。",
                    priority="high",
                    related_state=state,
                    related_goal=ProjectGoal.MEET_DEADLINE,
                    decision_source=decision.decision,
                    source_tables=["仕入"],
                    action_type="phone_call",
                    trace_id=trace_id,
                    confidence=decision.confidence,
                ))
                action_id += 1

            elif decision.decision == ProjectDecision.REQUEST_COST_CONFIRMATION:
                actions.append(ProjectAction(
                    action_id=f"act-{action_id}",
                    project_id=data.project_id,
                    title=f"原価確認要求: {data.po_number}",
                    description=f"{data.supplier_name}に原価の正式確認を依頼してください。",
                    priority="medium",
                    related_state=state,
                    related_goal=ProjectGoal.CONFIRM_COST,
                    decision_source=decision.decision,
                    source_tables=["仕入"],
                    action_type="email",
                    trace_id=trace_id,
                    confidence=decision.confidence,
                ))
                action_id += 1

            elif decision.decision == ProjectDecision.IMPROVE_MARGIN:
                actions.append(ProjectAction(
                    action_id=f"act-{action_id}",
                    project_id=data.project_id,
                    title=f"粗利改善検討: {data.po_number}",
                    description=f"粗利{data.profit_margin_pct:.1f}%が目標値15%未満です。コスト削減または価格改定を検討してください。",
                    priority="medium",
                    related_state=state,
                    related_goal=ProjectGoal.SECURE_MARGIN,
                    decision_source=decision.decision,
                    source_tables=["仕入"],
                    action_type="review",
                    trace_id=trace_id,
                    confidence=decision.confidence,
                ))
                action_id += 1

        return actions

    def build_project_aggregate(self, project_id: str) -> ProjectAggregate | None:
        """Build complete ProjectAggregate for a single project."""
        data = self._build_project_data(project_id)
        if not data:
            return None

        trace_id = self._generate_trace_id()
        events = self._generate_project_events(data, trace_id)
        state = self._determine_state(data)
        goals = self._evaluate_goals(data, state)
        decisions = self._generate_decisions(data, state, goals)
        actions = self._generate_actions(data, state, decisions, trace_id)

        return ProjectAggregate(
            project_id=project_id,
            po_number=data.po_number,
            events=events,
            data=data,
            state=state,
            goal_evaluations=goals,
            decisions=decisions,
            actions=actions,
            trace_id=trace_id,
            priority="high" if decisions else "medium",
        )

    def build_multiple_projects(self, limit: int = 10) -> list[ProjectAggregate]:
        """Build ProjectAggregates for multiple projects."""
        project_ids = self._query_projects_from_db(limit=limit)
        aggregates = []

        for proj_record in project_ids[:limit]:
            proj_id = proj_record.get("id")
            if proj_id:
                agg = self.build_project_aggregate(proj_id)
                if agg:
                    aggregates.append(agg)

        return aggregates
