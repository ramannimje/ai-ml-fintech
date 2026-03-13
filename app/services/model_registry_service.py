from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.training_run import TrainingRun
from ml.inference.artifacts import load_model


class ModelRegistryService:
    _model_cache: dict[tuple[str, str], tuple[Any, dict[str, Any]]] = {}

    async def latest_metrics(self, session: AsyncSession, commodity: str, region: str) -> TrainingRun | None:
        result = await session.execute(
            select(TrainingRun)
            .where(TrainingRun.commodity == commodity)
            .where(TrainingRun.region == region)
            .order_by(TrainingRun.trained_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    def load_model_bundle(self, metrics: TrainingRun) -> tuple[Any, dict[str, Any]]:
        cache_key = (metrics.commodity, metrics.region)
        cached = self._model_cache.get(cache_key)
        if cached and str(cached[1].get("version", "")) == metrics.model_version:
            return cached

        model, metadata = load_model(Path(metrics.artifact_path))
        self._model_cache[cache_key] = (model, metadata)
        return model, metadata

    async def prewarm_latest_models(
        self,
        session: AsyncSession,
        commodities: list[str],
        regions: list[str],
    ) -> None:
        for commodity in commodities:
            for region in regions:
                try:
                    metrics = await self.latest_metrics(session, commodity, region)
                    if not metrics:
                        continue
                    self.load_model_bundle(metrics)
                except Exception:
                    continue
