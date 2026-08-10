"""Analytics Engine — transforms DB financial data into structured intelligence."""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.category import Category
from app.models.expense import Expense
from app.models.goal import SavingsGoal
from app.models.income import Income
from app.schemas.analytics import (
    AnalyticsDashboard,
    BudgetAnalyticsItem,
    CategoryAmount,
    FinancialSummary,
    GoalProgressItem,
    HealthScoreDetails,
    MonthlyPoint,
)


ZERO = Decimal("0")


class AnalyticsEngine:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def month_bounds(self, year: int, month: int) -> tuple[date, date]:
        last_day = monthrange(year, month)[1]
        return date(year, month, 1), date(year, month, last_day)

    def total_income(self, start: date, end: date) -> Decimal:
        value = (
            self.db.query(func.coalesce(func.sum(Income.amount), 0))
            .filter(
                Income.user_id == self.user_id,
                Income.income_date >= start,
                Income.income_date <= end,
            )
            .scalar()
        )
        return Decimal(str(value))

    def total_expenses(self, start: date, end: date) -> Decimal:
        value = (
            self.db.query(func.coalesce(func.sum(Expense.amount), 0))
            .filter(
                Expense.user_id == self.user_id,
                Expense.expense_date >= start,
                Expense.expense_date <= end,
            )
            .scalar()
        )
        return Decimal(str(value))

    def income_by_source(self, start: date, end: date) -> list[CategoryAmount]:
        rows = (
            self.db.query(Income.source, func.sum(Income.amount))
            .filter(
                Income.user_id == self.user_id,
                Income.income_date >= start,
                Income.income_date <= end,
            )
            .group_by(Income.source)
            .all()
        )
        total = sum((Decimal(str(amount)) for _, amount in rows), ZERO) or Decimal("1")
        return [
            CategoryAmount(
                category=source,
                amount=Decimal(str(amount)),
                percentage=round(float(Decimal(str(amount)) / total * 100), 2),
            )
            for source, amount in rows
        ]

    def expense_by_category(self, start: date, end: date) -> list[CategoryAmount]:
        rows = (
            self.db.query(Category.name, func.sum(Expense.amount))
            .join(Category, Category.id == Expense.category_id)
            .filter(
                Expense.user_id == self.user_id,
                Expense.expense_date >= start,
                Expense.expense_date <= end,
            )
            .group_by(Category.name)
            .all()
        )
        total = sum((Decimal(str(amount)) for _, amount in rows), ZERO) or Decimal("1")
        return [
            CategoryAmount(
                category=name,
                amount=Decimal(str(amount)),
                percentage=round(float(Decimal(str(amount)) / total * 100), 2),
            )
            for name, amount in rows
        ]

    def budget_analytics(self, year: int, month: int) -> list[BudgetAnalyticsItem]:
        start, end = self.month_bounds(year, month)
        budgets = (
            self.db.query(Budget, Category.name)
            .join(Category, Category.id == Budget.category_id)
            .filter(Budget.user_id == self.user_id, Budget.year == year, Budget.month == month)
            .all()
        )
        items: list[BudgetAnalyticsItem] = []
        for budget, category_name in budgets:
            spent = Decimal(
                str(
                    self.db.query(func.coalesce(func.sum(Expense.amount), 0))
                    .filter(
                        Expense.user_id == self.user_id,
                        Expense.category_id == budget.category_id,
                        Expense.expense_date >= start,
                        Expense.expense_date <= end,
                    )
                    .scalar()
                )
            )
            budget_amount = Decimal(str(budget.amount))
            remaining = budget_amount - spent
            utilization = float(spent / budget_amount * 100) if budget_amount else 0.0
            if utilization >= 100:
                status = "exceeded"
            elif utilization >= 90:
                status = "warning"
            else:
                status = "on_track"
            items.append(
                BudgetAnalyticsItem(
                    category=category_name,
                    budget=budget_amount,
                    spent=spent,
                    remaining=remaining,
                    utilization=round(utilization, 2),
                    status=status,
                )
            )
        return items

    def goal_progress(self) -> list[GoalProgressItem]:
        goals = (
            self.db.query(SavingsGoal)
            .filter(SavingsGoal.user_id == self.user_id)
            .order_by(SavingsGoal.created_at.desc())
            .all()
        )
        result: list[GoalProgressItem] = []
        for goal in goals:
            target = Decimal(str(goal.target_amount)) or Decimal("1")
            current = Decimal(str(goal.current_amount))
            pct = min(100.0, float(current / target * 100))
            result.append(
                GoalProgressItem(
                    name=goal.name,
                    target_amount=target,
                    current_amount=current,
                    completion_percentage=round(pct, 2),
                    status=goal.status,
                )
            )
        return result

    def monthly_trends(self, months: int = 6) -> list[MonthlyPoint]:
        today = date.today()
        points: list[MonthlyPoint] = []
        year, month = today.year, today.month
        for _ in range(months):
            start, end = self.month_bounds(year, month)
            income = self.total_income(start, end)
            expenses = self.total_expenses(start, end)
            points.append(
                MonthlyPoint(
                    period=f"{year:04d}-{month:02d}",
                    income=income,
                    expenses=expenses,
                    savings=income - expenses,
                )
            )
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        points.reverse()
        return points

    @staticmethod
    def health_status_label(score: float, has_data: bool) -> str:
        if not has_data:
            return "No Data"
        if score >= 85:
            return "Excellent"
        if score >= 70:
            return "Good"
        if score >= 50:
            return "Fair"
        return "Needs Attention"

    def financial_health_score(
        self,
        income: Decimal,
        expenses: Decimal,
        budget_items: list[BudgetAnalyticsItem],
        goals: list[GoalProgressItem],
        trends: list[MonthlyPoint] | None = None,
    ) -> HealthScoreDetails:
        """
        Deterministic 0–100 health score from the selected period's user data.

        Four equal components (max 25 each):
          - spending_score: lower expense/income ratio → higher score
          - savings_score: higher savings rate → higher score (full at 30%+)
          - budget_score: share of budgets on track (neutral 12.5 if none set)
          - goals_score: average goal completion (neutral 12.5 if none set)

        health_score is exactly the sum of the four component scores.
        `trends` is accepted for call-site compatibility but not used in the score.
        """
        _ = trends  # unused — score is period-based, not MoM volatility
        income_f = float(income or 0)
        expenses_f = float(expenses or 0)
        has_data = bool(
            income_f > 0
            or expenses_f > 0
            or budget_items
            or goals
        )

        if not has_data:
            return HealthScoreDetails(
                health_score=0,
                health_status="No Data",
                spending_score=0,
                savings_score=0,
                budget_score=0,
                goals_score=0,
                has_data=False,
            )

        # Spending (0–25): 0% of income spent → 25; 100%+ → 0
        if income_f > 0:
            expense_ratio = min(expenses_f / income_f, 1.0)
        else:
            expense_ratio = 1.0 if expenses_f > 0 else 0.0
        spending_score = round(max(0.0, min(25.0, 25.0 * (1.0 - expense_ratio))), 2)

        # Savings (0–25): full credit at 30%+ savings rate
        if income_f > 0:
            savings_rate = ((income_f - expenses_f) / income_f) * 100.0
        else:
            savings_rate = 0.0
        savings_score = round(max(0.0, min(25.0, savings_rate * (25.0 / 30.0))), 2)

        # Budget (0–25)
        if budget_items:
            on_track = sum(1 for b in budget_items if b.status == "on_track")
            budget_score = round((on_track / len(budget_items)) * 25.0, 2)
        else:
            budget_score = 12.5

        # Goals (0–25)
        if goals:
            avg_goal = sum(g.completion_percentage for g in goals) / len(goals)
            goals_score = round(max(0.0, min(25.0, (avg_goal / 100.0) * 25.0)), 2)
        else:
            goals_score = 12.5

        health_score = round(
            spending_score + savings_score + budget_score + goals_score,
            2,
        )
        health_score = max(0.0, min(100.0, health_score))

        return HealthScoreDetails(
            health_score=health_score,
            health_status=self.health_status_label(health_score, True),
            spending_score=spending_score,
            savings_score=savings_score,
            budget_score=budget_score,
            goals_score=goals_score,
            has_data=True,
        )

    def generate_insights(
        self,
        year: int,
        month: int,
        income: Decimal,
        expenses: Decimal,
        expense_cats: list[CategoryAmount],
        budget_items: list[BudgetAnalyticsItem],
        trends: list[MonthlyPoint],
    ) -> list[str]:
        insights: list[str] = []
        prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
        prev_start, prev_end = self.month_bounds(prev_year, prev_month)
        prev_expenses = self.total_expenses(prev_start, prev_end)
        prev_income = self.total_income(prev_start, prev_end)

        if prev_expenses > 0 and expenses > 0:
            change = float((expenses - prev_expenses) / prev_expenses * 100)
            if abs(change) >= 5:
                direction = "increased" if change > 0 else "decreased"
                insights.append(f"Total expenses {direction} by {abs(change):.1f}% vs last month.")

        if income > prev_income and prev_income > 0:
            savings_delta = (income - expenses) - (prev_income - prev_expenses)
            if savings_delta > 0:
                insights.append(f"Your savings improved by ₹{savings_delta:,.0f} compared to last month.")

        for item in budget_items:
            if item.status == "exceeded":
                insights.append(f"{item.category} budget exceeded.")
            elif item.status == "warning":
                insights.append(
                    f"You have already used {item.utilization:.0f}% of your {item.category} budget."
                )
            elif item.utilization < 80:
                insights.append(f"{item.category} expenses are within the planned budget.")

        if expense_cats:
            top = max(expense_cats, key=lambda x: x.amount)
            insights.append(f"Largest expense category this month: {top.category} (₹{top.amount:,.0f}).")

        if income > 0:
            rate = float((income - expenses) / income * 100)
            insights.append(f"Current savings rate is {rate:.1f}%.")

        # Category MoM spikes
        prev_cats = {
            c.category: c.amount for c in self.expense_by_category(prev_start, prev_end)
        }
        for cat in expense_cats:
            prev = prev_cats.get(cat.category)
            if prev and prev > 0:
                pct = float((cat.amount - prev) / prev * 100)
                if pct >= 20:
                    insights.append(
                        f"{cat.category} expenses increased by {pct:.0f}% this month."
                    )
                elif pct <= -10:
                    insights.append(
                        f"{cat.category} expenses decreased by {abs(pct):.0f}%."
                    )

        return insights[:10]

    def build_dashboard(self, year: int | None = None, month: int | None = None) -> AnalyticsDashboard:
        today = date.today()
        year = year or today.year
        month = month or today.month
        start, end = self.month_bounds(year, month)

        income = self.total_income(start, end)
        expenses = self.total_expenses(start, end)
        net = income - expenses
        savings_rate = float(net / income * 100) if income else 0.0

        budget_items = self.budget_analytics(year, month)
        if budget_items:
            total_budget = sum((b.budget for b in budget_items), ZERO)
            total_spent = sum((b.spent for b in budget_items), ZERO)
            budget_usage = float(total_spent / total_budget * 100) if total_budget else 0.0
        else:
            budget_usage = 0.0

        expense_cats = self.expense_by_category(start, end)
        income_sources = self.income_by_source(start, end)
        goals = self.goal_progress()
        trends = self.monthly_trends()
        health = self.financial_health_score(
            income, expenses, budget_items, goals, trends
        )
        insights = self.generate_insights(
            year, month, income, expenses, expense_cats, budget_items, trends
        )

        summary = FinancialSummary(
            total_income=income,
            total_expenses=expenses,
            net_savings=net,
            savings_rate=round(savings_rate, 2),
            budget_usage=round(budget_usage, 2),
            financial_health_score=health.health_score,
        )

        # Component scores on 0–25 scale; keep legacy keys for older UI/AI readers
        breakdown = {
            "spending_score": health.spending_score,
            "savings_score": health.savings_score,
            "budget_score": health.budget_score,
            "goals_score": health.goals_score,
            # legacy aliases (same values)
            "expense_ratio": health.spending_score,
            "savings_rate": health.savings_score,
            "budget_discipline": health.budget_score,
            "goal_progress": health.goals_score,
        }

        return AnalyticsDashboard(
            summary=summary,
            income_by_source=income_sources,
            expense_by_category=expense_cats,
            monthly_trends=trends,
            budget_analytics=budget_items,
            goal_progress=goals,
            insights=insights,
            health_breakdown=breakdown,
            health_score=health.health_score,
            health_status=health.health_status,
            spending_score=health.spending_score,
            savings_score=health.savings_score,
            budget_score=health.budget_score,
            goals_score=health.goals_score,
            health_has_data=health.has_data,
        )

    def build_context_summary(self, year: int | None = None, month: int | None = None) -> dict:
        """Compact context for the AI layer — never raw DB rows."""
        from datetime import date

        today = date.today()
        year = year or today.year
        month = month or today.month
        dashboard = self.build_dashboard(year, month)
        summary = dashboard.summary.model_dump(mode="json")
        income = float(summary.get("total_income", 0) or 0)
        expenses = float(summary.get("total_expenses", 0) or 0)
        return {
            "period": {
                "year": year,
                "month": month,
                "label": date(year, month, 1).strftime("%B %Y"),
            },
            "summary": summary,
            "remaining_balance": income - expenses,
            "top_expense_categories": [
                c.model_dump(mode="json") for c in dashboard.expense_by_category[:5]
            ],
            "income_sources": [
                c.model_dump(mode="json") for c in dashboard.income_by_source[:5]
            ],
            "budgets": [b.model_dump(mode="json") for b in dashboard.budget_analytics],
            "budget_alerts": [
                b.model_dump(mode="json")
                for b in dashboard.budget_analytics
                if b.status in {"warning", "exceeded"}
            ],
            "goal_progress": [g.model_dump(mode="json") for g in dashboard.goal_progress[:5]],
            "insights": dashboard.insights,
            "health_breakdown": dashboard.health_breakdown,
            "health_score": dashboard.health_score,
            "health_status": dashboard.health_status,
            "spending_score": dashboard.spending_score,
            "savings_score": dashboard.savings_score,
            "budget_score": dashboard.budget_score,
            "goals_score": dashboard.goals_score,
            "health_has_data": dashboard.health_has_data,
        }
