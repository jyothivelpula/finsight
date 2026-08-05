from decimal import Decimal

from pydantic import BaseModel


class FinancialSummary(BaseModel):
    total_income: Decimal
    total_expenses: Decimal
    net_savings: Decimal
    savings_rate: float
    budget_usage: float
    financial_health_score: float


class CategoryAmount(BaseModel):
    category: str
    amount: Decimal
    percentage: float


class MonthlyPoint(BaseModel):
    period: str
    income: Decimal
    expenses: Decimal
    savings: Decimal


class BudgetAnalyticsItem(BaseModel):
    category: str
    budget: Decimal
    spent: Decimal
    remaining: Decimal
    utilization: float
    status: str


class GoalProgressItem(BaseModel):
    name: str
    target_amount: Decimal
    current_amount: Decimal
    completion_percentage: float
    status: str


class AnalyticsDashboard(BaseModel):
    summary: FinancialSummary
    income_by_source: list[CategoryAmount]
    expense_by_category: list[CategoryAmount]
    monthly_trends: list[MonthlyPoint]
    budget_analytics: list[BudgetAnalyticsItem]
    goal_progress: list[GoalProgressItem]
    insights: list[str]
    health_breakdown: dict[str, float]
