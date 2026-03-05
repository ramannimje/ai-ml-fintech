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
    postgres_db: str = "commodity"

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
