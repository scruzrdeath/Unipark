from __future__ import annotations

from typing import Sequence

from parking.domain.entities import Spot
from parking.domain.ports import UnitOfWorkFactory


def seed_spots(uow_factory: UnitOfWorkFactory, zones: Sequence[str] = ("A", "B"),
               per_zone: int = 10) -> int:
    """Create zones x spots (A-01..A-10, B-01..B-10). Idempotent: does nothing if spots exist."""
    with uow_factory() as uow:
        if uow.spots.list_all():
            return 0
        created = 0
        for zone in zones:
            for i in range(1, per_zone + 1):
                code = f"{zone}-{i:02d}"
                uow.spots.add(Spot(code=code, name=f"Spot {code}", zone=zone))
                created += 1
        uow.commit()
        return created
