from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CommodityNotSupportedError, TrainingError
from app.db.session import get_session
from app.schemas.responses import (
    CommodityListResponse,
    ForecastPoint,
    HealthResponse,
    HistoricalPoint,
    HistoricalResponse,
    MetricsResponse,
    PredictionResponse,
    RegionalComparisonResponse,
    RegionalHistoricalPoint,
    RegionalHistoricalResponse,
    RegionalPredictionResponse,
    RegionPrice,
    RetrainAllResponse,
    TrainResponse,
)
from app.services.commodity_service import CommodityService

router = APIRouter()
service = CommodityService()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", timestamp=datetime.now(timezone.utc))


@router.get("/commodities", response_model=CommodityListResponse)
async def commodities() -> CommodityListResponse:
    return CommodityListResponse(commodities=service.commodities)


@router.get("/historical/{commodity}", response_model=RegionalHistoricalResponse)
async def historical(
    commodity: str,
    region: str = Query("us", description="Market region: india | us | europe"),
    range: str = Query("5y", description="Historical range e.g. 5y, 1y, 6mo"),
) -> RegionalHistoricalResponse:
    try:
        result = await service.historical(commodity, region=region, period=range)
    except CommodityNotSupportedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.post("/train/{commodity}", response_model=TrainResponse)
async def train(
    commodity: str,
    horizon: int = Query(1, ge=1, le=30),
    region: str = Query("us", description="Market region: india | us | europe"),
    session: AsyncSession = Depends(get_session),
) -> TrainResponse:
    try:
        return await service.train(session, commodity, horizon, region=region)
    except (CommodityNotSupportedError, TrainingError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/predict/{commodity}", response_model=RegionalPredictionResponse)
async def predict(
    commodity: str,
    horizon: int = Query(1, ge=1, le=30),
    region: str = Query("us", description="Market region: india | us | europe"),
    session: AsyncSession = Depends(get_session),
) -> RegionalPredictionResponse:
    try:
        payload = await service.predict(session, commodity, horizon, region=region)
    except (CommodityNotSupportedError, TrainingError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return payload


@router.get("/metrics/{commodity}", response_model=MetricsResponse)
async def metrics(
    commodity: str,
    region: str = Query("us", description="Market region: india | us | europe"),
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
        model_name=latest.model_version,
        rmse=latest.rmse,
        mape=latest.mape,
        trained_at=latest.trained_at,
        region=latest.region,
    )


@router.get("/regional-comparison/{commodity}", response_model=RegionalComparisonResponse)
async def regional_comparison(
    commodity: str,
    session: AsyncSession = Depends(get_session),
) -> RegionalComparisonResponse:
    """Return current predicted price for a commodity in all 3 regions."""
    try:
        result = await service.regional_comparison(session, commodity)
    except (CommodityNotSupportedError, TrainingError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.post("/retrain-all", response_model=RetrainAllResponse)
async def retrain_all(
    horizon: int = Query(1, ge=1, le=30),
    region: str = Query("us", description="Market region: india | us | europe"),
    session: AsyncSession = Depends(get_session),
) -> RetrainAllResponse:
    return RetrainAllResponse(results=await service.retrain_all(session, horizon, region=region))
