"""Application settings, read from environment variables (or backend/.env).

Secrets such as DATABASE_URL live ONLY here on the backend. They are never
sent to the frontend, logged, or returned in API responses.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../backend
REPO_ROOT = BACKEND_DIR.parent


def to_sqlalchemy_url(url: str) -> str:
    """Supabase shows URLs as postgresql://...; SQLAlchemy needs to know the driver (psycopg v3)."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


class Settings(BaseSettings):
    # Pydantic reads each field from an environment variable with the same
    # name (case-insensitive), falling back to backend/.env.
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "production", "test"] = "development"

    # Required: no default, so the app refuses to start without it.
    database_url: str

    # Comma-separated list of allowed frontend origins. Never "*".
    # NoDecode: read the raw string; the validator below splits it.
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["http://localhost:5173"])

    seed_data_dir: Path = REPO_ROOT / "seed_data" / "guides"

    # ---- OpenAI research agent (Phase 3) ----
    # SecretStr hides the value in logs/tracebacks: printing it shows '**********'.
    # Optional so the directory API still runs without a key; research then
    # answers with a safe "not configured" error.
    openai_api_key: SecretStr | None = None
    # No default model on purpose: the spec forbids hard-coding an unverified name.
    openai_model: str | None = None
    openai_reasoning_effort: Literal["none", "low", "medium", "high"] = "medium"
    openai_search_context_size: Literal["low", "medium", "high"] = "medium"
    # Cost bounds for ONE research request. Reasoning tokens count toward max_output_tokens.
    openai_max_output_tokens: Annotated[int, Field(ge=1000, le=64000)] = 20000
    openai_max_tool_calls: Annotated[int, Field(ge=1, le=20)] = 8
    openai_timeout_seconds: Annotated[float, Field(ge=30, le=900)] = 300

    # ---- Research rate limits (in-process: per server instance) ----
    research_requests_per_ip_per_hour: Annotated[int, Field(ge=1)] = 5
    research_requests_per_day: Annotated[int, Field(ge=1)] = 30
    research_max_concurrent: Annotated[int, Field(ge=1, le=10)] = 2

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        return to_sqlalchemy_url(value.strip())

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            value = [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
        if isinstance(value, list) and "*" in value:
            raise ValueError("CORS_ORIGINS must list explicit origins, not '*'")
        return value


@lru_cache
def get_settings() -> Settings:
    """Create Settings once and reuse it (lru_cache remembers the result)."""
    return Settings()  # type: ignore[call-arg]  # values come from the environment
