from fastapi import APIRouter

from app.api import ai, analytics, auth, finance, reports


api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(finance.router)
api_router.include_router(analytics.router)
api_router.include_router(reports.router)
api_router.include_router(ai.router)
