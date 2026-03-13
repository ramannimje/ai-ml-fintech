from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TrainingError
from app.models.training_job import TrainingJob


class TrainingJobService:
    async def create_job(
        self,
        session: AsyncSession,
        *,
        commodity: str,
        region: str,
        horizon: int,
    ) -> TrainingJob:
        job = TrainingJob(
            commodity=commodity,
            region=region,
            horizon=horizon,
            status="queued",
            message="Training queued.",
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job

    async def mark_processing(
        self,
        session: AsyncSession,
        *,
        job_id: int,
        message: str = "Training started...",
    ) -> TrainingJob:
        job = await self._get_job(session, job_id)
        job.status = "processing"
        job.message = message
        job.started_at = datetime.now(timezone.utc)
        job.completed_at = None
        job.error_payload = None
        await session.commit()
        await session.refresh(job)
        return job

    async def mark_completed(
        self,
        session: AsyncSession,
        *,
        job_id: int,
        message: str,
        result_payload: dict[str, Any],
    ) -> TrainingJob:
        job = await self._get_job(session, job_id)
        job.status = "completed"
        job.message = message
        job.result_payload = result_payload
        job.error_payload = None
        job.completed_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(job)
        return job

    async def mark_failed(
        self,
        session: AsyncSession,
        *,
        job_id: int,
        message: str,
        error_payload: dict[str, Any],
    ) -> TrainingJob:
        job = await self._get_job(session, job_id)
        job.status = "failed"
        job.message = message
        job.error_payload = error_payload
        job.completed_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(job)
        return job

    async def get_status(self, session: AsyncSession, *, commodity: str, region: str) -> dict[str, Any]:
        result = await session.execute(
            select(TrainingJob)
            .where(TrainingJob.commodity == commodity)
            .where(TrainingJob.region == region)
            .order_by(TrainingJob.created_at.desc(), TrainingJob.id.desc())
            .limit(1)
        )
        job = result.scalar_one_or_none()
        if not job:
            return {
                "status": "none",
                "message": "No recent training run found.",
            }

        payload: dict[str, Any] = {
            "status": job.status,
            "message": job.message or "",
        }
        if job.result_payload is not None:
            payload["result"] = job.result_payload
        if job.error_payload is not None:
            payload["error"] = job.error_payload
        return payload

    async def _get_job(self, session: AsyncSession, job_id: int) -> TrainingJob:
        job = await session.get(TrainingJob, job_id)
        if not job:
            raise TrainingError(f"Training job not found: {job_id}")
        return job
