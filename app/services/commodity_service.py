from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import logging
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
REGION_UNITS = {
    "india": "10g_24k",
    "us": "oz",
    "europe": "exchange_standard",
}
PRIMARY_SOURCE_BY_COMMODITY = {
    "gold": "comex",
    "silver": "comex",
    "crude_oil": "comex",
}
logger = logging.getLogger(__name__)


class CommodityService:
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

    def _to_regional_price(self, usd_per_troy_oz: float, region: str, fx: dict[str, float]) -> float:
        return convert_price(troy_oz_to_grams(usd_per_troy_oz), region, fx)

    def _enrich_features(self, raw: pd.DataFrame, region: str) -> pd.DataFrame:
        feat = add_features(raw)
        fx = get_fx_rates()
        inr = fx.get("INR")
        eur = fx.get("EUR")
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
        regions = [self._validate_region(region)] if region else self.regions
        fx = get_fx_rates()
        now = datetime.now(timezone.utc)
        out: list[LivePriceResponse] = []

        for commodity in self.commodities:
            try:
                raw = self.fetcher.get_historical(commodity, period="1mo")
                if raw.empty:
                    raise TrainingError(f"No market data available for {commodity}")
                latest = float(raw["Close"].iloc[-1])
                source = f"{PRIMARY_SOURCE_BY_COMMODITY.get(commodity, 'yahoo_finance')}/yahoo_finance"

                for reg in regions:
                    price = self._to_regional_price(latest, reg, fx)
                    out.append(
                        LivePriceResponse(
                            commodity=commodity,
                            region=reg,
                            unit=REGION_UNITS[reg],
                            currency=REGION_CURRENCY[reg],
                            live_price=round(price, 4),
                            source=source,
                            timestamp=now,
                        )
                    )
            except Exception as exc:
                logger.error(
                    "pricing_failure commodity=%s reason=%s",
                    commodity,
                    str(exc),
                )
                continue
        if not out:
            raise TrainingError("No live prices available from active sources")
        return out

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
            unit=REGION_UNITS[region],
            rows=len(points),
            data=points,
        )

    async def train(
        self, session: AsyncSession, commodity: str, region: str, horizon: int = 1
    ) -> TrainResponse:
        self._validate(commodity)
        region = self._validate_region(region)

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
        return TrainResponse(
            commodity=commodity,
            region=region,
            best_model=best.name,
            model_version=version,
            rmse=wf_rmse,
            mape=wf_mape,
        )

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

    async def predict(
        self, session: AsyncSession, commodity: str, region: str, horizon: int = 1
    ) -> RegionalPredictionResponse:
        self._validate(commodity)
        region = self._validate_region(region)

        metrics = await self.latest_metrics(session, commodity, region=region)
        if not metrics:
            await self.train(session, commodity, region=region, horizon=horizon)
            metrics = await self.latest_metrics(session, commodity, region=region)
            if not metrics:
                raise TrainingError("Training did not persist metadata")

        model, metadata = load_model(Path(metrics.artifact_path))
        raw = self.fetcher.get_historical(commodity, region=region)
        feat = self._enrich_features(raw, region)
        x, _ = make_supervised(feat, horizon=max(1, metadata.get("horizon", horizon)))
        latest_features = x.tail(1)
        base_usd_oz = float(model.predict(latest_features)[0])
        fx = get_fx_rates()
        point_forecast = self._to_regional_price(base_usd_oz, region, fx)

        spread_usd_oz = max(0.01 * base_usd_oz, float(metrics.rmse))
        low = self._to_regional_price(base_usd_oz - spread_usd_oz, region, fx)
        high = self._to_regional_price(base_usd_oz + spread_usd_oz, region, fx)
        scenarios = {
            "bull": round(point_forecast * 1.06, 4),
            "base": round(point_forecast, 4),
            "bear": round(point_forecast * 0.94, 4),
        }
        return RegionalPredictionResponse(
            commodity=commodity,
            region=region,
            unit=REGION_UNITS[region],
            currency=REGION_CURRENCY[region],
            forecast_horizon=date(2026, 12, 31),
            point_forecast=round(point_forecast, 4),
            confidence_interval=(round(low, 4), round(high, 4)),
            scenario="base",
            scenario_forecasts=scenarios,
            model_used=metrics.model_version,
        )
