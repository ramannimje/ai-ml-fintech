from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_sub: Mapped[str] = mapped_column(String(128), index=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, default="")
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    commodity: Mapped[str] = mapped_column(String(32), index=True)
    region: Mapped[str] = mapped_column(String(16), index=True)
    currency: Mapped[str] = mapped_column(String(8))
    unit: Mapped[str] = mapped_column(String(32))
    whatsapp_number: Mapped[str | None] = mapped_column(String(32), nullable=True)

    alert_type: Mapped[str] = mapped_column(String(32), index=True)
    direction: Mapped[str | None] = mapped_column(
        Enum("above", "below", name="price_alert_direction", native_enum=False),
        nullable=True,
        index=True,
    )
    threshold: Mapped[float] = mapped_column(Float)
    target_price: Mapped[float] = mapped_column(Float, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_triggered: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=30)
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
