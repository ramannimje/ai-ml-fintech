import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.secrets import DB_SECRETS, get_secret_value, vault


class Settings(BaseSettings):
    app_name: str = "TradeSight"
    environment: str = "local"
    api_host: str = "localhost"
    api_port: int = 8000
    database_url: str | None = None
    redis_url: str = "redis://localhost:6379/0"
    auth0_domain: str = ""
    auth0_client_id: str = ""
    auth0_client_secret: str = ""
    jwt_secret: str = ""
    openrouter_api_key: str = ""
    infisical_project_id: str = ""
    infisical_env: str = "dev"
    infisical_token: str = ""
    resend_api_key: str = ""
    sendgrid_api_key: str = ""
    frontend_url: str = "http://localhost:5173"
    cors_allowed_origins: str = ""
    cors_allow_origin_regex: str = r"https://.*\.vercel\.app$"
    data_cache_dir: str = "ml/cache"
    artifact_dir: str = "ml/artifacts"
    forecast_horizons: tuple[int, ...] = (1, 7, 30)
    min_training_rows: int = 180
    supported_regions: tuple[str, ...] = ("india", "us", "europe")
    fx_api_url: str = "https://open.er-api.com/v6/latest/USD"
    default_region: str = "us"
    auth0_callback_url: str = "http://localhost:8000/api/auth/callback"
    auth0_audience: str | None = None
    secret_key: str = ""
    resend_from_email: str = "onboarding@resend.dev"
    sendgrid_from_email: str = "alerts@example.com"
    whatsapp_provider: str = "twilio"
    whatsapp_meta_api_version: str = "v20.0"
    whatsapp_rate_limit_window_seconds: int = 3600
    whatsapp_rate_limit_max_messages: int = 5
    whatsapp_alert_poll_interval_seconds: int = 60
    whatsapp_worker_enabled: bool = True
    anthropic_model: str = "claude-3-5-haiku-latest"
    ai_chat_provider: str = "openrouter"
    openrouter_chat_model: str = "qwen/qwen3-next-80b-a3b-instruct"
    openrouter_base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1"
    postgres_db: str = "commodity_db"

    model_config = SettingsConfigDict(env_file=".env.local", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    environment = (os.getenv("ENVIRONMENT", "local").strip().lower() or "local")
    env_file = ".env.production" if environment == "production" else ".env.local"
    if env_file == ".env.local" and not os.path.exists(env_file) and os.path.exists(".env"):
        env_file = ".env"

    settings = Settings(_env_file=env_file)
    if settings.environment.lower() != "production":
        return settings

    infisical_updates = {
        "database_url": vault.get_value(path="database", key="DATABASE_URL", env_fallbacks=["DATABASE_URL"]),
        "redis_url": vault.get_value(path="database", key="REDIS_URL", env_fallbacks=["REDIS_URL"]),
        "auth0_domain": vault.get_value(path="auth", key="AUTH0_DOMAIN", env_fallbacks=["AUTH0_DOMAIN"]),
        "auth0_client_id": vault.get_value(path="auth", key="AUTH0_CLIENT_ID", env_fallbacks=["AUTH0_CLIENT_ID"]),
        "auth0_client_secret": vault.get_value(
            path="auth",
            key="AUTH0_SECRET",
            env_fallbacks=["AUTH0_CLIENT_SECRET", "AUTH0_SECRET"],
        ),
        "jwt_secret": vault.get_value(path="auth", key="JWT_SECRET", env_fallbacks=["JWT_SECRET", "SECRET_KEY"]),
        "openrouter_api_key": vault.get_value(path="ai", key="OPENROUTER_API_KEY", env_fallbacks=["OPENROUTER_API_KEY"]),
        "resend_api_key": vault.get_value(path="email", key="RESEND_API_KEY", env_fallbacks=["RESEND_API_KEY"]),
        "sendgrid_api_key": vault.get_value(path="email", key="SENDGRID_API_KEY", env_fallbacks=["SENDGRID_API_KEY"]),
    }
    updates = {k: v for k, v in infisical_updates.items() if isinstance(v, str) and v}
    if not updates:
        return settings
    return settings.model_copy(update=updates)


def resolve_database_url() -> str:
    settings = get_settings()
    if settings.database_url:
        return settings.database_url

    # Legacy fallback for environments that still provide discrete Postgres vars.
    db_user = get_secret_value(DB_SECRETS, "POSTGRES_USER", env_fallback="POSTGRES_USER")
    db_password = get_secret_value(DB_SECRETS, "POSTGRES_PASSWORD", env_fallback="POSTGRES_PASSWORD")
    db_host = get_secret_value(DB_SECRETS, "POSTGRES_HOST", env_fallback="POSTGRES_HOST")
    db_name = get_secret_value(DB_SECRETS, "POSTGRES_DB", env_fallback="POSTGRES_DB", default=settings.postgres_db)

    if db_user and db_password and db_host and db_name:
        return f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:5432/{db_name}"

    return "sqlite+aiosqlite:///./commodity.db"
