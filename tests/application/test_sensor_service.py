from parking.domain.entities import SpotStatus


def test_sensor_marks_spot_occupied_then_free(sensors, probe, store):
    probe.readings["A-01"] = True
    assert sensors.tick() == 1
    assert store.spots["A-01"].status is SpotStatus.OCCUPIED
    probe.readings["A-01"] = False
    sensors.tick()
    assert store.spots["A-01"].status is SpotStatus.FREE


def test_tick_without_changes_returns_zero(sensors):
    assert sensors.tick() == 0


def test_sensor_does_not_touch_reserved_spot(sensors, probe, reservations, store):
    reservations.reserve("u1", "A-01")
    probe.readings["A-01"] = True
    sensors.tick()
    assert store.spots["A-01"].status is SpotStatus.RESERVED


def test_sensor_does_not_free_spot_of_confirmed_reservation(
    sensors, probe, reservations, access, store
):
    r = reservations.reserve("u1", "A-01")
    access.confirm_entry(r.id)
    probe.readings["A-01"] = False  # sensor glitch
    sensors.tick()
    assert store.spots["A-01"].status is SpotStatus.OCCUPIED
