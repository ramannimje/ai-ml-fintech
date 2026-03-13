from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import TrainingError
from app.services.training_job_service import TrainingJobService
from app.models.training_run import TrainingRun
from app.schemas.market_data import NormalizedHistoricalSeries
from app.schemas.responses import TrainResponse
from app.services.feature_store_service import FeatureStoreService
from ml.features.engineer import make_supervised
from ml.inference.artifacts import save_model


class TrainingService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def train(
        self,
        *,
        session: AsyncSession,
        commodity: str,
        region: str,
        horizon: int,
        series: NormalizedHistoricalSeries,
        feature_store_service: FeatureStoreService,
        job_id: int | None = None,
        training_job_service: TrainingJobService | None = None,
    ) -> TrainResponse:
        job_service = training_job_service or TrainingJobService()
        if job_id is not None:
            await job_service.mark_processing(session, job_id=job_id)

        try:
            feat = await feature_store_service.materialize_online_features_for_session(
                session,
                commodity=commodity,
                series=series,
                region=region,
            )
            if len(feat) < self.settings.min_training_rows:
                raise TrainingError("Not enough data points to train")

            x, y = make_supervised(feat, horizon=horizon)
            from ml.training.models import benchmark_models

            ranked = benchmark_models(x, y)
            if not ranked:
                raise TrainingError("No model could be trained")

            best = ranked[0]
            version, artifact = self._persist_model_artifact(
                commodity=commodity,
                region=region,
                horizon=horizon,
                model=best.model,
                model_name=best.name,
                rmse=best.rmse,
                mape=best.mape,
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
                rmse=best.rmse,
                mape=best.mape,
            )
            if job_id is not None:
                await job_service.mark_completed(
                    session,
                    job_id=job_id,
                    message=f"Successfully trained {best.name}",
                    result_payload=response.model_dump(),
                )
            return response
        except Exception as exc:
            if job_id is not None:
                await session.rollback()
                await job_service.mark_failed(
                    session,
                    job_id=job_id,
                    message=str(exc),
                    error_payload={"message": str(exc), "type": exc.__class__.__name__},
                )
            raise

    def _persist_model_artifact(
        self,
        *,
        commodity: str,
        region: str,
        horizon: int,
        model,
        model_name: str,
        rmse: float,
        mape: float,
    ) -> tuple[str, Path]:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        version = f"{model_name}_{region}_{ts}"
        artifact = Path(self.settings.artifact_dir) / commodity / region / f"{version}.joblib"
        save_model(
            artifact,
            model,
            {
                "rmse": rmse,
                "mape": mape,
                "horizon": horizon,
                "commodity": commodity,
                "region": region,
                "version": version,
                "model_name": model_name,
            },
        )
        if not artifact.exists():
            raise TrainingError(f"Model artifact not found after save: {artifact}")
        return version, artifact
