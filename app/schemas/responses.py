from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime


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
