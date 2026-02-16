from datetime import datetime
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime


class CommodityListResponse(BaseModel):
    commodities: list[str]


class HistoricalPoint(BaseModel):
    timestamp: datetime
    close: float
    open: float | None = None
    high: float | None = None
    low: float | None = None
    volume: float | None = None


class HistoricalResponse(BaseModel):
    commodity: str
    region: str
    currency: str
    unit: str
    source: str
    rows: int
    data: list[HistoricalPoint]


class TrainResponse(BaseModel):
    commodity: str
    region: str
    best_model: str
    model_version: str
    rmse: float
    mape: float


class PredictionPoint(BaseModel):
    date: str
    price: float


class PredictionResponse(BaseModel):
    commodity: str
    region: str
    unit: str
    currency: str
    predictions: list[PredictionPoint]
    confidence_interval: list[float]
    model_used: str
    model_accuracy_rmse: float
    horizon_days: int = Field(default=1)


class MetricsResponse(BaseModel):
    commodity: str
    region: str
    model_name: str
    rmse: float
    mape: float
    trained_at: datetime


class RetrainAllResponse(BaseModel):
    results: list[TrainResponse]
