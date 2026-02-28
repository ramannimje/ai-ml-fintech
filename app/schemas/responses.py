from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime


class CommodityListResponse(BaseModel):
    commodities: list[str]


class HistoricalPoint(BaseModel):
    date: date
    close: float


class HistoricalResponse(BaseModel):
    commodity: str
    rows: int
    data: list[HistoricalPoint]


# --- Region-aware historical response ---

class RegionalHistoricalPoint(BaseModel):
    date: date
    close: float          # price in regional currency/unit
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
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


# --- Legacy prediction response (backwards compat) ---

class PredictionResponse(BaseModel):
    commodity: str
    prediction_date: date
    predicted_price: float
    confidence_interval: tuple[float, float]
    model_used: str
    model_accuracy_rmse: float
    horizon_days: int = Field(default=1)


# --- Regional multi-step prediction response ---

class ForecastPoint(BaseModel):
    date: date
    price: float


class RegionalPredictionResponse(BaseModel):
    commodity: str
    region: str
    unit: str
    currency: str
    predictions: list[ForecastPoint]
    confidence_interval: tuple[float, float]
    model_used: str


# --- Regional comparison ---

class RegionPrice(BaseModel):
    region: str
    currency: str
    unit: str
    price: float
    formatted: str


class RegionalComparisonResponse(BaseModel):
    commodity: str
    regions: list[RegionPrice]


# --- Retrain all ---

class RetrainAllResponse(BaseModel):
    results: list[TrainResponse]
