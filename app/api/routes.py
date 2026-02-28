from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CommodityNotSupportedError, TrainingError
from app.db.session import get_session
from app.schemas.responses import (
    CommodityDefinition,
    ErrorResponse,
    HealthResponse,
    LivePriceResponse,
    LivePricesEnvelope,
    RegionDefinition,
    RegionalHistoricalResponse,
    RegionalPredictionResponse,
    TrainResponse,
)
from app.services.commodity_service import CommodityService

router = APIRouter()
service = CommodityService()

REGION_CATALOG = [
    RegionDefinition(id="india", currency="INR", unit="10g_24k"),
    RegionDefinition(id="us", currency="USD", unit="oz"),
    RegionDefinition(id="europe", currency="EUR", unit="exchange_standard"),
]

COMMODITY_CATALOG = [
    CommodityDefinition(id="gold"),
    CommodityDefinition(id="silver"),
    CommodityDefinition(id="crude_oil"),
]


def _err(code: str, message: str, **context: str) -> dict:
    return {"error": {"code": code, "message": message, "context": context}}


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", timestamp=datetime.now(timezone.utc))


@router.get("/regions", response_model=list[RegionDefinition])
async def regions() -> list[RegionDefinition]:
    return REGION_CATALOG


@router.get("/commodities", response_model=list[CommodityDefinition])
async def commodities() -> list[CommodityDefinition]:
    return COMMODITY_CATALOG


@router.get(
    "/live-prices",
    response_model=LivePricesEnvelope,
    responses={503: {"model": ErrorResponse}},
)
async def live_prices() -> LivePricesEnvelope:
    try:
        return LivePricesEnvelope(items=await service.live_prices())
    except (CommodityNotSupportedError, TrainingError, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail=_err("LIVE_PRICE_UNAVAILABLE", str(exc)),
        ) from exc


@router.get(
    "/live-prices/{region}",
    response_model=LivePricesEnvelope,
    responses={400: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def live_prices_region(region: str) -> LivePricesEnvelope:
    try:
        return LivePricesEnvelope(items=await service.live_prices(region=region))
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=_err("INVALID_REGION", str(exc), region=region),
        ) from exc
    except (CommodityNotSupportedError, TrainingError, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail=_err("LIVE_PRICE_UNAVAILABLE", str(exc), region=region),
        ) from exc


@router.get(
    "/historical/{commodity}/{region}",
    response_model=RegionalHistoricalResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def historical(
    commodity: str,
    region: str,
    range: str = Query("1y", description="1m|6m|1y|5y|max"),
) -> RegionalHistoricalResponse:
    try:
        return await service.historical(commodity, region=region, period=range)
    except CommodityNotSupportedError as exc:
        raise HTTPException(
            status_code=404,
            detail=_err("UNSUPPORTED_COMMODITY", str(exc), commodity=commodity),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=_err("INVALID_REQUEST", str(exc), commodity=commodity, region=region),
        ) from exc


@router.get(
    "/predict/{commodity}/{region}",
    response_model=RegionalPredictionResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def predict(
    commodity: str,
    region: str,
    horizon: int = Query(1, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
) -> RegionalPredictionResponse:
    try:
        return await service.predict(session, commodity, region=region, horizon=horizon)
    except CommodityNotSupportedError as exc:
        raise HTTPException(
            status_code=404,
            detail=_err("UNSUPPORTED_COMMODITY", str(exc), commodity=commodity),
        ) from exc
    except (ValueError, TrainingError) as exc:
        raise HTTPException(
            status_code=400,
            detail=_err("PREDICTION_FAILED", str(exc), commodity=commodity, region=region),
        ) from exc


@router.post(
    "/train/{commodity}/{region}",
    response_model=TrainResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def train(
    commodity: str,
    region: str,
    horizon: int = Query(1, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
) -> TrainResponse:
    try:
        return await service.train(session, commodity, region=region, horizon=horizon)
    except CommodityNotSupportedError as exc:
        raise HTTPException(
            status_code=404,
            detail=_err("UNSUPPORTED_COMMODITY", str(exc), commodity=commodity),
        ) from exc
    except (ValueError, TrainingError) as exc:
        raise HTTPException(
            status_code=400,
            detail=_err("TRAINING_FAILED", str(exc), commodity=commodity, region=region),
        ) from exc
