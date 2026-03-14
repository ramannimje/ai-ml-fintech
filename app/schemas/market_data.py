from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class MarketDataProvenanceRecord(BaseModel):
    source_type: Literal["live", "historical", "features"]
    provider: str
    detail: str | None = None
    observed_at: datetime | None = None
    ingested_at: datetime | None = None
    raw_symbol: str | None = None
    fallback_level: int = Field(default=0, ge=0)


class NormalizedLiveQuote(BaseModel):
    commodity: str
    price_usd_per_troy_oz: float
    daily_change: float | None = None
    daily_change_pct: float | None = None
    observed_at: datetime
    provenance: MarketDataProvenanceRecord


class NormalizedHistoricalBar(BaseModel):
    date: date
    open_usd_per_troy_oz: float
    high_usd_per_troy_oz: float
    low_usd_per_troy_oz: float
    close_usd_per_troy_oz: float
    volume: float | None = None


class NormalizedHistoricalSeries(BaseModel):
    commodity: str
    region: str
    bars: list[NormalizedHistoricalBar]
    provenance: MarketDataProvenanceRecord
