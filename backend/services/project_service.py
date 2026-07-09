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

    _PO_SELECT_COLUMNS = (
        '"ID", "PO_No", "仕入先ID", "仕入先名", "顧客ID", "顧客名", '
        '"PO発行日", "顧客納品日", "納品日", "LOGS_CODE", '
        '"合計発注金額", "合計売上原価", "合計売上金額"'
    )

    # 2026-07-09（14.33）: 納品日/支払日はPOデータに実質入らないため、
    # 「納品済みか」「原価確定済みか」を判定するのに使えない
    # （Noritsuguの指摘、実データで確認済み）。代わりに、同じLOGS_CODEで
    # sales/purchasesに実際にデータが入っているかをEXISTSで判定する。
    # production_mass（生産管理『量産』シート）の"表示"列が0の行が
    # 1件でもあれば、担当者が案件を終了済みとして表示OFFにした印として
    # 「納品済み」扱いにする（14.28で学んだ通り、N回接続ではなく
    # サブクエリで1回のクエリにまとめている）。
    _EXISTENCE_SELECT_COLUMNS = (
        'EXISTS(SELECT 1 FROM sales s WHERE s."LOGS_CODE" = po."LOGS_CODE") AS "has_sales", '
        'EXISTS(SELECT 1 FROM purchases pu WHERE pu."LOGS_CODE" = po."LOGS_CODE") AS "has_purchase", '
        'EXISTS('
        '    SELECT 1 FROM production_mass pm '
        '    WHERE pm."POnum" = po."PO_No" AND pm."表示"::text = \'0\''
        ') AS "production_closed"'
    )

    @staticmethod
    def _parse_date(date_val: Any) -> datetime | None:
        if not date_val:
            return None
        if isinstance(date_val, datetime):
            return date_val
        try:
            return datetime.fromisoformat(str(date_val).replace("Z", "+00:00"))
        except Exception:
            return None

    @staticmethod
    def _format_logs_code_for_project(value: Any) -> str | None:
        """purchase_orders.LOGS_CODEもproducts.LOGS_CODEと同じ理由
        （Supabase上でdouble precision型のため13564が13564.0になる、14.30）
        で正規化が必要。sales/purchasesとの突合キーとして使う前に統一する。
        """
        if value is None:
            return None
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    def _po_dict_to_project_data(self, project_id: str, po_dict: dict[str, Any]) -> ProjectData | None:
        """Convert an already-fetched purchase_orders row (as a dict) into
        ProjectData. Shared by both the single-project and batch code paths
        so the parsing logic only lives in one place.
        """
        try:
            po_number = po_dict.get("PO_No", "") or ""
            supplier_id = str(po_dict.get("仕入先ID", "") or "unknown")
            supplier_name = po_dict.get("仕入先名", "") or ""
            customer_id = str(po_dict.get("顧客ID", "") or "unknown")
            customer_name = po_dict.get("顧客名", "") or ""
            po_created = self._parse_date(po_dict.get("PO発行日")) or datetime.now()
            po_required_delivery = self._parse_date(po_dict.get("顧客納品日")) or (datetime.now() + timedelta(days=30))

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
                actual_delivery_date=self._parse_date(po_dict.get("納品日")),
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
                logs_code=self._format_logs_code_for_project(po_dict.get("LOGS_CODE")),
                has_sales=bool(po_dict.get("has_sales", False)),
                has_purchase=bool(po_dict.get("has_purchase", False)),
                production_closed=bool(po_dict.get("production_closed", False)),
            )

            if project_data.cost_amount and project_data.sale_amount:
                project_data.gross_profit = project_data.sale_amount - project_data.cost_amount
                project_data.gross_profit_margin = project_data.profit_margin_pct

            return project_data
        except Exception as e:
            print(f"Error building project data: {e}")
            return None

    def _build_project_data(self, project_id: str) -> ProjectData | None:
        """Build ProjectData for a single project by querying purchase_orders
        (real Supabase public schema). For fetching many projects at once
        (list views), use `_build_project_data_batch` instead — each call to
        this method opens its own DB connection, which is fine for a single
        lookup but far too slow in a loop (docs/architecture.md 14.28).
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f'SELECT {self._PO_SELECT_COLUMNS}, {self._EXISTENCE_SELECT_COLUMNS} '
                    'FROM purchase_orders po WHERE po."ID" = %s',
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

        return self._po_dict_to_project_data(project_id, po_dict)

    def _build_project_data_batch(self, project_ids: list[str]) -> dict[str, ProjectData]:
        """Fetch ProjectData for many projects in a single DB round-trip
        (one connection, one query with `WHERE "ID" = ANY(%s)`), instead of
        one connection per project. Added 2026-07-08 (docs/architecture.md
        14.28) after 案件一覧/今日のタスク were measured taking 20〜80秒 —
        almost entirely connection-open overhead multiplied by project
        count, not query cost itself.
        """
        if not project_ids:
            return {}

        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f'SELECT {self._PO_SELECT_COLUMNS}, {self._EXISTENCE_SELECT_COLUMNS} '
                    'FROM purchase_orders po WHERE po."ID" = ANY(%s)',
                    (list(project_ids),),
                )
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
        except Exception as e:
            print(f"Error batch-building project data: {e}")
            return {}
        finally:
            conn.close()

        result: dict[str, ProjectData] = {}
        for row in rows:
            po_dict = dict(zip(columns, row))
            project_id = str(po_dict.get("ID"))
            data = self._po_dict_to_project_data(project_id, po_dict)
            if data:
                result[project_id] = data
        return result

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
        """Determine project state based on data.

        2026-07-09（14.33、Noritsuguの指摘を反映した修正）: POデータの
        納品日/支払日は実質常に空のため、以前はこれに依存した判定
        （AWAITING_PAYMENT・GROSS_PROFIT_DEGRADED等）が実データでは
        機能していなかった。代わりに、同じLOGS_CODEにsales/purchasesの
        実データがあるか（has_sales/has_purchase）、または生産管理
        『量産』シートで表示OFFにされているか（production_closed）で
        判定する。優先順位: 完了 > 納期超過 > 原価未確定 > 開始済み。
        粗利のズレ（PO予定粗利 vs 仕入確定粗利）は状態バッジではなく
        案件詳細の評価項目として別途扱う（今日のタスクの対象外）。
        """
        if data.is_delivered:
            return ProjectState.COMPLETED

        if data.is_overdue:
            return ProjectState.DELIVERY_OVERDUE

        if not data.has_purchase:
            return ProjectState.COST_UNCONFIRMED

        return ProjectState.INITIATED

    def _evaluate_goals(self, data: ProjectData, state: ProjectState) -> GoalEvaluations:
        """Evaluate business goals for a project.

        2026-07-09（14.33）: 今日のタスクを「売上入力の必要性」「仕入
        入力の必要性」の2種類だけに絞り込むため、それ以外の目標
        （納期遵守・粗利確保・支払処理・顧客満足度）は評価しない
        （どこにも表示されず、Decisionも生成していなかった、
        Noritsuguの確認済み）。CONFIRM_DELIVERY（納品確認=売上入力の
        有無）とCONFIRM_COST（原価確定=仕入入力の有無）の2つだけを
        評価する。
        """
        evals = GoalEvaluations(project_id=data.project_id)

        if data.has_purchase and not data.has_sales:
            evals.evaluations[ProjectGoal.CONFIRM_DELIVERY] = GoalEvaluation(
                goal=ProjectGoal.CONFIRM_DELIVERY,
                status=GoalStatus.AT_RISK,
                reason="仕入は入力済みだが売上が未入力",
                confidence=0.9,
            )
        elif data.has_sales:
            evals.evaluations[ProjectGoal.CONFIRM_DELIVERY] = GoalEvaluation(
                goal=ProjectGoal.CONFIRM_DELIVERY,
                status=GoalStatus.ACHIEVED,
                reason="売上入力済み（納品済みと判断）",
                confidence=0.9,
            )
        else:
            evals.evaluations[ProjectGoal.CONFIRM_DELIVERY] = GoalEvaluation(
                goal=ProjectGoal.CONFIRM_DELIVERY,
                status=GoalStatus.UNKNOWN,
                reason="仕入・売上ともまだ未入力",
                confidence=0.5,
            )

        if data.has_sales and not data.has_purchase and data.is_overdue:
            evals.evaluations[ProjectGoal.CONFIRM_COST] = GoalEvaluation(
                goal=ProjectGoal.CONFIRM_COST,
                status=GoalStatus.AT_RISK,
                reason="納期を過ぎ売上は入力済みだが仕入が未入力",
                confidence=0.9,
            )
        elif data.has_purchase:
            evals.evaluations[ProjectGoal.CONFIRM_COST] = GoalEvaluation(
                goal=ProjectGoal.CONFIRM_COST,
                status=GoalStatus.ACHIEVED,
                reason="仕入入力済み（原価確定済みと判断）",
                confidence=0.9,
            )
        else:
            evals.evaluations[ProjectGoal.CONFIRM_COST] = GoalEvaluation(
                goal=ProjectGoal.CONFIRM_COST,
                status=GoalStatus.UNKNOWN,
                reason="仕入未入力（まだ納期前、または売上も未入力）",
                confidence=0.5,
            )

        return evals

    def _generate_decisions(self, data: ProjectData, state: ProjectState, goals: GoalEvaluations) -> list[ProjectDecisionDetail]:
        """Generate decisions from goal evaluations.

        2026-07-09（14.33）: 今日のタスクをa/bの2種類だけに絞る
        （Noritsuguの指定）。CONFIRM_DELIVERYがAT_RISK（仕入はあるが
        売上が無い）ならRECORD_SALES、CONFIRM_COSTがAT_RISK（納期後で
        売上はあるが仕入が無い）ならRECORD_PURCHASE。この2つは
        定義上同時には成立しない（前者はhas_salesが偽、後者は真が
        前提のため）。
        """
        decisions = []
        goal_dict = goals.evaluations

        confirm_delivery_eval = goal_dict.get(ProjectGoal.CONFIRM_DELIVERY)
        if confirm_delivery_eval and confirm_delivery_eval.status == GoalStatus.AT_RISK:
            decisions.append(ProjectDecisionDetail(
                decision=ProjectDecision.RECORD_SALES,
                priority=1,
                reason="仕入は入力済みだが売上が未入力",
                confidence=0.9,
                triggered_by_goals=[ProjectGoal.CONFIRM_DELIVERY],
                business_rule="SALES_ENTRY_NEEDED",
            ))

        confirm_cost_eval = goal_dict.get(ProjectGoal.CONFIRM_COST)
        if confirm_cost_eval and confirm_cost_eval.status == GoalStatus.AT_RISK:
            decisions.append(ProjectDecisionDetail(
                decision=ProjectDecision.RECORD_PURCHASE,
                priority=1,
                reason="納期を過ぎ売上は入力済みだが仕入が未入力",
                confidence=0.9,
                triggered_by_goals=[ProjectGoal.CONFIRM_COST],
                business_rule="PURCHASE_ENTRY_NEEDED",
            ))

        return decisions

    def _generate_actions(self, data: ProjectData, state: ProjectState, decisions: list[ProjectDecisionDetail], trace_id: str) -> list[ProjectAction]:
        """Generate concrete actions from decisions.

        2026-07-09（14.33）: 今日のタスクはa（売上入力の必要性）・b
        （仕入入力の必要性）の2種類のみ（Noritsuguの指定）。粗利改善・
        納期急ぎ連絡等の旧アクションは、実データで判定に使えない前提
        （POの納品日/支払日が空、粗利の予定/確定比較はまだ未実装）に
        基づいていたため廃止した。
        """
        actions = []
        action_id = 1

        for decision in decisions:
            if decision.decision == ProjectDecision.RECORD_SALES:
                actions.append(ProjectAction(
                    action_id=f"act-{action_id}",
                    project_id=data.project_id,
                    title=f"売上入力の必要性: {data.po_number}",
                    description=f"仕入は入力済みですが、{data.customer_name}への売上がまだ入力されていません。売上の入力をお願いします。",
                    priority="high",
                    related_state=state,
                    related_goal=ProjectGoal.CONFIRM_DELIVERY,
                    decision_source=decision.decision,
                    source_tables=["purchase_orders", "sales", "purchases"],
                    action_type="data_entry",
                    trace_id=trace_id,
                    confidence=decision.confidence,
                    condition=decision.reason,
                ))
                action_id += 1

            elif decision.decision == ProjectDecision.RECORD_PURCHASE:
                actions.append(ProjectAction(
                    action_id=f"act-{action_id}",
                    project_id=data.project_id,
                    title=f"仕入入力の必要性: {data.po_number}",
                    description=f"納期（{data.po_required_delivery_date.strftime('%Y-%m-%d')}）を過ぎ、{data.customer_name}への売上は入力済みですが、{data.supplier_name}への仕入がまだ入力されていません。仕入の入力をお願いします。",
                    priority="high",
                    related_state=state,
                    related_goal=ProjectGoal.CONFIRM_COST,
                    decision_source=decision.decision,
                    source_tables=["purchase_orders", "sales", "purchases"],
                    action_type="data_entry",
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

    def build_project_aggregate(self, project_id: str, record_capability: bool = True) -> ProjectAggregate | None:
        """Build complete ProjectAggregate for a single project.

        This is recorded as a Blueprint Capability execution (Principle 2:
        Capability Driven) via the shared registry in
        `services.capability_instance`, so it is visible/measurable through
        the `/capabilities` API — not just an ad-hoc function call.

        record_capability: 案件を1件だけ詳しく見る場面（/api/projects/{id}
        等）ではTrue（既定）のまま、Capability実行履歴・トレースへの書き込み
        を行う。一方、案件一覧・今日のタスクのように多数の案件をまとめて
        処理する場面では、案件1件ごとにSupabaseへの同期書き込みが複数回
        発生し体感速度を大きく損なうため、呼び出し側からFalseを渡して
        この記録処理自体をスキップできるようにしている
        （docs/architecture.md 14.28、実測で"今日のタスク"が数分かかる
        原因の大半がここだった）。
        """
        if not record_capability:
            return self._build_project_aggregate_impl(project_id)

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
        """Build complete ProjectAggregate for a single project (unwrapped).

        record_capability=Falseで呼ばれた場合はtrace保存もスキップする
        （save_trace自体もSupabase書き込みのため）。
        """
        data = self._build_project_data(project_id)
        if not data:
            return None
        return self._build_aggregate_from_data(project_id, data)

    def _build_aggregate_from_data(
        self, project_id: str, data: ProjectData, save_trace_flag: bool = True
    ) -> ProjectAggregate:
        """Run the (pure-Python, no DB access) event/goal/decision/action/
        health/risk calculations for an already-fetched ProjectData and
        assemble a ProjectAggregate. Split out from `_build_project_aggregate_impl`
        so `build_project_aggregates_bulk` can reuse it against data that was
        fetched in one batched query, instead of one query per project
        (docs/architecture.md 14.28).
        """
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

        if save_trace_flag:
            try:
                save_trace(trace_id, aggregate.to_dict())
            except Exception:
                # Trace persistence must never block the actual response.
                pass

        return aggregate

    def build_project_aggregates_bulk(self, project_ids: list[str]) -> list[ProjectAggregate]:
        """Build ProjectAggregates for many projects at once, using exactly
        one DB connection/query total (via `_build_project_data_batch`)
        instead of one per project. This is the method list-style call
        sites (/api/projects, /api/today-actions, home's recent projects,
        get_my_projects) should use — `build_project_aggregate()` in a loop
        was measured taking 20〜80秒 for 20〜50 projects, almost entirely
        connection-open overhead (docs/architecture.md 14.28). Trace/
        Capability bookkeeping is always skipped here, matching
        record_capability=False's behavior, since this is inherently a
        bulk/listing code path.

        Returns aggregates in the same order as `project_ids`, skipping any
        id that no longer exists in purchase_orders.
        """
        data_map = self._build_project_data_batch(project_ids)
        aggregates = []
        for project_id in project_ids:
            data = data_map.get(str(project_id))
            if data:
                aggregates.append(self._build_aggregate_from_data(str(project_id), data, save_trace_flag=False))
        return aggregates
        

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