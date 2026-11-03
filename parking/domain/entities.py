"""Core entities and their business rules (no I/O, no frameworks)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from parking.domain.errors import (
    InvalidTransition,
    ReservationExpired,
    SpotNotAvailable,
)


class SpotStatus(str, Enum):
    FREE = "FREE"
    RESERVED = "RESERVED"
    OCCUPIED = "OCCUPIED"


class ReservationStatus(str, Enum):
    ACTIVE = "ACTIVE"          # waiting for the vehicle to arrive
    CONFIRMED = "CONFIRMED"    # vehicle entered, spot occupied
    COMPLETED = "COMPLETED"    # vehicle left, spot released
    EXPIRED = "EXPIRED"        # nobody arrived in time


@dataclass
class Spot:
    code: str                  # e.g. "A-01"
    name: str                  # e.g. "Spot A-01"
    zone: str                  # e.g. "A"
    status: SpotStatus = SpotStatus.FREE

    def reserve(self) -> None:
        if self.status is not SpotStatus.FREE:
            raise SpotNotAvailable(f"Spot {self.code} is {self.status.value}")
        self.status = SpotStatus.RESERVED

    def occupy_by_reservation(self) -> None:
        if self.status is not SpotStatus.RESERVED:
            raise InvalidTransition(f"Spot {self.code} is not RESERVED")
        self.status = SpotStatus.OCCUPIED

    def release(self) -> None:
        if self.status is SpotStatus.FREE:
            raise InvalidTransition(f"Spot {self.code} is already FREE")
        self.status = SpotStatus.FREE

    def apply_sensor_reading(self, occupied: bool) -> bool:
        """Apply a sensor reading. RESERVED spots are ignored by sensors.

        Returns True when the status actually changed.
        """
        if self.status is SpotStatus.RESERVED:
            return False
        new_status = SpotStatus.OCCUPIED if occupied else SpotStatus.FREE
        changed = new_status is not self.status
        self.status = new_status
        return changed


@dataclass
class Reservation:
    spot_code: str
    user_code: str
    created_at: datetime
    expires_at: datetime
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: ReservationStatus = ReservationStatus.ACTIVE
    entered_at: Optional[datetime] = None
    exited_at: Optional[datetime] = None

    @staticmethod
    def create(spot_code: str, user_code: str, now: datetime, ttl: timedelta) -> "Reservation":
        return Reservation(
            spot_code=spot_code, user_code=user_code,
            created_at=now, expires_at=now + ttl,
        )

    @property
    def is_open(self) -> bool:
        return self.status in (ReservationStatus.ACTIVE, ReservationStatus.CONFIRMED)

    def is_overdue(self, now: datetime) -> bool:
        return self.status is ReservationStatus.ACTIVE and now >= self.expires_at

    def confirm_entry(self, now: datetime) -> None:
        if self.status is not ReservationStatus.ACTIVE:
            raise InvalidTransition(f"Reservation is {self.status.value}")
        if now >= self.expires_at:
            raise ReservationExpired("Reservation time is over")
        self.status = ReservationStatus.CONFIRMED
        self.entered_at = now

    def complete(self, now: datetime) -> None:
        if self.status is not ReservationStatus.CONFIRMED:
            raise InvalidTransition(f"Reservation is {self.status.value}")
        self.status = ReservationStatus.COMPLETED
        self.exited_at = now

    def expire(self) -> None:
        if self.status is not ReservationStatus.ACTIVE:
            raise InvalidTransition(f"Reservation is {self.status.value}")
        self.status = ReservationStatus.EXPIRED
