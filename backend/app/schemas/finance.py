from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: str = Field(default="expense", pattern="^(expense|income)$")


class CategoryResponse(BaseModel):
    id: int
    name: str
    type: str
    is_default: bool

    model_config = {"from_attributes": True}


class IncomeCreate(BaseModel):
    source: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str | None = None
    income_date: date


class IncomeUpdate(BaseModel):
    source: str | None = Field(default=None, min_length=1, max_length=100)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    description: str | None = None
    income_date: date | None = None


class IncomeResponse(BaseModel):
    id: int
    source: str
    amount: Decimal
    description: str | None
    income_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class ExpenseCreate(BaseModel):
    category_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str | None = None
    merchant: str | None = None
    expense_date: date


class ExpenseUpdate(BaseModel):
    category_id: int | None = None
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    description: str | None = None
    merchant: str | None = None
    expense_date: date | None = None


class ExpenseResponse(BaseModel):
    id: int
    category_id: int
    amount: Decimal
    description: str | None
    merchant: str | None
    expense_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class BudgetCreate(BaseModel):
    category_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)


class BudgetUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)


class BudgetResponse(BaseModel):
    id: int
    category_id: int
    amount: Decimal
    year: int
    month: int
    spent: Decimal = Decimal("0")
    remaining: Decimal = Decimal("0")
    utilization: float = 0.0
    status: str = "on_track"

    model_config = {"from_attributes": True}


class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    target_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    target_date: date | None = None
    notes: str | None = None


class GoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    target_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    current_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    target_date: date | None = None
    status: str | None = Field(default=None, pattern="^(active|completed|paused)$")
    notes: str | None = None


class GoalResponse(BaseModel):
    id: int
    name: str
    target_amount: Decimal
    current_amount: Decimal
    target_date: date | None
    status: str
    notes: str | None
    completion_percentage: float = 0.0
    remaining_amount: Decimal = Decimal("0")

    model_config = {"from_attributes": True}
