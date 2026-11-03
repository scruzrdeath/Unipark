"""Retry with exponential backoff + circuit breaker (closed / open / half-open)."""
from __future__ import annotations

import threading
import time
from typing import Callable, Tuple, Type, TypeVar

from parking.domain.errors import CircuitOpen

T = TypeVar("T")


def call_with_retry(
    func: Callable[[], T],
    retry_on: Tuple[Type[BaseException], ...],
    attempts: int = 3,
    base_delay: float = 0.5,
    factor: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Run ``func`` up to ``attempts`` times. Waits base_delay, base_delay*factor, ... between tries.

    Default schedule: 0.5 s, then 1.0 s (3 attempts => 2 waits).
    Only exceptions listed in ``retry_on`` are retried; anything else propagates at once.
    """
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except retry_on:
            if attempt == attempts:
                raise
            sleep(base_delay * (factor ** (attempt - 1)))
    raise AssertionError("unreachable")


class CircuitBreaker:
    """CLOSED: calls pass. After ``failure_threshold`` consecutive failures -> OPEN.
    OPEN: calls are rejected (CircuitOpen) until ``recovery_timeout`` seconds pass -> HALF_OPEN.
    HALF_OPEN: one trial call. Success -> CLOSED, failure -> OPEN again.
    """

    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half-open"

    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30.0,
                 time_fn: Callable[[], float] = time.monotonic) -> None:
        self._threshold = failure_threshold
        self._timeout = recovery_timeout
        self._time = time_fn
        self._lock = threading.Lock()
        self._state = self.CLOSED
        self._failures = 0
        self._opened_at = 0.0
        self._trial_in_flight = False

    @property
    def state(self) -> str:
        with self._lock:
            return self._current_state()

    def _current_state(self) -> str:
        if self._state == self.OPEN and self._time() - self._opened_at >= self._timeout:
            self._state = self.HALF_OPEN
            self._trial_in_flight = False
        return self._state

    def call(self, func: Callable[[], T]) -> T:
        with self._lock:
            state = self._current_state()
            if state == self.OPEN or (state == self.HALF_OPEN and self._trial_in_flight):
                raise CircuitOpen("Circuit breaker is open; external API call rejected")
            if state == self.HALF_OPEN:
                self._trial_in_flight = True
        try:
            result = func()
        except Exception:
            self._record_failure()
            raise
        self._record_success()
        return result

    def _record_success(self) -> None:
        with self._lock:
            self._state = self.CLOSED
            self._failures = 0
            self._trial_in_flight = False

    def _record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            self._trial_in_flight = False
            if self._state == self.HALF_OPEN or self._failures >= self._threshold:
                self._state = self.OPEN
                self._opened_at = self._time()
