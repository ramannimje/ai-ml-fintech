from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import logging
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import CommodityNotSupportedError, TrainingError
from app.models.training_run import TrainingRun
from app.schemas.responses import (
    LivePriceResponse,
    RegionalHistoricalPoint,
    RegionalHistoricalResponse,
    RegionalPredictionResponse,
    TrainResponse,
)
from app.services.fx_cache import get_fx_rates
from app.services.price_conversion import REGION_CURRENCY, REGION_UNIT, convert_price, troy_oz_to_grams
from ml.data.data_fetcher import COMMODITY_SYMBOLS, MarketDataFetcher
from ml.features.engineer import add_features, make_supervised
from ml.inference.artifacts import load_model, save_model

SUPPORTED_COMMODITIES = ("gold", "silver", "crude_oil")
COMMODITY_REGION_UNITS = {
    "gold": {"india": "10g_24k", "us": "oz", "europe": "exchange_standard"},
    "silver": {"india": "10g", "us": "oz", "europe": "exchange_standard"},
    "crude_oil": {"india": "barrel", "us": "barrel", "europe": "barrel"},
}
PRIMARY_SOURCE_BY_COMMODITY = {
    "gold": "comex",
    "silver": "comex",
    "crude_oil": "comex",
}
logger = logging.getLogger(__name__)


class CommodityService:
    # Simple in-memory cache for loaded models per (commodity, region)
    _model_cache: dict[tuple[str, str], tuple[Any, dict]] = {}
    # Short-lived prediction response cache for smoother UI refreshes.
    _prediction_cache: dict[tuple[str, str, int], tuple[datetime, RegionalPredictionResponse]] = {}
    
    # Tracks the status of background training runs: {(commodity, region): {"status": str, "message": str, "result": dict}}
    _training_status: dict[tuple[str, str], dict] = {}
    
    _metals_live_cooldown_until: datetime | None = None
    _metals_live_last_error: str | None = None
    def __init__(self) -> None:
        self.settings = get_settings()
        self.fetcher = MarketDataFetcher(cache_dir=self.settings.data_cache_dir)

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
        feat = add_features(raw)
        rates = fx or get_fx_rates()
        inr = rates.get("INR")
        eur = rates.get("EUR")
        fx_series = pd.Series(dtype=float, index=feat.index)
        if region == "india" and inr:
            fx_series = pd.Series(inr, index=feat.index)
        elif region == "europe" and eur:
            fx_series = pd.Series(eur, index=feat.index)
        else:
            fx_series = pd.Series(1.0, index=feat.index)

        feat["fx_rate"] = fx_series
        feat["fx_volatility"] = fx_series.pct_change().rolling(10, min_periods=2).std().fillna(0.0)
        # Proxies when direct CPI/FRED/ECB/RBI feeds are unavailable in live execution path.
        feat["inflation_proxy"] = feat["returns"].rolling(30, min_periods=5).mean().fillna(0.0)
        feat["interest_rates_fred_ecb_rbi"] = feat["returns"].rolling(60, min_periods=10).std().fillna(0.0)
        return feat

    def _walk_forward_score(self, x: pd.DataFrame, y: pd.Series) -> tuple[float, float]:
        from ml.training.models import benchmark_models

        min_train = max(60, int(len(x) * 0.6))
        if len(x) <= min_train + 5:
            ranked = benchmark_models(x, y)
            if not ranked:
                raise TrainingError("No model could be trained")
            return ranked[0].rmse, ranked[0].mape

        rmses: list[float] = []
        mapes: list[float] = []
        step = max(5, int(len(x) * 0.1))
        for split in range(min_train, len(x) - 1, step):
            x_train = x.iloc[:split]
            y_train = y.iloc[:split]
            x_test = x.iloc[split : split + step]
            y_test = y.iloc[split : split + step]
            ranked = benchmark_models(x_train, y_train)
            if not ranked or x_test.empty:
                continue
            pred = ranked[0].model.predict(x_test)
            residual = y_test.to_numpy() - pred
            rmse = float(np.sqrt(np.mean(np.square(residual))))
            denom = np.where(y_test.to_numpy() == 0, 1.0, y_test.to_numpy())
            mape = float(np.mean(np.abs(residual / denom)) * 100.0)
            rmses.append(rmse)
            mapes.append(mape)

        if not rmses:
            ranked = benchmark_models(x, y)
            if not ranked:
                raise TrainingError("No model could be trained")
            return ranked[0].rmse, ranked[0].mape
        return float(np.mean(rmses)), float(np.mean(mapes))

    async def live_prices(self, region: str | None = None) -> list[LivePriceResponse]:
        """Fetch live commodity prices.

        Uses Metals-API.com if METALS_API_KEY is configured; otherwise falls back to yfinance.
        Prices are converted to regional units and currencies.
        """
        regions = [self._validate_region(region)] if region else self.regions
        fx = get_fx_rates()
        now = datetime.now(timezone.utc)
        out: list[LivePriceResponse] = []

        rates = await self._fetch_metals_live_rates()
        fetched_commodities: set[str] = set()

        # Process rates for known commodities
        for commodity in self.commodities:
            price_usd = rates.get(commodity)
            if price_usd is not None:
                fetched_commodities.add(commodity)
                for reg in regions:
                    price = self._to_regional_price(price_usd, reg, fx)
                    out.append(
                        LivePriceResponse(
                            commodity=commodity,
                            region=reg,
                            unit=self._unit_for(commodity, reg),
                            currency=REGION_CURRENCY[reg],
                            live_price=round(price, 4),
                            source='metals.live',
                            timestamp=now,
                        )
                    )
        # If we got results from free API, return them (skip yfinance)
        if len(fetched_commodities) == len(self.commodities):
            return out

        # Direct HTTP Fetch Fallback from Yahoo Finance API (bypassing yfinance library rate limits)
        if len(fetched_commodities) < len(self.commodities):
            yf_rates = await self._fetch_yahoo_finance_live_rates()
            for commodity in set(self.commodities) - fetched_commodities:
                price_usd = yf_rates.get(commodity)
                if price_usd is not None:
                    fetched_commodities.add(commodity)
                    source = f"{PRIMARY_SOURCE_BY_COMMODITY.get(commodity, 'yahoo_finance')}/yahoo_api"
                    for reg in regions:
                        price = self._to_regional_price(price_usd, reg, fx)
                        out.append(
                            LivePriceResponse(
                                commodity=commodity,
                                region=reg,
                                unit=self._unit_for(commodity, reg),
                                currency=REGION_CURRENCY[reg],
                                live_price=round(price, 4),
                                source=source,
                                timestamp=now,
                            )
                        )

        if len(fetched_commodities) == len(self.commodities):
            return out

        # Deep Fallback to cached history (existing logic)
        for commodity in set(self.commodities) - fetched_commodities:
            try:
                raw = self.fetcher.get_historical(commodity, period="1y")
                if raw.empty:
                    raise TrainingError(f"No cached market data available for {commodity}")

                latest = float(raw["Close"].iloc[-1])
                source = f"{PRIMARY_SOURCE_BY_COMMODITY.get(commodity, 'yahoo_finance')}/cached_history"
                fetched_commodities.add(commodity)
                for reg in regions:
                    price = self._to_regional_price(latest, reg, fx)
                    out.append(
                        LivePriceResponse(
                            commodity=commodity,
                            region=reg,
                            unit=self._unit_for(commodity, reg),
                            currency=REGION_CURRENCY[reg],
                            live_price=round(price, 4),
                            source=source,
                            timestamp=now,
                        )
                    )
            except Exception as exc:
                logger.error("pricing_failure deep fallback commodity=%s reason=%s", commodity, str(exc))
                continue
                
        # Final Fallback static prices when external sources fail entirely
        missing_commodities = set(self.commodities) - fetched_commodities
        if missing_commodities:
            placeholder_prices = {
                'gold': {'us': 1900.0, 'india': 173080.0, 'europe': 1800.0},
                'silver': {'us': 24.0, 'india': 2000.0, 'europe': 23.0},
                'crude_oil': {'us': 80.0, 'india': 80.0, 'europe': 80.0},
            }
            for commodity in missing_commodities:
                region_prices = placeholder_prices[commodity]
                for reg in regions:
                    price = region_prices[reg]
                    out.append(
                        LivePriceResponse(
                            commodity=commodity,
                            region=reg,
                            unit=self._unit_for(commodity, reg),
                            currency=REGION_CURRENCY[reg],
                            live_price=price,
                            source='placeholder',
                            timestamp=now,
                        )
                    )

        return out

    async def _fetch_metals_live_rates(self) -> dict[str, float]:
        now = datetime.now(timezone.utc)
        if self._metals_live_cooldown_until and now < self._metals_live_cooldown_until:
            return {}

        try:
            async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "tradesight/1.0"}) as client:
                resp = await client.get("https://api.metals.live/v1/spot")
            resp.raise_for_status()
            raw_data = resp.json()
            rates: dict[str, float] = {}
            for entry in raw_data:
                if isinstance(entry, dict):
                    rates.update(entry)
            self._metals_live_last_error = None
            return rates
        except Exception as exc:
            self._metals_live_last_error = str(exc)
            # Back off this source to avoid repeated TLS/noise; yfinance fallback remains active.
            self._metals_live_cooldown_until = now + timedelta(minutes=10)
            logger.warning("Metals.live API fetch failed: %s (cooldown 10m)", exc)
            return {}

    async def _fetch_yahoo_finance_live_rates(self) -> dict[str, float]:
        rates: dict[str, float] = {}
        # Direct fetch to Yahoo Finance v8 API bypassing yfinance library rate limit blocks
        async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
            for commodity, symbol in COMMODITY_SYMBOLS.items():
                try:
                    resp = await client.get(f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d")
                    resp.raise_for_status()
                    data = resp.json()
                    price = data.get("chart", {}).get("result", [{}])[0].get("meta", {}).get("regularMarketPrice")
                    if price is not None:
                        rates[commodity] = float(price)
                except Exception as exc:
                    logger.warning("Direct YF API fetch failed for %s: %s", commodity, exc)
                    continue
        return rates

    async def historical(self, commodity: str, region: str, period: str = "1y") -> RegionalHistoricalResponse:
        self._validate(commodity)
        region = self._validate_region(region)
        valid_ranges = {"1m", "6m", "1y", "5y", "max"}
        if period not in valid_ranges:
            raise ValueError(f"Invalid range {period!r}. Must be one of {sorted(valid_ranges)}")

        fx = get_fx_rates()
        raw = self.fetcher.get_historical(commodity, period=period, region=region)
        points: list[RegionalHistoricalPoint] = []
        for row in raw.itertuples():
            open_price = self._to_regional_price(float(row.Open), region, fx)
            high_price = self._to_regional_price(float(row.High), region, fx)
            low_price = self._to_regional_price(float(row.Low), region, fx)
            close_price = self._to_regional_price(float(row.Close), region, fx)
            points.append(
                RegionalHistoricalPoint(
                    date=row.Date.date() if hasattr(row.Date, "date") else row.Date,
                    open=round(open_price, 4),
                    high=round(high_price, 4),
                    low=round(low_price, 4),
                    close=round(close_price, 4),
                    volume=float(row.Volume) if row.Volume is not None else None,
                )
            )
        return RegionalHistoricalResponse(
            commodity=commodity,
            region=region,
            currency=REGION_CURRENCY[region],
            unit=self._unit_for(commodity, region),
            rows=len(points),
            data=points,
        )

    async def train(
        self, session: AsyncSession, commodity: str, region: str, horizon: int = 1
    ) -> TrainResponse:
        self._validate(commodity)
        region = self._validate_region(region)
        status_key = (commodity, region)
        self._training_status[status_key] = {"status": "processing", "message": "Training started..."}

        try:
            raw = self.fetcher.get_historical(commodity, region=region)
            feat = self._enrich_features(raw, region)
            if len(feat) < self.settings.min_training_rows:
                raise TrainingError("Not enough data points to train")

            x, y = make_supervised(feat, horizon=horizon)
            from ml.training.models import benchmark_models

            ranked = benchmark_models(x, y)
            if not ranked:
                raise TrainingError("No model could be trained")
            best = ranked[0]
            wf_rmse, wf_mape = self._walk_forward_score(x, y)

            ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            version = f"{best.name}_{region}_{ts}"
            artifact = Path(self.settings.artifact_dir) / commodity / region / f"{version}.joblib"
            save_model(
                artifact,
                best.model,
                {
                    "rmse": wf_rmse,
                    "mape": wf_mape,
                    "horizon": horizon,
                    "commodity": commodity,
                    "region": region,
                    "version": version,
                    "model_name": best.name,
                },
            )
            if not artifact.exists():
                raise TrainingError(f"Model artifact not found after save: {artifact}")

            run = TrainingRun(
                commodity=commodity,
                region=region,
                model_name=best.name,
                model_version=version,
                rmse=wf_rmse,
                mape=wf_mape,
                artifact_path=str(artifact),
            )
            session.add(run)
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                msg = str(exc.orig).lower() if exc.orig else str(exc).lower()
                if "model_version" in msg and "unique" in msg:
                    raise TrainingError("Duplicate model_version detected; retry training") from exc
                raise TrainingError("Training metadata insert failed (integrity error)") from exc
            except SQLAlchemyError as exc:
                await session.rollback()
                raise TrainingError("Training metadata insert failed (database error)") from exc
                
            response = TrainResponse(
                commodity=commodity,
                region=region,
                best_model=best.name,
                model_version=version,
                rmse=wf_rmse,
                mape=wf_mape,
            )
            
            self._training_status[status_key] = {
                "status": "completed", 
                "message": f"Successfully trained {best.name}", 
                "result": response.model_dump()
            }
            return response
            
        except Exception as e:
            self._training_status[status_key] = {"status": "failed", "message": str(e)}
            raise e

    def get_training_status(self, commodity: str, region: str) -> dict:
        self._validate(commodity)
        region = self._validate_region(region)
        return self._training_status.get((commodity, region)) or {"status": "none", "message": "No recent training run found."}

    async def latest_metrics(self, session: AsyncSession, commodity: str, region: str) -> TrainingRun | None:
        self._validate(commodity)
        region = self._validate_region(region)
        result = await session.execute(
            select(TrainingRun)
            .where(TrainingRun.commodity == commodity)
            .where(TrainingRun.region == region)
            .order_by(TrainingRun.trained_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def prewarm_latest_models(self, session: AsyncSession) -> None:
        for commodity in self.commodities:
            for region in self.regions:
                try:
                    metrics = await self.latest_metrics(session, commodity, region=region)
                    if not metrics:
                        continue
                    model, metadata = load_model(Path(metrics.artifact_path))
                    self._model_cache[(commodity, region)] = (model, metadata)
                except Exception:
                    continue

    async def predict(
        self, session: AsyncSession, commodity: str, region: str, horizon: int = 1
    ) -> RegionalPredictionResponse:
        self._validate(commodity)
        region = self._validate_region(region)
        requested_horizon = max(1, int(horizon))
        cache_key = (commodity, region, requested_horizon)
        cached = self._prediction_cache.get(cache_key)
        now = datetime.now(timezone.utc)
        if cached and (now - cached[0]).total_seconds() <= 20:
            return cached[1]
        try:
            metrics = await self.latest_metrics(session, commodity, region=region)
            if not metrics:
                raise TrainingError("No trained model metadata available yet")

            model_cache_key = (commodity, region)
            cached_model = self._model_cache.get(model_cache_key)
            if cached_model and str(cached_model[1].get("version", "")) == metrics.model_version:
                model, metadata = cached_model
            else:
                model, metadata = load_model(Path(metrics.artifact_path))
                self._model_cache[model_cache_key] = (model, metadata)
            trained_horizon = int(metadata.get("horizon", requested_horizon))

            raw = self.fetcher.get_historical(commodity, region=region)
            fx = get_fx_rates()
            feat = self._enrich_features(raw, region, fx=fx)
            model_name = str(metadata.get("model_name", "")).lower()
            if model_name == "chronos_bolt" and hasattr(model, "predict_from_series"):
                close_series = raw["Close"].dropna().astype(float)
                if close_series.empty:
                    raise TrainingError("Not enough data points to generate Chronos prediction")
                # Use requested API horizon for Chronos multi-step forecasting.
                chronos_forecast = model.predict_from_series(close_series, prediction_length=max(1, horizon))
                base_usd_oz = float(np.asarray(chronos_forecast).reshape(-1)[-1])
            else:
                x, _ = make_supervised(feat, horizon=max(1, metadata.get("horizon", horizon)))
                if x.empty:
                    raise TrainingError("Not enough data points to generate prediction features")
                latest_features = x.tail(1)
                base_usd_oz = float(model.predict(latest_features)[0])
                if trained_horizon != requested_horizon:
                    # Fast horizon adaptation to avoid slow retraining during UI horizon toggles.
                    latest_close = float(raw["Close"].iloc[-1])
                    trained_ret = (base_usd_oz - latest_close) / max(1e-9, latest_close)
                    scaled_ret = float(np.clip(trained_ret * (requested_horizon / max(1, trained_horizon)), -0.35, 0.35))
                    base_usd_oz = latest_close * (1.0 + scaled_ret)
            point_forecast = self._to_regional_price(base_usd_oz, region, fx)

            horizon_scale = math.sqrt(max(1, requested_horizon) / max(1, trained_horizon))
            spread_usd_oz = max(0.01 * abs(base_usd_oz), float(metrics.rmse) * horizon_scale)
            low = self._to_regional_price(base_usd_oz - spread_usd_oz, region, fx)
            high = self._to_regional_price(base_usd_oz + spread_usd_oz, region, fx)
            scenarios = {
                "bull": round(point_forecast * 1.06, 4),
                "base": round(point_forecast, 4),
                "bear": round(point_forecast * 0.94, 4),
            }
            response = RegionalPredictionResponse(
                commodity=commodity,
                region=region,
                unit=self._unit_for(commodity, region),
                currency=REGION_CURRENCY[region],
                forecast_horizon=(datetime.now(timezone.utc) + timedelta(days=horizon)).date(),
                point_forecast=round(point_forecast, 4),
                confidence_interval=(round(low, 4), round(high, 4)),
                scenario="base",
                scenario_forecasts=scenarios,
                model_used=(
                    metrics.model_version
                    if trained_horizon == requested_horizon
                    else f"{metrics.model_version}@h{trained_horizon}->h{requested_horizon}"
                ),
            )
            self._prediction_cache[cache_key] = (now, response)
            return response
        except Exception as exc:
            # Keep dashboard/predictions available even if model training/artifacts fail.
            logger.warning(
                "prediction_fallback commodity=%s region=%s reason=%s",
                commodity,
                region,
                str(exc),
            )
            raw = self.fetcher.get_historical(commodity, region=region)
            if raw.empty:
                raise TrainingError("No market data available for fallback prediction") from exc

            fx = get_fx_rates()
            latest_usd_oz = float(raw["Close"].iloc[-1])
            point_forecast = self._to_regional_price(latest_usd_oz, region, fx)
            vol = float(raw["Close"].pct_change().tail(30).std() or 0.01)
            spread = max(abs(point_forecast) * max(0.01, vol), abs(point_forecast) * 0.01)
            low = max(0.0, point_forecast - spread)
            high = point_forecast + spread
            scenarios = {
                "bull": round(point_forecast * 1.04, 4),
                "base": round(point_forecast, 4),
                "bear": round(point_forecast * 0.96, 4),
            }
            response = RegionalPredictionResponse(
                commodity=commodity,
                region=region,
                unit=self._unit_for(commodity, region),
                currency=REGION_CURRENCY[region],
                forecast_horizon=(datetime.now(timezone.utc) + timedelta(days=horizon)).date(),
                point_forecast=round(point_forecast, 4),
                confidence_interval=(round(low, 4), round(high, 4)),
                scenario="base",
                scenario_forecasts=scenarios,
                model_used="naive_fallback_v1",
            )
            self._prediction_cache[cache_key] = (now, response)
            return response
