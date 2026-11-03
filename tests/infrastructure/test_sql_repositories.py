"""Runs the same use cases against SQLAlchemy (SQLite in memory). Skipped if SQLAlchemy is missing."""
from datetime import timedelta

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from parking.application.services import AccessService, ReservationService  # noqa: E402
from parking.domain.entities import SpotStatus  # noqa: E402
from parking.domain.errors import SpotNotAvailable  # noqa: E402
from parking.infrastructure.clock import ManualClock  # noqa: E402
from parking.infrastructure.seed import seed_spots  # noqa: E402
from parking.infrastructure.sql_models import Base  # noqa: E402
from parking.infrastructure.sql_repositories import SqlAlchemyUnitOfWork  # noqa: E402


@pytest.fixture
def uow_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sf = sessionmaker(engine, expire_on_commit=False)
    factory = lambda: SqlAlchemyUnitOfWork(sf)  # noqa: E731
    seed_spots(factory)
    return factory


def test_seed_creates_two_zones_of_ten_and_is_idempotent(uow_factory):
    with uow_factory() as uow:
        assert len(uow.spots.list_all()) == 20
    assert seed_spots(uow_factory) == 0


def test_reserve_enter_exit_cycle(uow_factory):
    clock = ManualClock()
    res = ReservationService(uow_factory, clock, timedelta(minutes=60))
    acc = AccessService(uow_factory, clock)
    r = res.reserve("u1", "A-01")
    with uow_factory() as uow:
        assert uow.spots.get_by_code("A-01").status is SpotStatus.RESERVED
    acc.confirm_entry(r.id)
    acc.register_exit(r.id)
    with uow_factory() as uow:
        assert uow.spots.get_by_code("A-01").status is SpotStatus.FREE


def test_double_reservation_rejected(uow_factory):
    res = ReservationService(uow_factory, ManualClock(), timedelta(minutes=60))
    res.reserve("u1", "A-01")
    with pytest.raises(SpotNotAvailable):
        res.reserve("u2", "A-01")


def test_expiration(uow_factory):
    clock = ManualClock()
    res = ReservationService(uow_factory, clock, timedelta(minutes=60))
    res.reserve("u1", "A-01")
    clock.advance(minutes=60)
    assert res.expire_overdue() == 1
    with uow_factory() as uow:
        assert uow.spots.get_by_code("A-01").status is SpotStatus.FREE
