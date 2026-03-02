from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_sub: Mapped[str] = mapped_column(String(128), index=True)
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    commodity: Mapped[str] = mapped_column(String(32), index=True)
    region: Mapped[str] = mapped_column(String(16), index=True)
    currency: Mapped[str] = mapped_column(String(8))
    unit: Mapped[str] = mapped_column(String(32))

    alert_type: Mapped[str] = mapped_column(String(32), index=True)
    threshold: Mapped[float] = mapped_column(Float)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=30)
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
