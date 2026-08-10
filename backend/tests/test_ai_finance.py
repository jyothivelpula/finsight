"""Tests for FinSight AI routing and finance helpers."""

import asyncio
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.services.ai_engine import ConversationPath, FinancialIntelligenceEngine, IntentDomain
from app.services.financial_calculator import (
    calculate_current_balance,
    calculate_remaining_after_expense,
    calculate_remaining_balance,
    calculate_savings,
    format_inr,
)
from app.services.message_parser import StatementKind, parse_user_message


SAMPLE_CONTEXT = {
    "period": {"year": 2026, "month": 8, "label": "August 2026"},
    "summary": {
        "total_income": 50000,
        "total_expenses": 32000,
        "net_savings": 18000,
        "savings_rate": 36.0,
        "budget_usage": 80.0,
        "financial_health_score": 72,
    },
    "remaining_balance": 18000,
    "top_expense_categories": [
        {"category": "Shopping", "amount": 10000, "percentage": 31.25},
        {"category": "Food", "amount": 8000, "percentage": 25.0},
    ],
    "income_sources": [{"category": "Salary", "amount": 50000, "percentage": 100.0}],
    "budgets": [],
    "budget_alerts": [
        {
            "category": "Shopping",
            "budget": 8000,
            "spent": 10000,
            "utilization": 125.0,
            "status": "exceeded",
        }
    ],
    "goal_progress": [],
    "insights": [
        "Shopping expenses increased by 24% this month.",
        "Current savings rate is 36.0%.",
    ],
    "health_breakdown": {
        "spending_score": 16,
        "savings_score": 18,
        "budget_score": 10,
        "goals_score": 14,
    },
    "health_score": 72,
    "health_status": "Good",
    "spending_score": 16,
    "savings_score": 18,
    "budget_score": 10,
    "goals_score": 14,
    "health_has_data": True,
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


def test_classify_natural_vs_financial():
    engine = _engine_with_context()
    path, domain = engine.classify("hi")
    assert path == ConversationPath.NATURAL
    assert domain == IntentDomain.GREETING

    path, domain = engine.classify("Where did I spend the most money?")
    assert path == ConversationPath.FINANCIAL
    assert domain == IntentDomain.EXPENSES

    path, domain = engine.classify("Which category exceeded my budget?")
    assert path == ConversationPath.FINANCIAL
    assert domain == IntentDomain.BUDGET

    path, domain = engine.classify("How am I doing financially this month?")
    assert path == ConversationPath.FINANCIAL
    assert domain == IntentDomain.ANALYTICS

    path, domain = engine.classify("Tell me about my current situation")
    assert path == ConversationPath.FINANCIAL
    assert domain == IntentDomain.ANALYTICS


def test_situation_snapshot_uses_current_stats():
    engine = _engine_with_context()
    reply = engine.rule_based_answer(
        "How am I doing financially this month?",
        IntentDomain.ANALYTICS,
        SAMPLE_CONTEXT,
    )
    assert "August 2026" in reply or "current financial situation" in reply.lower()
    assert "50,000" in reply
    assert "32,000" in reply
    assert "18,000" in reply
    assert "72" in reply


def test_rule_based_top_spend():
    engine = _engine_with_context()
    reply = engine.rule_based_answer(
        "Where did I spend the most money?",
        IntentDomain.EXPENSES,
        SAMPLE_CONTEXT,
    )
    assert "Shopping" in reply
    assert "10,000" in reply


def test_rule_based_budget_exceeded():
    engine = _engine_with_context()
    reply = engine.rule_based_answer(
        "Which category exceeded my budget?",
        IntentDomain.BUDGET,
        SAMPLE_CONTEXT,
    )
    assert "Shopping" in reply
    assert "exceeded" in reply.lower() or "125" in reply


def test_rule_based_health_score():
    engine = _engine_with_context()
    reply = engine.rule_based_answer(
        "What is affecting my financial health score?",
        IntentDomain.ANALYTICS,
        SAMPLE_CONTEXT,
    )
    assert "72" in reply
    assert "budget score" in reply.lower() or "spending score" in reply.lower()


def test_rule_based_savings_tip():
    engine = _engine_with_context()
    reply = engine.rule_based_answer(
        "How can I save ₹10,000 next month?",
        IntentDomain.SAVINGS,
        SAMPLE_CONTEXT,
    )
    assert "50,000" in reply
    assert "32,000" in reply
    assert "shopping" in reply.lower()


def test_answer_financial_path_with_actions():
    engine = _engine_with_context()

    async def _run():
        with patch.object(engine, "ask_llm", return_value=None):
            return await engine.answer("Where did I spend the most money?")

    result = asyncio.run(_run())
    assert "Shopping" in result["answer"]
    assert result["suggested_actions"]
    assert result["context_summary"]["path"] == "financial_intent"
    assert result["context_summary"]["intent_domain"] == "expenses"
    assert "suggested_actions" in result["context_summary"]["pipeline"]
    engine.analytics.build_context_summary.assert_called_once()


def test_answer_natural_path_skips_database():
    engine = _engine_with_context()

    async def _run():
        with patch.object(engine, "ask_llm", return_value=None):
            return await engine.answer("hi")

    result = asyncio.run(_run())
    assert result["context_summary"]["path"] == "natural_conversation"
    assert result["suggested_actions"]
    engine.analytics.build_context_summary.assert_not_called()


def test_answer_prefers_llm_when_available():
    engine = _engine_with_context()

    async def _run():
        with patch.object(engine, "ask_llm", return_value="LLM personalized advice."):
            return await engine.answer("How can I improve my savings?")

    result = asyncio.run(_run())
    assert result["answer"] == "LLM personalized advice."
    assert result["suggested_actions"]


def test_chat_records_expense_and_skips_hypothetical():
    from types import SimpleNamespace

    engine = _engine_with_context()
    engine.db = MagicMock()
    food = SimpleNamespace(id=1, name="Food")
    other = SimpleNamespace(id=2, name="Other")
    engine.db.query.return_value.filter.return_value.all.return_value = [food, other]

    def _add(obj):
        obj.id = 42

    engine.db.add.side_effect = _add

    recorded = engine.try_record_transaction("I spent 750 on food yesterday")
    assert recorded is not None
    assert recorded["kind"] == "expense"
    assert recorded["amount"] == 750.0
    assert recorded["label"] == "Food"

    assert engine.try_record_transaction("What if I spend 3000 on shopping?") is None
    assert engine.try_record_transaction("Where did I spend the most?") is None


def test_answer_includes_recorded_transaction_note():
    engine = _engine_with_context()

    async def _run():
        with (
            patch.object(
                engine,
                "try_record_transaction",
                return_value={
                    "kind": "expense",
                    "id": 1,
                    "amount": 500,
                    "label": "Food",
                    "date": "2026-08-07",
                },
            ),
            patch.object(engine, "ask_llm", return_value="Food is now a notable category."),
        ):
            return await engine.answer("I spent 500 on food")

    result = asyncio.run(_run())
    assert "Logged expense" in result["answer"]
    assert result["context_summary"]["recorded_transaction"]["kind"] == "expense"
