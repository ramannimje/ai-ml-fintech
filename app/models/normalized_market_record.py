from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NormalizedMarketRecord(Base):
    __tablename__ = "normalized_market_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    record_type: Mapped[str] = mapped_column(String(16), index=True)
    commodity: Mapped[str] = mapped_column(String(32), index=True)
    region: Mapped[str] = mapped_column(String(16), index=True)
    period: Mapped[str | None] = mapped_column(String(16), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    price_usd_per_troy_oz: Mapped[float | None] = mapped_column(Float, nullable=True)
    open_usd_per_troy_oz: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_usd_per_troy_oz: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_usd_per_troy_oz: Mapped[float | None] = mapped_column(Float, nullable=True)
    close_usd_per_troy_oz: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    provenance_provider: Mapped[str] = mapped_column(String(64))
    provenance_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    validation_status: Mapped[str] = mapped_column(String(16), default="valid", index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
