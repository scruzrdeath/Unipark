"""Object-level authorization: users cannot act on other users' reservations."""
import pytest

from parking.domain.errors import Forbidden


def test_owner_can_enter_and_exit(reservations, access):
    r = reservations.reserve("ana", "A-01")
    access.confirm_entry(r.id, requested_by="ana")
    access.register_exit(r.id, requested_by="ana")


def test_other_user_cannot_enter(reservations, access):
    r = reservations.reserve("ana", "A-01")
    with pytest.raises(Forbidden):
        access.confirm_entry(r.id, requested_by="bob")


def test_other_user_cannot_exit(reservations, access):
    r = reservations.reserve("ana", "A-01")
    access.confirm_entry(r.id, requested_by="ana")
    with pytest.raises(Forbidden):
        access.register_exit(r.id, requested_by="bob")


def test_other_user_cannot_read_reservation(reservations):
    r = reservations.reserve("ana", "A-01")
    with pytest.raises(Forbidden):
        reservations.get(r.id, requested_by="bob")


def test_list_open_only_returns_own_reservations(reservations):
    reservations.reserve("ana", "A-01")
    reservations.reserve("bob", "A-02")
    assert [r.user_code for r in reservations.list_open(user_code="ana")] == ["ana"]
    assert len(reservations.list_open()) == 2
