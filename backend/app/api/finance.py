from calendar import monthrange
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.budget import Budget
from app.models.category import Category
from app.models.expense import Expense
from app.models.goal import SavingsGoal
from app.models.income import Income
from app.models.user import User
from app.schemas.finance import (
    BudgetCreate,
    BudgetResponse,
    BudgetUpdate,
    CategoryCreate,
    CategoryResponse,
    ExpenseCreate,
    ExpenseResponse,
    ExpenseUpdate,
    GoalCreate,
    GoalResponse,
    GoalUpdate,
    IncomeCreate,
    IncomeResponse,
    IncomeUpdate,
)


router = APIRouter(prefix="/finance", tags=["Finance API"])


def _goal_response(goal: SavingsGoal) -> GoalResponse:
    target = Decimal(str(goal.target_amount)) or Decimal("1")
    current = Decimal(str(goal.current_amount))
    return GoalResponse(
        id=goal.id,
        name=goal.name,
        target_amount=target,
        current_amount=current,
        target_date=goal.target_date,
        status=goal.status,
        notes=goal.notes,
        completion_percentage=round(min(100.0, float(current / target * 100)), 2),
        remaining_amount=max(Decimal("0"), target - current),
    )


def _budget_response(db: Session, budget: Budget, user_id: int) -> BudgetResponse:
    start = date(budget.year, budget.month, 1)
    end = date(budget.year, budget.month, monthrange(budget.year, budget.month)[1])
    spent = Decimal(
        str(
            db.query(func.coalesce(func.sum(Expense.amount), 0))
            .filter(
                Expense.user_id == user_id,
                Expense.category_id == budget.category_id,
                Expense.expense_date >= start,
                Expense.expense_date <= end,
            )
            .scalar()
        )
    )
    amount = Decimal(str(budget.amount))
    utilization = float(spent / amount * 100) if amount else 0.0
    if utilization >= 100:
        status_label = "exceeded"
    elif utilization >= 90:
        status_label = "warning"
    else:
        status_label = "on_track"
    return BudgetResponse(
        id=budget.id,
        category_id=budget.category_id,
        amount=amount,
        year=budget.year,
        month=budget.month,
        spent=spent,
        remaining=amount - spent,
        utilization=round(utilization, 2),
        status=status_label,
    )


# ---------- Categories ----------
@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[Category]:
    return (
        db.query(Category)
        .filter(Category.user_id == current_user.id)
        .order_by(Category.name)
        .all()
    )


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Category:
    exists = (
        db.query(Category)
        .filter(Category.user_id == current_user.id, Category.name == payload.name)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Category already exists")
    category = Category(user_id=current_user.id, name=payload.name, type=payload.type)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


# ---------- Income ----------
@router.get("/income", response_model=list[IncomeResponse])
def list_income(
    search: str | None = None,
    source: str | None = None,
    year: int | None = None,
    month: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[Income]:
    query = db.query(Income).filter(Income.user_id == current_user.id)
    if search:
        query = query.filter(Income.description.ilike(f"%{search}%"))
    if source:
        query = query.filter(Income.source == source)
    if year:
        query = query.filter(Income.income_date >= date(year, month or 1, 1))
        if month:
            end = date(year, month, monthrange(year, month)[1])
            query = query.filter(Income.income_date <= end)
    return query.order_by(Income.income_date.desc()).all()


@router.post("/income", response_model=IncomeResponse, status_code=status.HTTP_201_CREATED)
def create_income(
    payload: IncomeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Income:
    income = Income(user_id=current_user.id, **payload.model_dump())
    db.add(income)
    db.commit()
    db.refresh(income)
    return income


@router.put("/income/{income_id}", response_model=IncomeResponse)
def update_income(
    income_id: int,
    payload: IncomeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Income:
    income = (
        db.query(Income)
        .filter(Income.id == income_id, Income.user_id == current_user.id)
        .first()
    )
    if not income:
        raise HTTPException(status_code=404, detail="Income not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(income, key, value)
    db.commit()
    db.refresh(income)
    return income


@router.delete("/income/{income_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_income(
    income_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    income = (
        db.query(Income)
        .filter(Income.id == income_id, Income.user_id == current_user.id)
        .first()
    )
    if not income:
        raise HTTPException(status_code=404, detail="Income not found")
    db.delete(income)
    db.commit()


# ---------- Expenses ----------
@router.get("/expenses", response_model=list[ExpenseResponse])
def list_expenses(
    search: str | None = None,
    category_id: int | None = None,
    year: int | None = None,
    month: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[Expense]:
    query = db.query(Expense).filter(Expense.user_id == current_user.id)
    if search:
        query = query.filter(Expense.description.ilike(f"%{search}%"))
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    if year and month:
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        query = query.filter(Expense.expense_date >= start, Expense.expense_date <= end)
    return query.order_by(Expense.expense_date.desc()).all()


@router.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Expense:
    category = (
        db.query(Category)
        .filter(Category.id == payload.category_id, Category.user_id == current_user.id)
        .first()
    )
    if not category:
        raise HTTPException(status_code=400, detail="Invalid category")
    expense = Expense(user_id=current_user.id, **payload.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.put("/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: int,
    payload: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Expense:
    expense = (
        db.query(Expense)
        .filter(Expense.id == expense_id, Expense.user_id == current_user.id)
        .first()
    )
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    data = payload.model_dump(exclude_unset=True)
    if "category_id" in data:
        category = (
            db.query(Category)
            .filter(Category.id == data["category_id"], Category.user_id == current_user.id)
            .first()
        )
        if not category:
            raise HTTPException(status_code=400, detail="Invalid category")
    for key, value in data.items():
        setattr(expense, key, value)
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    expense = (
        db.query(Expense)
        .filter(Expense.id == expense_id, Expense.user_id == current_user.id)
        .first()
    )
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    db.delete(expense)
    db.commit()


# ---------- Budgets ----------
@router.get("/budgets", response_model=list[BudgetResponse])
def list_budgets(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[BudgetResponse]:
    budgets = (
        db.query(Budget)
        .filter(Budget.user_id == current_user.id, Budget.year == year, Budget.month == month)
        .all()
    )
    return [_budget_response(db, b, current_user.id) for b in budgets]


@router.post("/budgets", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    payload: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BudgetResponse:
    category = (
        db.query(Category)
        .filter(Category.id == payload.category_id, Category.user_id == current_user.id)
        .first()
    )
    if not category:
        raise HTTPException(status_code=400, detail="Invalid category")
    existing = (
        db.query(Budget)
        .filter(
            Budget.user_id == current_user.id,
            Budget.category_id == payload.category_id,
            Budget.year == payload.year,
            Budget.month == payload.month,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Budget already exists for this period")
    budget = Budget(user_id=current_user.id, **payload.model_dump())
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return _budget_response(db, budget, current_user.id)


@router.put("/budgets/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: int,
    payload: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BudgetResponse:
    budget = (
        db.query(Budget)
        .filter(Budget.id == budget_id, Budget.user_id == current_user.id)
        .first()
    )
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(budget, key, value)
    db.commit()
    db.refresh(budget)
    return _budget_response(db, budget, current_user.id)


@router.delete("/budgets/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    budget = (
        db.query(Budget)
        .filter(Budget.id == budget_id, Budget.user_id == current_user.id)
        .first()
    )
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    db.delete(budget)
    db.commit()


# ---------- Savings Goals ----------
@router.get("/goals", response_model=list[GoalResponse])
def list_goals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[GoalResponse]:
    goals = (
        db.query(SavingsGoal)
        .filter(SavingsGoal.user_id == current_user.id)
        .order_by(SavingsGoal.created_at.desc())
        .all()
    )
    return [_goal_response(g) for g in goals]


@router.post("/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(
    payload: GoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> GoalResponse:
    goal = SavingsGoal(user_id=current_user.id, **payload.model_dump())
    if goal.current_amount >= goal.target_amount:
        goal.status = "completed"
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _goal_response(goal)


@router.put("/goals/{goal_id}", response_model=GoalResponse)
def update_goal(
    goal_id: int,
    payload: GoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> GoalResponse:
    goal = (
        db.query(SavingsGoal)
        .filter(SavingsGoal.id == goal_id, SavingsGoal.user_id == current_user.id)
        .first()
    )
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(goal, key, value)
    if goal.current_amount >= goal.target_amount:
        goal.status = "completed"
    db.commit()
    db.refresh(goal)
    return _goal_response(goal)


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    goal = (
        db.query(SavingsGoal)
        .filter(SavingsGoal.id == goal_id, SavingsGoal.user_id == current_user.id)
        .first()
    )
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(goal)
    db.commit()
