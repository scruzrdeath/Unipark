"""In-memory adapters. A shared lock serializes transactions (like row locks would)."""
from __future__ import annotations

import copy
import threading
from datetime import datetime
from typing import Dict, List, Optional

from parking.domain.entities import Reservation, Spot
from parking.domain.errors import ReservationNotFound, SpotNotFound
from parking.domain.ports import (
    ReservationRepository,
    SpotRepository,
    UnitOfWork,
)


class InMemoryStore:
    def __init__(self) -> None:
        self.spots: Dict[str, Spot] = {}
        self.reservations: Dict[str, Reservation] = {}
        self.lock = threading.RLock()

    def uow_factory(self) -> "InMemoryUnitOfWork":
        return InMemoryUnitOfWork(self)


class _Spots(SpotRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._s = store

    def add(self, spot: Spot) -> None:
        self._s.spots[spot.code] = copy.deepcopy(spot)

    def get_by_code(self, code: str, for_update: bool = False) -> Spot:
        try:
            return copy.deepcopy(self._s.spots[code])
        except KeyError:
            raise SpotNotFound(f"Spot {code} not found") from None

    def list_all(self) -> List[Spot]:
        return [copy.deepcopy(s) for s in self._s.spots.values()]

    def save(self, spot: Spot) -> None:
        self._s.spots[spot.code] = copy.deepcopy(spot)


class _Reservations(ReservationRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._s = store

    def add(self, reservation: Reservation) -> None:
        self._s.reservations[reservation.id] = copy.deepcopy(reservation)

    def get(self, reservation_id: str, for_update: bool = False) -> Reservation:
        try:
            return copy.deepcopy(self._s.reservations[reservation_id])
        except KeyError:
            raise ReservationNotFound(f"Reservation {reservation_id} not found") from None

    def _open(self):
        return (r for r in self._s.reservations.values() if r.is_open)

    def get_open_for_user(self, user_code: str) -> Optional[Reservation]:
        return next((copy.deepcopy(r) for r in self._open() if r.user_code == user_code), None)

    def get_open_for_spot(self, spot_code: str) -> Optional[Reservation]:
        return next((copy.deepcopy(r) for r in self._open() if r.spot_code == spot_code), None)

    def list_open(self) -> List[Reservation]:
        return sorted((copy.deepcopy(r) for r in self._open()), key=lambda r: r.created_at)

    def list_overdue(self, now: datetime) -> List[Reservation]:
        return [copy.deepcopy(r) for r in self._s.reservations.values() if r.is_overdue(now)]

    def save(self, reservation: Reservation) -> None:
        self._s.reservations[reservation.id] = copy.deepcopy(reservation)


class InMemoryUnitOfWork(UnitOfWork):
    """No rollback: services validate before they mutate, so nothing is half-written."""

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store
        self.spots = _Spots(store)
        self.reservations = _Reservations(store)

    def __enter__(self) -> "InMemoryUnitOfWork":
        self._store.lock.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._store.lock.release()

    def commit(self) -> None:
        pass
