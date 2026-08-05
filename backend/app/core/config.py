from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "FinSight"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "dev-secret-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Prefer PostgreSQL in production; SQLite works for local bootstrap.
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'finsight.db'}"

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:3000"

    # OpenAI-compatible LLM settings (Groq works here too).
    LLM_API_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_API_KEY: str = ""

    REPORTS_DIR: str = str(BASE_DIR / "generated_reports")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def llm_api_key(self) -> str:
        return self.LLM_API_KEY or self.GROQ_API_KEY

    @property
    def llm_api_url(self) -> str:
        if self.LLM_API_URL:
            return self.LLM_API_URL
        if self.GROQ_API_KEY or self.LLM_API_KEY:
            return GROQ_CHAT_URL
        return ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
