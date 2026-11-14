"""Ports: interfaces the domain/application need from the outside world.

Adapters live in ``parking.infrastructure``. Dependencies point INTO the domain.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from parking.domain.entities import Reservation, Spot, User


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


class UserRepository(ABC):
    @abstractmethod
    def add(self, user: User) -> None:
        """Raise UsernameTaken if the username already exists."""

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]: ...


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, password: str) -> str: ...

    @abstractmethod
    def verify(self, password: str, password_hash: str) -> bool: ...


@dataclass(frozen=True)
class TokenClaims:
    subject: str
    token_id: str
    expires_at: float      # epoch seconds


class TokenService(ABC):
    @abstractmethod
    def issue(self, subject: str) -> str: ...

    @abstractmethod
    def decode(self, token: str) -> TokenClaims:
        """Raise InvalidToken when the token is invalid or expired."""


class TokenDenylist(ABC):
    """Revoked tokens (logout). Entries only need to live until the token expires."""

    @abstractmethod
    def revoke(self, token_id: str, expires_at: float) -> None: ...

    @abstractmethod
    def is_revoked(self, token_id: str) -> bool: ...
