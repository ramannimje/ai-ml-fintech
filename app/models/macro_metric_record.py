from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MacroMetricRecord(Base):
    __tablename__ = "macro_metric_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    metric_key: Mapped[str] = mapped_column(String(64), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    value: Mapped[float] = mapped_column(Float)
    provider: Mapped[str] = mapped_column(String(64))
    source_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
