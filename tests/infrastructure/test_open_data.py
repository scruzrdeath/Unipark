import json

import pytest

from parking.domain.errors import CircuitOpen, ExternalServiceUnavailable
from parking.infrastructure.open_data import (
    PermanentHttpError,
    SocrataDataSource,
    TransientHttpError,
)
from parking.infrastructure.resilience import CircuitBreaker


class FakeTransport:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append((url, headers, timeout))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def make(transport, **kw):
    return SocrataDataSource("abcd-1234", transport=transport, sleep=lambda s: None, **kw)


def test_builds_soda_url_and_parses_json():
    t = FakeTransport(json.dumps([{"a": 1}]).encode())
    rows = make(t, app_token="tok", timeout=7).fetch(limit=5, offset=10, where="x > 1")
    assert rows == [{"a": 1}]
    url, headers, timeout = t.calls[0]
    assert url.startswith("https://www.datos.gov.co/resource/abcd-1234.json?")
    assert "%24limit=5" in url and "%24offset=10" in url and "%24where=x+%3E+1" in url
    assert headers["X-App-Token"] == "tok" and timeout == 7


def test_retries_transient_errors_then_succeeds():
    t = FakeTransport(TransientHttpError("503"), TransientHttpError("timeout"), b"[]")
    assert make(t).fetch() == []
    assert len(t.calls) == 3


def test_three_failed_attempts_raise_unavailable():
    t = FakeTransport(*[TransientHttpError("x")] * 3)
    with pytest.raises(ExternalServiceUnavailable):
        make(t).fetch()
    assert len(t.calls) == 3


def test_permanent_error_is_not_retried():
    t = FakeTransport(PermanentHttpError("HTTP 404"))
    with pytest.raises(ExternalServiceUnavailable):
        make(t).fetch()
    assert len(t.calls) == 1


def test_invalid_json_shape_rejected():
    with pytest.raises(ExternalServiceUnavailable):
        make(FakeTransport(b'{"not": "a list"}')).fetch()


def test_breaker_opens_and_stops_calling_the_api():
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
    t = FakeTransport(*[TransientHttpError("x")] * 6)
    src = make(t, breaker=breaker)
    for _ in range(2):
        with pytest.raises(ExternalServiceUnavailable):
            src.fetch()
    calls_before = len(t.calls)
    with pytest.raises(CircuitOpen):
        src.fetch()
    assert len(t.calls) == calls_before  # rejected without touching the network
