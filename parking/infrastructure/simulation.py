"""Simulated IoT sensors: a background thread that keeps updating the spots."""
from __future__ import annotations

import logging
import random
import threading
from typing import Optional

from parking.application.services import ReservationService, SensorService
from parking.domain.ports import OccupancyProbe

log = logging.getLogger(__name__)


class RandomProbe(OccupancyProbe):
    """Each reading flips the spot state with probability ``flip_probability``."""

    def __init__(self, flip_probability: float = 0.1, rng: Optional[random.Random] = None) -> None:
        self._p = flip_probability
        self._rng = rng or random.Random()

    def read(self, spot_code: str, currently_occupied: bool) -> bool:
        if self._rng.random() < self._p:
            return not currently_occupied
        return currently_occupied


class SimulationRunner:
    """One thread: every ``interval`` real seconds run a sensor round and expire reservations."""

    def __init__(self, sensors: SensorService, reservations: ReservationService,
                 interval: float = 1.0) -> None:
        self._sensors = sensors
        self._reservations = reservations
        self._interval = interval
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="sensor-simulation", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._sensors.tick()
                self._reservations.expire_overdue()
            except Exception:  # keep the simulation alive
                log.exception("Simulation round failed")
            self._stop.wait(self._interval)
