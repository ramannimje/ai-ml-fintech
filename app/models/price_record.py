"""Region-tagged historical price record model."""
from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PriceRecord(Base):
    __tablename__ = "price_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    commodity: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    region: Mapped[str] = mapped_column(String(16), index=True)
    price_in_grams: Mapped[float] = mapped_column(Float)  # canonical USD/gram
    currency: Mapped[str] = mapped_column(String(8))
    source: Mapped[str] = mapped_column(String(64))
