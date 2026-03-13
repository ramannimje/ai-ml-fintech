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
        current_spot_usd_oz: float,
        spot_timestamp: datetime,
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
                raw=raw,
                feat=feat,
                base_usd_oz=base_usd_oz,
                current_spot_usd_oz=current_spot_usd_oz,
                spot_timestamp=spot_timestamp,
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
                current_spot_usd_oz=current_spot_usd_oz,
                spot_timestamp=spot_timestamp,
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
        raw: pd.DataFrame,
        feat: pd.DataFrame,
        base_usd_oz: float,
        current_spot_usd_oz: float,
        spot_timestamp: datetime,
        fx_rates: dict[str, float],
        unit: str,
        currency: str,
        to_regional_price: Callable[[float, str, dict[str, float]], float],
    ) -> RegionalPredictionResponse:
        capped_return, volatility_scale = self._calibrate_base_return(
            commodity=commodity,
            raw=raw,
            feat=feat,
            spot_usd_oz=current_spot_usd_oz,
            raw_model_usd_oz=base_usd_oz,
            horizon_days=requested_horizon,
            trained_horizon=trained_horizon,
        )
        calibrated_usd_oz = current_spot_usd_oz * (1.0 + capped_return)
        low_usd_oz, high_usd_oz = self._build_spot_anchored_ci(
            raw=raw,
            spot_usd_oz=current_spot_usd_oz,
            point_usd_oz=calibrated_usd_oz,
            horizon_days=requested_horizon,
            rmse=float(metrics.rmse),
            volatility_scale=volatility_scale,
        )
        point_forecast = to_regional_price(calibrated_usd_oz, region, fx_rates)
        current_spot_price = to_regional_price(current_spot_usd_oz, region, fx_rates)
        low = to_regional_price(low_usd_oz, region, fx_rates)
        high = to_regional_price(high_usd_oz, region, fx_rates)
        stress_width = max(abs(capped_return) + max(0.04, volatility_scale * 1.5), 0.06)
        scenarios = {
            "bull": round(current_spot_price * (1.0 + min(0.25, stress_width)), 4),
            "base": round(point_forecast, 4),
            "bear": round(current_spot_price * (1.0 - min(0.25, stress_width)), 4),
        }
        return RegionalPredictionResponse(
            commodity=commodity,
            region=region,
            unit=unit,
            currency=currency,
            forecast_horizon=(datetime.now(timezone.utc) + timedelta(days=requested_horizon)).date(),
            current_spot_price=round(current_spot_price, 4),
            spot_timestamp=spot_timestamp,
            point_forecast=round(point_forecast, 4),
            forecast_vs_spot_pct=round(((point_forecast / max(current_spot_price, 1e-9)) - 1.0) * 100.0, 4),
            confidence_interval=(round(low, 4), round(high, 4)),
            confidence_method="spot_anchored_volatility_90",
            scenario="base",
            scenario_forecasts=scenarios,
            forecast_basis_label=f"{requested_horizon}D base scenario (spot-anchored consensus)",
            macro_sensitivity_tags=self._derive_macro_tags(commodity=commodity, feat=feat),
            last_calibrated_at=metrics.trained_at,
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
        current_spot_usd_oz: float,
        spot_timestamp: datetime,
        cause: Exception,
    ) -> RegionalPredictionResponse:
        if raw.empty:
            raise TrainingError("No market data available for fallback prediction") from cause

        capped_return, volatility_scale = self._calibrate_base_return(
            commodity=commodity,
            raw=raw,
            feat=pd.DataFrame(),
            spot_usd_oz=current_spot_usd_oz,
            raw_model_usd_oz=float(raw["Close"].iloc[-1]),
            horizon_days=horizon,
            trained_horizon=horizon,
        )
        point_usd_oz = current_spot_usd_oz * (1.0 + capped_return)
        low_usd_oz, high_usd_oz = self._build_spot_anchored_ci(
            raw=raw,
            spot_usd_oz=current_spot_usd_oz,
            point_usd_oz=point_usd_oz,
            horizon_days=horizon,
            rmse=0.0,
            volatility_scale=volatility_scale,
        )
        point_forecast = to_regional_price(point_usd_oz, region, fx_rates)
        current_spot_price = to_regional_price(current_spot_usd_oz, region, fx_rates)
        low = to_regional_price(low_usd_oz, region, fx_rates)
        high = to_regional_price(high_usd_oz, region, fx_rates)
        stress_width = max(abs(capped_return) + max(0.04, volatility_scale * 1.5), 0.06)
        scenarios = {
            "bull": round(current_spot_price * (1.0 + min(0.25, stress_width)), 4),
            "base": round(point_forecast, 4),
            "bear": round(current_spot_price * (1.0 - min(0.25, stress_width)), 4),
        }
        return RegionalPredictionResponse(
            commodity=commodity,
            region=region,
            unit=unit,
            currency=currency,
            forecast_horizon=(datetime.now(timezone.utc) + timedelta(days=horizon)).date(),
            current_spot_price=round(current_spot_price, 4),
            spot_timestamp=spot_timestamp,
            point_forecast=round(point_forecast, 4),
            forecast_vs_spot_pct=round(((point_forecast / max(current_spot_price, 1e-9)) - 1.0) * 100.0, 4),
            confidence_interval=(round(low, 4), round(high, 4)),
            confidence_method="spot_anchored_volatility_90",
            scenario="base",
            scenario_forecasts=scenarios,
            forecast_basis_label=f"{horizon}D base scenario (spot-anchored consensus)",
            macro_sensitivity_tags=self._derive_macro_tags(commodity=commodity, feat=pd.DataFrame()),
            last_calibrated_at=None,
            model_used="naive_fallback_v1",
        )

    @staticmethod
    def _rolling_atr_pct(raw: pd.DataFrame, window: int = 30) -> float:
        if raw.empty:
            return 0.0
        high = raw["High"].astype(float)
        low = raw["Low"].astype(float)
        close = raw["Close"].astype(float)
        prev_close = close.shift(1).fillna(close)
        tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
        atr = float(tr.tail(window).mean() or 0.0)
        latest_close = max(float(close.iloc[-1]), 1e-9)
        return max(0.0, atr / latest_close)

    def _calibrate_base_return(
        self,
        *,
        commodity: str,
        raw: pd.DataFrame,
        feat: pd.DataFrame,
        spot_usd_oz: float,
        raw_model_usd_oz: float,
        horizon_days: int,
        trained_horizon: int,
    ) -> tuple[float, float]:
        closes = raw["Close"].astype(float)
        returns = closes.pct_change().dropna()
        realized_vol = float(returns.tail(30).std() or 0.0)
        atr_pct = self._rolling_atr_pct(raw, window=30)
        horizon_scale = math.sqrt(max(1, horizon_days) / max(1, trained_horizon))
        vol_scale = max(realized_vol * math.sqrt(max(1, horizon_days)), atr_pct * math.sqrt(max(1, horizon_days)), 0.01)
        base_cap = min(0.15, max(0.03, 1.645 * vol_scale))

        ret_5d = float((closes.iloc[-1] / closes.iloc[-6]) - 1.0) if len(closes) >= 6 and closes.iloc[-6] else 0.0
        ret_20d = float((closes.iloc[-1] / closes.iloc[-21]) - 1.0) if len(closes) >= 21 and closes.iloc[-21] else 0.0
        rolling_mean_20 = float(closes.tail(20).mean() or closes.iloc[-1])
        mean_reversion = (rolling_mean_20 - spot_usd_oz) / max(spot_usd_oz, 1e-9)
        raw_model_return = ((raw_model_usd_oz - spot_usd_oz) / max(spot_usd_oz, 1e-9)) * horizon_scale
        momentum_bias = (ret_5d * 0.55) + (ret_20d * 0.45)
        macro_bias = self._macro_bias_return(commodity=commodity, feat=feat)
        calibrated_return = (raw_model_return * 0.40) + (momentum_bias * 0.30) + (mean_reversion * 0.15) + (macro_bias * 0.15)

        if math.copysign(1.0, raw_model_return or 1.0) != math.copysign(1.0, momentum_bias or 1.0):
            if abs(momentum_bias) >= 0.01 and abs(raw_model_return) >= 0.02:
                aligned_magnitude = max(min(abs(momentum_bias), base_cap), 0.005)
                calibrated_return = math.copysign(aligned_magnitude, momentum_bias)

        if commodity in {"gold", "silver"} and macro_bias > 0.01 and calibrated_return < 0.0:
            calibrated_return = max(calibrated_return, -min(0.04, base_cap * 0.5))
        if commodity in {"gold", "silver"} and macro_bias < -0.01 and calibrated_return > 0.0:
            calibrated_return = min(calibrated_return, min(0.04, base_cap * 0.5))

        return float(np.clip(calibrated_return, -base_cap, base_cap)), base_cap

    def _build_spot_anchored_ci(
        self,
        *,
        raw: pd.DataFrame,
        spot_usd_oz: float,
        point_usd_oz: float,
        horizon_days: int,
        rmse: float,
        volatility_scale: float,
    ) -> tuple[float, float]:
        returns = raw["Close"].astype(float).pct_change().dropna()
        sigma = float(returns.tail(30).std() or 0.0)
        atr_pct = self._rolling_atr_pct(raw, window=30)
        horizon_vol = max(sigma * math.sqrt(max(1, horizon_days)), atr_pct * math.sqrt(max(1, horizon_days)), 0.008)
        half_width = max(
            spot_usd_oz * 1.645 * horizon_vol,
            abs(point_usd_oz - spot_usd_oz) + max(rmse * 0.35, spot_usd_oz * volatility_scale * 0.15),
            spot_usd_oz * 0.005,
        )
        low = max(0.0, spot_usd_oz - half_width)
        high = spot_usd_oz + half_width
        if not low < spot_usd_oz < high:
            epsilon = max(spot_usd_oz * 0.001, 0.01)
            low = max(0.0, spot_usd_oz - epsilon)
            high = spot_usd_oz + epsilon
        low, high = self._apply_base_ci_bounds(
            spot_usd_oz=spot_usd_oz,
            low_usd_oz=low,
            high_usd_oz=high,
            horizon_days=horizon_days,
        )
        return low, high

    @staticmethod
    def _apply_base_ci_bounds(
        *,
        spot_usd_oz: float,
        low_usd_oz: float,
        high_usd_oz: float,
        horizon_days: int,
    ) -> tuple[float, float]:
        if horizon_days >= 30 and horizon_days < 90:
            floor_ratio, cap_ratio = 0.70, 1.30
        elif horizon_days >= 90:
            floor_ratio, cap_ratio = 0.60, 1.40
        elif horizon_days >= 7:
            floor_ratio, cap_ratio = 0.85, 1.15
        else:
            floor_ratio, cap_ratio = 0.93, 1.07

        bounded_low = max(low_usd_oz, spot_usd_oz * floor_ratio)
        bounded_high = min(high_usd_oz, spot_usd_oz * cap_ratio)
        if bounded_low >= spot_usd_oz:
            bounded_low = max(0.0, spot_usd_oz * (1.0 - max(0.01, 1.0 - floor_ratio)))
        if bounded_high <= spot_usd_oz:
            bounded_high = spot_usd_oz * (1.0 + max(0.01, cap_ratio - 1.0))
        return bounded_low, bounded_high

    @staticmethod
    def _macro_bias_return(*, commodity: str, feat: pd.DataFrame) -> float:
        if feat.empty:
            return 0.0

        latest = feat.iloc[-1]
        dxy = pd.to_numeric(latest.get("dxy"), errors="coerce")
        dxy_avg = pd.to_numeric(feat["dxy"].tail(20), errors="coerce").mean() if "dxy" in feat else np.nan
        treasury = pd.to_numeric(latest.get("treasury_10y"), errors="coerce")
        treasury_avg = pd.to_numeric(feat["treasury_10y"].tail(20), errors="coerce").mean() if "treasury_10y" in feat else np.nan
        momentum_20 = 0.0
        if "Close" in feat and len(feat["Close"]) >= 21 and float(feat["Close"].iloc[-21]) != 0.0:
            momentum_20 = float((float(feat["Close"].iloc[-1]) / float(feat["Close"].iloc[-21])) - 1.0)

        bias = 0.0
        if commodity in {"gold", "silver"}:
            if not np.isnan(dxy) and (np.isnan(dxy_avg) or dxy <= dxy_avg):
                bias += 0.018
            elif not np.isnan(dxy):
                bias -= 0.018
            if not np.isnan(treasury) and (np.isnan(treasury_avg) or treasury <= treasury_avg):
                bias += 0.018
            elif not np.isnan(treasury):
                bias -= 0.018
            if commodity == "silver":
                bias += -0.010 if momentum_20 < 0.0 else 0.006
        elif commodity == "crude_oil":
            bias += 0.015 if momentum_20 > 0.0 else -0.015

        return float(np.clip(bias, -0.04, 0.04))

    @staticmethod
    def _derive_macro_tags(*, commodity: str, feat: pd.DataFrame) -> list[str]:
        tags: list[str] = []
        latest = feat.iloc[-1] if not feat.empty else pd.Series(dtype=float)
        dxy = pd.to_numeric(latest.get("dxy"), errors="coerce")
        dxy_avg = pd.to_numeric(feat["dxy"].tail(10), errors="coerce").mean() if "dxy" in feat else np.nan
        treasury = pd.to_numeric(latest.get("treasury_10y"), errors="coerce")
        treasury_avg = pd.to_numeric(feat["treasury_10y"].tail(10), errors="coerce").mean() if "treasury_10y" in feat else np.nan
        if "Close" in feat and len(feat["Close"]) >= 21 and float(feat["Close"].iloc[-21]) != 0.0:
            momentum = float((float(feat["Close"].iloc[-1]) / float(feat["Close"].iloc[-21])) - 1.0)
        else:
            momentum = np.nan
        if not np.isnan(dxy):
            tags.append("DXY ↓" if np.isnan(dxy_avg) or dxy <= dxy_avg else "DXY ↑")
        if not np.isnan(treasury):
            tags.append("Fed Hold" if np.isnan(treasury_avg) or abs(treasury - treasury_avg) < 0.05 else ("Yields ↓" if treasury < treasury_avg else "Yields ↑"))
        if commodity == "crude_oil":
            tags.append("Demand Firm" if np.isnan(momentum) or momentum >= 0 else "Demand Soft")
        elif commodity == "silver":
            tags.append("Industrial Bid" if np.isnan(momentum) or momentum >= 0 else "Industrial Drag")
        else:
            tags.append("Risk-Off" if np.isnan(momentum) or momentum >= 0 else "Risk-On")
        return tags[:3]
