"""
FinSight AI

                    FIN SIGHT AI
                         │
           ┌─────────────┴─────────────┐
           │                           │
     Natural Conversation        Financial Intent
           │                           │
    Greetings / Context       Income · Expenses · Budget
                              Savings · Goals · Analytics
                                       │
                              Financial Engine
                                       │
                         Current user statistics (DB)
                                       │
                              AI Response
                                       │
                              Suggested Actions

Financial answers always use the user's current-period statistics
from analytics. The AI never invents money amounts.
"""

from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal
from enum import Enum

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.category import Category
from app.models.expense import Expense
from app.models.income import Income
from app.services.analytics_engine import AnalyticsEngine
from app.services.message_parser import (
    StatementKind,
    extract_context_from_history,
    parse_user_message,
)

# Map chat keywords → default expense category names
_CATEGORY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("Food", ("food", "lunch", "dinner", "breakfast", "grocery", "groceries", "restaurant", "cafe", "snacks")),
    ("Rent", ("rent", "house rent", "apartment")),
    ("Utilities", ("utility", "utilities", "electricity", "water bill", "internet", "wifi", "gas bill")),
    ("Shopping", ("shopping", "amazon", "clothes", "clothing", "flipkart")),
    ("Medical", ("medical", "doctor", "hospital", "medicine", "pharmacy", "health")),
    ("Education", ("education", "tuition", "school", "college", "course", "fees")),
    ("Entertainment", ("entertainment", "movie", "netflix", "spotify", "game")),
    ("Transportation", ("transport", "uber", "ola", "metro", "bus", "auto", "cab", "petrol", "fuel", "diesel")),
    ("Travel", ("travel", "flight", "hotel", "trip", "train")),
]


class ConversationPath(str, Enum):
    NATURAL = "natural_conversation"
    FINANCIAL = "financial_intent"


class IntentDomain(str, Enum):
    GREETING = "greeting"
    GENERAL = "general"
    INCOME = "income"
    EXPENSES = "expenses"
    BUDGET = "budget"
    SAVINGS = "savings"
    GOALS = "goals"
    ANALYTICS = "analytics"


_SITUATION_RE = re.compile(
    r"\b("
    r"current\s+(situation|status|finances?|position|standing)|"
    r"how\s+am\s+i\s+(doing|standing)|"
    r"how('?s|\s+is)\s+my\s+(money|finance|financial|budget|situation)|"
    r"my\s+(current\s+)?(financial\s+)?(situation|status|overview|snapshot|summary)|"
    r"tell\s+me\s+about\s+my\s+(money|finances?|spending)|"
    r"where\s+do\s+i\s+stand|"
    r"financial\s+(overview|summary|position)|"
    r"this\s+month('?s)?\s+(summary|overview)|"
    r"can\s+i\s+afford|"
    r"safe\s+to\s+spend"
    r")\b",
    re.IGNORECASE,
)


NATURAL_SYSTEM_PROMPT = """You are FinSight AI, a warm personal finance companion.
The user is greeting you or chatting naturally — not asking for a full finance report.
Reply in 1-3 short friendly sentences. Match their tone.
Do NOT dump income, expenses, budgets, or scores unless they asked.
You may lightly invite them to ask about their current finances, spending, budgets, savings, goals, or health score.

CRITICAL:
- NEVER say you lack data, don't have current info, or need them to "feed" finances.
- FinSight already stores their transactions. If they want numbers, invite a clear question
  like “How am I doing this month?” — do not claim the data is missing.
"""

FINANCE_SYSTEM_PROMPT = """You are FinSight AI, an intelligent personal finance assistant.
The user is asking about THEIR CURRENT financial situation.
Use ONLY the provided CURRENT PERIOD financial statistics from their FinSight database.
Do not invent amounts, categories, or goals.

Rules:
- Answer using the current-period numbers (income, expenses, savings, remaining, budgets, goals, health score).
- If they ask about their overall situation, give a clear snapshot first, then one practical tip.
- Lead with the direct answer in plain language (use ₹).
- 2 to 6 short sentences, or a short intro plus a few "- " bullet lines.
- No JSON dumps or markdown headers.
- NEVER say you don't have their data, don't have current info, or that expenses/budgets are unknown
  when the snapshot/context JSON is provided — that IS their live FinSight data.
- If a specific field is zero or an empty list, say that clearly (e.g. “No budgets set yet”)
  and suggest what to add — that is different from claiming you lack access to their account.
"""


DOMAIN_ACTIONS: dict[IntentDomain, list[str]] = {
    IntentDomain.GREETING: [
        "How am I doing financially this month?",
        "Where did I spend the most?",
        "How much have I saved?",
    ],
    IntentDomain.GENERAL: [
        "How am I doing financially this month?",
        "What is my financial health score?",
        "Which category exceeded my budget?",
    ],
    IntentDomain.INCOME: [
        "How much have I spent?",
        "What is my savings rate?",
        "Show income vs expenses",
    ],
    IntentDomain.EXPENSES: [
        "Where did I spend the most?",
        "Which budget am I over?",
        "How much money do I have left?",
    ],
    IntentDomain.BUDGET: [
        "Which category exceeded my budget?",
        "How can I stay under budget?",
        "Show my top expenses",
    ],
    IntentDomain.SAVINGS: [
        "How can I save ₹10,000 next month?",
        "Show my savings goals",
        "What is affecting my health score?",
    ],
    IntentDomain.GOALS: [
        "How much have I saved so far?",
        "How am I doing financially this month?",
        "Show my financial overview",
    ],
    IntentDomain.ANALYTICS: [
        "How am I doing financially this month?",
        "Where did I spend the most?",
        "Show budget vs actual",
    ],
}


class FinancialIntelligenceEngine:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.analytics = AnalyticsEngine(db, user_id)

    @staticmethod
    def _inr(amount: float | int) -> str:
        return f"₹{float(amount):,.0f}"

    # ------------------------------------------------------------------
    # Step 1 — Route: Natural Conversation vs Financial Intent
    # ------------------------------------------------------------------
    def classify(self, question: str, history: list[dict] | None = None) -> tuple[ConversationPath, IntentDomain]:
        parsed = parse_user_message(question, history)
        q = question.lower().strip()

        if parsed.kind == StatementKind.GREETING:
            return ConversationPath.NATURAL, IntentDomain.GREETING

        # Explicit "current situation / how am I doing" → analytics snapshot
        if _SITUATION_RE.search(q):
            return ConversationPath.FINANCIAL, IntentDomain.ANALYTICS

        if re.search(r"\bgoals?\b|\bemergency fund\b|\btarget\b", q):
            return ConversationPath.FINANCIAL, IntentDomain.GOALS

        # Budget before generic "category" language
        if parsed.kind == StatementKind.QUERY_BUDGET or "budget" in q:
            return ConversationPath.FINANCIAL, IntentDomain.BUDGET

        # Spending / expense language (including "other expenses", overview, breakdown)
        if re.search(
            r"\b(expenses?|spending|spent|spend|categories|merchant|"
            r"where\s+did\s+i\s+spend|breakdown|other\s+expenses?)\b",
            q,
        ):
            return ConversationPath.FINANCIAL, IntentDomain.EXPENSES

        if parsed.kind in {
            StatementKind.QUERY_SAVINGS,
            StatementKind.NEED,
        } or re.search(r"\bsave\b|\bsavings?\b", q):
            return ConversationPath.FINANCIAL, IntentDomain.SAVINGS

        if parsed.kind in {
            StatementKind.QUERY_INCOME,
            StatementKind.INCOME_STATEMENT,
        }:
            return ConversationPath.FINANCIAL, IntentDomain.INCOME

        if parsed.kind in {
            StatementKind.QUERY_EXPENSES,
            StatementKind.EXPENSE_STATEMENT,
            StatementKind.REMAINING_AFTER_EXPENSE,
            StatementKind.HYPOTHETICAL_EXPENSE,
            StatementKind.PLANNED_EXPENSE,
            StatementKind.QUERY_OTHER,
        }:
            return ConversationPath.FINANCIAL, IntentDomain.EXPENSES

        if parsed.kind in {
            StatementKind.QUERY_REMAINING,
            StatementKind.REMAINING_BALANCE_CLAIM,
            StatementKind.CORRECTION,
            StatementKind.AMBIGUOUS,
        } or re.search(r"\bhealth\b|\bscore\b|\banalytics?\b|\boverview\b|\btrend\b|\bleft\b|\bbalance\b", q):
            return ConversationPath.FINANCIAL, IntentDomain.ANALYTICS

        # Short follow-ups after a money topic → keep using live stats
        if history and re.search(
            r"\b(what about|and|also|more|details?|tell me more|continue|same)\b",
            q,
        ):
            recent = " ".join(
                str(t.get("content", "")) for t in (history or [])[-4:]
            ).lower()
            if re.search(
                r"\b(income|expense|spent|budget|save|money|₹|rs|salary|finance|financial|spend|afford|health)\b",
                recent,
            ):
                return ConversationPath.FINANCIAL, IntentDomain.ANALYTICS

        if parsed.kind == StatementKind.GENERAL:
            if re.search(
                r"\b(motivate|encourage|advice|tips?|talk|chat|hello|hi)\b",
                q,
            ) and not re.search(r"\b(income|expense|spent|budget|save|money|₹|rs|finance|financial)\b", q):
                return ConversationPath.NATURAL, IntentDomain.GENERAL
            if re.search(
                r"\b(income|expense|spent|budget|save|money|₹|rs|salary|finance|financial|spend|afford)\b",
                q,
            ):
                return ConversationPath.FINANCIAL, IntentDomain.ANALYTICS
            return ConversationPath.NATURAL, IntentDomain.GENERAL

        return ConversationPath.FINANCIAL, IntentDomain.ANALYTICS

    def suggested_actions(
        self,
        path: ConversationPath,
        domain: IntentDomain,
        context: dict | None = None,
    ) -> list[str]:
        actions = list(DOMAIN_ACTIONS.get(domain, DOMAIN_ACTIONS[IntentDomain.ANALYTICS]))
        context = context or {}
        if path == ConversationPath.FINANCIAL:
            alerts = context.get("budget_alerts") or []
            goals = context.get("goal_progress") or []
            if alerts:
                actions = [f"Why is {alerts[0]['category']} over budget?", *actions]
            if goals:
                actions = [f"How close am I to {goals[0]['name']}?", *actions[1:]]
        seen: set[str] = set()
        unique: list[str] = []
        for a in actions:
            if a not in seen:
                seen.add(a)
                unique.append(a)
        return unique[:4]

    def build_finance_prompt(
        self,
        question: str,
        domain: IntentDomain,
        context: dict,
        session_hints: dict | None = None,
        recorded: dict | None = None,
    ) -> str:
        period = (context.get("period") or {}).get("label") or "current month"
        snapshot = self._situation_snapshot_lines(context)
        extras: list[str] = []
        if recorded:
            extras.append(
                f"Just recorded from this chat: {recorded.get('kind')} "
                f"{self._inr(recorded.get('amount', 0))} "
                f"({recorded.get('label')}). Confirm briefly that it was saved."
            )
        if session_hints:
            if session_hints.get("user_income") is not None:
                extras.append(f"User earlier stated income ≈ {self._inr(session_hints['user_income'])}")
            if session_hints.get("last_expense") is not None:
                extras.append(f"User earlier stated a spend ≈ {self._inr(session_hints['last_expense'])}")
        extra_block = ("\n".join(extras) + "\n\n") if extras else ""
        return (
            f"Detected financial intent domain: {domain.value}\n"
            f"Period: {period} (user's CURRENT statistics)\n\n"
            f"{extra_block}"
            "Quick snapshot (verified):\n"
            + "\n".join(f"- {line}" for line in snapshot)
            + "\n\nFull financial context JSON from the user's database:\n"
            f"{json.dumps(context, indent=2, default=str)}\n\n"
            f"User question: {question}\n\n"
            "Answer using these CURRENT statistics only. "
            "If they ask about their situation overall, summarize the snapshot clearly. "
            "Do not claim you lack access to their expenses or budgets — the JSON above is live."
        )

    def _resolve_expense_category(self, text: str) -> Category:
        lower = text.lower()
        cats = (
            self.db.query(Category)
            .filter(Category.user_id == self.user_id, Category.type == "expense")
            .all()
        )
        by_name = {c.name.lower(): c for c in cats}

        for cat_name, keywords in _CATEGORY_KEYWORDS:
            if any(k in lower for k in keywords):
                found = by_name.get(cat_name.lower())
                if found:
                    return found

        for cat in cats:
            if cat.name.lower() in lower:
                return cat

        other = by_name.get("other")
        if other:
            return other
        if cats:
            return cats[0]

        # Create Other if user has no categories
        created = Category(
            user_id=self.user_id,
            name="Other",
            type="expense",
            is_default=True,
        )
        self.db.add(created)
        self.db.commit()
        self.db.refresh(created)
        return created

    def _guess_income_source(self, text: str) -> str:
        lower = text.lower()
        if "freelance" in lower or "client" in lower:
            return "Freelance"
        if "business" in lower:
            return "Business"
        if "salary" in lower or "paycheck" in lower or "wage" in lower:
            return "Salary"
        if "bonus" in lower:
            return "Bonus"
        return "Other"

    def try_record_transaction(self, question: str, history: list[dict] | None = None) -> dict | None:
        """
        Auto-save clear income/expense statements from chat.
        Skips hypothetical/planned spends. Returns a summary dict when saved.
        """
        if self.db is None:
            return None
        parsed = parse_user_message(question, history)
        today = date.today()
        desc = question.strip()[:240]

        # Confirmed expense statements (not "what if" / "planning to")
        if parsed.kind in {
            StatementKind.EXPENSE_STATEMENT,
            StatementKind.REMAINING_AFTER_EXPENSE,
        } and parsed.expense_amount and float(parsed.expense_amount) > 0:
            amount = Decimal(str(parsed.expense_amount)).quantize(Decimal("0.01"))
            category = self._resolve_expense_category(question)
            row = Expense(
                user_id=self.user_id,
                category_id=category.id,
                amount=amount,
                description=desc,
                merchant=None,
                expense_date=today,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {
                "kind": "expense",
                "id": row.id,
                "amount": float(amount),
                "label": category.name,
                "date": today.isoformat(),
            }

        if (
            parsed.kind == StatementKind.INCOME_STATEMENT
            and parsed.income_amount
            and float(parsed.income_amount) > 0
        ):
            amount = Decimal(str(parsed.income_amount)).quantize(Decimal("0.01"))
            source = self._guess_income_source(question)
            row = Income(
                user_id=self.user_id,
                source=source,
                amount=amount,
                description=desc,
                income_date=today,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {
                "kind": "income",
                "id": row.id,
                "amount": float(amount),
                "label": source,
                "date": today.isoformat(),
            }

        return None

    def _recorded_prefix(self, recorded: dict) -> str:
        kind = recorded.get("kind")
        amount = self._inr(recorded.get("amount", 0))
        label = recorded.get("label") or "Other"
        if kind == "expense":
            return f"Logged expense: {amount} under {label}."
        return f"Logged income: {amount} from {label}."

    def _situation_snapshot_lines(self, context: dict) -> list[str]:
        summary = context.get("summary") or {}
        period = (context.get("period") or {}).get("label") or "This month"
        remaining = context.get("remaining_balance")
        if remaining is None:
            remaining = float(summary.get("net_savings", 0) or 0)
        lines = [
            f"Period: {period}",
            f"Income: {self._inr(summary.get('total_income', 0))}",
            f"Expenses: {self._inr(summary.get('total_expenses', 0))}",
            f"Savings / remaining: {self._inr(remaining)}",
            f"Savings rate: {float(summary.get('savings_rate', 0) or 0):.1f}%",
            f"Budget usage: {float(summary.get('budget_usage', 0) or 0):.1f}%",
            f"Financial health score: {summary.get('financial_health_score', 0)}/100",
        ]
        top = (context.get("top_expense_categories") or [])[:1]
        if top:
            lines.append(
                f"Top spend category: {top[0]['category']} ({self._inr(top[0]['amount'])})"
            )
        alerts = context.get("budget_alerts") or []
        if alerts:
            lines.append(
                "Budget alerts: "
                + ", ".join(f"{a['category']} ({a['status']})" for a in alerts[:3])
            )
        goals = context.get("goal_progress") or []
        if goals:
            lines.append(
                "Goals: "
                + ", ".join(
                    f"{g['name']} {g['completion_percentage']}%" for g in goals[:3]
                )
            )
        return lines

    def rule_based_answer(self, question: str, domain: IntentDomain, context: dict) -> str:
        """Offline answers from verified analytics when the LLM is unavailable."""
        q = question.lower()
        summary = context.get("summary", {})
        insights = context.get("insights", [])
        top_cats = context.get("top_expense_categories", [])
        budget_alerts = context.get("budget_alerts", [])
        budgets = context.get("budgets") or budget_alerts
        health = context.get("health_breakdown", {})
        goals = context.get("goal_progress", [])
        income_sources = context.get("income_sources", [])
        period = (context.get("period") or {}).get("label") or "this month"
        remaining = context.get("remaining_balance")
        if remaining is None:
            remaining = float(summary.get("net_savings", 0) or 0)

        asks_health = bool(re.search(r"\b(health|score)\b", q))
        wants_situation = (not asks_health) and (
            bool(_SITUATION_RE.search(q))
            or bool(
                re.search(
                    r"\b(how\s+am\s+i|situation|overview|summary|where\s+do\s+i\s+stand|afford|safe\s+to\s+spend)\b",
                    q,
                )
            )
        )

        if domain == IntentDomain.ANALYTICS and asks_health and not wants_situation:
            score = summary.get("financial_health_score", 0)
            lines = [
                f"Your financial health score is {score}/100 for {period}.",
                f"Income {self._inr(summary.get('total_income', 0))}, "
                f"expenses {self._inr(summary.get('total_expenses', 0))}, "
                f"savings {self._inr(remaining)}.",
            ]
            if health:
                weakest = min(health, key=health.get)
                lines.append(f"The weakest area is {weakest.replace('_', ' ')}.")
                lines.append("Score breakdown:")
                for key, value in health.items():
                    lines.append(f"- {key.replace('_', ' ').title()}: {value}")
            if insights:
                lines.append("Key insights:")
                lines.extend(f"- {item}" for item in insights[:3])
            return "\n".join(lines)

        if domain == IntentDomain.INCOME and not wants_situation:
            income = float(summary.get("total_income", 0) or 0)
            lines = [f"For {period}, your total income is {self._inr(income)}."]
            if income_sources:
                lines.append("Top sources:")
                for src in income_sources[:4]:
                    lines.append(
                        f"- {src['category']}: {self._inr(src['amount'])} ({src['percentage']}%)"
                    )
            return "\n".join(lines)

        if (domain == IntentDomain.EXPENSES or "spend the most" in q or "most money" in q) and not wants_situation:
            if not top_cats:
                return f"No expense data is available for {period} yet."
            top = top_cats[0]
            lines = [
                f"In {period}, you spent the most on {top['category']} — "
                f"{self._inr(top['amount'])} ({top['percentage']}% of expenses).",
            ]
            if len(top_cats) > 1:
                lines.append("Next largest categories:")
                for cat in top_cats[1:4]:
                    lines.append(
                        f"- {cat['category']}: {self._inr(cat['amount'])} ({cat['percentage']}%)"
                    )
            expenses = float(summary.get("total_expenses", 0) or 0)
            lines.append(f"Total expenses till now in {period}: {self._inr(expenses)}.")
            return "\n".join(lines)

        if (domain == IntentDomain.BUDGET or ("budget" in q and ("exceed" in q or "over" in q))) and not wants_situation:
            if budget_alerts:
                lines = [f"Budget alerts for {period}:"]
                for b in budget_alerts:
                    status = str(b.get("status", "")).replace("_", " ")
                    lines.append(f"- {b['category']}: {b['utilization']}% used ({status})")
                lines.append("Try trimming those categories first to get back on plan.")
                return "\n".join(lines)
            if budgets:
                lines = [f"Budget status for {period}:"]
                for b in budgets[:5]:
                    lines.append(
                        f"- {b['category']}: {self._inr(b['spent'])} of {self._inr(b['budget'])} "
                        f"({b['utilization']}% · {b['status']})"
                    )
                return "\n".join(lines)
            return f"No budgets are set for {period} yet. Add category budgets to track usage."

        if (domain == IntentDomain.SAVINGS or "save" in q) and not wants_situation and "goal" not in q:
            income = float(summary.get("total_income", 0) or 0)
            expenses = float(summary.get("total_expenses", 0) or 0)
            rate = float(summary.get("savings_rate", 0) or 0)
            lines = [
                f"In {period} you earned {self._inr(income)} and spent {self._inr(expenses)}.",
                f"Your savings so far are {self._inr(remaining)} ({rate:.1f}% savings rate).",
            ]
            shopping = next(
                (c for c in top_cats if str(c.get("category", "")).lower() == "shopping"),
                None,
            )
            if shopping:
                cut = float(shopping["amount"]) * 0.2
                lines.append(f"Reducing shopping by 20% could free about {self._inr(cut)}.")
            lines.append("Prioritize high-spend categories and keep budgets under 90% utilization.")
            return "\n".join(lines)

        if domain == IntentDomain.GOALS and not wants_situation:
            if not goals:
                return "You don't have active savings goals yet. Create one under Goals to start tracking."
            lines = ["Here’s how your goals are progressing:"]
            for g in goals[:5]:
                lines.append(
                    f"- {g['name']}: {g['completion_percentage']}% "
                    f"({self._inr(g['current_amount'])} of {self._inr(g['target_amount'])})"
                )
            return "\n".join(lines)

        # Default / situation snapshot — current statistics overview
        score = summary.get("financial_health_score", 0)
        lines = [
            f"Here’s your current financial situation for {period}:",
            f"- Income: {self._inr(summary.get('total_income', 0))}",
            f"- Expenses: {self._inr(summary.get('total_expenses', 0))}",
            f"- Remaining / savings: {self._inr(remaining)}",
            f"- Savings rate: {float(summary.get('savings_rate', 0) or 0):.1f}%",
            f"- Health score: {score}/100",
        ]
        if top_cats:
            top = top_cats[0]
            lines.append(
                f"- Biggest spend: {top['category']} ({self._inr(top['amount'])})"
            )
        if budget_alerts:
            lines.append(
                "- Watch: "
                + ", ".join(f"{a['category']} ({a['status']})" for a in budget_alerts[:3])
            )
        elif not budgets:
            lines.append("- No budgets set yet.")
        if goals:
            g = goals[0]
            lines.append(
                f"- Goal progress: {g['name']} at {g['completion_percentage']}%"
            )
        if insights:
            lines.append(f"- Insight: {insights[0]}")
        lines.append("Ask me about any of these areas for more detail.")
        return "\n".join(lines)

    def natural_fallback(self, domain: IntentDomain, question: str) -> str:
        q = question.strip().lower()
        if domain == IntentDomain.GREETING:
            if re.search(r"how\s*are\s*you", q):
                return (
                    "I'm doing great — thanks for asking!\n"
                    "Want a quick look at your current finances this month?"
                )
            if re.search(r"bye|goodbye", q):
                return "Bye for now — come back anytime you want a money check-in."
            return (
                "Hey! Nice to see you.\n"
                "Ask about your current situation, spending, budgets, savings, or goals anytime."
            )
        return (
            "I'm with you.\n"
            "Try asking “How am I doing financially this month?” and I’ll use your live stats."
        )

    async def ask_llm(
        self,
        system: str,
        prompt: str,
        history: list[dict] | None = None,
        temperature: float = 0.4,
    ) -> str | None:
        api_key = settings.llm_api_key
        api_url = settings.llm_api_url
        if not api_key or not api_url:
            return None

        messages: list[dict] = [{"role": "system", "content": system}]
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
            "temperature": temperature,
            "max_tokens": 550,
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
        history = history or []
        # Sanitize history for LLM (drop empty / ultra-long welcomes)
        clean_history = [
            {"role": m.get("role"), "content": str(m.get("content", "")).strip()[:500]}
            for m in history
            if m.get("role") in {"user", "assistant"} and str(m.get("content", "")).strip()
        ][-10:]

        # Auto-log clear income/expense statements before answering
        recorded = self.try_record_transaction(question, clean_history)

        path, domain = self.classify(question, clean_history)
        # Recording always uses the financial path for a useful reply
        if recorded:
            path = ConversationPath.FINANCIAL
            domain = (
                IntentDomain.INCOME
                if recorded.get("kind") == "income"
                else IntentDomain.EXPENSES
            )

        # Pure greetings stay natural; everything financial uses current DB stats
        if path == ConversationPath.NATURAL and not recorded:
            llm = await self.ask_llm(
                NATURAL_SYSTEM_PROMPT,
                question,
                history=clean_history,
                temperature=0.8,
            )
            answer = llm or self.natural_fallback(domain, question)
            actions = self.suggested_actions(path, domain)
            return {
                "answer": answer,
                "insights": [],
                "suggested_actions": actions,
                "context_summary": {
                    "path": path.value,
                    "intent_domain": domain.value,
                    "pipeline": [
                        "finsight_ai",
                        "natural_conversation",
                        domain.value,
                        "ai_response",
                        "suggested_actions",
                    ],
                },
            }

        # Financial Intent → current statistics from User DB → AI Response
        # Rebuild context AFTER any chat-driven write so totals include it.
        context = self.analytics.build_context_summary(year, month)
        session_hints = extract_context_from_history(clean_history)
        prompt = self.build_finance_prompt(
            question,
            domain,
            context,
            session_hints=session_hints,
            recorded=recorded,
        )
        llm = await self.ask_llm(
            FINANCE_SYSTEM_PROMPT,
            prompt,
            history=clean_history,
            temperature=0.5,
        )
        answer = llm or self.rule_based_answer(question, domain, context)
        if recorded:
            prefix = self._recorded_prefix(recorded)
            if prefix.lower() not in answer.lower():
                answer = f"{prefix}\n\n{answer}"
        actions = self.suggested_actions(path, domain, context)
        if recorded:
            actions = [
                "How am I doing financially this month?",
                "Where did I spend the most?",
                *actions,
            ]
            # de-dupe
            seen: set[str] = set()
            unique: list[str] = []
            for a in actions:
                if a not in seen:
                    seen.add(a)
                    unique.append(a)
            actions = unique[:4]

        return {
            "answer": answer,
            "insights": context.get("insights", []),
            "suggested_actions": actions,
            "context_summary": {
                "path": path.value,
                "intent_domain": domain.value,
                "pipeline": [
                    "finsight_ai",
                    "financial_intent",
                    domain.value,
                    "financial_engine",
                    "current_user_statistics",
                    "ai_response",
                    "suggested_actions",
                ],
                "period": context.get("period", {}),
                "summary": context.get("summary", {}),
                "remaining_balance": context.get("remaining_balance"),
                "top_expense_categories": context.get("top_expense_categories", []),
                "budget_alerts": context.get("budget_alerts", []),
                "goal_progress": context.get("goal_progress", []),
                "insights": context.get("insights", []),
                "recorded_transaction": recorded,
            },
        }
