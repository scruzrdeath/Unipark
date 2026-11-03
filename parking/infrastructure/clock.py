"""Clock adapters. Simulated time: 1 real second = ``speed`` simulated seconds."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from parking.domain.ports import Clock


class SimulatedClock(Clock):
    """Default speed 60 => 1 real second is 1 simulated minute."""

    def __init__(self, speed: float = 60.0, start: Optional[datetime] = None) -> None:
        self._speed = speed
        self._start = start or datetime.now(timezone.utc).replace(tzinfo=None)
        self._t0 = time.monotonic()

    def now(self) -> datetime:
        elapsed = time.monotonic() - self._t0
        return self._start + timedelta(seconds=elapsed * self._speed)


class ManualClock(Clock):
    """Time that only moves when told to. Used in tests."""

    def __init__(self, start: Optional[datetime] = None) -> None:
        self._now = start or datetime(2026, 1, 1, 8, 0, 0)

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs) -> None:
        self._now += timedelta(**kwargs)
