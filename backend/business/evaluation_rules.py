"""Business Rules for Project Evaluation"""

from dataclasses import dataclass
from typing import Optional, Any

@dataclass
class RuleOutput:
    rule_name: str
    condition_met: bool
    score_impact: int
    reason: str
    applied_rules: list[str] = None

class GrossProfitHealthRule:
    """Evaluate project health based on gross profit margin"""

    @staticmethod
    def evaluate(gross_profit_rate: Optional[float]) -> RuleOutput:
        """
        Score impact:
        >= 35%: +20
        >= 25%: +10
        >= 15%: 0
        >= 10%: -15
        < 10%:  -30
        null:   -20 (unknown)
        """
        if gross_profit_rate is None:
            return RuleOutput(
                rule_name="GrossProfitHealthRule",
                condition_met=False,
                score_impact=-20,
                reason="Gross profit rate unknown"
            )

        if gross_profit_rate >= 35:
            return RuleOutput(
                rule_name="GrossProfitHealthRule",
                condition_met=True,
                score_impact=20,
                reason=f"Excellent margin: {gross_profit_rate:.1f}%"
            )
        elif gross_profit_rate >= 25:
            return RuleOutput(
                rule_name="GrossProfitHealthRule",
                condition_met=True,
                score_impact=10,
                reason=f"Good margin: {gross_profit_rate:.1f}%"
            )
        elif gross_profit_rate >= 15:
            return RuleOutput(
                rule_name="GrossProfitHealthRule",
                condition_met=True,
                score_impact=0,
                reason=f"Target margin: {gross_profit_rate:.1f}%"
            )
        elif gross_profit_rate >= 10:
            return RuleOutput(
                rule_name="GrossProfitHealthRule",
                condition_met=False,
                score_impact=-15,
                reason=f"Below target: {gross_profit_rate:.1f}%"
            )
        else:
            return RuleOutput(
                rule_name="GrossProfitHealthRule",
                condition_met=False,
                score_impact=-30,
                reason=f"Critical margin: {gross_profit_rate:.1f}%"
            )

class DeliveryRiskRule:
    """Evaluate delivery risk based on days until deadline"""

    @staticmethod
    def evaluate(days_until_delivery: int, is_delivered: bool) -> RuleOutput:
        """
        Score impact (health):
        delivered: +15
        > 14 days: +10
        7-14 days: -5
        3-6 days: -20
        1-2 days: -30
        overdue: -40

        Risk score:
        delivered: 0
        > 14 days: 10
        7-14 days: 30
        3-6 days: 70
        1-2 days: 90
        overdue: 100
        """
        if is_delivered:
            return RuleOutput(
                rule_name="DeliveryRiskRule",
                condition_met=True,
                score_impact=15,
                reason="Delivery completed successfully"
            )

        if days_until_delivery > 14:
            return RuleOutput(
                rule_name="DeliveryRiskRule",
                condition_met=True,
                score_impact=10,
                reason=f"Adequate time to delivery ({days_until_delivery} days)"
            )
        elif days_until_delivery >= 7:
            return RuleOutput(
                rule_name="DeliveryRiskRule",
                condition_met=False,
                score_impact=-5,
                reason=f"Delivery approaching ({days_until_delivery} days)"
            )
        elif days_until_delivery >= 3:
            return RuleOutput(
                rule_name="DeliveryRiskRule",
                condition_met=False,
                score_impact=-20,
                reason=f"Delivery urgent ({days_until_delivery} days)"
            )
        elif days_until_delivery >= 1:
            return RuleOutput(
                rule_name="DeliveryRiskRule",
                condition_met=False,
                score_impact=-30,
                reason=f"Delivery critical ({days_until_delivery} days)"
            )
        else:
            return RuleOutput(
                rule_name="DeliveryRiskRule",
                condition_met=False,
                score_impact=-40,
                reason=f"OVERDUE by {abs(days_until_delivery)} days"
            )

class PurchaseConfirmationRule:
    """Evaluate purchase confirmation status"""

    @staticmethod
    def evaluate(purchase_confirmed: bool, actual_cost: Optional[float]) -> RuleOutput:
        """
        Score impact:
        confirmed & cost known: +10
        confirmed & cost unknown: +5
        not confirmed: -15
        """
        if purchase_confirmed:
            if actual_cost is not None:
                return RuleOutput(
                    rule_name="PurchaseConfirmationRule",
                    condition_met=True,
                    score_impact=10,
                    reason="Purchase confirmed and cost known"
                )
            else:
                return RuleOutput(
                    rule_name="PurchaseConfirmationRule",
                    condition_met=True,
                    score_impact=5,
                    reason="Purchase confirmed but cost pending"
                )
        else:
            return RuleOutput(
                rule_name="PurchaseConfirmationRule",
                condition_met=False,
                score_impact=-15,
                reason="Purchase not yet confirmed"
            )

class BillingRiskRule:
    """Evaluate billing status risk"""

    @staticmethod
    def evaluate(billing_status: str, is_delivered: bool, days_overdue: int) -> RuleOutput:
        """
        Score impact:
        completed: +10
        not_required: +5
        pending & delivered: -20
        pending & not delivered: -5
        unknown: -10

        Risk score:
        completed/not_required: 0
        pending & delivered: 40 (cash flow risk)
        pending & not delivered: 15 (normal pending)
        unknown: 20
        overdue payment: 60
        """
        if billing_status == "completed":
            return RuleOutput(
                rule_name="BillingRiskRule",
                condition_met=True,
                score_impact=10,
                reason="Billing completed"
            )
        elif billing_status == "not_required":
            return RuleOutput(
                rule_name="BillingRiskRule",
                condition_met=True,
                score_impact=5,
                reason="Billing not required"
            )
        elif billing_status == "pending":
            if is_delivered:
                return RuleOutput(
                    rule_name="BillingRiskRule",
                    condition_met=False,
                    score_impact=-20,
                    reason="Delivered but billing pending (cash flow risk)"
                )
            else:
                return RuleOutput(
                    rule_name="BillingRiskRule",
                    condition_met=False,
                    score_impact=-5,
                    reason="Billing pending (normal)"
                )
        else:
            return RuleOutput(
                rule_name="BillingRiskRule",
                condition_met=False,
                score_impact=-10,
                reason="Billing status unknown"
            )

class DataCompletenessRule:
    """Evaluate data completeness"""

    @staticmethod
    def evaluate(data_completeness: int) -> RuleOutput:
        """
        Score impact:
        >= 95%: +5
        >= 80%: 0
        >= 60%: -10
        < 60%: -20
        """
        if data_completeness >= 95:
            return RuleOutput(
                rule_name="DataCompletenessRule",
                condition_met=True,
                score_impact=5,
                reason=f"Complete data ({data_completeness}%)"
            )
        elif data_completeness >= 80:
            return RuleOutput(
                rule_name="DataCompletenessRule",
                condition_met=True,
                score_impact=0,
                reason=f"Data mostly complete ({data_completeness}%)"
            )
        elif data_completeness >= 60:
            return RuleOutput(
                rule_name="DataCompletenessRule",
                condition_met=False,
                score_impact=-10,
                reason=f"Data incomplete ({data_completeness}%)"
            )
        else:
            return RuleOutput(
                rule_name="DataCompletenessRule",
                condition_met=False,
                score_impact=-20,
                reason=f"Critical data missing ({data_completeness}%)"
            )

class CustomerPriorityRule:
    """Evaluate customer priority impact"""

    @staticmethod
    def evaluate(customer_priority: str) -> tuple[int, int]:
        """
        Returns: (health_impact, opportunity_impact)

        vip: health +10, opportunity +30
        high: health +5, opportunity +15
        normal: health 0, opportunity 0
        low: health -5, opportunity -10
        """
        mapping = {
            "vip": (10, 30),
            "high": (5, 15),
            "normal": (0, 0),
            "low": (-5, -10),
        }
        return mapping.get(customer_priority.lower(), (0, 0))

class OpportunityRule:
    """Evaluate opportunity factors"""

    @staticmethod
    def evaluate(gross_profit_rate: Optional[float], customer_priority: str,
                 sales_amount: Optional[float]) -> int:
        """
        Opportunity score impacts:

        High margin (>= 35%) + VIP: +40
        High margin + high priority: +30
        High margin + normal: +20
        Medium margin + VIP: +25
        Large deal (>= 2M) + VIP: +35
        Large deal + high priority: +20
        """
        opportunity_score = 0

        # High margin opportunities
        if gross_profit_rate and gross_profit_rate >= 35:
            if customer_priority == "vip":
                opportunity_score += 40
            elif customer_priority == "high":
                opportunity_score += 30
            else:
                opportunity_score += 20
        elif gross_profit_rate and gross_profit_rate >= 25:
            if customer_priority == "vip":
                opportunity_score += 25
            elif customer_priority == "high":
                opportunity_score += 15

        # Large deal opportunities
        if sales_amount and sales_amount >= 2000000:
            if customer_priority == "vip":
                opportunity_score += 35
            elif customer_priority == "high":
                opportunity_score += 20

        return opportunity_score

class FocusRecommendationRule:
    """Recommend focus based on health and risk"""

    @staticmethod
    def recommend(health_score: int, risk_score: int, opportunity_score: int) -> str:
        """
        Focus recommendations:

        protect: health < 50 OR risk > 70
        recover: health < 60 AND risk > 60
        accelerate: opportunity > 60 AND health > 70
        monitor: health 60-75 OR risk 40-60
        ignore: health > 85 AND risk < 30 AND opportunity < 30
        """
        if health_score < 50 or risk_score > 70:
            return "protect"
        elif health_score < 60 and risk_score > 60:
            return "recover"
        elif opportunity_score > 60 and health_score > 70:
            return "accelerate"
        elif (60 <= health_score <= 75) or (40 <= risk_score <= 60):
            return "monitor"
        elif health_score > 85 and risk_score < 30 and opportunity_score < 30:
            return "ignore"
        else:
            return "monitor"
