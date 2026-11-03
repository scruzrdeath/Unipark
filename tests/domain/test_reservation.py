from datetime import datetime, timedelta

import pytest

from parking.domain.entities import Reservation, ReservationStatus
from parking.domain.errors import InvalidTransition, ReservationExpired

T0 = datetime(2026, 1, 1, 8, 0)


def make():
    return Reservation.create("A-01", "u1", T0, timedelta(minutes=60))


def test_create_sets_expiry_and_active_status():
    r = make()
    assert r.status is ReservationStatus.ACTIVE
    assert r.expires_at == T0 + timedelta(minutes=60)
    assert r.is_open


def test_confirm_entry_before_expiry():
    r = make()
    r.confirm_entry(T0 + timedelta(minutes=10))
    assert r.status is ReservationStatus.CONFIRMED
    assert r.entered_at == T0 + timedelta(minutes=10)


def test_confirm_entry_after_expiry_fails():
    with pytest.raises(ReservationExpired):
        make().confirm_entry(T0 + timedelta(minutes=60))


def test_complete_requires_confirmed():
    with pytest.raises(InvalidTransition):
        make().complete(T0)


def test_full_lifecycle():
    r = make()
    r.confirm_entry(T0)
    r.complete(T0 + timedelta(minutes=5))
    assert r.status is ReservationStatus.COMPLETED
    assert not r.is_open


def test_overdue_only_when_active_and_time_over():
    r = make()
    assert not r.is_overdue(T0 + timedelta(minutes=59))
    assert r.is_overdue(T0 + timedelta(minutes=60))
    r.confirm_entry(T0)
    assert not r.is_overdue(T0 + timedelta(minutes=120))


def test_expire_requires_active():
    r = make()
    r.confirm_entry(T0)
    with pytest.raises(InvalidTransition):
        r.expire()
