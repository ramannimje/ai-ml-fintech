from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ingestion_job import IngestionJob
from app.models.normalized_market_record import NormalizedMarketRecord
from app.models.raw_market_payload import RawMarketPayload
from app.schemas.market_data import NormalizedHistoricalSeries, NormalizedLiveQuote


class IngestionPersistenceService:
    @staticmethod
    def _normalize_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    async def create_job(
        self,
        session: AsyncSession,
        *,
        job_type: str,
        commodity: str | None = None,
        region: str | None = None,
        period: str | None = None,
        message: str = "Ingestion queued.",
    ) -> IngestionJob:
        job = IngestionJob(
            job_type=job_type,
            commodity=commodity,
            region=region,
            period=period,
            status="queued",
            message=message,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job

    async def get_job(self, session: AsyncSession, *, job_id: int) -> IngestionJob | None:
        return await session.get(IngestionJob, job_id)

    async def get_latest_job(
        self,
        session: AsyncSession,
        *,
        job_type: str | None = None,
        commodity: str | None = None,
        region: str | None = None,
    ) -> IngestionJob | None:
        stmt = select(IngestionJob)
        if job_type is not None:
            stmt = stmt.where(IngestionJob.job_type == job_type)
        if commodity is not None:
            stmt = stmt.where(IngestionJob.commodity == commodity)
        if region is not None:
            stmt = stmt.where(IngestionJob.region == region)
        stmt = stmt.order_by(IngestionJob.created_at.desc(), IngestionJob.id.desc()).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    def serialize_job(self, job: IngestionJob) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "job_id": job.id,
            "job_type": job.job_type,
            "status": job.status,
            "message": job.message or "",
            "commodity": job.commodity,
            "region": job.region,
            "period": job.period,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
        }
        if job.result_payload is not None:
            payload["result"] = job.result_payload
        if job.error_payload is not None:
            payload["error"] = job.error_payload
        return payload

    async def get_status(self, session: AsyncSession, *, job_id: int) -> dict[str, Any] | None:
        job = await self.get_job(session, job_id=job_id)
        if job is None:
            return None
        return self.serialize_job(job)

    async def mark_processing(self, session: AsyncSession, *, job_id: int, message: str) -> IngestionJob | None:
        job = await session.get(IngestionJob, job_id)
        if not job:
            return None
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
        result_payload: dict[str, Any],
        message: str = "Ingestion completed.",
    ) -> IngestionJob | None:
        job = await session.get(IngestionJob, job_id)
        if not job:
            return None
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
        error_payload: dict[str, Any] | None = None,
    ) -> IngestionJob | None:
        job = await session.get(IngestionJob, job_id)
        if not job:
            return None
        job.status = "failed"
        job.message = message
        job.error_payload = error_payload or {"message": message}
        job.completed_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(job)
        return job

    async def persist_live_quotes(
        self,
        session: AsyncSession,
        *,
        quotes: dict[str, NormalizedLiveQuote],
        region: str,
        job_id: int | None = None,
    ) -> dict[str, int]:
        raw_payloads_written = 0
        observed_by_commodity = {
            commodity: self._normalize_datetime(quote.observed_at)
            for commodity, quote in quotes.items()
        }
        commodities = list(quotes.keys())
        existing_rows = []
        if commodities:
            with session.no_autoflush:
                existing_rows = (
                    await session.execute(
                        select(NormalizedMarketRecord)
                        .where(NormalizedMarketRecord.record_type == "live")
                        .where(NormalizedMarketRecord.commodity.in_(commodities))
                        .where(NormalizedMarketRecord.region == region)
                    )
                ).scalars().all()
        existing_by_key = {
            (
                row.record_type,
                row.commodity,
                row.region,
                row.period,
                self._normalize_datetime(row.observed_at),
            ): row
            for row in existing_rows
        }
        normalized_records_inserted = 0
        for commodity, quote in quotes.items():
            observed_at = observed_by_commodity[commodity]
            session.add(
                RawMarketPayload(
                    job_id=job_id,
                    source_type="live",
                    commodity=commodity,
                    region=region,
                    provider=quote.provenance.provider,
                    period=None,
                    observed_at=quote.observed_at,
                    raw_symbol=quote.provenance.raw_symbol,
                    payload={
                        "price_usd_per_troy_oz": quote.price_usd_per_troy_oz,
                        "provenance": quote.provenance.model_dump(mode="json"),
                    },
                )
            )
            raw_payloads_written += 1

            existing = existing_by_key.get(("live", commodity, region, None, observed_at))
            if existing is None:
                existing = NormalizedMarketRecord(
                    record_type="live",
                    commodity=commodity,
                    region=region,
                    period=None,
                    observed_at=observed_at,
                    provenance_provider=quote.provenance.provider,
                    provenance_detail=quote.provenance.detail,
                )
                session.add(existing)
                existing_by_key[("live", commodity, region, None, observed_at)] = existing
                normalized_records_inserted += 1
            existing.price_usd_per_troy_oz = quote.price_usd_per_troy_oz
            existing.provenance_provider = quote.provenance.provider
            existing.provenance_detail = quote.provenance.detail
            existing.validation_status = "valid"

        await session.commit()
        return {
            "raw_payloads_written": raw_payloads_written,
            "normalized_records_written": len(quotes),
            "normalized_records_inserted": normalized_records_inserted,
        }

    async def persist_historical_series(
        self,
        session: AsyncSession,
        *,
        series: NormalizedHistoricalSeries,
        period: str,
        job_id: int | None = None,
    ) -> dict[str, int]:
        observed_dates = [
            self._normalize_datetime(datetime.combine(bar.date, time.min, tzinfo=timezone.utc))
            for bar in series.bars
        ]
        existing_rows = []
        if observed_dates:
            with session.no_autoflush:
                existing_rows = (
                    await session.execute(
                        select(NormalizedMarketRecord)
                        .where(NormalizedMarketRecord.record_type == "historical")
                        .where(NormalizedMarketRecord.commodity == series.commodity)
                        .where(NormalizedMarketRecord.region == series.region)
                        .where(NormalizedMarketRecord.period == period)
                        .where(NormalizedMarketRecord.observed_at >= min(observed_dates))
                        .where(NormalizedMarketRecord.observed_at <= max(observed_dates))
                    )
                ).scalars().all()
        existing_by_key = {
            (
                row.record_type,
                row.commodity,
                row.region,
                row.period,
                self._normalize_datetime(row.observed_at),
            ): row
            for row in existing_rows
        }
        session.add(
            RawMarketPayload(
                job_id=job_id,
                source_type="historical",
                commodity=series.commodity,
                region=series.region,
                provider=series.provenance.provider,
                period=period,
                observed_at=series.provenance.observed_at,
                raw_symbol=series.provenance.raw_symbol,
                payload={
                    "bars": [bar.model_dump(mode="json") for bar in series.bars],
                    "provenance": series.provenance.model_dump(mode="json"),
                },
            )
        )
        normalized_records_inserted = 0

        for bar in series.bars:
            observed_at = self._normalize_datetime(datetime.combine(bar.date, time.min, tzinfo=timezone.utc))
            existing = existing_by_key.get(("historical", series.commodity, series.region, period, observed_at))
            if existing is None:
                existing = NormalizedMarketRecord(
                    record_type="historical",
                    commodity=series.commodity,
                    region=series.region,
                    period=period,
                    observed_at=observed_at,
                    provenance_provider=series.provenance.provider,
                    provenance_detail=series.provenance.detail,
                )
                session.add(existing)
                existing_by_key[("historical", series.commodity, series.region, period, observed_at)] = existing
                normalized_records_inserted += 1
            existing.open_usd_per_troy_oz = bar.open_usd_per_troy_oz
            existing.high_usd_per_troy_oz = bar.high_usd_per_troy_oz
            existing.low_usd_per_troy_oz = bar.low_usd_per_troy_oz
            existing.close_usd_per_troy_oz = bar.close_usd_per_troy_oz
            existing.volume = bar.volume
            existing.validation_status = "valid"

        await session.commit()
        return {
            "raw_payloads_written": 1,
            "normalized_records_written": len(series.bars),
            "normalized_records_inserted": normalized_records_inserted,
        }
