"""Project Service - Orchestrates domain model to build complete project understanding."""

from __future__ import annotations

import hashlib
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
    ProjectHealth,
    ProjectState,
)
from capability.domain import ExecutionStatus
from services.supabase_client import get_connection
from services.trace_store import save_trace
from services.capability_instance import (
    PROJECT_AGGREGATE_CAPABILITY,
    ensure_registered,
    registry as capability_registry,
)


class ProjectService:
    """Service for building complete ProjectAggregate from database."""

    def __init__(self, db_path: Path | None = None):
        """Initialize service. Supabase connection details come from services.supabase_client."""
        self.db_path = db_path

    def _generate_trace_id(self, project_id: str) -> str:
        """Generate deterministic trace ID based on project."""
        project_hash = hashlib.md5(str(project_id).encode()).hexdigest()[:8]
        return f"project-{project_hash}"

    def _query_projects_from_db(self, limit: int = 50, owner_name: str | None = None) -> list[dict[str, Any]]:
        """Query database to find all project candidates (Purchase Orders).

        owner_name: 指定すると、その氏名が「営業担当者名」または
        「営業事務担当者名」と完全一致する案件だけに絞り込む
        （ログイン中の本人の案件をデフォルト表示するための絞り込み、
        docs/architecture.md 14.28）。Noneなら従来通り全件対象。
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                if owner_name:
                    cur.execute(
                        'SELECT DISTINCT "ID" FROM purchase_orders '
                        'WHERE "営業担当者名" = %s OR "営業事務担当者名" = %s '
                        'ORDER BY "ID" DESC LIMIT %s',
                        (owner_name, owner_name, limit),
                    )
                else:
                    cur.execute('SELECT DISTINCT "ID" FROM purchase_orders ORDER BY "ID" DESC LIMIT %s', (limit,))
                rows = cur.fetchall()
            return [{"id": row[0]} for row in rows]
        except Exception as e:
            print(f"Error querying projects: {e}")
            return []
        finally:
            conn.close()

    def _build_project_data(self, project_id: str) -> ProjectData | None:
        """Build ProjectData by querying purchase_orders (real Supabase public schema)."""

        def parse_date(date_val: Any) -> datetime | None:
            if not date_val:
                return None
            if isinstance(date_val, datetime):
                return date_val
            try:
                return datetime.fromisoformat(str(date_val).replace("Z", "+00:00"))
            except Exception:
                return None

        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT "PO_No", "仕入先ID", "仕入先名", "顧客ID", "顧客名", '
                    '"PO発行日", "顧客納品日", "納品日", '
                    '"合計発注金額", "合計売上原価", "合計売上金額" '
                    'FROM purchase_orders WHERE "ID" = %s',
                    (project_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                columns = [desc[0] for desc in cur.description]
                po_dict = dict(zip(columns, row))
        except Exception as e:
            print(f"Error building project data: {e}")
            return None
        finally:
            conn.close()

        try:
            po_number = po_dict.get("PO_No", "") or ""
            supplier_id = str(po_dict.get("仕入先ID", "") or "unknown")
            supplier_name = po_dict.get("仕入先名", "") or ""
            customer_id = str(po_dict.get("顧客ID", "") or "unknown")
            customer_name = po_dict.get("顧客名", "") or ""
            po_created = parse_date(po_dict.get("PO発行日")) or datetime.now()
            po_required_delivery = parse_date(po_dict.get("顧客納品日")) or (datetime.now() + timedelta(days=30))

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
                po_amount=float(po_dict.get("合計発注金額", 0) or 0),
                supplier_invoice_amount=None,
                cost_amount=float(po_dict.get("合計売上原価", 0) or 0),
                sale_amount=float(po_dict.get("合計売上金額", 0) or 0),
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
            source_table="purchase_orders",
            business_meaning="PO作成 - 新規案件始動",
            impact_summary="プロジェクト開始、納期管理開始",
            trace_id=trace_id,
            event_source_type="actual",
            after_state=ProjectState.INITIATED,
            confidence=1.0,
        ))
        event_id += 1

        if data.sale_amount and data.sale_amount > 0:
            events.add_event(ProjectEvent(
                event_id=f"evt-{event_id}",
                project_id=data.project_id,
                event_type=ProjectEventType.SALES_REGISTERED,
                event_time=now,
                source_table="purchase_orders",
                business_meaning="売上登録 - 収入確定",
                impact_summary="売上が確定し、粗利を計算可能に",
                trace_id=trace_id,
                event_source_type="actual",
                before_state=ProjectState.INITIATED,
                after_state=ProjectState.AWAITING_PAYMENT,
                confidence=1.0,
            ))
            event_id += 1

        if data.cost_amount and data.cost_amount > 0:
            events.add_event(ProjectEvent(
                event_id=f"evt-{event_id}",
                project_id=data.project_id,
                event_type=ProjectEventType.PURCHASE_REGISTERED,
                event_time=now,
                source_table="purchase_orders",
                business_meaning="仕入登録 - 原価確定",
                impact_summary="原価が確定し、粗利を計算可能に",
                trace_id=trace_id,
                event_source_type="actual",
                before_state=ProjectState.INITIATED,
                after_state=ProjectState.COST_UNCONFIRMED,
                confidence=1.0,
            ))
            event_id += 1

        if data.actual_delivery_date:
            events.add_event(ProjectEvent(
                event_id=f"evt-{event_id}",
                project_id=data.project_id,
                event_type=ProjectEventType.DELIVERY_COMPLETED,
                event_time=data.actual_delivery_date,
                source_table="purchase_orders",
                business_meaning="納品完了 - 納期達成",
                impact_summary="納期目標達成",
                trace_id=trace_id,
                event_source_type="actual",
                before_state=ProjectState.INITIATED,
                after_state=ProjectState.DELIVERY_RECEIVED,
                confidence=1.0,
            ))
            event_id += 1

        if data.actual_payment_date:
            events.add_event(ProjectEvent(
                event_id=f"evt-{event_id}",
                project_id=data.project_id,
                event_type=ProjectEventType.PAYMENT_PROCESSED,
                event_time=data.actual_payment_date,
                source_table="purchase_orders",
                business_meaning="支払完了 - 現金化",
                impact_summary="全資金回収完了",
                trace_id=trace_id,
                event_source_type="actual",
                before_state=ProjectState.AWAITING_PAYMENT,
                after_state=ProjectState.COMPLETED,
                confidence=1.0,
            ))
            event_id += 1

        if data.gross_profit_margin and data.gross_profit_margin >= 15:
            events.add_event(ProjectEvent(
                event_id=f"evt-{event_id}",
                project_id=data.project_id,
                event_type=ProjectEventType.GROSS_PROFIT_RECALCULATED,
                event_time=now,
                source_table="purchase_orders",
                business_meaning="粗利再計算 - 目標達成",
                impact_summary="粗利15%以上確保",
                trace_id=trace_id,
                event_source_type="derived",
                derivation_rule="MARGIN_CALCULATION",
                confidence=0.95,
            ))
            event_id += 1
        elif data.gross_profit_margin and data.gross_profit_margin < 15:
            events.add_event(ProjectEvent(
                event_id=f"evt-{event_id}",
                project_id=data.project_id,
                event_type=ProjectEventType.GROSS_PROFIT_DECLINED,
                event_time=now,
                source_table="purchase_orders",
                business_meaning="粗利低下 - リスク検知",
                impact_summary="粗利が15%未満に低下",
                trace_id=trace_id,
                event_source_type="derived",
                derivation_rule="MARGIN_THRESHOLD",
                after_state=ProjectState.GROSS_PROFIT_DEGRADED,
                confidence=0.95,
            ))
            event_id += 1

        if data.days_until_delivery < 7 and not data.actual_delivery_date:
            events.add_event(ProjectEvent(
                event_id=f"evt-{event_id}",
                project_id=data.project_id,
                event_type=ProjectEventType.DELIVERY_RISK_DETECTED,
                event_time=now,
                source_table="purchase_orders",
                business_meaning="納期リスク検知 - 7日以内",
                impact_summary="納期まで時間が少ない - 急ぎ対応必要",
                trace_id=trace_id,
                event_source_type="derived",
                derivation_rule="DELIVERY_SLA_7DAYS",
                after_state=ProjectState.INITIATED,
                confidence=0.9,
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
                    source_tables=["purchase_orders"],
                    action_type="phone_call",
                    trace_id=trace_id,
                    confidence=decision.confidence,
                    condition=decision.reason,
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
                    source_tables=["purchase_orders"],
                    action_type="email",
                    trace_id=trace_id,
                    confidence=decision.confidence,
                    condition=decision.reason,
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
                    source_tables=["purchase_orders"],
                    action_type="review",
                    trace_id=trace_id,
                    confidence=decision.confidence,
                    condition=decision.reason,
                ))
                action_id += 1

        return actions

    def _calculate_health_score(self, data: ProjectData, state: ProjectState, goals: GoalEvaluations, decisions: list[ProjectDecisionDetail], actions: list[ProjectAction], trace_id: str) -> ProjectHealth:
        """Calculate project health score - reflects current operational health."""
        score = 100
        factors = {}

        if state == ProjectState.COMPLETED:
            if data.profit_margin_pct and data.profit_margin_pct < 10:
                score = 85
                factors["completed_low_margin"] = -15
            return ProjectHealth(
                health_score=score,
                health_status="healthy" if score >= 80 else "watch",
                factors=factors,
                reason="Completed",
                trace_id=trace_id,
            )

        if data.profit_margin_pct is not None:
            if data.profit_margin_pct < 0:
                penalty = 70
                factors["margin_negative"] = -penalty
            elif data.profit_margin_pct < 5:
                penalty = 55
                factors["margin_critical"] = -penalty
            elif data.profit_margin_pct < 10:
                penalty = 40
                factors["margin_low"] = -penalty
            elif data.profit_margin_pct < 15:
                penalty = 20
                factors["margin_below_target"] = -penalty
            else:
                penalty = 0
            if penalty > 0:
                score -= penalty

        if not data.actual_delivery_date and data.days_until_delivery is not None:
            if data.days_until_delivery < 0:
                penalty = 50
                factors["delivery_overdue"] = -penalty
            elif data.days_until_delivery < 3:
                penalty = 35
                factors["delivery_critical"] = -penalty
            elif data.days_until_delivery < 7:
                penalty = 20
                factors["delivery_risk"] = -penalty
            elif data.days_until_delivery < 14:
                penalty = 5
                factors["delivery_approaching"] = -penalty
            else:
                penalty = 0
            if penalty > 0:
                score -= penalty

        if state == ProjectState.DELIVERY_RECEIVED or (state == ProjectState.AWAITING_PAYMENT and data.actual_delivery_date):
            penalty = 20
            score -= penalty
            factors["cash_flow_pending"] = -penalty

        confirm_cost_eval = goals.evaluations.get(ProjectGoal.CONFIRM_COST)
        if confirm_cost_eval and confirm_cost_eval.status == GoalStatus.AT_RISK:
            penalty = 15
            score -= penalty
            factors["cost_unconfirmed"] = -penalty

        if len(actions) > 0 and any(a.priority == "high" for a in actions):
            penalty = 15
            score -= penalty
            factors["high_priority_action"] = -penalty

        has_missing_data = ((data.sale_amount == 0 or data.sale_amount is None) or
                           (data.cost_amount == 0 or data.cost_amount is None) or
                           (data.po_amount == 0 or data.po_amount is None))
        if has_missing_data and state not in (ProjectState.COMPLETED, ProjectState.DELIVERY_RECEIVED):
            penalty = 20
            score -= penalty
            factors["data_incomplete"] = -penalty

        score = max(0, min(100, score))

        if score >= 80:
            status = "healthy"
        elif score >= 60:
            status = "watch"
        elif score >= 40:
            status = "risk"
        else:
            status = "critical"

        reason = f"Score {score}: {', '.join([f'{k}({v})' for k, v in factors.items()])}" if factors else "All metrics optimal"

        return ProjectHealth(
            health_score=score,
            health_status=status,
            factors=factors,
            reason=reason,
            trace_id=trace_id,
        )

    def _calculate_risk_score(self, data: ProjectData, state: ProjectState, goals: GoalEvaluations) -> tuple[int, str]:
        """Calculate risk score (0-100) reflecting danger if ignored."""
        risk_components = []

        if data.profit_margin_pct is not None:
            if data.profit_margin_pct < 0:
                margin_risk = 100
            elif data.profit_margin_pct < 5:
                margin_risk = 90
            elif data.profit_margin_pct < 10:
                margin_risk = 75
            elif data.profit_margin_pct < 15:
                margin_risk = 55
            else:
                margin_risk = 20
            risk_components.append(("margin", margin_risk, 0.40))

        if not data.actual_delivery_date and data.days_until_delivery is not None:
            if data.days_until_delivery < 0:
                delivery_risk = 100
            elif data.days_until_delivery < 1:
                delivery_risk = 95
            elif data.days_until_delivery < 3:
                delivery_risk = 85
            elif data.days_until_delivery < 7:
                delivery_risk = 70
            elif data.days_until_delivery < 14:
                delivery_risk = 40
            else:
                delivery_risk = 15
            risk_components.append(("delivery", delivery_risk, 0.35))
        else:
            risk_components.append(("delivery", 0, 0.35))

        if data.actual_delivery_date and not data.actual_payment_date:
            billing_risk = 70
        elif state == ProjectState.DELIVERY_OVERDUE:
            billing_risk = 65
        else:
            billing_risk = 15
        risk_components.append(("billing", billing_risk, 0.25))

        risk_score = sum(component[1] * component[2] for component in risk_components)
        risk_score = min(100, int(risk_score))

        if risk_score >= 80:
            risk_level = "critical"
        elif risk_score >= 60:
            risk_level = "high"
        elif risk_score >= 40:
            risk_level = "medium"
        else:
            risk_level = "low"

        return risk_score, risk_level

    def _calculate_opportunity_score(self, data: ProjectData, customer_priority: str = "normal") -> tuple[int, str]:
        """Calculate opportunity score (0-100) from margins and deal size."""
        opportunity_score = 0
        vip_multiplier = 1.5 if customer_priority == "vip" else (1.2 if customer_priority == "high" else 1.0)

        if data.profit_margin_pct and data.profit_margin_pct >= 35:
            margin_score = int(50 * vip_multiplier)
            opportunity_score += margin_score
        elif data.profit_margin_pct and data.profit_margin_pct >= 25:
            margin_score = int(30 * vip_multiplier)
            opportunity_score += margin_score
        elif data.profit_margin_pct and data.profit_margin_pct >= 15:
            margin_score = int(15 * vip_multiplier)
            opportunity_score += margin_score

        if data.sale_amount and data.sale_amount >= 2000000:
            deal_score = int(30 * vip_multiplier)
            opportunity_score += deal_score
        elif data.sale_amount and data.sale_amount >= 1000000:
            deal_score = int(15 * vip_multiplier)
            opportunity_score += deal_score

        opportunity_score = min(100, opportunity_score)

        if opportunity_score >= 70:
            opportunity_level = "high"
        elif opportunity_score >= 40:
            opportunity_level = "medium"
        else:
            opportunity_level = "low"

        return opportunity_score, opportunity_level

    def _recommend_focus(self, health_score: int, risk_score: int, opportunity_score: int) -> str:
        """Recommend focus based on 3-axis scores."""
        from business.evaluation_rules import FocusRecommendationRule

        return FocusRecommendationRule.recommend(health_score, risk_score, opportunity_score)

    def build_project_aggregate(self, project_id: str) -> ProjectAggregate | None:
        """Build complete ProjectAggregate for a single project.

        This is recorded as a Blueprint Capability execution (Principle 2:
        Capability Driven) via the shared registry in
        `services.capability_instance`, so it is visible/measurable through
        the `/capabilities` API — not just an ad-hoc function call.
        """
        ensure_registered(PROJECT_AGGREGATE_CAPABILITY)
        trace_id = self._generate_trace_id(project_id)
        execution = capability_registry.execute_capability(
            capability_id=PROJECT_AGGREGATE_CAPABILITY.capability_id,
            inputs={"project_id": str(project_id)},
            user_id="system",
            project_id=str(project_id),
            trace_id=trace_id,
        )

        try:
            aggregate = self._build_project_aggregate_impl(project_id)
        except Exception as e:
            capability_registry.record_execution_result(
                execution_id=execution.execution_id,
                outputs={},
                status=ExecutionStatus.FAILED,
                error_message=str(e),
            )
            raise

        capability_registry.record_execution_result(
            execution_id=execution.execution_id,
            outputs={
                "found": aggregate is not None,
                "state": aggregate.state.value if aggregate else None,
                "priority": aggregate.priority if aggregate else None,
            },
            status=ExecutionStatus.COMPLETED if aggregate else ExecutionStatus.FAILED,
            error_message=None if aggregate else "project not found",
        )
        return aggregate

    def _build_project_aggregate_impl(self, project_id: str) -> ProjectAggregate | None:
        """Build complete ProjectAggregate for a single project (unwrapped)."""
        data = self._build_project_data(project_id)
        if not data:
            return None

        trace_id = self._generate_trace_id(project_id)

        events = self._generate_project_events(data, trace_id)
        state = self._determine_state(data)
        goals = self._evaluate_goals(data, state)
        decisions = self._generate_decisions(data, state, goals)
        actions = self._generate_actions(data, state, decisions, trace_id)

        health = self._calculate_health_score(data, state, goals, decisions, actions, trace_id)
        risk_score, risk_level = self._calculate_risk_score(data, state, goals)
        opportunity_score, opportunity_level = self._calculate_opportunity_score(data)
        recommended_focus = self._recommend_focus(health.health_score, risk_score, opportunity_score)

        aggregate = ProjectAggregate(
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
            health=health,
            risk_score=risk_score,
            risk_level=risk_level,
            opportunity_score=opportunity_score,
            opportunity_level=opportunity_level,
            recommended_focus=recommended_focus,
        )

        try:
            save_trace(trace_id, aggregate.to_dict())
        except Exception:
            # Trace persistence must never block the actual response.
            pass

        return aggregate
        

    def build_project_aggregates(self, limit: int = 50) -> list[ProjectAggregate]:
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