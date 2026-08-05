"""Seed default expense categories for new users."""

from sqlalchemy.orm import Session

from app.models.category import Category


DEFAULT_EXPENSE_CATEGORIES = [
    "Food",
    "Rent",
    "Utilities",
    "Shopping",
    "Medical",
    "Education",
    "Entertainment",
    "Transportation",
    "Travel",
    "Other",
]


def seed_default_categories(db: Session, user_id: int) -> None:
    existing = (
        db.query(Category)
        .filter(Category.user_id == user_id, Category.is_default.is_(True))
        .count()
    )
    if existing:
        return

    for name in DEFAULT_EXPENSE_CATEGORIES:
        db.add(
            Category(
                user_id=user_id,
                name=name,
                type="expense",
                is_default=True,
            )
        )
    db.commit()
