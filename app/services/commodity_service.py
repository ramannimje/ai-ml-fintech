from __future__ import annotations

from datetime import datetime, timezone
import logging

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import CommodityNotSupportedError, TrainingError
from app.models.training_run import TrainingRun
from app.schemas.responses import (
    LivePriceResponse,
    RegionalHistoricalResponse,
    RegionalPredictionResponse,
    TrainResponse,
)
from app.services.feature_store_service import FeatureStoreService
from app.services.forecast_service import ForecastService
from app.services.fx_cache import get_fx_rates
from app.services.ingestion_service import MarketIngestionService
from app.services.ingestion_persistence_service import IngestionPersistenceService
from app.services.ingestion_replay_service import IngestionReplayService
from app.services.model_registry_service import ModelRegistryService
from app.services.normalization_service import MarketDataNormalizationService
from app.services.price_conversion import REGION_CURRENCY, REGION_UNIT, convert_price, troy_oz_to_grams
from app.services.training_job_service import TrainingJobService
from app.services.training_service import TrainingService
from ml.data.data_fetcher import MarketDataFetcher

SUPPORTED_COMMODITIES = ("gold", "silver", "crude_oil")
COMMODITY_REGION_UNITS = {
    "gold": {"india": "10g_24k", "us": "oz", "europe": "g"},
    "silver": {"india": "10g", "us": "oz", "europe": "g"},
    "crude_oil": {"india": "barrel", "us": "barrel", "europe": "barrel"},
}
logger = logging.getLogger(__name__)


class CommodityService:
    _metals_live_cooldown_until: datetime | None = None
    _metals_live_last_error: str | None = None
    def __init__(self) -> None:
        self.settings = get_settings()
        self.fetcher = MarketDataFetcher(cache_dir=self.settings.data_cache_dir)
        self.ingestion_service = MarketIngestionService(fetcher=self.fetcher)
        self.normalization_service = MarketDataNormalizationService(
            to_regional_price=self._to_regional_price,
            unit_for=self._unit_for,
            region_currency=REGION_CURRENCY,
        )
        self.ingestion_persistence_service = IngestionPersistenceService()
        self.ingestion_replay_service = IngestionReplayService(
            ingestion_service=self.ingestion_service,
            persistence_service=self.ingestion_persistence_service,
        )
        self.feature_store_service = FeatureStoreService(fetcher=self.fetcher)
        self.model_registry_service = ModelRegistryService()
        self.forecast_service = ForecastService(model_registry_service=self.model_registry_service)
        self.training_job_service = TrainingJobService()
        self.training_service = TrainingService()

    @property
    def commodities(self) -> list[str]:
        return list(SUPPORTED_COMMODITIES)

    @property
    def regions(self) -> list[str]:
        return list(self.settings.supported_regions)

    def _validate(self, commodity: str) -> None:
        if commodity not in SUPPORTED_COMMODITIES:
            raise CommodityNotSupportedError(f"Unsupported commodity: {commodity}")

    def _validate_region(self, region: str) -> str:
        out = region.lower()
        if out not in self.settings.supported_regions:
            raise ValueError(
                f"Unsupported region: {region!r}. Must be one of: {self.settings.supported_regions}"
            )
        return out

    @staticmethod
    def _unit_for(commodity: str, region: str) -> str:
        return COMMODITY_REGION_UNITS.get(commodity, {}).get(region, REGION_UNIT.get(region, "unit"))

    def _to_regional_price(self, usd_per_troy_oz: float, region: str, fx: dict[str, float]) -> float:
        # Convert from canonical USD/troy_oz feed into region unit/currency without extra multipliers.
        return convert_price(troy_oz_to_grams(usd_per_troy_oz), region, fx)

    def _enrich_features(self, raw: pd.DataFrame, region: str, fx: dict[str, float] | None = None) -> pd.DataFrame:
        return self.feature_store_service.materialize_from_frame(raw=raw, region=region, fx=fx)

    async def live_prices(self, region: str | None = None, session: AsyncSession | None = None) -> list[LivePriceResponse]:
        """Fetch live commodity prices.

        Uses Metals-API.com if METALS_API_KEY is configured; otherwise falls back to yfinance.
        Prices are converted to regional units and currencies.
        """
        regions = [self._validate_region(region)] if region else self.regions
        fx = get_fx_rates()
        out: list[LivePriceResponse] = []
        quotes = await self.ingestion_service.fetch_live_quotes(self.commodities)
        if session is not None:
            for reg in regions:
                await self.ingestion_persistence_service.persist_live_quotes(session, quotes=quotes, region=reg)
        for commodity in self.commodities:
            quote = quotes.get(commodity)
            if not quote:
                continue
            for reg in regions:
                out.append(self.normalization_service.to_live_price_response(quote=quote, region=reg, fx_rates=fx))
        return out

    async def _fetch_metals_live_rates(self) -> dict[str, float]:
        provider = self.ingestion_service.metals_live_provider
        provider.cooldown_until = self._metals_live_cooldown_until
        provider.last_error = self._metals_live_last_error
        quotes = await provider.fetch(self.commodities)
        self._metals_live_cooldown_until = provider.cooldown_until
        self._metals_live_last_error = provider.last_error
        return {commodity: quote.price_usd_per_troy_oz for commodity, quote in quotes.items()}

    async def _fetch_yahoo_finance_live_rates(self) -> dict[str, float]:
        quotes = await self.ingestion_service.yahoo_live_provider.fetch(self.commodities)
        return {commodity: quote.price_usd_per_troy_oz for commodity, quote in quotes.items()}

    async def historical(
        self,
        commodity: str,
        region: str,
        period: str = "1y",
        session: AsyncSession | None = None,
    ) -> RegionalHistoricalResponse:
        self._validate(commodity)
        region = self._validate_region(region)
        valid_ranges = {"1m", "6m", "1y", "5y", "max"}
        if period not in valid_ranges:
            raise ValueError(f"Invalid range {period!r}. Must be one of {sorted(valid_ranges)}")

        fx = get_fx_rates()
        series = self.ingestion_service.load_historical_series(commodity=commodity, region=region, period=period)
        if session is not None:
            await self.ingestion_persistence_service.persist_historical_series(
                session,
                series=series,
                period=period,
            )
        return self.normalization_service.to_historical_response(
            series=series,
            fx_rates=fx,
            fx_history=self.fetcher.get_fx_history(region=region, period=period),
        )

    async def train(
        self, session: AsyncSession, commodity: str, region: str, horizon: int = 1, job_id: int | None = None
    ) -> TrainResponse:
        self._validate(commodity)
        region = self._validate_region(region)
        series = self.ingestion_service.load_historical_series(commodity=commodity, region=region)
        return await self.training_service.train(
            session=session,
            commodity=commodity,
            region=region,
            horizon=horizon,
            series=series,
            feature_store_service=self.feature_store_service,
            job_id=job_id,
            training_job_service=self.training_job_service,
        )

    async def create_training_job(
        self,
        session: AsyncSession,
        commodity: str,
        region: str,
        horizon: int = 1,
    ):
        self._validate(commodity)
        region = self._validate_region(region)
        return await self.training_job_service.create_job(
            session,
            commodity=commodity,
            region=region,
            horizon=horizon,
        )

    async def get_training_status(self, session: AsyncSession, commodity: str, region: str) -> dict:
        self._validate(commodity)
        region = self._validate_region(region)
        return await self.training_job_service.get_status(session, commodity=commodity, region=region)

    async def create_ingestion_backfill_job(
        self,
        session: AsyncSession,
        commodity: str,
        region: str,
        period: str = "1y",
    ):
        self._validate(commodity)
        region = self._validate_region(region)
        valid_ranges = {"1m", "6m", "1y", "5y", "max"}
        if period not in valid_ranges:
            raise ValueError(f"Invalid range {period!r}. Must be one of {sorted(valid_ranges)}")
        return await self.ingestion_replay_service.create_historical_backfill_job(
            session,
            commodity=commodity,
            region=region,
            period=period,
        )

    async def run_ingestion_backfill_job(self, session: AsyncSession, *, job_id: int) -> dict:
        return await self.ingestion_replay_service.run_job(session, job_id=job_id)

    async def get_ingestion_job_status(self, session: AsyncSession, *, job_id: int) -> dict | None:
        return await self.ingestion_replay_service.get_job_status(session, job_id=job_id)

    async def latest_metrics(self, session: AsyncSession, commodity: str, region: str) -> TrainingRun | None:
        self._validate(commodity)
        region = self._validate_region(region)
        return await self.model_registry_service.latest_metrics(session, commodity, region)

    async def prewarm_latest_models(self, session: AsyncSession) -> None:
        await self.model_registry_service.prewarm_latest_models(session, self.commodities, self.regions)

    async def predict(
        self, session: AsyncSession, commodity: str, region: str, horizon: int = 1
    ) -> RegionalPredictionResponse:
        self._validate(commodity)
        region = self._validate_region(region)
        series = self.ingestion_service.load_historical_series(commodity=commodity, region=region)
        fx = get_fx_rates()
        live_quotes = await self.ingestion_service.fetch_live_quotes([commodity])
        live_quote = live_quotes.get(commodity)
        current_spot_usd_oz = (
            float(live_quote.price_usd_per_troy_oz)
            if live_quote is not None
            else float(series.bars[-1].close_usd_per_troy_oz)
        )
        spot_timestamp = live_quote.observed_at if live_quote is not None else datetime.now(timezone.utc)
        return await self.forecast_service.generate_prediction(
            session=session,
            commodity=commodity,
            region=region,
            horizon=horizon,
            series=series,
            feature_store_service=self.feature_store_service,
            fx_rates=fx,
            unit=self._unit_for(commodity, region),
            currency=REGION_CURRENCY[region],
            to_regional_price=self._to_regional_price,
            current_spot_usd_oz=current_spot_usd_oz,
            spot_timestamp=spot_timestamp,
            latest_metrics_loader=self.latest_metrics,
        )
