"""Tests for production AI engine and supporting finance helpers."""

import asyncio
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.services.ai_engine import FinancialIntelligenceEngine
from app.services.financial_calculator import (
    calculate_current_balance,
    calculate_remaining_after_expense,
    calculate_remaining_balance,
    calculate_savings,
    format_inr,
)
from app.services.message_parser import StatementKind, parse_user_message


SAMPLE_CONTEXT = {
    "summary": {
        "total_income": 50000,
        "total_expenses": 32000,
        "net_savings": 18000,
        "savings_rate": 36.0,
        "budget_usage": 80.0,
        "financial_health_score": 72,
    },
    "top_expense_categories": [
        {"category": "Shopping", "amount": 10000, "percentage": 31.25},
        {"category": "Food", "amount": 8000, "percentage": 25.0},
    ],
    "income_sources": [{"category": "Salary", "amount": 50000, "percentage": 100.0}],
    "budget_alerts": [
        {"category": "Shopping", "budget": 8000, "spent": 10000, "utilization": 125.0, "status": "exceeded"}
    ],
    "goal_progress": [],
    "insights": [
        "Shopping expenses increased by 24% this month.",
        "Current savings rate is 36.0%.",
    ],
    "health_breakdown": {
        "savings_rate": 18,
        "budget_discipline": 10,
        "expense_ratio": 16,
        "goal_progress": 14,
        "spending_stability": 14,
    },
}


def _engine_with_context(context: dict | None = None) -> FinancialIntelligenceEngine:
    engine = FinancialIntelligenceEngine.__new__(FinancialIntelligenceEngine)
    engine.db = None
    engine.user_id = 1
    engine.analytics = MagicMock()
    engine.analytics.build_context_summary.return_value = context or SAMPLE_CONTEXT
    return engine


def test_format_and_basic_math():
    assert format_inr(3000) == "₹3,000"
    assert format_inr(50000) == "₹50,000"
    assert calculate_remaining_after_expense(50000, 3000) == Decimal("47000")
    assert calculate_current_balance(50000, 40000) == Decimal("10000")
    assert calculate_remaining_balance(50000, 3000) == Decimal("47000")
    assert calculate_savings(50000, 3000) == Decimal("47000")


def test_parser_kinds_still_work():
    assert parse_user_message("I have 3000 left.").kind == StatementKind.REMAINING_BALANCE_CLAIM
    assert parse_user_message("how much my total money").kind == StatementKind.QUERY_INCOME
    assert parse_user_message("What if I spend 3000?").kind == StatementKind.HYPOTHETICAL_EXPENSE
    assert parse_user_message("can you motivate me to save my money").kind == StatementKind.GENERAL
    assert parse_user_message("income").kind == StatementKind.QUERY_INCOME
    assert parse_user_message("spending").kind == StatementKind.QUERY_EXPENSES
    assert parse_user_message("remaining").kind == StatementKind.QUERY_REMAINING


def test_rule_based_top_spend():
    engine = _engine_with_context()
    reply = engine.rule_based_answer("Where did I spend the most money?", SAMPLE_CONTEXT)
    assert "Shopping" in reply
    assert "10,000" in reply


def test_rule_based_budget_exceeded():
    engine = _engine_with_context()
    reply = engine.rule_based_answer("Which category exceeded my budget?", SAMPLE_CONTEXT)
    assert "Shopping" in reply
    assert "exceeded" in reply.lower() or "125" in reply


def test_rule_based_health_score():
    engine = _engine_with_context()
    reply = engine.rule_based_answer("What is affecting my financial health score?", SAMPLE_CONTEXT)
    assert "72" in reply
    assert "budget discipline" in reply.lower()


def test_rule_based_savings_tip():
    engine = _engine_with_context()
    reply = engine.rule_based_answer("How can I save ₹10,000 next month?", SAMPLE_CONTEXT)
    assert "50,000" in reply
    assert "32,000" in reply
    assert "shopping" in reply.lower()


def test_answer_uses_analytics_context_and_fallback():
    engine = _engine_with_context()

    async def _run():
        with patch.object(engine, "ask_llm", return_value=None):
            result = await engine.answer("Where did I spend the most money?")
        return result

    result = asyncio.run(_run())
    assert "Shopping" in result["answer"]
    assert result["insights"] == SAMPLE_CONTEXT["insights"]
    assert result["context_summary"]["summary"]["financial_health_score"] == 72
    engine.analytics.build_context_summary.assert_called_once()


def test_answer_prefers_llm_when_available():
    engine = _engine_with_context()

    async def _run():
        with patch.object(engine, "ask_llm", return_value="LLM personalized advice."):
            result = await engine.answer("How can I improve my savings?")
        return result

    result = asyncio.run(_run())
    assert result["answer"] == "LLM personalized advice."
    assert result["insights"] == SAMPLE_CONTEXT["insights"]
