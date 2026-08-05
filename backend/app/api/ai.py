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
    Production workflow:
    User question → Analytics Engine → Context Builder → LLM (or rule fallback).
    The AI layer never reads the database; it only consumes verified analytics context.
    """
    engine = FinancialIntelligenceEngine(db, current_user.id)
    history = [{"role": m.role, "content": m.content} for m in payload.history]
    result = await engine.answer(payload.question, year, month, history=history)
    return AIChatResponse(**result)
