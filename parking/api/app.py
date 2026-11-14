"""FastAPI application factory. The API only talks to the application layer."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable, List, Optional

from fastapi import APIRouter, Depends, FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from parking.api.schemas import (
    CredentialsRequest,
    DataPageOut,
    OccupancyMapOut,
    ReservationOut,
    ReserveRequest,
    TokenOut,
    UserOut,
    ZoneOut,
)
from parking.application.auth_service import AuthService
from parking.application.container import Services
from parking.domain import errors
from parking.domain.entities import User

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
    errors.InvalidCredentials: 401,
    errors.InvalidToken: 401,
    errors.Forbidden: 403,
    errors.UsernameTaken: 409,
    errors.WeakPassword: 400,
    errors.TooManyAttempts: 429,
}

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
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
        headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
        return JSONResponse(status_code=status, content={"detail": str(exc)}, headers=headers)

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response

    bearer = HTTPBearer(auto_error=False, description="Paste the access_token returned by /api/auth/login")

    def auth_service() -> AuthService:
        if services.auth is None:
            raise errors.InvalidToken("Authentication is not configured")
        return services.auth

    def current_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> str:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise errors.InvalidToken("Missing bearer token")
        return credentials.credentials

    def current_user(token: str = Depends(current_token)) -> User:
        return auth_service().authenticate(token)

    router = APIRouter(prefix="/api")

    @router.post("/auth/register", response_model=UserOut, status_code=201, tags=["auth"],
                 summary="Create an account (password stored with BCrypt)")
    def register(body: CredentialsRequest):
        return UserOut(username=auth_service().register(body.username, body.password).username)

    @router.post("/auth/login", response_model=TokenOut, tags=["auth"],
                 summary="Log in and get a JWT access token")
    def login(body: CredentialsRequest):
        return TokenOut(access_token=auth_service().login(body.username, body.password))

    @router.post("/auth/logout", status_code=204, tags=["auth"],
                 summary="Log out: the token is revoked and stops working")
    def logout(token: str = Depends(current_token)):
        auth_service().logout(token)

    @router.get("/auth/me", response_model=UserOut, tags=["auth"], summary="Current user")
    def me(user: User = Depends(current_user)):
        return UserOut(username=user.username)

    @router.get("/map", response_model=OccupancyMapOut, summary="Real-time occupancy map (requires login)")
    def occupancy_map(user: User = Depends(current_user)):
        return OccupancyMapOut(
            simulated_time=services.occupancy.now(),
            zones=[ZoneOut.of(z) for z in services.occupancy.get_map()],
        )

    @router.get("/reservations", response_model=List[ReservationOut], summary="My open reservations")
    def list_open_reservations(user: User = Depends(current_user)):
        return [ReservationOut.of(r) for r in services.reservations.list_open(user.username)]

    @router.post("/reservations", response_model=ReservationOut, status_code=201,
                 summary="Reserve a free spot")
    def reserve(body: ReserveRequest, user: User = Depends(current_user)):
        return ReservationOut.of(services.reservations.reserve(user.username, body.spot_code))

    @router.get("/reservations/{reservation_id}", response_model=ReservationOut)
    def get_reservation(reservation_id: str, user: User = Depends(current_user)):
        return ReservationOut.of(services.reservations.get(reservation_id, requested_by=user.username))

    @router.post("/reservations/{reservation_id}/entry", response_model=ReservationOut,
                 summary="Confirm vehicle entry")
    def confirm_entry(reservation_id: str, user: User = Depends(current_user)):
        return ReservationOut.of(services.access.confirm_entry(reservation_id, requested_by=user.username))

    @router.post("/reservations/{reservation_id}/exit", response_model=ReservationOut,
                 summary="Register vehicle exit (frees the spot)")
    def register_exit(reservation_id: str, user: User = Depends(current_user)):
        return ReservationOut.of(services.access.register_exit(reservation_id, requested_by=user.username))

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
