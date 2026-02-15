from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.exceptions import CommodityNotSupportedError, TrainingError
from backend.app.models.training_run import TrainingRun
from backend.app.schemas.responses import TrainResponse
from backend.ml.data.data_fetcher import COMMODITY_SYMBOLS, MarketDataFetcher
from backend.ml.features.engineer import add_features, make_supervised
from backend.ml.inference.artifacts import load_model, save_model


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

    async def historical(self, commodity: str):
        self._validate(commodity)
        return self.fetcher.get_historical(commodity)

    async def train(self, session: AsyncSession, commodity: str, horizon: int = 1) -> TrainResponse:
        self._validate(commodity)
        raw = self.fetcher.get_historical(commodity)
        feat = add_features(raw)
        if len(feat) < self.settings.min_training_rows:
            raise TrainingError("Not enough data points to train")

        x, y = make_supervised(feat, horizon=horizon)
        from backend.ml.training.models import benchmark_models
        ranked = benchmark_models(x, y)
        if not ranked:
            raise TrainingError("No model could be trained")

        best = ranked[0]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        version = f"{best.name}_{ts}"
        artifact = Path(self.settings.artifact_dir) / commodity / f"{version}.joblib"
        save_model(artifact, best.model, {"rmse": best.rmse, "mape": best.mape, "horizon": horizon, "commodity": commodity, "version": version, "model_name": best.name})

        run = TrainingRun(
            commodity=commodity,
            model_name=best.name,
            model_version=version,
            rmse=best.rmse,
            mape=best.mape,
            artifact_path=str(artifact),
        )
        session.add(run)
        await session.commit()

        return TrainResponse(commodity=commodity, best_model=best.name, model_version=version, rmse=best.rmse, mape=best.mape)

    async def latest_metrics(self, session: AsyncSession, commodity: str) -> TrainingRun | None:
        self._validate(commodity)
        result = await session.execute(
            select(TrainingRun)
            .where(TrainingRun.commodity == commodity)
            .order_by(TrainingRun.trained_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def predict(self, session: AsyncSession, commodity: str, horizon: int = 1):
        self._validate(commodity)
        metrics = await self.latest_metrics(session, commodity)
        if not metrics:
            metrics_resp = await self.train(session, commodity, horizon=horizon)
            metrics = await self.latest_metrics(session, commodity)
            if not metrics:
                raise TrainingError("Training did not persist metadata")

        model, metadata = load_model(Path(metrics.artifact_path))
        raw = self.fetcher.get_historical(commodity)
        feat = add_features(raw)
        x, _ = make_supervised(feat, horizon=max(1, metadata.get("horizon", horizon)))
        latest_features = x.tail(1)
        pred = float(model.predict(latest_features)[0])

        spread = max(0.01 * pred, metadata["rmse"])
        return {
            "commodity": commodity,
            "prediction_date": (datetime.now(timezone.utc) + timedelta(days=horizon)).date(),
            "predicted_price": pred,
            "confidence_interval": (pred - spread, pred + spread),
            "model_used": metrics.model_version,
            "model_accuracy_rmse": metrics.rmse,
            "horizon_days": horizon,
        }

    async def retrain_all(self, session: AsyncSession, horizon: int = 1) -> list[TrainResponse]:
        out = []
        for c in self.commodities:
            out.append(await self.train(session, c, horizon=horizon))
        return out
