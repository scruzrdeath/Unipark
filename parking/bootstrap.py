"""Composition root: the only place that knows every layer and wires them together."""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from parking.api.app import create_app
from parking.application.cache import TTLCache
from parking.application.container import Services
from parking.application.open_data_service import OpenDataService
from parking.application.services import (
    AccessService,
    OccupancyService,
    ReservationService,
    SensorService,
)
from parking.infrastructure.clock import SimulatedClock
from parking.infrastructure.config import Settings
from parking.infrastructure.seed import seed_spots
from parking.infrastructure.simulation import RandomProbe, SimulationRunner


def build_services(settings: Settings):
    if settings.database_url:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from parking.infrastructure.sql_models import Base
        from parking.infrastructure.sql_repositories import SqlAlchemyUnitOfWork

        engine = create_engine(settings.database_url, pool_pre_ping=True)
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(engine, expire_on_commit=False)

        def uow_factory():
            return SqlAlchemyUnitOfWork(session_factory)
    else:
        from parking.infrastructure.in_memory import InMemoryStore

        uow_factory = InMemoryStore().uow_factory

    seed_spots(uow_factory)
    clock = SimulatedClock(speed=settings.clock_speed)
    ttl = timedelta(minutes=settings.reservation_minutes)

    from parking.infrastructure.analytics_duckdb import DuckDbAnalyzer
    from parking.infrastructure.open_data import SocrataDataSource

    def soda(resource_id: str) -> SocrataDataSource:  # one circuit breaker per external API
        return SocrataDataSource(resource_id, app_token=settings.soda_app_token,
                                 timeout=settings.http_timeout)

    open_data = OpenDataService(
        sources={"parking": soda(settings.parking_dataset_id),
                 "weather": soda(settings.weather_dataset_id)},
        analyzer=DuckDbAnalyzer(),
        cache=TTLCache(settings.cache_ttl_seconds),
    )

    services = Services(
        reservations=ReservationService(uow_factory, clock, ttl),
        access=AccessService(uow_factory, clock),
        sensors=SensorService(uow_factory, RandomProbe()),
        occupancy=OccupancyService(uow_factory, clock),
        open_data=open_data,
    )
    runner: Optional[SimulationRunner] = None
    if settings.simulation_enabled:
        runner = SimulationRunner(services.sensors, services.reservations, settings.tick_interval)
    return services, runner


def create_app_from_env():
    settings = Settings.from_env()
    services, runner = build_services(settings)
    return create_app(
        services,
        on_startup=runner.start if runner else None,
        on_shutdown=runner.stop if runner else None,
    )
