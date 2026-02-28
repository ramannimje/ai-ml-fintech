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
    fx_api_url: str = "https://open.er-api.com/v6/latest/USD"
    default_region: str = "us"
    supported_regions: tuple[str, ...] = ("india", "us", "europe")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
