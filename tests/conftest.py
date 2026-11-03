from datetime import timedelta

import pytest

from parking.application.services import (
    AccessService,
    OccupancyService,
    ReservationService,
    SensorService,
)
from parking.domain.entities import Spot
from parking.domain.ports import OccupancyProbe
from parking.infrastructure.clock import ManualClock
from parking.infrastructure.in_memory import InMemoryStore


class FakeProbe(OccupancyProbe):
    """Sensor whose reading we control from the test."""

    def __init__(self) -> None:
        self.readings: dict[str, bool] = {}

    def read(self, spot_code: str, currently_occupied: bool) -> bool:
        return self.readings.get(spot_code, currently_occupied)


@pytest.fixture
def clock():
    return ManualClock()


@pytest.fixture
def store():
    s = InMemoryStore()
    for zone in ("A", "B"):
        for i in range(1, 4):
            code = f"{zone}-{i:02d}"
            s.spots[code] = Spot(code=code, name=f"Spot {code}", zone=zone)
    return s


@pytest.fixture
def probe():
    return FakeProbe()


@pytest.fixture
def reservations(store, clock):
    return ReservationService(store.uow_factory, clock, ttl=timedelta(minutes=60))


@pytest.fixture
def access(store, clock):
    return AccessService(store.uow_factory, clock)


@pytest.fixture
def sensors(store, probe):
    return SensorService(store.uow_factory, probe)


@pytest.fixture
def occupancy(store, clock):
    return OccupancyService(store.uow_factory, clock)
