def test_map_groups_by_zone_with_counts(occupancy, reservations, access, sensors, probe):
    reservations.reserve("u1", "A-01")
    r2 = reservations.reserve("u2", "A-02")
    access.confirm_entry(r2.id)
    probe.readings["B-01"] = True
    sensors.tick()

    zones = {z.zone: z for z in occupancy.get_map()}
    assert set(zones) == {"A", "B"}
    a, b = zones["A"], zones["B"]
    assert (a.total, a.free, a.reserved, a.occupied) == (3, 1, 1, 1)
    assert (b.total, b.free, b.reserved, b.occupied) == (3, 2, 0, 1)
    assert [s.code for s in a.spots] == ["A-01", "A-02", "A-03"]
