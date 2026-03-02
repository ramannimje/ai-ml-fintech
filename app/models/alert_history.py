from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(Integer, index=True)
    user_sub: Mapped[str] = mapped_column(String(128), index=True)

    commodity: Mapped[str] = mapped_column(String(32), index=True)
    region: Mapped[str] = mapped_column(String(16), index=True)
    currency: Mapped[str] = mapped_column(String(8))

    alert_type: Mapped[str] = mapped_column(String(32))
    threshold: Mapped[float] = mapped_column(Float)
    observed_value: Mapped[float] = mapped_column(Float)
    message: Mapped[str] = mapped_column(String(512))
    email_status: Mapped[str] = mapped_column(String(32), default="skipped")
    delivery_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    delivery_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    delivery_attempts: Mapped[int] = mapped_column(Integer, default=0)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
