from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ingestion_persistence_service import IngestionPersistenceService
from app.services.ingestion_service import MarketIngestionService


class IngestionReplayService:
    def __init__(
        self,
        *,
        ingestion_service: MarketIngestionService,
        persistence_service: IngestionPersistenceService,
    ) -> None:
        self.ingestion_service = ingestion_service
        self.persistence_service = persistence_service

    async def create_historical_backfill_job(
        self,
        session: AsyncSession,
        *,
        commodity: str,
        region: str,
        period: str,
    ):
        return await self.persistence_service.create_job(
            session,
            job_type="historical_backfill",
            commodity=commodity,
            region=region,
            period=period,
            message=f"Historical backfill queued for {commodity}/{region} ({period}).",
        )

    async def get_job_status(self, session: AsyncSession, *, job_id: int) -> dict[str, Any] | None:
        return await self.persistence_service.get_status(session, job_id=job_id)

    async def run_job(self, session: AsyncSession, *, job_id: int) -> dict[str, Any]:
        job = await self.persistence_service.get_job(session, job_id=job_id)
        if job is None:
            raise ValueError(f"Ingestion job not found: {job_id}")
        if job.job_type != "historical_backfill":
            raise ValueError(f"Unsupported ingestion job type: {job.job_type}")
        if not job.commodity or not job.region or not job.period:
            raise ValueError(f"Ingestion job {job_id} is missing commodity, region, or period")

        await self.persistence_service.mark_processing(
            session,
            job_id=job.id,
            message=f"Replaying historical ingestion for {job.commodity}/{job.region} ({job.period}).",
        )

        try:
            series = self.ingestion_service.load_historical_series(
                commodity=job.commodity,
                region=job.region,
                period=job.period,
            )
            persistence_result = await self.persistence_service.persist_historical_series(
                session,
                series=series,
                period=job.period,
                job_id=job.id,
            )
            completed = await self.persistence_service.mark_completed(
                session,
                job_id=job.id,
                message=f"Historical backfill completed for {job.commodity}/{job.region} ({job.period}).",
                result_payload={
                    **persistence_result,
                    "commodity": job.commodity,
                    "region": job.region,
                    "period": job.period,
                    "rows_loaded": len(series.bars),
                },
            )
        except Exception as exc:
            await self.persistence_service.mark_failed(
                session,
                job_id=job.id,
                message=f"Historical backfill failed for job {job.id}.",
                error_payload={
                    "message": str(exc),
                    "job_type": job.job_type,
                    "commodity": job.commodity,
                    "region": job.region,
                    "period": job.period,
                },
            )
            raise

        if completed is None:
            raise ValueError(f"Ingestion job not found after completion: {job_id}")
        return self.persistence_service.serialize_job(completed)
