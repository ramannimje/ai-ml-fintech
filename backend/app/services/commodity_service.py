from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.exceptions import CommodityNotSupportedError, TrainingError
from backend.app.models.training_run import TrainingRun
from backend.app.schemas.responses import TrainResponse
from backend.app.services.price_conversion import REGIONS
from backend.ml.data.data_fetcher import COMMODITY_SYMBOLS, MarketDataFetcher
from backend.ml.features.engineer import add_features, add_macro_features, make_supervised
from backend.ml.inference.artifacts import load_model, save_model


class CommodityService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.fetcher = MarketDataFetcher(cache_dir=self.settings.data_cache_dir)

    @property
    def commodities(self) -> list[str]:
        return sorted(COMMODITY_SYMBOLS.keys())

    def _validate(self, commodity: str, region: str) -> None:
        if commodity not in COMMODITY_SYMBOLS:
            raise CommodityNotSupportedError(f"Unsupported commodity: {commodity}")
        if region not in REGIONS:
            raise CommodityNotSupportedError(f"Unsupported region: {region}")

    async def historical(self, commodity: str, region: str, range_period: str = "5y"):
        self._validate(commodity, region)
        return await self.fetcher.get_historical(commodity, region, period=range_period)

    async def train(self, session: AsyncSession, commodity: str, region: str = "us", horizon: int = 1) -> TrainResponse:
        self._validate(commodity, region)
        raw = await self.fetcher.get_historical(commodity, region)
        feat = add_macro_features(add_features(raw))
        if len(feat) < self.settings.min_training_rows:
            raise TrainingError("Not enough data points to train")

        x, y = make_supervised(feat, horizon=horizon)
        from backend.ml.training.models import benchmark_models

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
            {"rmse": best.rmse, "mape": best.mape, "horizon": horizon, "commodity": commodity, "version": version, "model_name": best.name, "region": region},
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

        return TrainResponse(commodity=commodity, region=region, best_model=best.name, model_version=version, rmse=best.rmse, mape=best.mape)

    async def latest_metrics(self, session: AsyncSession, commodity: str, region: str) -> TrainingRun | None:
        self._validate(commodity, region)
        result = await session.execute(
            select(TrainingRun)
            .where(TrainingRun.commodity == commodity, TrainingRun.region == region)
            .order_by(TrainingRun.trained_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def predict(self, session: AsyncSession, commodity: str, region: str = "us", horizon: int = 1):
        self._validate(commodity, region)
        metrics = await self.latest_metrics(session, commodity, region)
        if not metrics:
            await self.train(session, commodity, region=region, horizon=horizon)
            metrics = await self.latest_metrics(session, commodity, region)
            if not metrics:
                raise TrainingError("Training did not persist metadata")

        model, metadata = load_model(Path(metrics.artifact_path))
        raw = await self.fetcher.get_historical(commodity, region)
        feat = add_macro_features(add_features(raw))
        x, _ = make_supervised(feat, horizon=max(1, metadata.get("horizon", horizon)))

        latest_features = x.tail(1)
        pred_base = float(model.predict(latest_features)[0])

        dates = [
            (datetime.now(timezone.utc) + timedelta(days=horizon)).date(),
            datetime(datetime.now(timezone.utc).year + 1, 1, 1, tzinfo=timezone.utc).date(),
            datetime(2028, 1, 1, tzinfo=timezone.utc).date(),
        ]
        predictions = [{"date": d.isoformat(), "price": round(pred_base * (1 + 0.03 * i), 2)} for i, d in enumerate(dates)]

        return {
            "commodity": commodity,
            "region": region,
            "unit": REGIONS[region]["unit"],
            "currency": REGIONS[region]["currency"],
            "predictions": predictions,
            "confidence_interval": [0.94, 1.07],
            "model_used": metrics.model_version,
            "model_accuracy_rmse": metrics.rmse,
            "horizon_days": horizon,
        }

    async def retrain_all(self, session: AsyncSession, region: str = "us", horizon: int = 1) -> list[TrainResponse]:
        out = []
        for c in self.commodities:
            out.append(await self.train(session, c, region=region, horizon=horizon))
        return out
