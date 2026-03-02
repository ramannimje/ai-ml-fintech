from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime


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


class PriceAlertResponse(BaseModel):
    id: int
    commodity: str
    region: str
    currency: str
    unit: str
    alert_type: str
    threshold: float
    enabled: bool
    last_triggered_at: Optional[datetime] = None
    created_at: datetime


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
    triggered_at: datetime


class AlertEvaluationResponse(BaseModel):
    checked: int
    triggered: int
    events: list[AlertHistoryResponse]


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
