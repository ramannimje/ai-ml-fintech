from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RawMarketPayload(Base):
    __tablename__ = "raw_market_payloads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("ingestion_jobs.id"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(16), index=True)
    commodity: Mapped[str] = mapped_column(String(32), index=True)
    region: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    period: Mapped[str | None] = mapped_column(String(16), nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    raw_symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
