import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CommodityNotSupportedError, TrainingError
from app.core.auth import get_current_user
from app.db.session import get_session
from app.schemas.responses import (
    AlertCreateRequest,
    AlertEvaluationResponse,
    AlertHistoryResponse,
    AlertUpdateRequest,
    CommodityNewsSummaryResponse,
    CommodityDefinition,
    ErrorResponse,
    HealthResponse,
    LivePriceResponse,
    LivePricesEnvelope,
    PriceAlertResponse,
    RegionDefinition,
    RegionalHistoricalResponse,
    RegionalPredictionResponse,
    TrainResponse,
    UserProfileResponse,
    UserProfileUpdateRequest,
    WhatsAppAlertCreateRequest,
    WhatsAppAlertResponse,
)
from app.services.alert_service import AlertService
from app.services.commodity_service import CommodityService
from app.services.market_quote_service import ALERT_COMMODITY_SYMBOLS
from app.services.news_service import CommodityNewsService
from app.services.profile_service import ProfileService

router = APIRouter()
service = CommodityService()
alert_service = AlertService()
news_service = CommodityNewsService()
profile_service = ProfileService()

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
async def live_prices(current_user: dict = Depends(get_current_user)) -> LivePricesEnvelope:
    _ = current_user
    try:
        return LivePricesEnvelope(items=await service.live_prices())
    except (CommodityNotSupportedError, TrainingError, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail=_err("LIVE_PRICE_UNAVAILABLE", str(exc)),
        ) from exc


@router.get(
    "/public/live-prices/{region}",
    response_model=LivePricesEnvelope,
    responses={400: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def public_live_prices_region(region: str) -> LivePricesEnvelope:
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
    "/live-prices/{region}",
    response_model=LivePricesEnvelope,
    responses={400: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def live_prices_region(
    region: str,
    current_user: dict = Depends(get_current_user),
) -> LivePricesEnvelope:
    _ = current_user
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
    "/news-summary/{commodity}",
    response_model=CommodityNewsSummaryResponse,
    responses={400: {"model": ErrorResponse}},
)
async def commodity_news_summary(
    commodity: str,
    current_user: dict = Depends(get_current_user),
) -> CommodityNewsSummaryResponse:
    _ = current_user
    if commodity not in ALERT_COMMODITY_SYMBOLS:
        raise HTTPException(
            status_code=400,
            detail=_err("INVALID_COMMODITY", "Unsupported commodity for news summary", commodity=commodity),
        )
    return await news_service.summarize(commodity)


@router.get(
    "/historical/{commodity}/{region}",
    response_model=RegionalHistoricalResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def historical(
    commodity: str,
    region: str,
    range: str = Query("1y", description="1m|6m|1y|5y|max"),
    current_user: dict = Depends(get_current_user),
) -> RegionalHistoricalResponse:
    _ = current_user
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
    current_user: dict = Depends(get_current_user),
) -> RegionalPredictionResponse:
    _ = current_user
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


@router.post("/alerts", response_model=PriceAlertResponse, responses={400: {"model": ErrorResponse}})
async def create_alert(
    payload: AlertCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> PriceAlertResponse:
    try:
        return await alert_service.create_alert(
            session=session,
            user_sub=current_user.get("sub", "unknown"),
            user_email=current_user.get("email"),
            payload=payload,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=_err("ALERT_CREATE_FAILED", str(exc)),
        ) from exc


@router.post("/alerts/whatsapp", response_model=WhatsAppAlertResponse, responses={400: {"model": ErrorResponse}})
async def create_whatsapp_alert(
    payload: WhatsAppAlertCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> WhatsAppAlertResponse:
    try:
        return await alert_service.create_whatsapp_alert(
            session=session,
            user_id=current_user.get("sub", "unknown"),
            payload=payload,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=_err("WHATSAPP_ALERT_CREATE_FAILED", str(exc)),
        ) from exc


@router.patch("/alerts/{alert_id}", response_model=PriceAlertResponse, responses={400: {"model": ErrorResponse}})
async def patch_alert(
    alert_id: int,
    payload: AlertUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> PriceAlertResponse:
    try:
        return await alert_service.update_alert(
            session=session,
            user_sub=current_user.get("sub", "unknown"),
            alert_id=alert_id,
            payload=payload,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=_err("ALERT_UPDATE_FAILED", str(exc), alert_id=str(alert_id)),
        ) from exc


@router.get("/alerts", response_model=list[PriceAlertResponse])
async def list_alerts(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> list[PriceAlertResponse]:
    return await alert_service.list_alerts(session, current_user.get("sub", "unknown"))


@router.delete("/alerts/{alert_id}", response_model=dict[str, str])
async def delete_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> dict[str, str]:
    await alert_service.delete_alert(session, current_user.get("sub", "unknown"), alert_id)
    return {"status": "deleted"}


@router.get("/alerts/history", response_model=list[AlertHistoryResponse])
async def list_alert_history(
    commodity: str | None = Query(default=None),
    alert_type: str | None = Query(default=None),
    email_status: str | None = Query(default=None),
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> list[AlertHistoryResponse]:
    return await alert_service.alert_history(
        session,
        current_user.get("sub", "unknown"),
        commodity=commodity,
        alert_type=alert_type,
        email_status=email_status,
        start_at=start_at,
        end_at=end_at,
        search=search,
        limit=limit,
    )


@router.get("/alerts/history/export")
async def export_alert_history(
    commodity: str | None = Query(default=None),
    alert_type: str | None = Query(default=None),
    email_status: str | None = Query(default=None),
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
    search: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> StreamingResponse:
    rows = await alert_service.alert_history(
        session,
        current_user.get("sub", "unknown"),
        commodity=commodity,
        alert_type=alert_type,
        email_status=email_status,
        start_at=start_at,
        end_at=end_at,
        search=search,
        limit=1000,
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "alert_id",
            "commodity",
            "region",
            "alert_type",
            "threshold",
            "observed_value",
            "message",
            "email_status",
            "delivery_provider",
            "delivery_error",
            "delivery_attempts",
            "triggered_at",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.id,
                row.alert_id,
                row.commodity,
                row.region,
                row.alert_type,
                row.threshold,
                row.observed_value,
                row.message,
                row.email_status,
                row.delivery_provider or "",
                row.delivery_error or "",
                row.delivery_attempts,
                row.triggered_at.isoformat(),
            ]
        )
    payload = buf.getvalue()
    filename = f"alert-history-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.csv"
    return StreamingResponse(
        iter([payload]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/alerts/evaluate", response_model=AlertEvaluationResponse)
async def evaluate_alerts(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> AlertEvaluationResponse:
    return await alert_service.evaluate_user_alerts(
        session=session,
        user_sub=current_user.get("sub", "unknown"),
        user_email=current_user.get("email"),
    )


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> UserProfileResponse:
    return await profile_service.get_or_create(
        session=session,
        user_sub=current_user.get("sub", "unknown"),
        user_email=current_user.get("email"),
        user_name=current_user.get("name"),
        picture_url=current_user.get("picture"),
        user_context=current_user,
    )


@router.put("/profile", response_model=UserProfileResponse)
async def update_profile(
    payload: UserProfileUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> UserProfileResponse:
    return await profile_service.update(
        session=session,
        user_sub=current_user.get("sub", "unknown"),
        payload=payload,
        user_email=current_user.get("email"),
    )


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
    current_user: dict = Depends(get_current_user),
) -> TrainResponse:
    _ = current_user
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
