from datetime import date, datetime
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


class TrainResponse(BaseModel):
    commodity: str
    best_model: str
    model_version: str
    rmse: float
    mape: float


class PredictionResponse(BaseModel):
    commodity: str
    prediction_date: date
    predicted_price: float
    confidence_interval: tuple[float, float]
    model_used: str
    model_accuracy_rmse: float
    horizon_days: int = Field(default=1)


class MetricsResponse(BaseModel):
    commodity: str
    model_name: str
    rmse: float
    mape: float
    trained_at: datetime


class RetrainAllResponse(BaseModel):
    results: list[TrainResponse]
