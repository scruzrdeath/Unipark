"""Request/response models (the REST contract)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from parking.application.open_data_service import DataPage
from parking.application.services import ZoneOccupancy
from parking.domain.entities import Reservation, Spot


class ReserveRequest(BaseModel):
    user_code: str = Field(min_length=1, max_length=40, examples=["u1001"])
    spot_code: str = Field(min_length=1, max_length=20, examples=["A-01"])


class ReservationOut(BaseModel):
    id: str
    spot_code: str
    user_code: str
    status: str
    created_at: datetime
    expires_at: datetime
    entered_at: Optional[datetime] = None
    exited_at: Optional[datetime] = None

    @staticmethod
    def of(r: Reservation) -> "ReservationOut":
        return ReservationOut(
            id=r.id, spot_code=r.spot_code, user_code=r.user_code, status=r.status.value,
            created_at=r.created_at, expires_at=r.expires_at,
            entered_at=r.entered_at, exited_at=r.exited_at,
        )


class SpotOut(BaseModel):
    code: str
    name: str
    zone: str
    status: str

    @staticmethod
    def of(s: Spot) -> "SpotOut":
        return SpotOut(code=s.code, name=s.name, zone=s.zone, status=s.status.value)


class ZoneOut(BaseModel):
    zone: str
    total: int
    free: int
    reserved: int
    occupied: int
    spots: List[SpotOut]

    @staticmethod
    def of(z: ZoneOccupancy) -> "ZoneOut":
        return ZoneOut(
            zone=z.zone, total=z.total, free=z.free, reserved=z.reserved,
            occupied=z.occupied, spots=[SpotOut.of(s) for s in z.spots],
        )


class OccupancyMapOut(BaseModel):
    simulated_time: datetime
    zones: List[ZoneOut]


class DataPageOut(BaseModel):
    source: str
    page: int
    page_size: int
    total: int
    stale: bool = Field(description="True when the external API failed and cached data was served")
    items: List[Dict[str, Any]]

    @staticmethod
    def of(p: DataPage) -> "DataPageOut":
        return DataPageOut(source=p.source, page=p.page, page_size=p.page_size,
                           total=p.total, stale=p.stale, items=p.items)
