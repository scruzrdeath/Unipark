import threading
from datetime import timedelta

import pytest

from parking.domain.entities import ReservationStatus, SpotStatus
from parking.domain.errors import (
    SpotNotAvailable,
    SpotNotFound,
    UserAlreadyHasReservation,
)


def test_reserve_marks_spot_reserved(reservations, store):
    r = reservations.reserve("u1", "A-01")
    assert r.status is ReservationStatus.ACTIVE
    assert store.spots["A-01"].status is SpotStatus.RESERVED


def test_cannot_reserve_same_spot_twice(reservations):
    reservations.reserve("u1", "A-01")
    with pytest.raises(SpotNotAvailable):
        reservations.reserve("u2", "A-01")


def test_cannot_reserve_occupied_spot(reservations, store):
    store.spots["A-01"].status = SpotStatus.OCCUPIED
    with pytest.raises(SpotNotAvailable):
        reservations.reserve("u1", "A-01")


def test_user_cannot_hold_two_reservations(reservations):
    reservations.reserve("u1", "A-01")
    with pytest.raises(UserAlreadyHasReservation):
        reservations.reserve("u1", "A-02")


def test_unknown_spot(reservations):
    with pytest.raises(SpotNotFound):
        reservations.reserve("u1", "Z-99")


def test_list_open_returns_active_reservations(reservations):
    reservations.reserve("u1", "A-01")
    reservations.reserve("u2", "A-02")
    assert {r.user_code for r in reservations.list_open()} == {"u1", "u2"}


def test_expire_overdue_frees_spot(reservations, store, clock):
    r = reservations.reserve("u1", "A-01")
    clock.advance(minutes=59)
    assert reservations.expire_overdue() == 0
    clock.advance(minutes=1)
    assert reservations.expire_overdue() == 1
    assert store.spots["A-01"].status is SpotStatus.FREE
    assert store.reservations[r.id].status is ReservationStatus.EXPIRED


def test_after_expiry_user_can_reserve_again(reservations, clock):
    reservations.reserve("u1", "A-01")
    clock.advance(minutes=60)
    reservations.expire_overdue()
    assert reservations.reserve("u1", "A-02").spot_code == "A-02"


def test_concurrent_users_only_one_wins(reservations):
    """20 users race for the same spot: exactly one reservation may succeed."""
    results = []
    barrier = threading.Barrier(20)

    def attempt(i):
        barrier.wait()
        try:
            reservations.reserve(f"user{i}", "A-01")
            results.append("ok")
        except SpotNotAvailable:
            results.append("taken")

    threads = [threading.Thread(target=attempt, args=(i,)) for i in range(20)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results.count("ok") == 1
    assert results.count("taken") == 19
