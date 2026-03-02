from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Commodity Predictor"
    environment: str = "dev"
    database_url: str = "sqlite+aiosqlite:///./commodity.db"
    data_cache_dir: str = "ml/cache"
    artifact_dir: str = "ml/artifacts"
    forecast_horizons: tuple[int, ...] = (1, 7, 30)
    min_training_rows: int = 180
    supported_regions: tuple[str, ...] = ("india", "us", "europe")
    metals_api_key: str | None = None
    fx_api_url: str = "https://open.er-api.com/v6/latest/USD"
    default_region: str = "us"
    auth0_domain: str = "dev-mrxlgcmm2f0itm0g.us.auth0.com"
    auth0_client_id: str = "0aSmSDeSBI3UbUA4ls7MzJCEAsavmWg7"
    auth0_client_secret: str = "your-client-secret"
    auth0_callback_url: str = "http://localhost:8000/api/auth/callback"
    auth0_audience: str | None = None
    frontend_url: str = "http://localhost:5173"
    secret_key: str = "change-this-secret-key-32-chars-min"
    resend_api_key: str | None = None
    resend_from_email: str = "onboarding@resend.dev"
    sendgrid_api_key: str | None = None
    sendgrid_from_email: str = "alerts@example.com"
    newsapi_key: str | None = None
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-haiku-latest"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
