"""Deterministic financial calculations — never performed by the LLM."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


ZERO = Decimal("0")


def to_decimal(value: Any) -> Decimal:
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def format_inr(amount: Any) -> str:
    """Format as Indian rupees without inventing precision."""
    value = to_decimal(amount).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    negative = value < 0
    n = abs(int(value))
    s = str(n)
    if len(s) <= 3:
        grouped = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        parts: list[str] = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        grouped = ",".join(parts + [last3])
    sign = "-" if negative else ""
    return f"₹{sign}{grouped}"


def calculate_remaining_balance(total_money: Any, spent_or_used: Any = 0) -> Decimal:
    return to_decimal(total_money) - to_decimal(spent_or_used)


def calculate_remaining_after_expense(total_income: Any, expense_amount: Any) -> Decimal:
    """remaining = total_income - expense_amount"""
    return calculate_remaining_balance(total_income, expense_amount)


def calculate_current_balance(total_income: Any, total_expenses: Any) -> Decimal:
    """current_balance = total_income - total_expenses"""
    return calculate_remaining_balance(total_income, total_expenses)


def calculate_total_income(amounts: list[Any]) -> Decimal:
    return sum((to_decimal(a) for a in amounts), ZERO)


def calculate_total_expenses(amounts: list[Any]) -> Decimal:
    return sum((to_decimal(a) for a in amounts), ZERO)


def calculate_savings(income: Any, expenses: Any) -> Decimal:
    return to_decimal(income) - to_decimal(expenses)


def calculate_budget_remaining(budget_amount: Any, spent: Any) -> Decimal:
    return to_decimal(budget_amount) - to_decimal(spent)


def calculate_goal_progress(current_amount: Any, target_amount: Any) -> dict[str, Decimal | float]:
    current = to_decimal(current_amount)
    target = to_decimal(target_amount)
    remaining = max(ZERO, target - current)
    pct = float((current / target * 100) if target > 0 else 0)
    return {
        "current_amount": current,
        "target_amount": target,
        "remaining_amount": remaining,
        "completion_percentage": round(min(100.0, pct), 2),
    }
