from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field
from pydantic import field_validator


class HealthResponse(BaseModel):
    status: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    context: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail


class CommodityListResponse(BaseModel):
    commodities: list[str]


class RegionDefinition(BaseModel):
    id: Literal["india", "us", "europe"]
    currency: Literal["INR", "USD", "EUR"]
    unit: str


class CommodityDefinition(BaseModel):
    id: Literal["gold", "silver", "crude_oil"]


class LivePriceResponse(BaseModel):
    commodity: str
    region: str
    unit: str
    currency: str
    live_price: float
    source: str
    timestamp: datetime


class LivePricesEnvelope(BaseModel):
    items: list[LivePriceResponse]


class RegionalHistoricalPoint(BaseModel):
    date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: float
    volume: Optional[float] = None


class RegionalHistoricalResponse(BaseModel):
    commodity: str
    region: str
    currency: str
    unit: str
    rows: int
    data: list[RegionalHistoricalPoint]


# --- Train / Metrics ---

class TrainResponse(BaseModel):
    commodity: str
    region: str
    best_model: str
    model_version: str
    rmse: float
    mape: float


class MetricsResponse(BaseModel):
    commodity: str
    model_name: str
    rmse: float
    mape: float
    trained_at: datetime
    region: str = "us"


class RegionalPredictionResponse(BaseModel):
    commodity: str
    region: str
    unit: str
    currency: str
    forecast_horizon: date = Field(default=date(2026, 12, 31))
    point_forecast: float
    confidence_interval: tuple[float, float]
    scenario: Literal["bull", "base", "bear"]
    scenario_forecasts: dict[str, float]
    model_used: str


class RetrainAllResponse(BaseModel):
    results: list[TrainResponse]


class AlertCreateRequest(BaseModel):
    commodity: Literal["gold", "silver", "crude_oil", "natural_gas", "copper"]
    region: Literal["india", "us", "europe"]
    alert_type: Literal["above", "below", "pct_change_24h", "spike", "drop"]
    threshold: float = Field(gt=0)
    enabled: bool = True
    cooldown_minutes: int = Field(default=30, ge=5, le=1440)
    email_notifications_enabled: bool = True


class AlertUpdateRequest(BaseModel):
    threshold: Optional[float] = Field(default=None, gt=0)
    enabled: Optional[bool] = None
    cooldown_minutes: Optional[int] = Field(default=None, ge=5, le=1440)
    email_notifications_enabled: Optional[bool] = None


class PriceAlertResponse(BaseModel):
    id: int
    commodity: str
    region: str
    currency: str
    unit: str
    alert_type: str
    threshold: float
    enabled: bool
    cooldown_minutes: int
    email_notifications_enabled: bool
    last_triggered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AlertHistoryResponse(BaseModel):
    id: int
    alert_id: int
    commodity: str
    region: str
    currency: str
    alert_type: str
    threshold: float
    observed_value: float
    message: str
    email_status: str
    delivery_provider: Optional[str] = None
    delivery_error: Optional[str] = None
    delivery_attempts: int = 0
    triggered_at: datetime


class AlertEvaluationResponse(BaseModel):
    checked: int
    triggered: int
    events: list[AlertHistoryResponse]


class WhatsAppAlertCreateRequest(BaseModel):
    commodity: Literal["gold", "silver", "crude_oil", "natural_gas", "copper"]
    region: Literal["india", "us", "europe"]
    target_price: float = Field(gt=0)
    direction: Literal["above", "below"]
    whatsapp_number: str = Field(min_length=8, max_length=24)

    @field_validator("whatsapp_number")
    @classmethod
    def validate_whatsapp_number(cls, value: str) -> str:
        out = value.strip()
        if out.startswith("whatsapp:"):
            out = out.split(":", 1)[1]
        if not out.startswith("+"):
            raise ValueError("whatsapp_number must be in E.164 format, e.g. +15551234567")
        if not out[1:].isdigit():
            raise ValueError("whatsapp_number must contain digits after '+'")
        return value.strip()


class WhatsAppAlertResponse(BaseModel):
    id: int
    user_id: str
    commodity: str
    region: str
    target_price: float
    direction: Literal["above", "below"]
    whatsapp_number: str
    is_active: bool
    is_triggered: bool
    created_at: datetime
    triggered_at: Optional[datetime] = None


class NewsHeadline(BaseModel):
    title: str
    source: str
    url: str
    published_at: datetime


class CommodityNewsSummaryResponse(BaseModel):
    commodity: str
    sentiment: Literal["bullish", "bearish", "neutral"]
    summary: str
    headlines: list[NewsHeadline]
    updated_at: datetime


class UserProfileResponse(BaseModel):
    user_sub: str
    email: Optional[str] = None
    name: Optional[str] = None
    picture_url: Optional[str] = None
    preferred_region: Literal["india", "us", "europe"]
    email_notifications_enabled: bool
    alert_cooldown_minutes: int
    created_at: datetime
    updated_at: datetime


class UserProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    picture_url: Optional[str] = None
    preferred_region: Optional[Literal["india", "us", "europe"]] = None
    email_notifications_enabled: Optional[bool] = None
    alert_cooldown_minutes: Optional[int] = Field(default=None, ge=5, le=1440)


class UserSettingsResponse(BaseModel):
    id: int
    user_id: str
    default_region: Literal["india", "us", "europe"]
    default_commodity: Literal["gold", "silver", "crude_oil"]
    prediction_horizon: int = Field(ge=1, le=90)
    email_notifications: bool
    alert_cooldown_minutes: int = Field(ge=5, le=1440)
    alerts_enabled: bool
    enable_chronos_bolt: bool
    enable_xgboost: bool
    auto_retrain: bool
    theme_preference: Literal["light", "dark", "system"]
    created_at: datetime
    updated_at: datetime


class UserSettingsUpdateRequest(BaseModel):
    default_region: Optional[Literal["india", "us", "europe"]] = None
    default_commodity: Optional[Literal["gold", "silver", "crude_oil"]] = None
    prediction_horizon: Optional[int] = Field(default=None, ge=1, le=90)
    email_notifications: Optional[bool] = None
    alert_cooldown_minutes: Optional[int] = Field(default=None, ge=5, le=1440)
    alerts_enabled: Optional[bool] = None
    enable_chronos_bolt: Optional[bool] = None
    enable_xgboost: Optional[bool] = None
    auto_retrain: Optional[bool] = None
    theme_preference: Optional[Literal["light", "dark", "system"]] = None


class AIChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=4000)


class AIChatResponse(BaseModel):
    answer: str
    intent: Literal[
        "market_summary",
        "price_forecast",
        "historical_trend_analysis",
        "commodity_comparison",
        "region_comparison",
        "trading_outlook",
        "volatility_explanation",
    ]
    region: Literal["india", "us", "europe"]
    commodity: Optional[Literal["gold", "silver", "crude_oil", "natural_gas", "copper"]] = None
    horizon_days: int = Field(ge=1, le=1095)
    generated_at: datetime


class AIProviderStatusResponse(BaseModel):
    provider: Literal["openrouter", "disabled"]
    openrouter_model: str
    openrouter_api_key_present: bool
    openrouter_cooldown_seconds_remaining: int = Field(ge=0)
    last_openrouter_error: Optional[str] = None
