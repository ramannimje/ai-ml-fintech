from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import CommodityNotSupportedError, TrainingError
from backend.app.db.session import get_session
from backend.app.schemas.responses import (
    CommodityListResponse,
    HealthResponse,
    HistoricalPoint,
    HistoricalResponse,
    MetricsResponse,
    PredictionResponse,
    RetrainAllResponse,
    TrainResponse,
)
from backend.app.services.commodity_service import CommodityService

router = APIRouter(prefix="/api")
service = CommodityService()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", timestamp=datetime.now(timezone.utc))


@router.get("/commodities", response_model=CommodityListResponse)
async def commodities() -> CommodityListResponse:
    return CommodityListResponse(commodities=service.commodities)


@router.get("/historical/{commodity}", response_model=HistoricalResponse)
async def historical(
    commodity: str,
    region: str = Query("us"),
    range: str = Query("5y"),
) -> HistoricalResponse:
    try:
        data = await service.historical(commodity, region=region, range_period=range)
    except CommodityNotSupportedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    points = [
        HistoricalPoint(timestamp=row.timestamp, close=float(row.close), open=float(row.open), high=float(row.high), low=float(row.low), volume=float(row.volume))
        for row in data.itertuples()
    ]
    return HistoricalResponse(
        commodity=commodity,
        region=region,
        currency=data.iloc[-1]["currency"] if len(data) else "USD",
        unit=data.iloc[-1]["unit"] if len(data) else "oz",
        source=data.iloc[-1]["source"] if len(data) else "unknown",
        rows=len(points),
        data=points,
    )


@router.post("/train/{commodity}", response_model=TrainResponse)
async def train(
    commodity: str,
    horizon: int = Query(1, ge=1, le=365),
    region: str = Query("us"),
    session: AsyncSession = Depends(get_session),
) -> TrainResponse:
    try:
        return await service.train(session, commodity, region=region, horizon=horizon)
    except (CommodityNotSupportedError, TrainingError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/predict/{commodity}", response_model=PredictionResponse)
async def predict(
    commodity: str,
    horizon: int = Query(1, ge=1, le=365),
    region: str = Query("us"),
    session: AsyncSession = Depends(get_session),
) -> PredictionResponse:
    try:
        payload = await service.predict(session, commodity, region=region, horizon=horizon)
    except (CommodityNotSupportedError, TrainingError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PredictionResponse(**payload)


@router.get("/metrics/{commodity}", response_model=MetricsResponse)
async def metrics(
    commodity: str,
    region: str = Query("us"),
    session: AsyncSession = Depends(get_session),
) -> MetricsResponse:
    try:
        latest = await service.latest_metrics(session, commodity, region=region)
    except CommodityNotSupportedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if latest is None:
        raise HTTPException(status_code=404, detail="No metrics found")

    return MetricsResponse(
        commodity=latest.commodity,
        region=latest.region,
        model_name=latest.model_version,
        rmse=latest.rmse,
        mape=latest.mape,
        trained_at=latest.trained_at,
    )


@router.post("/retrain-all", response_model=RetrainAllResponse)
async def retrain_all(
    horizon: int = Query(1, ge=1, le=365),
    region: str = Query("us"),
    session: AsyncSession = Depends(get_session),
) -> RetrainAllResponse:
    return RetrainAllResponse(results=await service.retrain_all(session, region=region, horizon=horizon))
