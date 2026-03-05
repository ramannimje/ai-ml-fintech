from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.secrets import DB_SECRETS, get_secret_value


class Settings(BaseSettings):
    app_name: str = "AI Commodity Predictor"
    environment: str = "dev"
    database_url: str | None = None
    data_cache_dir: str = "ml/cache"
    artifact_dir: str = "ml/artifacts"
    forecast_horizons: tuple[int, ...] = (1, 7, 30)
    min_training_rows: int = 180
    supported_regions: tuple[str, ...] = ("india", "us", "europe")
    fx_api_url: str = "https://open.er-api.com/v6/latest/USD"
    default_region: str = "us"
    auth0_domain: str = ""
    auth0_client_id: str = ""
    auth0_client_secret: str = ""
    auth0_callback_url: str = "http://localhost:8000/api/auth/callback"
    auth0_audience: str | None = None
    frontend_url: str = "http://localhost:5173"
    secret_key: str = ""
    resend_from_email: str = "onboarding@resend.dev"
    sendgrid_from_email: str = "alerts@example.com"
    whatsapp_provider: str = "twilio"
    whatsapp_meta_api_version: str = "v20.0"
    redis_url: str = "redis://localhost:6379/0"
    whatsapp_rate_limit_window_seconds: int = 3600
    whatsapp_rate_limit_max_messages: int = 5
    whatsapp_alert_poll_interval_seconds: int = 60
    whatsapp_worker_enabled: bool = True
    anthropic_model: str = "claude-3-5-haiku-latest"
    ai_chat_provider: str = "gemini"
    openai_chat_model: str = "gpt-5.2"
    openai_fallback_models: str = "gpt-5,gpt-4.1,gpt-4o-mini"
    gemini_model: str = "gemini-1.5-pro"
    gemini_fallback_models: str = "gemini-1.5-flash"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1"
    postgres_db: str = "commodity"
    infisical_project_id: str = ""
    infisical_env: str = "dev"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def resolve_database_url() -> str:
    settings = get_settings()
    if settings.database_url:
        return settings.database_url

    db_user = get_secret_value(DB_SECRETS, "POSTGRES_USER", env_fallback="POSTGRES_USER")
    db_password = get_secret_value(DB_SECRETS, "POSTGRES_PASSWORD", env_fallback="POSTGRES_PASSWORD")
    db_host = get_secret_value(DB_SECRETS, "POSTGRES_HOST", env_fallback="POSTGRES_HOST")
    db_name = get_secret_value(DB_SECRETS, "POSTGRES_DB", env_fallback="POSTGRES_DB", default=settings.postgres_db)

    if db_user and db_password and db_host and db_name:
        return f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:5432/{db_name}"

    return "sqlite+aiosqlite:///./commodity.db"
