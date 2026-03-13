from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import math
from typing import Callable

import numpy as np
import pandas as pd

from app.core.exceptions import TrainingError
from app.models.training_run import TrainingRun
from app.schemas.market_data import NormalizedHistoricalSeries
from app.schemas.responses import RegionalPredictionResponse
from app.services.feature_store_service import FeatureStoreService
from app.services.model_registry_service import ModelRegistryService

logger = logging.getLogger(__name__)


class ForecastService:
    _prediction_cache: dict[tuple[str, str, int], tuple[datetime, RegionalPredictionResponse]] = {}

    def __init__(self, model_registry_service: ModelRegistryService) -> None:
        self.model_registry_service = model_registry_service

    async def generate_prediction(
        self,
        *,
        session,
        commodity: str,
        region: str,
        horizon: int,
        series: NormalizedHistoricalSeries,
        feature_store_service: FeatureStoreService,
        fx_rates: dict[str, float],
        unit: str,
        currency: str,
        to_regional_price: Callable[[float, str, dict[str, float]], float],
        latest_metrics_loader,
    ) -> RegionalPredictionResponse:
        requested_horizon = max(1, int(horizon))
        cache_key = (commodity, region, requested_horizon)
        now = datetime.now(timezone.utc)
        cached = self._prediction_cache.get(cache_key)
        if cached and (now - cached[0]).total_seconds() <= 20:
            return cached[1]

        raw = self._series_to_frame(series)

        try:
            metrics = await latest_metrics_loader(session, commodity, region)
            if not metrics:
                raise TrainingError("No trained model metadata available yet")

            model, metadata = self.model_registry_service.load_model_bundle(metrics)
            trained_horizon = int(metadata.get("horizon", requested_horizon))
            feat = await feature_store_service.materialize_online_features_for_session(
                session,
                commodity=commodity,
                series=series,
                region=region,
                period="1y",
                fx=fx_rates,
            )
            base_usd_oz = self._predict_base_usd_oz(
                model=model,
                metadata=metadata,
                raw=raw,
                feat=feat,
                requested_horizon=requested_horizon,
                fallback_horizon=horizon,
            )
            response = self._build_model_response(
                commodity=commodity,
                region=region,
                requested_horizon=requested_horizon,
                metrics=metrics,
                trained_horizon=trained_horizon,
                base_usd_oz=base_usd_oz,
                fx_rates=fx_rates,
                unit=unit,
                currency=currency,
                to_regional_price=to_regional_price,
            )
        except Exception as exc:
            logger.warning(
                "prediction_fallback commodity=%s region=%s reason=%s",
                commodity,
                region,
                str(exc),
            )
            response = self._build_fallback_response(
                commodity=commodity,
                region=region,
                horizon=horizon,
                raw=raw,
                fx_rates=fx_rates,
                unit=unit,
                currency=currency,
                to_regional_price=to_regional_price,
                cause=exc,
            )

        self._prediction_cache[cache_key] = (now, response)
        return response

    @staticmethod
    def _series_to_frame(series: NormalizedHistoricalSeries) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "Date": pd.Timestamp(bar.date),
                    "Open": bar.open_usd_per_troy_oz,
                    "High": bar.high_usd_per_troy_oz,
                    "Low": bar.low_usd_per_troy_oz,
                    "Close": bar.close_usd_per_troy_oz,
                    "Volume": bar.volume,
                }
                for bar in series.bars
            ]
        )

    @staticmethod
    def _predict_base_usd_oz(
        *,
        model,
        metadata: dict,
        raw: pd.DataFrame,
        feat: pd.DataFrame,
        requested_horizon: int,
        fallback_horizon: int,
    ) -> float:
        model_name = str(metadata.get("model_name", "")).lower()
        trained_horizon = int(metadata.get("horizon", requested_horizon))
        if model_name == "chronos_bolt" and hasattr(model, "predict_from_series"):
            close_series = raw["Close"].dropna().astype(float)
            if close_series.empty:
                raise TrainingError("Not enough data points to generate Chronos prediction")
            chronos_forecast = model.predict_from_series(close_series, prediction_length=max(1, fallback_horizon))
            return float(np.asarray(chronos_forecast).reshape(-1)[-1])

        from ml.features.engineer import make_supervised

        x, _ = make_supervised(feat, horizon=max(1, trained_horizon))
        if x.empty:
            raise TrainingError("Not enough data points to generate prediction features")
        latest_features = x.tail(1)
        base_usd_oz = float(model.predict(latest_features)[0])
        if trained_horizon != requested_horizon:
            latest_close = float(raw["Close"].iloc[-1])
            trained_ret = (base_usd_oz - latest_close) / max(1e-9, latest_close)
            scaled_ret = float(np.clip(trained_ret * (requested_horizon / max(1, trained_horizon)), -0.35, 0.35))
            base_usd_oz = latest_close * (1.0 + scaled_ret)
        return base_usd_oz

    def _build_model_response(
        self,
        *,
        commodity: str,
        region: str,
        requested_horizon: int,
        metrics: TrainingRun,
        trained_horizon: int,
        base_usd_oz: float,
        fx_rates: dict[str, float],
        unit: str,
        currency: str,
        to_regional_price: Callable[[float, str, dict[str, float]], float],
    ) -> RegionalPredictionResponse:
        point_forecast = to_regional_price(base_usd_oz, region, fx_rates)
        horizon_scale = math.sqrt(max(1, requested_horizon) / max(1, trained_horizon))
        spread_usd_oz = max(0.01 * abs(base_usd_oz), float(metrics.rmse) * horizon_scale)
        low = to_regional_price(base_usd_oz - spread_usd_oz, region, fx_rates)
        high = to_regional_price(base_usd_oz + spread_usd_oz, region, fx_rates)
        scenarios = {
            "bull": round(point_forecast * 1.06, 4),
            "base": round(point_forecast, 4),
            "bear": round(point_forecast * 0.94, 4),
        }
        return RegionalPredictionResponse(
            commodity=commodity,
            region=region,
            unit=unit,
            currency=currency,
            forecast_horizon=(datetime.now(timezone.utc) + timedelta(days=requested_horizon)).date(),
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

    def _build_fallback_response(
        self,
        *,
        commodity: str,
        region: str,
        horizon: int,
        raw: pd.DataFrame,
        fx_rates: dict[str, float],
        unit: str,
        currency: str,
        to_regional_price: Callable[[float, str, dict[str, float]], float],
        cause: Exception,
    ) -> RegionalPredictionResponse:
        if raw.empty:
            raise TrainingError("No market data available for fallback prediction") from cause

        latest_usd_oz = float(raw["Close"].iloc[-1])
        point_forecast = to_regional_price(latest_usd_oz, region, fx_rates)
        vol = float(raw["Close"].pct_change().tail(30).std() or 0.01)
        spread = max(abs(point_forecast) * max(0.01, vol), abs(point_forecast) * 0.01)
        low = max(0.0, point_forecast - spread)
        high = point_forecast + spread
        scenarios = {
            "bull": round(point_forecast * 1.04, 4),
            "base": round(point_forecast, 4),
            "bear": round(point_forecast * 0.96, 4),
        }
        return RegionalPredictionResponse(
            commodity=commodity,
            region=region,
            unit=unit,
            currency=currency,
            forecast_horizon=(datetime.now(timezone.utc) + timedelta(days=horizon)).date(),
            point_forecast=round(point_forecast, 4),
            confidence_interval=(round(low, 4), round(high, 4)),
            scenario="base",
            scenario_forecasts=scenarios,
            model_used="naive_fallback_v1",
        )
