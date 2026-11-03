import pytest

from parking.domain.errors import CircuitOpen
from parking.infrastructure.resilience import CircuitBreaker, call_with_retry


class Boom(Exception):
    pass


class FakeTime:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_retry_succeeds_after_failures_with_exponential_waits():
    calls, waits = [], []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise Boom()
        return "ok"

    assert call_with_retry(flaky, (Boom,), attempts=3, base_delay=0.5, sleep=waits.append) == "ok"
    assert len(calls) == 3
    assert waits == [0.5, 1.0]


def test_retry_gives_up_after_three_attempts():
    calls, waits = [], []

    def always():
        calls.append(1)
        raise Boom()

    with pytest.raises(Boom):
        call_with_retry(always, (Boom,), attempts=3, sleep=waits.append)
    assert len(calls) == 3 and len(waits) == 2


def test_non_retryable_error_is_not_retried():
    calls = []

    def bad():
        calls.append(1)
        raise ValueError()

    with pytest.raises(ValueError):
        call_with_retry(bad, (Boom,), attempts=3, sleep=lambda s: None)
    assert len(calls) == 1


def fail():
    raise Boom()


def test_breaker_closed_open_half_open_closed():
    t = FakeTime()
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=30, time_fn=t)
    assert cb.state == "closed"
    for _ in range(2):
        with pytest.raises(Boom):
            cb.call(fail)
    assert cb.state == "open"
    with pytest.raises(CircuitOpen):
        cb.call(lambda: "never runs")
    t.t = 30
    assert cb.state == "half-open"
    assert cb.call(lambda: "ok") == "ok"
    assert cb.state == "closed"


def test_half_open_failure_reopens():
    t = FakeTime()
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10, time_fn=t)
    with pytest.raises(Boom):
        cb.call(fail)
    t.t = 10
    assert cb.state == "half-open"
    with pytest.raises(Boom):
        cb.call(fail)
    assert cb.state == "open"
    with pytest.raises(CircuitOpen):
        cb.call(lambda: 1)


def test_success_resets_failure_count():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=30, time_fn=FakeTime())
    with pytest.raises(Boom):
        cb.call(fail)
    cb.call(lambda: 1)
    with pytest.raises(Boom):
        cb.call(fail)
    assert cb.state == "closed"
