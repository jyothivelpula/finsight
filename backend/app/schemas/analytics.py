from decimal import Decimal

from pydantic import BaseModel, Field


class FinancialSummary(BaseModel):
    total_income: Decimal
    total_expenses: Decimal
    net_savings: Decimal
    savings_rate: float
    budget_usage: float
    financial_health_score: float


class HealthScoreDetails(BaseModel):
    """Deterministic health score derived from the authenticated user's period data."""

    health_score: float = Field(ge=0, le=100)
    health_status: str
    spending_score: float = Field(ge=0, le=25)
    savings_score: float = Field(ge=0, le=25)
    budget_score: float = Field(ge=0, le=25)
    goals_score: float = Field(ge=0, le=25)
    has_data: bool = True


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
    # Explicit health fields (also mirrored in summary.financial_health_score)
    health_score: float = 0
    health_status: str = "No Data"
    spending_score: float = 0
    savings_score: float = 0
    budget_score: float = 0
    goals_score: float = 0
    health_has_data: bool = False
