"""
Prove Dashboard API metrics and PDF reports share one AnalyticsEngine calculation.

Scenario (selected month):
  Income   ₹62,00,000
  Expenses ₹9,47,000
  Savings  ₹52,53,000
  Budgets  all on_track  → Budget bar 100
  Goals    34% complete  → Goals bar 34

Expected (4 × 25 formula):
  spending_score ≈ 21.18  → bar 85
  savings_score  = 25.00  → bar 100
  budget_score   = 25.00  → bar 100
  goals_score    = 8.50   → bar 34
  health_score   ≈ 79.68  → displayed 80
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.schemas.analytics import (
    AnalyticsDashboard,
    BudgetAnalyticsItem,
    FinancialSummary,
    GoalProgressItem,
)
from app.schemas.reports import ReportRequest
from app.services.analytics_engine import AnalyticsEngine
from app.services.reports import ReportService, _PremiumPdfBuilder


INCOME = Decimal("6200000")
EXPENSES = Decimal("947000")
SAVINGS = INCOME - EXPENSES  # 5253000 ≈ ₹52.53L


def _on_track_budget() -> BudgetAnalyticsItem:
    return BudgetAnalyticsItem(
        category="Entertainment",
        budget=Decimal("5500"),
        spent=Decimal("0"),
        remaining=Decimal("5500"),
        utilization=0.0,
        status="on_track",
    )


def _goal_34pct() -> GoalProgressItem:
    return GoalProgressItem(
        name="Emergency Fund",
        target_amount=Decimal("100000"),
        current_amount=Decimal("34000"),
        completion_percentage=34.0,
        status="active",
    )


def _compute_health():
    eng = AnalyticsEngine.__new__(AnalyticsEngine)
    return eng.financial_health_score(
        INCOME,
        EXPENSES,
        budget_items=[_on_track_budget()],
        goals=[_goal_34pct()],
        trends=[],
    )


def test_scenario_matches_dashboard_bars_and_score_80():
    health = _compute_health()

    spending_bar = round((health.spending_score / 25) * 100)
    savings_bar = round((health.savings_score / 25) * 100)
    budget_bar = round((health.budget_score / 25) * 100)
    goals_bar = round((health.goals_score / 25) * 100)

    assert float(SAVINGS) == 5253000.0
    assert health.spending_score == 21.18
    assert health.savings_score == 25.0
    assert health.budget_score == 25.0
    assert health.goals_score == 8.5
    assert spending_bar == 85
    assert savings_bar == 100
    assert budget_bar == 100
    assert goals_bar == 34
    assert health.health_score == 79.68
    assert round(health.health_score) == 80
    assert health.health_status == "Good"
    assert health.health_score == round(
        health.spending_score
        + health.savings_score
        + health.budget_score
        + health.goals_score,
        2,
    )


def _sample_dashboard() -> AnalyticsDashboard:
    health = _compute_health()
    summary = FinancialSummary(
        total_income=INCOME,
        total_expenses=EXPENSES,
        net_savings=SAVINGS,
        savings_rate=round(float(SAVINGS / INCOME * 100), 2),
        budget_usage=0.0,
        financial_health_score=health.health_score,
    )
    breakdown = {
        "spending_score": health.spending_score,
        "savings_score": health.savings_score,
        "budget_score": health.budget_score,
        "goals_score": health.goals_score,
    }
    return AnalyticsDashboard(
        summary=summary,
        income_by_source=[],
        expense_by_category=[],
        monthly_trends=[],
        budget_analytics=[_on_track_budget()],
        goal_progress=[_goal_34pct()],
        insights=[],
        health_breakdown=breakdown,
        health_score=health.health_score,
        health_status=health.health_status,
        spending_score=health.spending_score,
        savings_score=health.savings_score,
        budget_score=health.budget_score,
        goals_score=health.goals_score,
        health_has_data=True,
    )


def test_pdf_builder_reads_same_health_fields_as_api_dashboard():
    dashboard = _sample_dashboard()
    api_score = dashboard.health_score
    api_status = dashboard.health_status
    api_components = (
        dashboard.spending_score,
        dashboard.savings_score,
        dashboard.budget_score,
        dashboard.goals_score,
    )

    builder = _PremiumPdfBuilder(
        stream=MagicMock(),
        dashboard=dashboard,
        report_type="monthly",
        year=2026,
        month=8,
        recent=[],
        total_pages=1,
    )
    assert float(builder.dashboard.health_score) == api_score
    assert builder.dashboard.health_status == api_status
    assert (
        builder.dashboard.spending_score,
        builder.dashboard.savings_score,
        builder.dashboard.budget_score,
        builder.dashboard.goals_score,
    ) == api_components
    assert round(api_score) == 80
    # PDF display scale matches Dashboard bars
    assert round((builder.dashboard.spending_score / 25) * 100) == 85
    assert round((builder.dashboard.goals_score / 25) * 100) == 34


def test_report_service_uses_analytics_build_dashboard(tmp_path: Path):
    """Monthly/health/savings PDFs all call the same build_dashboard once."""
    dashboard = _sample_dashboard()
    db = MagicMock()
    service = ReportService(db, user_id=3)
    service.analytics = MagicMock()
    service.analytics.build_dashboard.return_value = dashboard
    service.reports_dir = tmp_path
    service._recent_transactions = MagicMock(return_value=[])  # type: ignore[method-assign]

    for report_type in ("monthly", "health", "savings"):
        service.analytics.build_dashboard.reset_mock()
        captured: dict = {}

        original_write = service._write_pdf

        def _capture_write(path, dash, rtype, year, month, recent, _orig=original_write):
            captured["dashboard"] = dash
            captured["report_type"] = rtype
            return _orig(path, dash, rtype, year, month, recent)

        with patch.object(service, "_write_pdf", side_effect=_capture_write):
            result = service.generate(
                ReportRequest(report_type=report_type, year=2026, month=8, format="pdf")
            )

        service.analytics.build_dashboard.assert_called_once_with(2026, 8)
        assert result.format == "pdf"
        assert (tmp_path / result.filename).exists()
        # Same object/fields the API would return — no separate PDF formula
        pdf_dash = captured["dashboard"]
        assert pdf_dash is dashboard
        assert pdf_dash.health_score == dashboard.health_score == 79.68
        assert pdf_dash.health_status == "Good"
        assert pdf_dash.spending_score == dashboard.spending_score
        assert pdf_dash.summary.total_income == INCOME
        assert pdf_dash.summary.total_expenses == EXPENSES
        assert pdf_dash.summary.net_savings == SAVINGS
        assert pdf_dash.summary.financial_health_score == pdf_dash.health_score


def test_context_summary_mirrors_dashboard_health():
    """AI Coach context uses the same build_dashboard health fields."""
    eng = AnalyticsEngine.__new__(AnalyticsEngine)
    eng.db = MagicMock()
    eng.user_id = 1
    dash = _sample_dashboard()
    eng.build_dashboard = MagicMock(return_value=dash)  # type: ignore[method-assign]

    ctx = eng.build_context_summary(2026, 8)
    assert ctx["health_score"] == dash.health_score
    assert ctx["health_status"] == dash.health_status
    assert ctx["spending_score"] == dash.spending_score
    assert ctx["savings_score"] == dash.savings_score
    assert ctx["budget_score"] == dash.budget_score
    assert ctx["goals_score"] == dash.goals_score
    assert ctx["summary"]["financial_health_score"] == dash.health_score
    assert float(ctx["summary"]["total_income"]) == float(INCOME)
    assert float(ctx["summary"]["total_expenses"]) == float(EXPENSES)
