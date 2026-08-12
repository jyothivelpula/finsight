from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def _engine_kwargs() -> dict:
    if settings.is_sqlite:
        return {"connect_args": {"check_same_thread": False}}
    # Supabase / managed Postgres typically require SSL.
    connect_args: dict = {}
    url = settings.DATABASE_URL.lower()
    if "sslmode=" not in url and ("supabase" in url or "pooler" in url):
        connect_args["sslmode"] = "require"
    return {
        "connect_args": connect_args,
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
    }


engine = create_engine(settings.DATABASE_URL, **_engine_kwargs())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
