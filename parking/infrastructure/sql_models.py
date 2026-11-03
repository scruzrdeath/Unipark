"""SQLAlchemy table definitions (infrastructure detail, not domain)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SpotModel(Base):
    __tablename__ = "spots"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    zone: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False)


class ReservationModel(Base):
    __tablename__ = "reservations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    spot_code: Mapped[str] = mapped_column(ForeignKey("spots.code"), nullable=False, index=True)
    user_code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    entered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    exited_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
