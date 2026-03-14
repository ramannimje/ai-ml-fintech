from __future__ import annotations

from datetime import timezone

import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.macro_metric_record import MacroMetricRecord
from ml.data.data_fetcher import MarketDataFetcher


class MacroPersistenceService:
    def __init__(self, fetcher: MarketDataFetcher) -> None:
        self.fetcher = fetcher

    async def ingest_macro_series(self, session: AsyncSession, *, period: str = "1y") -> dict[str, int]:
        frame = self.fetcher.get_macro_features(period=period)
        if frame.empty:
            return {"rows_seen": 0, "rows_inserted": 0}

        normalized = frame.copy()
        normalized.index = pd.to_datetime(normalized.index, errors="coerce")
        normalized = normalized.dropna(how="all")
        normalized = normalized[~normalized.index.isna()]
        
        if normalized.empty:
            return {"rows_seen": 0, "rows_inserted": 0}
        
        desired: dict[tuple[str, object], float] = {}
        for observed_at, row in normalized.iterrows():
            observed_dt = self._normalize_observed_at(observed_at.to_pydatetime())
            for metric_key, value in row.items():
                if pd.isna(value):
                    continue
                desired[(str(metric_key), observed_dt)] = float(value)

        if not desired:
            return {"rows_seen": 0, "rows_inserted": 0}

        metric_keys = sorted({metric_key for metric_key, _ in desired})
        observed_values = [observed_at for _, observed_at in desired]
        existing_rows = (
            await session.execute(
                select(MacroMetricRecord)
                .where(MacroMetricRecord.metric_key.in_(metric_keys))
                .where(MacroMetricRecord.observed_at >= min(observed_values))
                .where(MacroMetricRecord.observed_at <= max(observed_values))
            )
        ).scalars().all()
        existing_by_key = {
            (row.metric_key, self._normalize_observed_at(row.observed_at)): row
            for row in existing_rows
        }

        inserted = 0
        for key, value in desired.items():
            metric_key, observed_dt = key
            existing = existing_by_key.get(key)
            if existing is None:
                session.add(
                    MacroMetricRecord(
                        metric_key=metric_key,
                        observed_at=observed_dt,
                        value=value,
                        provider="yfinance/cache",
                        source_detail=f"macro_{metric_key}.csv",
                    )
                )
                inserted += 1
            else:
                existing.value = value
                existing.provider = "yfinance/cache"
                existing.source_detail = f"macro_{metric_key}.csv"
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            inserted = 0
        return {"rows_seen": len(desired), "rows_inserted": inserted}

    async def load_macro_frame(self, session: AsyncSession) -> pd.DataFrame:
        rows = (
            await session.execute(
                select(MacroMetricRecord).order_by(MacroMetricRecord.observed_at.asc(), MacroMetricRecord.metric_key.asc())
            )
        ).scalars().all()
        if not rows:
            return pd.DataFrame()
        frame = pd.DataFrame(
            [{"Date": row.observed_at, "metric_key": row.metric_key, "value": row.value} for row in rows]
        )
        pivot = frame.pivot_table(index="Date", columns="metric_key", values="value", aggfunc="last").sort_index()
        pivot.index = pd.to_datetime(pivot.index)
        return pivot.ffill().bfill()

    async def get_or_ingest_macro_frame(self, session: AsyncSession, *, period: str = "1y") -> pd.DataFrame:
        await self.ingest_macro_series(session, period=period)
        return await self.load_macro_frame(session)

    @staticmethod
    def _normalize_observed_at(value) -> object:
        """Normalize datetime to UTC-naive, handling NaT gracefully."""
        from pandas import NaT
        
        if value is None or (hasattr(value, "tzinfo") and value is NaT):
            raise ValueError("observed_at cannot be NaT or None")
        if getattr(value, "tzinfo", None) is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)
