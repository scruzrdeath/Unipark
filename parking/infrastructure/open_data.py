"""HTTP client for Colombian open-data APIs published on datos.gov.co (Socrata SODA)."""
from __future__ import annotations

import json
import socket
import time
from typing import Any, Callable, Dict, List, Optional
from urllib import error, parse, request

from parking.domain.errors import ExternalServiceUnavailable
from parking.domain.ports import ExternalDataSource
from parking.infrastructure.resilience import CircuitBreaker, call_with_retry


class TransientHttpError(Exception):
    """Timeouts, connection problems, HTTP 429 / 5xx: worth retrying."""


class PermanentHttpError(Exception):
    """HTTP 4xx (except 429) or an invalid payload: retrying will not help."""


Transport = Callable[[str, Dict[str, str], float], bytes]


def urllib_transport(url: str, headers: Dict[str, str], timeout: float) -> bytes:
    req = request.Request(url, headers=headers)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except error.HTTPError as exc:
        if exc.code == 429 or exc.code >= 500:
            raise TransientHttpError(f"HTTP {exc.code}") from exc
        raise PermanentHttpError(f"HTTP {exc.code}") from exc
    except (error.URLError, socket.timeout, TimeoutError, ConnectionError) as exc:
        raise TransientHttpError(str(exc)) from exc


class SocrataDataSource(ExternalDataSource):
    def __init__(
        self,
        resource_id: str,
        base_url: str = "https://www.datos.gov.co",
        app_token: Optional[str] = None,
        timeout: float = 10.0,
        attempts: int = 3,
        base_delay: float = 0.5,
        breaker: Optional[CircuitBreaker] = None,
        transport: Transport = urllib_transport,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._resource_id = resource_id
        self._base_url = base_url.rstrip("/")
        self._token = app_token
        self._timeout = timeout
        self._attempts = attempts
        self._base_delay = base_delay
        self.breaker = breaker or CircuitBreaker()
        self._transport = transport
        self._sleep = sleep

    def _url(self, limit: int, offset: int, where: Optional[str]) -> str:
        params = {"$limit": limit, "$offset": offset}
        if where:
            params["$where"] = where
        return f"{self._base_url}/resource/{self._resource_id}.json?{parse.urlencode(params)}"

    def _get_once(self, url: str) -> List[Dict[str, Any]]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["X-App-Token"] = self._token
        raw = self._transport(url, headers, self._timeout)
        try:
            data = json.loads(raw)
        except ValueError as exc:
            raise PermanentHttpError("Response is not valid JSON") from exc
        if not isinstance(data, list):
            raise PermanentHttpError("Unexpected JSON shape (expected a list of records)")
        return data

    def fetch(self, limit: int = 1000, offset: int = 0, where: Optional[str] = None) -> List[Dict[str, Any]]:
        url = self._url(limit, offset, where)

        def with_retry() -> List[Dict[str, Any]]:
            return call_with_retry(
                lambda: self._get_once(url), retry_on=(TransientHttpError,),
                attempts=self._attempts, base_delay=self._base_delay, sleep=self._sleep,
            )

        try:
            return self.breaker.call(with_retry)
        except (TransientHttpError, PermanentHttpError) as exc:
            raise ExternalServiceUnavailable(f"datos.gov.co/{self._resource_id}: {exc}") from exc
