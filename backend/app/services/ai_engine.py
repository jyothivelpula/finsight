"""
Financial Intelligence Engine.

Production workflow:
  User question
    → Analytics Engine
    → Financial Summary
    → Context Builder
    → LLM (or rule-based fallback)
    → AI Response

The AI layer never reads the database. It only consumes a compact
analytics context. The LLM must not invent transactions or amounts.
"""

from __future__ import annotations

import json

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.analytics_engine import AnalyticsEngine


SYSTEM_PROMPT = """You are FinSight, an intelligent personal finance assistant.
Use ONLY the provided financial context. Do not invent transactions or amounts.
Give practical advice for professionals in India (use ₹ when mentioning money).

Write like a normal chat reply:
- 2 to 5 short sentences, or a short intro plus a few bullet lines
- Put each bullet on its own line starting with "- "
- Prefer plain language; avoid dense JSON, tables, or markdown headers
- Lead with the direct answer, then one clear next step
If the context lacks data for the question, say so clearly and suggest what to add.
"""


class FinancialIntelligenceEngine:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.analytics = AnalyticsEngine(db, user_id)

    @staticmethod
    def _inr(amount: float | int) -> str:
        return f"₹{float(amount):,.0f}"

    def build_prompt(self, question: str, context: dict) -> str:
        return (
            "Financial context (JSON — verified by the backend analytics engine):\n"
            f"{json.dumps(context, indent=2, default=str)}\n\n"
            f"User question: {question}\n\n"
            "Reply in natural structured text (short paragraphs and simple bullets). "
            "Use only numbers that appear in the financial context."
        )

    def rule_based_answer(self, question: str, context: dict) -> str:
        """Offline answers from verified analytics when the LLM is unavailable."""
        q = question.lower()
        summary = context.get("summary", {})
        insights = context.get("insights", [])
        top_cats = context.get("top_expense_categories", [])
        budget_alerts = context.get("budget_alerts", [])
        health = context.get("health_breakdown", {})

        if "spend the most" in q or "largest" in q or "most money" in q:
            if not top_cats:
                return "No expense data is available for this period yet."
            top = top_cats[0]
            lines = [
                f"You spent the most on {top['category']} — "
                f"{self._inr(top['amount'])} ({top['percentage']}% of expenses).",
            ]
            if len(top_cats) > 1:
                lines.append("Next largest categories:")
                for cat in top_cats[1:4]:
                    lines.append(
                        f"- {cat['category']}: {self._inr(cat['amount'])} ({cat['percentage']}%)"
                    )
            return "\n".join(lines)

        if "budget" in q and ("exceed" in q or "over" in q):
            if not budget_alerts:
                return "No categories have exceeded or nearly exceeded their budgets this month."
            lines = ["Categories needing attention:"]
            for b in budget_alerts:
                status = str(b.get("status", "")).replace("_", " ")
                lines.append(
                    f"- {b['category']}: {b['utilization']}% used ({status})"
                )
            lines.append("Try trimming those categories first to get back on plan.")
            return "\n".join(lines)

        if "health" in q or "score" in q:
            score = summary.get("financial_health_score", 0)
            lines = [f"Your financial health score is {score}/100."]
            if health:
                weakest = min(health, key=health.get)
                lines.append(
                    f"The weakest area right now is {weakest.replace('_', ' ')}."
                )
                lines.append("Score breakdown:")
                for key, value in health.items():
                    lines.append(f"- {key.replace('_', ' ').title()}: {value}")
            lines.append("Focus on improving the weakest component next.")
            return "\n".join(lines)

        if "save" in q:
            income = float(summary.get("total_income", 0) or 0)
            expenses = float(summary.get("total_expenses", 0) or 0)
            rate = float(summary.get("savings_rate", 0) or 0)
            lines = [
                f"This month you earned {self._inr(income)} and spent {self._inr(expenses)}.",
                f"Your savings rate is {rate:.1f}%.",
            ]
            shopping = next(
                (c for c in top_cats if str(c.get("category", "")).lower() == "shopping"),
                None,
            )
            if shopping:
                cut = float(shopping["amount"]) * 0.2
                lines.append(
                    f"Reducing shopping by 20% could free about {self._inr(cut)}."
                )
            lines.append(
                "Prioritize high-spend categories and keep budgets under 90% utilization."
            )
            return "\n".join(lines)

        if insights:
            lines = ["Based on your latest analytics:"]
            lines.extend(f"- {item}" for item in insights[:5])
            return "\n".join(lines)

        return (
            "I analyzed your financial summary.\n"
            "Add more income, expenses, and budgets to unlock deeper personalized recommendations."
        )

    async def ask_llm(
        self,
        prompt: str,
        history: list[dict] | None = None,
    ) -> str | None:
        api_key = settings.llm_api_key
        api_url = settings.llm_api_url
        if not api_key or not api_url:
            return None

        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for turn in (history or [])[-6:]:
            role = turn.get("role")
            content = str(turn.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content[:500]})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.LLM_MODEL,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": 500,
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(api_url, headers=headers, json=payload)
                response.raise_for_status()
                text = response.json()["choices"][0]["message"]["content"].strip()
                return text or None
        except Exception:
            return None

    async def answer(
        self,
        question: str,
        year: int | None = None,
        month: int | None = None,
        history: list[dict] | None = None,
    ) -> dict:
        # User Question → Analytics Engine → Context Builder → LLM → Response
        context = self.analytics.build_context_summary(year, month)
        prompt = self.build_prompt(question, context)
        llm_answer = await self.ask_llm(prompt, history=history)
        answer = llm_answer or self.rule_based_answer(question, context)
        return {
            "answer": answer,
            "insights": context.get("insights", []),
            "context_summary": context,
        }
