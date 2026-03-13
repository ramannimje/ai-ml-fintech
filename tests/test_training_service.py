from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.exceptions import TrainingError
from app.db.base import Base
from app.schemas.market_data import (
    MarketDataProvenanceRecord,
    NormalizedHistoricalBar,
    NormalizedHistoricalSeries,
)
from app.services.training_job_service import TrainingJobService
from app.services import training_service as training_service_module
from app.services.feature_store_service import FeatureStoreService
from app.services.training_service import TrainingService
from app.models import training_job as training_job_model  # noqa: F401
from app.models import training_run as training_run_model  # noqa: F401


class _FakeSession:
    def __init__(self) -> None:
        self.added = []
        self.committed = False
        self.rolled_back = False

    def add(self, obj) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


def _series(rows: int = 240) -> NormalizedHistoricalSeries:
    return NormalizedHistoricalSeries(
        commodity="gold",
        region="us",
        provenance=MarketDataProvenanceRecord(source_type="historical", provider="cache"),
        bars=[
            NormalizedHistoricalBar(
                date=date(2026, 1, min(day, 28)),
                open_usd_per_troy_oz=2200.0 + day,
                high_usd_per_troy_oz=2205.0 + day,
                low_usd_per_troy_oz=2195.0 + day,
                close_usd_per_troy_oz=2200.0 + day,
                volume=1000.0 + day,
            )
            for day in range(1, rows + 1)
        ],
    )


def test_training_service_records_status_and_persists(monkeypatch) -> None:
    service = TrainingService()
    session = _FakeSession()
    features = FeatureStoreService()

    class _Candidate:
        name = "xgboost"
        rmse = 12.5
        mape = 1.1
        model = object()

    monkeypatch.setattr(training_service_module, "save_model", lambda path, model, metadata: path.parent.mkdir(parents=True, exist_ok=True) or path.write_text("ok"))

    async def _run():
        from ml.training import models as training_models

        monkeypatch.setattr(training_models, "benchmark_models", lambda x, y: [_Candidate()])
        return await service.train(
            session=session,
            commodity="gold",
            region="us",
            horizon=7,
            series=_series(),
            feature_store_service=features,
        )

    response = asyncio.run(_run())
    assert response.best_model == "xgboost"
    assert session.committed is True
    assert len(session.added) == 1


def test_training_service_marks_failure_status(monkeypatch) -> None:
    service = TrainingService()
    session = _FakeSession()
    features = FeatureStoreService()

    async def _run():
        from ml.training import models as training_models

        monkeypatch.setattr(training_models, "benchmark_models", lambda x, y: [])
        await service.train(
            session=session,
            commodity="gold",
            region="us",
            horizon=7,
            series=_series(),
            feature_store_service=features,
        )

    try:
        asyncio.run(_run())
    except TrainingError as exc:
        assert "No model could be trained" in str(exc)
    else:
        raise AssertionError("expected TrainingError")


def test_training_job_service_persists_status_lifecycle(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "training_jobs.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _run() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        service = TrainingService()
        jobs = TrainingJobService()
        features = FeatureStoreService()

        class _Candidate:
            name = "xgboost"
            rmse = 12.5
            mape = 1.1
            model = object()

        monkeypatch.setattr(
            training_service_module,
            "save_model",
            lambda path, model, metadata: path.parent.mkdir(parents=True, exist_ok=True) or path.write_text("ok"),
        )

        from ml.training import models as training_models

        monkeypatch.setattr(training_models, "benchmark_models", lambda x, y: [_Candidate()])

        async with session_factory() as session:
            job = await jobs.create_job(session, commodity="gold", region="us", horizon=7)

        async with session_factory() as session:
            queued = await jobs.get_status(session, commodity="gold", region="us")
            assert queued["status"] == "queued"

        async with session_factory() as session:
            await service.train(
                session=session,
                commodity="gold",
                region="us",
                horizon=7,
                series=_series(),
                feature_store_service=features,
                job_id=job.id,
                training_job_service=jobs,
            )

        async with session_factory() as session:
            status = await jobs.get_status(session, commodity="gold", region="us")
            assert status["status"] == "completed"
            assert status["result"]["best_model"] == "xgboost"

        await engine.dispose()

    asyncio.run(_run())


def test_training_job_service_persists_failure_status(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "training_jobs_failed.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _run() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        service = TrainingService()
        jobs = TrainingJobService()
        features = FeatureStoreService()

        from ml.training import models as training_models

        monkeypatch.setattr(training_models, "benchmark_models", lambda x, y: [])

        async with session_factory() as session:
            job = await jobs.create_job(session, commodity="gold", region="us", horizon=7)

        async with session_factory() as session:
            try:
                await service.train(
                    session=session,
                    commodity="gold",
                    region="us",
                    horizon=7,
                    series=_series(),
                    feature_store_service=features,
                    job_id=job.id,
                    training_job_service=jobs,
                )
            except TrainingError as exc:
                assert "No model could be trained" in str(exc)
            else:
                raise AssertionError("expected TrainingError")

        async with session_factory() as session:
            status = await jobs.get_status(session, commodity="gold", region="us")
            assert status["status"] == "failed"
            assert status["error"]["type"] == "TrainingError"

        await engine.dispose()

    asyncio.run(_run())
