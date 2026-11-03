from __future__ import annotations

import threading
import time
from typing import Callable, Dict, Generic, Tuple, TypeVar

V = TypeVar("V")


class TTLCache(Generic[V]):
    """Tiny thread-safe cache. If the loader fails, an expired entry is served as 'stale'."""

    def __init__(self, ttl_seconds: float, now_fn: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._now = now_fn
        self._data: Dict[str, Tuple[V, float]] = {}
        self._lock = threading.Lock()

    def get_or_load(self, key: str, loader: Callable[[], V]) -> Tuple[V, bool]:
        """Return (value, stale)."""
        with self._lock:
            entry = self._data.get(key)
            if entry and self._now() < entry[1]:
                return entry[0], False
        try:
            value = loader()
        except Exception:
            if entry:
                return entry[0], True
            raise
        with self._lock:
            self._data[key] = (value, self._now() + self._ttl)
        return value, False
