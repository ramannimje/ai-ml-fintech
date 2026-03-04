from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, unique=True)
    default_region: Mapped[str] = mapped_column(String(16), default="us", index=True)
    default_commodity: Mapped[str] = mapped_column(String(32), default="gold")
    prediction_horizon: Mapped[int] = mapped_column(Integer, default=30)

    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_cooldown_minutes: Mapped[int] = mapped_column(Integer, default=30)
    alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    enable_chronos_bolt: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_xgboost: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_retrain: Mapped[bool] = mapped_column(Boolean, default=False)
    theme_preference: Mapped[str] = mapped_column(String(16), default="system")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
