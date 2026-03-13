import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
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
    DataProvenance,
    ErrorResponse,
    FeatureSnapshotResponse,
    HealthResponse,
    IngestionJobResponse,
    LivePriceResponse,
    LivePricesEnvelope,
    MarketIntelligenceResponse,
    MarketSignalResponse,
    NormalizedHistoricalBarResponse,
    NormalizedHistoricalSeriesResponse,
    NormalizedLiveQuoteResponse,
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
from app.services.news_persistence_service import NewsPersistenceService
from app.services.profile_service import ProfileService
from app.services.market_signal_service import MarketSignalService
from app.services.settings_service import SettingsService

router = APIRouter()
service = CommodityService()
alert_service = AlertService()
news_service = CommodityNewsService()
news_persistence_service = NewsPersistenceService(news_service)
profile_service = ProfileService()
settings_service = SettingsService()
market_signal_service = MarketSignalService()

REGION_CATALOG = [
    RegionDefinition(id="india", currency="INR", unit="10g"),
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
    return HealthResponse(status="ok")


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
async def live_prices(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> LivePricesEnvelope:
    _ = current_user
    try:
        return LivePricesEnvelope(items=await service.live_prices(session=session))
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
async def public_live_prices_region(region: str, session: AsyncSession = Depends(get_session)) -> LivePricesEnvelope:
    try:
        return LivePricesEnvelope(items=await service.live_prices(region=region, session=session))
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
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> LivePricesEnvelope:
    _ = current_user
    try:
        return LivePricesEnvelope(items=await service.live_prices(region=region, session=session))
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
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> CommodityNewsSummaryResponse:
    _ = current_user
    if commodity not in ALERT_COMMODITY_SYMBOLS:
        raise HTTPException(
            status_code=400,
            detail=_err("INVALID_COMMODITY", "Unsupported commodity for news summary", commodity=commodity),
        )
    headlines = await news_persistence_service.get_or_ingest_recent_headlines(session, commodity=commodity)
    return await news_service.summarize(commodity, headlines=headlines)


@router.get(
    "/historical/{commodity}/{region}",
    response_model=RegionalHistoricalResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def historical(
    commodity: str,
    region: str,
    range: str = Query("1y", description="1m|6m|1y|5y|max"),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> RegionalHistoricalResponse:
    _ = current_user
    try:
        return await service.historical(commodity, region=region, period=range, session=session)
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
    horizon: int | None = Query(default=None, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> RegionalPredictionResponse:
    if horizon is None:
        user_settings = await settings_service.get_or_create(
            session=session,
            user_id=current_user.get("sub", "unknown"),
        )
        horizon = user_settings.prediction_horizon
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


@router.get(
    "/forecasts/{commodity}/{region}",
    response_model=RegionalPredictionResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def forecast_snapshot(
    commodity: str,
    region: str,
    horizon: int | None = Query(default=None, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> RegionalPredictionResponse:
    return await predict(
        commodity=commodity,
        region=region,
        horizon=horizon,
        session=session,
        current_user=current_user,
    )


@router.get(
    "/normalized/live/{commodity}/{region}",
    response_model=NormalizedLiveQuoteResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def normalized_live_quote(
    commodity: str,
    region: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> NormalizedLiveQuoteResponse:
    _ = current_user
    try:
        service._validate(commodity)
        region = service._validate_region(region)
        quotes = await service.ingestion_service.fetch_live_quotes([commodity])
        quote = quotes.get(commodity)
        if not quote:
            raise ValueError(f"Live price unavailable for {commodity}/{region}")
        await service.ingestion_persistence_service.persist_live_quotes(session, quotes=quotes, region=region)
        return NormalizedLiveQuoteResponse(
            commodity=quote.commodity,
            price_usd_per_troy_oz=quote.price_usd_per_troy_oz,
            observed_at=quote.observed_at,
            provenance=DataProvenance(
                data_type="live_price",
                provider=quote.provenance.provider,
                detail=quote.provenance.detail,
                observed_at=quote.provenance.observed_at,
            ),
        )
    except CommodityNotSupportedError as exc:
        raise HTTPException(
            status_code=404,
            detail=_err("UNSUPPORTED_COMMODITY", str(exc), commodity=commodity),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=_err("NORMALIZED_DATA_FAILED", str(exc), commodity=commodity, region=region),
        ) from exc


@router.get(
    "/normalized/historical/{commodity}/{region}",
    response_model=NormalizedHistoricalSeriesResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def normalized_historical(
    commodity: str,
    region: str,
    range: str = Query("1y", description="1m|6m|1y|5y|max"),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> NormalizedHistoricalSeriesResponse:
    _ = current_user
    try:
        service._validate(commodity)
        region = service._validate_region(region)
        series = service.ingestion_service.load_historical_series(commodity=commodity, region=region, period=range)
        await service.ingestion_persistence_service.persist_historical_series(
            session,
            series=series,
            period=range,
        )
        return NormalizedHistoricalSeriesResponse(
            commodity=series.commodity,
            region=series.region,
            rows=len(series.bars),
            provenance=DataProvenance(
                data_type="historical",
                provider=series.provenance.provider,
                detail=series.provenance.detail,
                observed_at=series.provenance.observed_at,
            ),
            data=[
                NormalizedHistoricalBarResponse(
                    date=bar.date,
                    open_usd_per_troy_oz=bar.open_usd_per_troy_oz,
                    high_usd_per_troy_oz=bar.high_usd_per_troy_oz,
                    low_usd_per_troy_oz=bar.low_usd_per_troy_oz,
                    close_usd_per_troy_oz=bar.close_usd_per_troy_oz,
                    volume=bar.volume,
                )
                for bar in series.bars
            ],
        )
    except CommodityNotSupportedError as exc:
        raise HTTPException(
            status_code=404,
            detail=_err("UNSUPPORTED_COMMODITY", str(exc), commodity=commodity),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=_err("NORMALIZED_DATA_FAILED", str(exc), commodity=commodity, region=region),
        ) from exc


@router.get(
    "/features/{commodity}/{region}",
    response_model=FeatureSnapshotResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def feature_snapshot(
    commodity: str,
    region: str,
    range: str = Query("1y", description="1m|6m|1y|5y|max"),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> FeatureSnapshotResponse:
    _ = current_user
    try:
        service._validate(commodity)
        region = service._validate_region(region)
        series = service.ingestion_service.load_historical_series(commodity=commodity, region=region, period=range)
        await service.ingestion_persistence_service.persist_historical_series(
            session,
            series=series,
            period=range,
        )
        enriched = await service.feature_store_service.materialize_online_features_for_session(
            session,
            commodity=commodity,
            series=series,
            region=region,
            period=range,
        )
        closes = [bar.close_usd_per_troy_oz for bar in series.bars]
        features = service.feature_store_service.build_feature_snapshot(closes=closes, enriched=enriched)
        return FeatureSnapshotResponse(
            commodity=commodity,
            region=region,
            period=range,
            features=features,
            provenance=[
                DataProvenance(
                    data_type="historical",
                    provider=series.provenance.provider,
                    detail=series.provenance.detail,
                    observed_at=series.provenance.observed_at,
                ),
                DataProvenance(
                    data_type="features",
                    provider="feature_store_service_v1",
                    detail="returns, momentum, volatility, FX proxy, inflation proxy, rate proxy",
                ),
            ],
        )
    except CommodityNotSupportedError as exc:
        raise HTTPException(
            status_code=404,
            detail=_err("UNSUPPORTED_COMMODITY", str(exc), commodity=commodity),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=_err("FEATURE_SNAPSHOT_FAILED", str(exc), commodity=commodity, region=region),
        ) from exc


@router.get(
    "/signals/{commodity}/{region}",
    response_model=MarketSignalResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def market_signal(
    commodity: str,
    region: str,
    horizon: int = Query(default=30, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> MarketSignalResponse:
    _ = current_user
    try:
        return await market_signal_service.build_signal_response(
            session=session,
            commodity=commodity,
            region=region,
            horizon=horizon,
        )
    except CommodityNotSupportedError as exc:
        raise HTTPException(
            status_code=404,
            detail=_err("UNSUPPORTED_COMMODITY", str(exc), commodity=commodity),
        ) from exc
    except (ValueError, TrainingError, RuntimeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=_err("SIGNAL_FAILED", str(exc), commodity=commodity, region=region),
        ) from exc


@router.get(
    "/intelligence/{commodity}/{region}",
    response_model=MarketIntelligenceResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def market_intelligence(
    commodity: str,
    region: str,
    horizon: int = Query(default=30, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> MarketIntelligenceResponse:
    _ = current_user
    try:
        return await market_signal_service.build_market_intelligence(
            session=session,
            commodity=commodity,
            region=region,
            horizon=horizon,
        )
    except CommodityNotSupportedError as exc:
        raise HTTPException(
            status_code=404,
            detail=_err("UNSUPPORTED_COMMODITY", str(exc), commodity=commodity),
        ) from exc
    except (ValueError, TrainingError, RuntimeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=_err("INTELLIGENCE_FAILED", str(exc), commodity=commodity, region=region),
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
    status_code=status.HTTP_202_ACCEPTED,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def train(
    commodity: str,
    region: str,
    background_tasks: BackgroundTasks,
    horizon: int = Query(1, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    _ = current_user

    try:
        job = await service.create_training_job(session, commodity, region=region, horizon=horizon)
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

    from app.db.session import AsyncSessionLocal

    async def run_training():
        async with AsyncSessionLocal() as bg_session:
            try:
                await service.train(bg_session, commodity, region=region, horizon=horizon, job_id=job.id)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Background training failed for {commodity}/{region}: {e}")

    background_tasks.add_task(run_training)

    return {"message": f"Training initiated in background for {commodity} in {region}", "status": "processing"}

@router.get("/train/{commodity}/{region}/status")
async def get_training_status(
    commodity: str,
    region: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    _ = current_user
    try:
        return await service.get_training_status(session, commodity, region=region)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=_err("STATUS_CHECK_FAILED", str(exc)))


@router.post(
    "/ingestion/backfill/{commodity}/{region}",
    response_model=IngestionJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def backfill_historical_ingestion(
    commodity: str,
    region: str,
    background_tasks: BackgroundTasks,
    range: str = Query("1y", description="1m|6m|1y|5y|max"),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> IngestionJobResponse:
    _ = current_user
    try:
        job = await service.create_ingestion_backfill_job(session, commodity, region=region, period=range)
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

    from app.db.session import AsyncSessionLocal

    async def run_backfill() -> None:
        async with AsyncSessionLocal() as bg_session:
            try:
                await service.run_ingestion_backfill_job(bg_session, job_id=job.id)
            except Exception as exc:
                import logging

                logging.getLogger(__name__).error("Background ingestion replay failed for job %s: %s", job.id, exc)

    background_tasks.add_task(run_backfill)
    job_status = await service.get_ingestion_job_status(session, job_id=job.id)
    if job_status is None:
        raise HTTPException(
            status_code=404,
            detail=_err("INGESTION_JOB_NOT_FOUND", "Ingestion job not found after creation", job_id=str(job.id)),
        )
    return IngestionJobResponse(**job_status)


@router.get(
    "/ingestion/jobs/{job_id}",
    response_model=IngestionJobResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_ingestion_job_status(
    job_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> IngestionJobResponse:
    _ = current_user
    payload = await service.get_ingestion_job_status(session, job_id=job_id)
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail=_err("INGESTION_JOB_NOT_FOUND", f"Ingestion job not found: {job_id}", job_id=str(job_id)),
        )
    return IngestionJobResponse(**payload)
