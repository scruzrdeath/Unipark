import pytest

from parking.domain.entities import ReservationStatus, SpotStatus
from parking.domain.errors import (
    InvalidTransition,
    ReservationExpired,
    ReservationNotFound,
)


def test_entry_occupies_spot(reservations, access, store):
    r = reservations.reserve("u1", "A-01")
    access.confirm_entry(r.id)
    assert store.spots["A-01"].status is SpotStatus.OCCUPIED
    assert store.reservations[r.id].status is ReservationStatus.CONFIRMED


def test_exit_frees_spot_automatically(reservations, access, store):
    r = reservations.reserve("u1", "A-01")
    access.confirm_entry(r.id)
    access.register_exit(r.id)
    assert store.spots["A-01"].status is SpotStatus.FREE
    assert store.reservations[r.id].status is ReservationStatus.COMPLETED


def test_entry_after_time_is_rejected_and_spot_released(reservations, access, store, clock):
    r = reservations.reserve("u1", "A-01")
    clock.advance(minutes=61)
    with pytest.raises(ReservationExpired):
        access.confirm_entry(r.id)
    assert store.spots["A-01"].status is SpotStatus.FREE
    assert store.reservations[r.id].status is ReservationStatus.EXPIRED


def test_cannot_enter_twice(reservations, access):
    r = reservations.reserve("u1", "A-01")
    access.confirm_entry(r.id)
    with pytest.raises(InvalidTransition):
        access.confirm_entry(r.id)


def test_cannot_exit_without_entering(reservations, access):
    r = reservations.reserve("u1", "A-01")
    with pytest.raises(InvalidTransition):
        access.register_exit(r.id)


def test_unknown_reservation(access):
    with pytest.raises(ReservationNotFound):
        access.confirm_entry("nope")
