"""Use cases. Every service receives its collaborators through the constructor (DI)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

from parking.domain.entities import Reservation, Spot, SpotStatus
from parking.domain.errors import (
    ReservationExpired,
    UserAlreadyHasReservation,
)
from parking.domain.ports import Clock, OccupancyProbe, UnitOfWorkFactory


class ReservationService:
    """Reserve a spot for 'now' and expire reservations nobody used."""

    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock, ttl: timedelta) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._ttl = ttl

    def reserve(self, user_code: str, spot_code: str) -> Reservation:
        with self._uow_factory() as uow:
            # Row lock: two users racing for the same spot are serialized here.
            spot = uow.spots.get_by_code(spot_code, for_update=True)
            if uow.reservations.get_open_for_user(user_code) is not None:
                raise UserAlreadyHasReservation(f"User {user_code} already has an open reservation")
            spot.reserve()  # raises SpotNotAvailable unless FREE
            reservation = Reservation.create(spot_code, user_code, self._clock.now(), self._ttl)
            uow.spots.save(spot)
            uow.reservations.add(reservation)
            uow.commit()
            return reservation

    def get(self, reservation_id: str) -> Reservation:
        with self._uow_factory() as uow:
            return uow.reservations.get(reservation_id)

    def list_open(self) -> List[Reservation]:
        with self._uow_factory() as uow:
            return uow.reservations.list_open()

    def expire_overdue(self) -> int:
        """Expire ACTIVE reservations whose time is over and free their spots."""
        now = self._clock.now()
        with self._uow_factory() as uow:
            codes = [r.id for r in uow.reservations.list_overdue(now)]
        expired = 0
        for reservation_id in codes:
            with self._uow_factory() as uow:
                reservation = uow.reservations.get(reservation_id, for_update=True)
                spot = uow.spots.get_by_code(reservation.spot_code, for_update=True)
                if not reservation.is_overdue(now):
                    continue  # changed in the meantime (e.g. the vehicle just entered)
                reservation.expire()
                spot.release()
                uow.reservations.save(reservation)
                uow.spots.save(spot)
                uow.commit()
                expired += 1
        return expired


class AccessService:
    """Vehicle entry (validates the reservation) and exit (frees the spot)."""

    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    def confirm_entry(self, reservation_id: str) -> Reservation:
        now = self._clock.now()
        expired = False
        with self._uow_factory() as uow:
            reservation = uow.reservations.get(reservation_id, for_update=True)
            spot = uow.spots.get_by_code(reservation.spot_code, for_update=True)
            if reservation.is_overdue(now):
                reservation.expire()
                spot.release()
                uow.reservations.save(reservation)
                uow.spots.save(spot)
                uow.commit()
                expired = True
            else:
                reservation.confirm_entry(now)
                spot.occupy_by_reservation()
                uow.reservations.save(reservation)
                uow.spots.save(spot)
                uow.commit()
                return reservation
        if expired:
            raise ReservationExpired("Reservation time is over; the spot was released")
        raise AssertionError("unreachable")

    def register_exit(self, reservation_id: str) -> Reservation:
        now = self._clock.now()
        with self._uow_factory() as uow:
            reservation = uow.reservations.get(reservation_id, for_update=True)
            spot = uow.spots.get_by_code(reservation.spot_code, for_update=True)
            reservation.complete(now)
            spot.release()
            uow.reservations.save(reservation)
            uow.spots.save(spot)
            uow.commit()
            return reservation


class SensorService:
    """Applies simulated sensor readings to the spots."""

    def __init__(self, uow_factory: UnitOfWorkFactory, probe: OccupancyProbe) -> None:
        self._uow_factory = uow_factory
        self._probe = probe

    def tick(self) -> int:
        """One reading round over all spots. Returns how many spots changed."""
        with self._uow_factory() as uow:
            codes = [s.code for s in uow.spots.list_all()]
        changed = 0
        for code in codes:
            with self._uow_factory() as uow:
                spot = uow.spots.get_by_code(code, for_update=True)
                if spot.status is SpotStatus.RESERVED:
                    continue
                if uow.reservations.get_open_for_spot(code) is not None:
                    continue  # occupied by a confirmed reservation: sensors do not override it
                reading = self._probe.read(code, spot.status is SpotStatus.OCCUPIED)
                if spot.apply_sensor_reading(reading):
                    uow.spots.save(spot)
                    uow.commit()
                    changed += 1
        return changed


@dataclass
class ZoneOccupancy:
    zone: str
    total: int
    free: int
    reserved: int
    occupied: int
    spots: List[Spot]


class OccupancyService:
    """Read model for the real-time occupancy map."""

    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    def now(self) -> datetime:
        return self._clock.now()

    def get_map(self) -> List[ZoneOccupancy]:
        with self._uow_factory() as uow:
            spots = sorted(uow.spots.list_all(), key=lambda s: s.code)
        zones: dict[str, List[Spot]] = {}
        for spot in spots:
            zones.setdefault(spot.zone, []).append(spot)
        result = []
        for zone, items in sorted(zones.items()):
            count = lambda st: sum(1 for s in items if s.status is st)  # noqa: E731
            result.append(ZoneOccupancy(
                zone=zone, total=len(items),
                free=count(SpotStatus.FREE),
                reserved=count(SpotStatus.RESERVED),
                occupied=count(SpotStatus.OCCUPIED),
                spots=items,
            ))
        return result
