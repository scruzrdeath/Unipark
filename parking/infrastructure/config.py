from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Settings:
    database_url: Optional[str]      # None => in-memory dev mode
    simulation_enabled: bool = True
    clock_speed: float = 60.0        # 1 real second = 1 simulated minute
    reservation_minutes: int = 60    # simulated minutes (= 60 real seconds at speed 60)
    tick_interval: float = 1.0       # real seconds between sensor rounds
    parking_dataset_id: str = "nc84-cdcp"   # datos.gov.co: Parqueaderos Publicos Chinchina (verify it returns JSON)
    weather_dataset_id: str = "s54a-sgyg"   # datos.gov.co: Precipitacion (IDEAM)
    soda_app_token: Optional[str] = None
    http_timeout: float = 10.0
    cache_ttl_seconds: float = 300.0

    @staticmethod
    def from_env() -> "Settings":
        return Settings(
            database_url=os.environ.get("DATABASE_URL") or None,
            simulation_enabled=os.environ.get("SIMULATION_ENABLED", "true").lower() == "true",
            parking_dataset_id=os.environ.get("PARKING_DATASET_ID", "nc84-cdcp"),
            weather_dataset_id=os.environ.get("WEATHER_DATASET_ID", "s54a-sgyg"),
            soda_app_token=os.environ.get("SODA_APP_TOKEN") or None,
            http_timeout=float(os.environ.get("HTTP_TIMEOUT", "10")),
            cache_ttl_seconds=float(os.environ.get("CACHE_TTL_SECONDS", "300")),
        )
