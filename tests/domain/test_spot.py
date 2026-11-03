import pytest

from parking.domain.entities import Spot, SpotStatus
from parking.domain.errors import InvalidTransition, SpotNotAvailable


def make(status=SpotStatus.FREE):
    return Spot(code="A-01", name="Spot A-01", zone="A", status=status)


def test_new_spot_is_free():
    assert make().status is SpotStatus.FREE


def test_reserve_free_spot():
    s = make()
    s.reserve()
    assert s.status is SpotStatus.RESERVED


@pytest.mark.parametrize("status", [SpotStatus.RESERVED, SpotStatus.OCCUPIED])
def test_cannot_reserve_unavailable_spot(status):
    with pytest.raises(SpotNotAvailable):
        make(status).reserve()


def test_reserved_spot_becomes_occupied_then_free():
    s = make()
    s.reserve()
    s.occupy_by_reservation()
    assert s.status is SpotStatus.OCCUPIED
    s.release()
    assert s.status is SpotStatus.FREE


def test_cannot_occupy_by_reservation_if_not_reserved():
    with pytest.raises(InvalidTransition):
        make().occupy_by_reservation()


def test_cannot_release_free_spot():
    with pytest.raises(InvalidTransition):
        make().release()


def test_sensor_changes_free_to_occupied_and_back():
    s = make()
    assert s.apply_sensor_reading(True) is True
    assert s.status is SpotStatus.OCCUPIED
    assert s.apply_sensor_reading(False) is True
    assert s.status is SpotStatus.FREE


def test_sensor_same_reading_reports_no_change():
    assert make().apply_sensor_reading(False) is False


def test_sensor_ignored_on_reserved_spot():
    s = make(SpotStatus.RESERVED)
    assert s.apply_sensor_reading(True) is False
    assert s.status is SpotStatus.RESERVED
