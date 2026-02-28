from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from pathlib import Path

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import CommodityNotSupportedError, TrainingError
from app.models.training_run import TrainingRun
from app.schemas.responses import (
    ForecastPoint,
    RegionalComparisonResponse,
    RegionalHistoricalPoint,
    RegionalHistoricalResponse,
    RegionPrice,
    RegionalPredictionResponse,
    TrainResponse,
)
from app.services.fx_cache import get_fx_rates
from app.services.price_conversion import (
    REGION_CURRENCY,
    REGION_UNIT,
    all_regions_price,
    convert_price,
    format_price,
    troy_oz_to_grams,
)
from ml.data.data_fetcher import COMMODITY_SYMBOLS, MarketDataFetcher
from ml.features.engineer import add_features, make_supervised
from ml.inference.artifacts import load_model, save_model

# Long-horizon forecast target dates
FORECAST_DATES = [
    date(2026, 6, 1),
    date(2027, 1, 1),
    date(2028, 1, 1),
]


class CommodityService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.fetcher = MarketDataFetcher(cache_dir=self.settings.data_cache_dir)

    @property
    def commodities(self) -> list[str]:
        return sorted(COMMODITY_SYMBOLS.keys())

    def _validate(self, commodity: str) -> None:
        if commodity not in COMMODITY_SYMBOLS:
            raise CommodityNotSupportedError(f"Unsupported commodity: {commodity}")

    def _validate_region(self, region: str) -> str:
        region = region.lower()
        if region not in self.settings.supported_regions:
            raise ValueError(
                f"Unsupported region: {region!r}. Must be one of: {self.settings.supported_regions}"
            )
        return region

    async def historical(
        self,
        commodity: str,
        region: str = "us",
        period: str = "5y",
    ) -> RegionalHistoricalResponse:
        self._validate(commodity)
        region = self._validate_region(region)

        raw = self.fetcher.get_historical(commodity, period=period)
        fx = get_fx_rates()

        points: list[RegionalHistoricalPoint] = []
        for row in raw.itertuples():
            # yfinance COMEX prices are in USD per troy ounce → convert to USD/gram
            close_usd_gram = troy_oz_to_grams(float(row.Close))
            regional_close = convert_price(close_usd_gram, region, fx)

            open_val = None
            high_val = None
            low_val = None
            if hasattr(row, "Open") and row.Open is not None:
                open_val = convert_price(troy_oz_to_grams(float(row.Open)), region, fx)
            if hasattr(row, "High") and row.High is not None:
                high_val = convert_price(troy_oz_to_grams(float(row.High)), region, fx)
            if hasattr(row, "Low") and row.Low is not None:
                low_val = convert_price(troy_oz_to_grams(float(row.Low)), region, fx)

            vol = float(row.Volume) if hasattr(row, "Volume") and row.Volume is not None else None

            points.append(
                RegionalHistoricalPoint(
                    date=row.Date.date() if hasattr(row.Date, "date") else row.Date,
                    close=round(regional_close, 2),
                    open=round(open_val, 2) if open_val is not None else None,
                    high=round(high_val, 2) if high_val is not None else None,
                    low=round(low_val, 2) if low_val is not None else None,
                    volume=vol,
                )
            )

        return RegionalHistoricalResponse(
            commodity=commodity,
            region=region,
            currency=REGION_CURRENCY[region],
            unit=REGION_UNIT[region],
            rows=len(points),
            data=points,
        )

    async def train(
        self,
        session: AsyncSession,
        commodity: str,
        horizon: int = 1,
        region: str = "us",
    ) -> TrainResponse:
        self._validate(commodity)
        region = self._validate_region(region)

        raw = self.fetcher.get_historical(commodity)
        feat = add_features(raw)
        if len(feat) < self.settings.min_training_rows:
            raise TrainingError("Not enough data points to train")

        x, y = make_supervised(feat, horizon=horizon)
        from ml.training.models import benchmark_models
        ranked = benchmark_models(x, y)
        if not ranked:
            raise TrainingError("No model could be trained")

        best = ranked[0]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        version = f"{best.name}_{region}_{ts}"
        artifact = Path(self.settings.artifact_dir) / commodity / region / f"{version}.joblib"
        save_model(
            artifact,
            best.model,
            {
                "rmse": best.rmse,
                "mape": best.mape,
                "horizon": horizon,
                "commodity": commodity,
                "region": region,
                "version": version,
                "model_name": best.name,
            },
        )

        run = TrainingRun(
            commodity=commodity,
            region=region,
            model_name=best.name,
            model_version=version,
            rmse=best.rmse,
            mape=best.mape,
            artifact_path=str(artifact),
        )
        session.add(run)
        await session.commit()

        return TrainResponse(
            commodity=commodity,
            best_model=best.name,
            model_version=version,
            rmse=best.rmse,
            mape=best.mape,
        )

    async def latest_metrics(
        self,
        session: AsyncSession,
        commodity: str,
        region: str = "us",
    ) -> TrainingRun | None:
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

    async def predict(
        self,
        session: AsyncSession,
        commodity: str,
        horizon: int = 1,
        region: str = "us",
    ) -> RegionalPredictionResponse:
        self._validate(commodity)
        region = self._validate_region(region)

        metrics = await self.latest_metrics(session, commodity, region=region)
        if not metrics:
            await self.train(session, commodity, horizon=horizon, region=region)
            metrics = await self.latest_metrics(session, commodity, region=region)
            if not metrics:
                raise TrainingError("Training did not persist metadata")

        model, metadata = load_model(Path(metrics.artifact_path))
        raw = self.fetcher.get_historical(commodity)
        feat = add_features(raw)
        x, _ = make_supervised(feat, horizon=max(1, metadata.get("horizon", horizon)))
        latest_features = x.tail(1)

        # Base prediction (USD per troy oz from model)
        base_pred_usd_oz = float(model.predict(latest_features)[0])
        base_pred_usd_gram = troy_oz_to_grams(base_pred_usd_oz)

        fx = get_fx_rates()

        # Build multi-step forecast for long-horizon dates
        # Use the base prediction with simple drift extrapolation
        today = datetime.now(timezone.utc).date()
        forecast_points: list[ForecastPoint] = []

        # Annual drift: use model RMSE as uncertainty proxy, apply small positive drift
        annual_drift_pct = 0.04  # 4% annual appreciation assumption
        for target_date in FORECAST_DATES:
            if target_date <= today:
                continue
            years_ahead = (target_date - today).days / 365.25
            drifted_usd_gram = base_pred_usd_gram * ((1 + annual_drift_pct) ** years_ahead)
            regional_price = convert_price(drifted_usd_gram, region, fx)
            forecast_points.append(
                ForecastPoint(date=target_date, price=round(regional_price, 2))
            )

        # If no future dates (e.g. running after 2028), add horizon-based prediction
        if not forecast_points:
            pred_date = (datetime.now(timezone.utc) + timedelta(days=horizon)).date()
            regional_price = convert_price(base_pred_usd_gram, region, fx)
            forecast_points.append(ForecastPoint(date=pred_date, price=round(regional_price, 2)))

        # Confidence interval: ±RMSE converted to regional units
        spread_usd_gram = max(0.01 * base_pred_usd_gram, troy_oz_to_grams(metadata["rmse"]))
        ci_low = convert_price(base_pred_usd_gram - spread_usd_gram, region, fx)
        ci_high = convert_price(base_pred_usd_gram + spread_usd_gram, region, fx)
        # Confidence interval as ratio (e.g. 0.94, 1.07)
        base_regional = convert_price(base_pred_usd_gram, region, fx)
        ci_ratio_low = round(ci_low / base_regional, 4) if base_regional else 0.94
        ci_ratio_high = round(ci_high / base_regional, 4) if base_regional else 1.07

        return RegionalPredictionResponse(
            commodity=commodity,
            region=region,
            unit=REGION_UNIT[region],
            currency=REGION_CURRENCY[region],
            predictions=forecast_points,
            confidence_interval=(ci_ratio_low, ci_ratio_high),
            model_used=metrics.model_version,
        )

    async def regional_comparison(
        self,
        session: AsyncSession,
        commodity: str,
    ) -> RegionalComparisonResponse:
        """Return current price for a commodity in all 3 regions."""
        self._validate(commodity)

        raw = self.fetcher.get_historical(commodity)
        if raw.empty:
            raise TrainingError("No historical data available")

        # Latest close price in USD/troy oz
        latest_usd_oz = float(raw["Close"].iloc[-1])
        latest_usd_gram = troy_oz_to_grams(latest_usd_oz)
        fx = get_fx_rates()

        all_prices = all_regions_price(latest_usd_gram, fx)
        region_list = [
            RegionPrice(
                region=region,
                currency=info["currency"],
                unit=info["unit"],
                price=round(info["price"], 2),
                formatted=info["formatted"],
            )
            for region, info in all_prices.items()
        ]

        return RegionalComparisonResponse(commodity=commodity, regions=region_list)

    async def retrain_all(
        self,
        session: AsyncSession,
        horizon: int = 1,
        region: str = "us",
    ) -> list[TrainResponse]:
        out = []
        for c in self.commodities:
            out.append(await self.train(session, c, horizon=horizon, region=region))
        return out
