"""FastAPI application factory. The API only talks to the application layer."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable, List, Optional

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse

from parking.api.schemas import (
    DataPageOut,
    OccupancyMapOut,
    ReservationOut,
    ReserveRequest,
    ZoneOut,
)
from parking.application.container import Services
from parking.domain import errors

STATIC_DIR = Path(__file__).parent / "static"

# domain error -> HTTP status
_STATUS = {
    errors.CircuitOpen: 503,              # must precede its parent class
    errors.ExternalServiceUnavailable: 502,
    errors.UnknownDataSource: 404,
    errors.InvalidQuery: 400,
    errors.SpotNotFound: 404,
    errors.ReservationNotFound: 404,
    errors.SpotNotAvailable: 409,
    errors.UserAlreadyHasReservation: 409,
    errors.InvalidTransition: 409,
    errors.ReservationExpired: 410,
}


def create_app(
    services: Services,
    on_startup: Optional[Callable[[], None]] = None,
    on_shutdown: Optional[Callable[[], None]] = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if on_startup:
            on_startup()
        yield
        if on_shutdown:
            on_shutdown()

    app = FastAPI(title="University Parking Monitor", version="1.0.0", lifespan=lifespan)

    @app.exception_handler(errors.DomainError)
    async def domain_error_handler(_: Request, exc: errors.DomainError):
        status = next((code for cls, code in _STATUS.items() if isinstance(exc, cls)), 400)
        return JSONResponse(status_code=status, content={"detail": str(exc)})

    router = APIRouter(prefix="/api")

    @router.get("/map", response_model=OccupancyMapOut, summary="Real-time occupancy map")
    def occupancy_map():
        return OccupancyMapOut(
            simulated_time=services.occupancy.now(),
            zones=[ZoneOut.of(z) for z in services.occupancy.get_map()],
        )

    @router.get("/reservations", response_model=List[ReservationOut], summary="Open reservations")
    def list_open_reservations():
        return [ReservationOut.of(r) for r in services.reservations.list_open()]

    @router.post("/reservations", response_model=ReservationOut, status_code=201,
                 summary="Reserve a free spot")
    def reserve(body: ReserveRequest):
        return ReservationOut.of(services.reservations.reserve(body.user_code, body.spot_code))

    @router.get("/reservations/{reservation_id}", response_model=ReservationOut)
    def get_reservation(reservation_id: str):
        return ReservationOut.of(services.reservations.get(reservation_id))

    @router.post("/reservations/{reservation_id}/entry", response_model=ReservationOut,
                 summary="Confirm vehicle entry")
    def confirm_entry(reservation_id: str):
        return ReservationOut.of(services.access.confirm_entry(reservation_id))

    @router.post("/reservations/{reservation_id}/exit", response_model=ReservationOut,
                 summary="Register vehicle exit (frees the spot)")
    def register_exit(reservation_id: str):
        return ReservationOut.of(services.access.register_exit(reservation_id))

    def open_data():
        if services.open_data is None:
            raise errors.UnknownDataSource("Open-data integration is not configured")
        return services.open_data

    @router.get("/open-data/sources", response_model=List[str], tags=["open-data"],
                summary="List the available Colombian open-data sources")
    def open_data_sources():
        return open_data().source_names()

    @router.get("/open-data/{source}", response_model=DataPageOut, tags=["open-data"],
                summary="Records of a source (cached, paginated)")
    def open_data_page(source: str,
                       page: int = Query(1, ge=1, description="Page number, starting at 1"),
                       page_size: int = Query(20, ge=1, le=100, description="Records per page")):
        return DataPageOut.of(open_data().get_page(source, page, page_size))

    @router.get("/open-data/{source}/stats", tags=["open-data"],
                summary="Statistics computed with DuckDB (count, min/avg/max, top groups)")
    def open_data_stats(source: str,
                        group_by: Optional[str] = Query(None, description="Column to count by"),
                        filter_column: Optional[str] = Query(None, description="Keep rows where this column..."),
                        filter_value: Optional[str] = Query(None, description="...equals this value")):
        return open_data().get_stats(source, group_by, filter_column, filter_value)

    app.include_router(router)

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    return app
