"""Ports: interfaces the domain/application need from the outside world.

Adapters live in ``parking.infrastructure``. Dependencies point INTO the domain.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from parking.domain.entities import Reservation, Spot


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime:
        """Current (possibly simulated) time."""


class OccupancyProbe(ABC):
    """What a physical sensor would report for a spot."""

    @abstractmethod
    def read(self, spot_code: str, currently_occupied: bool) -> bool:
        """Return True if the sensor says the spot is occupied."""


class SpotRepository(ABC):
    @abstractmethod
    def add(self, spot: Spot) -> None: ...

    @abstractmethod
    def get_by_code(self, code: str, for_update: bool = False) -> Spot:
        """Raise SpotNotFound. ``for_update`` locks the row until the transaction ends."""

    @abstractmethod
    def list_all(self) -> List[Spot]: ...

    @abstractmethod
    def save(self, spot: Spot) -> None: ...


class ReservationRepository(ABC):
    @abstractmethod
    def add(self, reservation: Reservation) -> None: ...

    @abstractmethod
    def get(self, reservation_id: str, for_update: bool = False) -> Reservation:
        """Raise ReservationNotFound. ``for_update`` locks the row until the transaction ends."""

    @abstractmethod
    def get_open_for_user(self, user_code: str) -> Optional[Reservation]: ...

    @abstractmethod
    def get_open_for_spot(self, spot_code: str) -> Optional[Reservation]: ...

    @abstractmethod
    def list_open(self) -> List[Reservation]: ...

    @abstractmethod
    def list_overdue(self, now: datetime) -> List[Reservation]: ...

    @abstractmethod
    def save(self, reservation: Reservation) -> None: ...


class UnitOfWork(ABC):
    """One atomic transaction. Commits only when ``commit()`` is called."""

    spots: SpotRepository
    reservations: ReservationRepository

    @abstractmethod
    def __enter__(self) -> "UnitOfWork": ...

    @abstractmethod
    def __exit__(self, exc_type, exc, tb) -> None: ...

    @abstractmethod
    def commit(self) -> None: ...


UnitOfWorkFactory = Callable[[], UnitOfWork]


class ExternalDataSource(ABC):
    """A remote open-data API that returns a list of JSON records."""

    @abstractmethod
    def fetch(self, limit: int = 1000, offset: int = 0, where: Optional[str] = None) -> List[Dict[str, Any]]:
        """Raise ExternalServiceUnavailable / CircuitOpen when the API cannot be used."""


class DataAnalyzer(ABC):
    """Computes statistics over JSON records (implemented with DuckDB)."""

    @abstractmethod
    def summarize(self, rows: List[Dict[str, Any]], group_by: Optional[str] = None,
                  filter_column: Optional[str] = None,
                  filter_value: Optional[str] = None) -> Dict[str, Any]:
        """Optionally keep only rows where ``filter_column`` equals ``filter_value``.

        Raise InvalidQuery if a column does not exist."""
