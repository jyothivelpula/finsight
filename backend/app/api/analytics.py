from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.schemas.analytics import AnalyticsDashboard, FinancialSummary
from app.services.analytics_engine import AnalyticsEngine


router = APIRouter(prefix="/analytics", tags=["Analytics API"])


@router.get("/dashboard", response_model=AnalyticsDashboard)
def analytics_dashboard(
    year: int | None = Query(default=None),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AnalyticsDashboard:
    engine = AnalyticsEngine(db, current_user.id)
    return engine.build_dashboard(year, month)


@router.get("/summary", response_model=FinancialSummary)
def financial_summary(
    year: int | None = Query(default=None),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FinancialSummary:
    engine = AnalyticsEngine(db, current_user.id)
    return engine.build_dashboard(year, month).summary


@router.get("/insights")
def smart_insights(
    year: int | None = Query(default=None),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    engine = AnalyticsEngine(db, current_user.id)
    dashboard = engine.build_dashboard(year, month)
    return {"insights": dashboard.insights, "health_breakdown": dashboard.health_breakdown}
