"""Financial health score — deterministic, period-based, responsive to expenses."""

from decimal import Decimal

from app.services.analytics_engine import AnalyticsEngine


def _health(income: str, expenses: str):
    eng = AnalyticsEngine.__new__(AnalyticsEngine)
    return eng.financial_health_score(
        Decimal(income),
        Decimal(expenses),
        budget_items=[],
        goals=[],
        trends=[],
    )


def test_components_sum_to_health_score():
    h = _health("100000", "40000")
    assert h.has_data is True
    assert h.health_score == round(
        h.spending_score + h.savings_score + h.budget_score + h.goals_score,
        2,
    )
    assert 0 <= h.health_score <= 100
    assert h.health_status in {"Excellent", "Good", "Fair", "Needs Attention"}


def test_health_score_drops_when_expenses_rise():
    before = _health("6200000", "762000")
    after = _health("6200000", "1862000")  # large spend increase
    assert after.health_score < before.health_score
    assert after.spending_score < before.spending_score
    assert after.savings_score <= before.savings_score


def test_small_expense_moves_spending_component():
    before = _health("100000", "20000")
    after = _health("100000", "25000")
    assert after.spending_score < before.spending_score
    assert after.health_score < before.health_score


def test_no_data_fallback_is_distinct():
    h = _health("0", "0")
    assert h.has_data is False
    assert h.health_score == 0
    assert h.health_status == "No Data"
    assert h.spending_score == h.savings_score == h.budget_score == h.goals_score == 0


def test_each_component_capped_at_25():
    h = _health("100000", "0")  # strong savings + spending
    assert h.spending_score <= 25
    assert h.savings_score <= 25
    assert h.budget_score <= 25
    assert h.goals_score <= 25
