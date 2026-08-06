from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.schemas.ai import AIChatRequest, AIChatResponse
from app.services.ai_engine import FinancialIntelligenceEngine


router = APIRouter(prefix="/ai", tags=["AI Assistant API"])


@router.post("/ask", response_model=AIChatResponse)
async def ask_assistant(
    payload: AIChatRequest,
    year: int | None = Query(default=None),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AIChatResponse:
    """
    FinSight AI flow:
    Natural Conversation (greetings/context) OR Financial Intent
    (income/expenses/budget/savings/goals/analytics)
    → Financial Engine → User DB → AI Response → Suggested Actions.
    """
    engine = FinancialIntelligenceEngine(db, current_user.id)
    history = [{"role": m.role, "content": m.content} for m in payload.history]
    result = await engine.answer(payload.question, year, month, history=history)
    return AIChatResponse(**result)
