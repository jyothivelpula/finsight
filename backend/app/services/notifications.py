"""User-scoped financial notifications with ref_key deduplication."""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy import func, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.category import Category
from app.models.expense import Expense
from app.models.goal import SavingsGoal
from app.models.income import Income
from app.models.notification import Notification

# Notification type constants (stored in Notification.type)
TYPE_BUDGET_EXCEEDED = "budget_exceeded"
TYPE_BUDGET_WARNING = "budget_warning"
TYPE_LARGE_EXPENSE = "large_expense"
TYPE_SAVINGS_MILESTONE = "savings_milestone"
TYPE_GOAL_PROGRESS = "goal_progress"
TYPE_GOAL_REMINDER = "goal_reminder"
TYPE_MONTHLY_REPORT = "monthly_report"


def ensure_notification_schema(engine: Engine) -> None:
    """Add ref_key to existing SQLite tables created before the column existed."""
    with engine.connect() as conn:
        dialect = engine.dialect.name
        if dialect == "sqlite":
            rows = conn.execute(text("PRAGMA table_info(notifications)")).fetchall()
            names = {row[1] for row in rows}
            if names and "ref_key" not in names:
                conn.execute(text("ALTER TABLE notifications ADD COLUMN ref_key VARCHAR(120)"))
                conn.commit()
        elif dialect == "postgresql":
            conn.execute(
                text(
                    "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS ref_key VARCHAR(120)"
                )
            )
            conn.commit()


def _inr(amount: float | Decimal) -> str:
    n = float(amount)
    return f"₹{n:,.0f}"


class NotificationService:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    # ── CRUD helpers ────────────────────────────────────────────────────

    def list_notifications(self, limit: int = 50, unread_only: bool = False) -> list[Notification]:
        q = self.db.query(Notification).filter(Notification.user_id == self.user_id)
        if unread_only:
            q = q.filter(Notification.is_read.is_(False))
        return q.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit).all()

    def unread_count(self) -> int:
        return (
            self.db.query(func.count(Notification.id))
            .filter(Notification.user_id == self.user_id, Notification.is_read.is_(False))
            .scalar()
            or 0
        )

    def mark_read(self, notification_id: int) -> Notification | None:
        row = (
            self.db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == self.user_id)
            .first()
        )
        if not row:
            return None
        if not row.is_read:
            row.is_read = True
            self.db.commit()
            self.db.refresh(row)
        return row

    def mark_all_read(self) -> int:
        updated = (
            self.db.query(Notification)
            .filter(Notification.user_id == self.user_id, Notification.is_read.is_(False))
            .update({Notification.is_read: True}, synchronize_session="fetch")
        )
        self.db.commit()
        return int(updated or 0)

    def create_if_absent(
        self,
        *,
        ntype: str,
        title: str,
        message: str,
        ref_key: str,
    ) -> Notification | None:
        """Insert a notification once per (user, ref_key). Returns None if duplicate."""
        exists = (
            self.db.query(Notification.id)
            .filter(Notification.user_id == self.user_id, Notification.ref_key == ref_key)
            .first()
        )
        if exists:
            return None
        row = Notification(
            user_id=self.user_id,
            title=title[:200],
            message=message,
            type=ntype,
            ref_key=ref_key[:120],
            is_read=False,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    # ── Periodic (safe to call on list; deduped by ref_key) ─────────────

    def refresh_periodic(self) -> None:
        """Create once-per-period alerts. Safe on every GET — never duplicates."""
        today = date.today()
        self._maybe_monthly_report(today.year, today.month)
        self._maybe_goal_reminders(today)
        self._maybe_savings_milestones(today.year, today.month)

    # ── Event-driven evaluation after mutations ─────────────────────────

    def after_expense(self, expense: Expense) -> None:
        self._check_budget_for_expense(expense)
        self._check_large_expense(expense)
        d = expense.expense_date
        self._maybe_savings_milestones(d.year, d.month)

    def after_income(self, income: Income) -> None:
        d = income.income_date
        self._maybe_savings_milestones(d.year, d.month)

    def after_budget(self, budget: Budget) -> None:
        # Re-evaluate category spend against the (new/updated) limit.
        start = date(budget.year, budget.month, 1)
        end = date(budget.year, budget.month, monthrange(budget.year, budget.month)[1])
        latest = (
            self.db.query(Expense)
            .filter(
                Expense.user_id == self.user_id,
                Expense.category_id == budget.category_id,
                Expense.expense_date >= start,
                Expense.expense_date <= end,
            )
            .order_by(Expense.expense_date.desc(), Expense.id.desc())
            .first()
        )
        if latest:
            self._check_budget_for_expense(latest)
        else:
            # No spend yet — clear nothing; optional info skipped to avoid noise.
            pass

    def after_goal(self, goal: SavingsGoal) -> None:
        target = Decimal(str(goal.target_amount)) or Decimal("1")
        current = Decimal(str(goal.current_amount))
        pct = float(current / target * 100) if target else 0.0

        if goal.status == "completed" or current >= target:
            self.create_if_absent(
                ntype=TYPE_GOAL_PROGRESS,
                title=f"Goal completed: {goal.name}",
                message=(
                    f"Congratulations — you've reached {_inr(current)} of your "
                    f"{_inr(target)} target for “{goal.name}”."
                ),
                ref_key=f"goal_complete:{goal.id}",
            )
            return

        for threshold in (25, 50, 75):
            if pct >= threshold:
                self.create_if_absent(
                    ntype=TYPE_GOAL_PROGRESS,
                    title=f"Goal {threshold}% reached: {goal.name}",
                    message=(
                        f"“{goal.name}” is {pct:.0f}% funded "
                        f"({_inr(current)} of {_inr(target)})."
                    ),
                    ref_key=f"goal_progress:{goal.id}:{threshold}",
                )

    # ── Internal checks ─────────────────────────────────────────────────

    def _category_name(self, category_id: int) -> str:
        cat = self.db.get(Category, category_id)
        return cat.name if cat else "Category"

    def _month_income(self, year: int, month: int) -> Decimal:
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        return Decimal(
            str(
                self.db.query(func.coalesce(func.sum(Income.amount), 0))
                .filter(
                    Income.user_id == self.user_id,
                    Income.income_date >= start,
                    Income.income_date <= end,
                )
                .scalar()
            )
        )

    def _month_expenses(self, year: int, month: int) -> Decimal:
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        return Decimal(
            str(
                self.db.query(func.coalesce(func.sum(Expense.amount), 0))
                .filter(
                    Expense.user_id == self.user_id,
                    Expense.expense_date >= start,
                    Expense.expense_date <= end,
                )
                .scalar()
            )
        )

    def _check_budget_for_expense(self, expense: Expense) -> None:
        d = expense.expense_date
        budget = (
            self.db.query(Budget)
            .filter(
                Budget.user_id == self.user_id,
                Budget.category_id == expense.category_id,
                Budget.year == d.year,
                Budget.month == d.month,
            )
            .first()
        )
        if not budget:
            return

        start = date(d.year, d.month, 1)
        end = date(d.year, d.month, monthrange(d.year, d.month)[1])
        spent = Decimal(
            str(
                self.db.query(func.coalesce(func.sum(Expense.amount), 0))
                .filter(
                    Expense.user_id == self.user_id,
                    Expense.category_id == expense.category_id,
                    Expense.expense_date >= start,
                    Expense.expense_date <= end,
                )
                .scalar()
            )
        )
        limit = Decimal(str(budget.amount))
        if not limit:
            return
        util = float(spent / limit * 100)
        name = self._category_name(expense.category_id)
        period = f"{d.year}-{d.month:02d}"

        if util >= 100:
            self.create_if_absent(
                ntype=TYPE_BUDGET_EXCEEDED,
                title=f"Budget exceeded: {name}",
                message=(
                    f"You've spent {_inr(spent)} of your {_inr(limit)} "
                    f"{name} budget for {d.strftime('%B %Y')} ({util:.0f}%)."
                ),
                ref_key=f"budget_exceeded:{budget.id}:{period}",
            )
        elif util >= 90:
            self.create_if_absent(
                ntype=TYPE_BUDGET_WARNING,
                title=f"Budget warning: {name}",
                message=(
                    f"You've used {util:.0f}% of your {_inr(limit)} "
                    f"{name} budget ({_inr(spent)} spent). Stay under the limit."
                ),
                ref_key=f"budget_warning:{budget.id}:{period}",
            )

    def _check_large_expense(self, expense: Expense) -> None:
        amount = Decimal(str(expense.amount))
        d = expense.expense_date
        income = self._month_income(d.year, d.month)

        # Average of prior expenses in same category (exclude this one)
        avg = self.db.query(func.avg(Expense.amount)).filter(
            Expense.user_id == self.user_id,
            Expense.category_id == expense.category_id,
            Expense.id != expense.id,
        ).scalar()
        avg_dec = Decimal(str(avg or 0))

        is_large = False
        reason = ""
        if income > 0 and amount >= income * Decimal("0.20"):
            is_large = True
            reason = f"about {float(amount / income * 100):.0f}% of this month's income"
        elif amount >= Decimal("50000"):
            is_large = True
            reason = "a large single transaction (≥ ₹50,000)"
        elif avg_dec > 0 and amount >= avg_dec * 2:
            is_large = True
            reason = f"more than 2× your usual {_inr(avg_dec)} in this category"

        if not is_large:
            return

        name = self._category_name(expense.category_id)
        self.create_if_absent(
            ntype=TYPE_LARGE_EXPENSE,
            title="Unusual expense detected",
            message=(
                f"{_inr(amount)} on {name} ({expense.expense_date}) looks high — {reason}."
            ),
            ref_key=f"large_expense:{expense.id}",
        )

    def _maybe_savings_milestones(self, year: int, month: int) -> None:
        income = self._month_income(year, month)
        if income <= 0:
            return
        expenses = self._month_expenses(year, month)
        savings = income - expenses
        rate = float(savings / income * 100)
        period = f"{year}-{month:02d}"
        label = date(year, month, 1).strftime("%B %Y")

        for threshold in (20, 30, 50):
            if rate >= threshold:
                self.create_if_absent(
                    ntype=TYPE_SAVINGS_MILESTONE,
                    title=f"Savings milestone: {threshold}%+",
                    message=(
                        f"Nice work — your savings rate for {label} is {rate:.1f}% "
                        f"({_inr(savings)} saved of {_inr(income)} income)."
                    ),
                    ref_key=f"savings_milestone:{period}:{threshold}",
                )

    def _maybe_goal_reminders(self, today: date) -> None:
        goals = (
            self.db.query(SavingsGoal)
            .filter(SavingsGoal.user_id == self.user_id, SavingsGoal.status == "active")
            .all()
        )
        period = f"{today.year}-{today.month:02d}"
        for goal in goals:
            target = Decimal(str(goal.target_amount)) or Decimal("1")
            current = Decimal(str(goal.current_amount))
            pct = float(current / target * 100)
            if pct >= 100:
                continue

            # Reminder if under 50% funded and target date within 60 days (or overdue)
            if goal.target_date:
                days_left = (goal.target_date - today).days
                if days_left <= 60 and pct < 50:
                    when = (
                        "overdue"
                        if days_left < 0
                        else f"due in {days_left} day{'s' if days_left != 1 else ''}"
                    )
                    self.create_if_absent(
                        ntype=TYPE_GOAL_REMINDER,
                        title=f"Goal reminder: {goal.name}",
                        message=(
                            f"“{goal.name}” is {pct:.0f}% funded ({_inr(current)} of "
                            f"{_inr(target)}) and {when}."
                        ),
                        ref_key=f"goal_reminder:{goal.id}:{period}",
                    )
            elif pct < 25:
                # No target date — gentle monthly nudge if barely started
                self.create_if_absent(
                    ntype=TYPE_GOAL_REMINDER,
                    title=f"Keep building: {goal.name}",
                    message=(
                        f"“{goal.name}” is at {pct:.0f}% ({_inr(current)} of {_inr(target)}). "
                        f"A small contribution this month keeps momentum."
                    ),
                    ref_key=f"goal_reminder:{goal.id}:{period}",
                )

    def _maybe_monthly_report(self, year: int, month: int) -> None:
        """Offer a report once the user has any activity in the period."""
        income = self._month_income(year, month)
        expenses = self._month_expenses(year, month)
        if income <= 0 and expenses <= 0:
            return
        period = f"{year}-{month:02d}"
        label = date(year, month, 1).strftime("%B %Y")
        self.create_if_absent(
            ntype=TYPE_MONTHLY_REPORT,
            title=f"Monthly report ready: {label}",
            message=(
                f"Your {label} financial summary is ready to export from Reports "
                f"(income {_inr(income)}, expenses {_inr(expenses)})."
            ),
            ref_key=f"monthly_report:{period}",
        )
