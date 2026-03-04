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
    whatsapp_provider: str = "twilio"
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_whatsapp_number: str | None = None
    whatsapp_meta_access_token: str | None = None
    whatsapp_meta_phone_number_id: str | None = None
    whatsapp_meta_api_version: str = "v20.0"
    redis_url: str = "redis://localhost:6379/0"
    whatsapp_rate_limit_window_seconds: int = 3600
    whatsapp_rate_limit_max_messages: int = 5
    whatsapp_alert_poll_interval_seconds: int = 60
    whatsapp_worker_enabled: bool = True
    newsapi_key: str | None = None
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-haiku-latest"
    ai_chat_provider: str = "gemini"
    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-5.2"
    openai_fallback_models: str = "gpt-5,gpt-4.1,gpt-4o-mini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-pro"
    gemini_fallback_models: str = "gemini-1.5-flash"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
