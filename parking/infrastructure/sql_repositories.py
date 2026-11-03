"""SQLAlchemy adapters for the repository ports + Unit of Work (MySQL in production)."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from parking.domain.entities import Reservation, ReservationStatus, Spot, SpotStatus
from parking.domain.errors import ReservationNotFound, SpotNotFound
from parking.domain.ports import ReservationRepository, SpotRepository, UnitOfWork
from parking.infrastructure.sql_models import ReservationModel, SpotModel

_OPEN = (ReservationStatus.ACTIVE.value, ReservationStatus.CONFIRMED.value)


def _spot_to_entity(m: SpotModel) -> Spot:
    return Spot(code=m.code, name=m.name, zone=m.zone, status=SpotStatus(m.status))


def _res_to_entity(m: ReservationModel) -> Reservation:
    return Reservation(
        id=m.id, spot_code=m.spot_code, user_code=m.user_code,
        status=ReservationStatus(m.status), created_at=m.created_at,
        expires_at=m.expires_at, entered_at=m.entered_at, exited_at=m.exited_at,
    )


class SqlSpotRepository(SpotRepository):
    def __init__(self, session: Session) -> None:
        self._s = session

    def add(self, spot: Spot) -> None:
        self._s.add(SpotModel(code=spot.code, name=spot.name, zone=spot.zone, status=spot.status.value))
        self._s.flush()

    def get_by_code(self, code: str, for_update: bool = False) -> Spot:
        stmt = select(SpotModel).where(SpotModel.code == code)
        if for_update:
            stmt = stmt.with_for_update()  # SELECT ... FOR UPDATE (row lock in InnoDB)
        model = self._s.execute(stmt).scalar_one_or_none()
        if model is None:
            raise SpotNotFound(f"Spot {code} not found")
        return _spot_to_entity(model)

    def list_all(self) -> List[Spot]:
        rows = self._s.execute(select(SpotModel).order_by(SpotModel.code)).scalars().all()
        return [_spot_to_entity(m) for m in rows]

    def save(self, spot: Spot) -> None:
        model = self._s.get(SpotModel, spot.code)
        if model is None:
            raise SpotNotFound(f"Spot {spot.code} not found")
        model.name, model.zone, model.status = spot.name, spot.zone, spot.status.value
        self._s.flush()


class SqlReservationRepository(ReservationRepository):
    def __init__(self, session: Session) -> None:
        self._s = session

    def add(self, r: Reservation) -> None:
        self._s.add(ReservationModel(
            id=r.id, spot_code=r.spot_code, user_code=r.user_code, status=r.status.value,
            created_at=r.created_at, expires_at=r.expires_at,
            entered_at=r.entered_at, exited_at=r.exited_at,
        ))
        self._s.flush()

    def get(self, reservation_id: str, for_update: bool = False) -> Reservation:
        stmt = select(ReservationModel).where(ReservationModel.id == reservation_id)
        if for_update:
            stmt = stmt.with_for_update()
        model = self._s.execute(stmt).scalar_one_or_none()
        if model is None:
            raise ReservationNotFound(f"Reservation {reservation_id} not found")
        return _res_to_entity(model)

    def get_open_for_user(self, user_code: str) -> Optional[Reservation]:
        stmt = select(ReservationModel).where(
            ReservationModel.user_code == user_code, ReservationModel.status.in_(_OPEN)
        ).limit(1)
        model = self._s.execute(stmt).scalar_one_or_none()
        return _res_to_entity(model) if model else None

    def get_open_for_spot(self, spot_code: str) -> Optional[Reservation]:
        stmt = select(ReservationModel).where(
            ReservationModel.spot_code == spot_code, ReservationModel.status.in_(_OPEN)
        ).limit(1)
        model = self._s.execute(stmt).scalar_one_or_none()
        return _res_to_entity(model) if model else None

    def list_open(self) -> List[Reservation]:
        stmt = select(ReservationModel).where(ReservationModel.status.in_(_OPEN)).order_by(
            ReservationModel.created_at
        )
        return [_res_to_entity(m) for m in self._s.execute(stmt).scalars().all()]

    def list_overdue(self, now: datetime) -> List[Reservation]:
        stmt = select(ReservationModel).where(
            ReservationModel.status == ReservationStatus.ACTIVE.value,
            ReservationModel.expires_at <= now,
        )
        return [_res_to_entity(m) for m in self._s.execute(stmt).scalars().all()]

    def save(self, r: Reservation) -> None:
        model = self._s.get(ReservationModel, r.id)
        if model is None:
            raise ReservationNotFound(f"Reservation {r.id} not found")
        model.status = r.status.value
        model.expires_at = r.expires_at
        model.entered_at = r.entered_at
        model.exited_at = r.exited_at
        self._s.flush()


class SqlAlchemyUnitOfWork(UnitOfWork):
    """One DB transaction per ``with`` block. Rolls back unless ``commit()`` was called."""

    def __init__(self, session_factory: "sessionmaker[Session]") -> None:
        self._session_factory = session_factory

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = self._session_factory()
        self.spots = SqlSpotRepository(self._session)
        self.reservations = SqlReservationRepository(self._session)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            self._session.rollback()  # harmless after a commit
        finally:
            self._session.close()

    def commit(self) -> None:
        self._session.commit()
