from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.models import (  # noqa: F401 — register models on Base.metadata
    Budget,
    Category,
    Expense,
    Income,
    Notification,
    SavingsGoal,
    User,
)
from app.services.notifications import ensure_notification_schema


@asynccontextmanager
async def lifespan(_: FastAPI):
    Path(settings.REPORTS_DIR).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    ensure_notification_schema(engine)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Intelligent Personal Finance Management Platform API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Explicit origins from CORS_ORIGINS, plus regex for local + all Vercel URLs.
    # Vercel creates a new *.vercel.app host per deployment — listing each one in
    # env vars is brittle, so production always allows https://*.vercel.app.
    cors_origins = settings.cors_origins_list
    allow_origin_regex = (
        r"http://(localhost|127\.0\.0\.1):\d+"
        r"|https://([a-z0-9-]+\.)*vercel\.app"
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}

    app.include_router(api_router)
    return app


app = create_app()
