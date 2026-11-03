import pytest

from parking.application.cache import TTLCache
from parking.application.open_data_service import OpenDataService
from parking.domain.errors import ExternalServiceUnavailable, InvalidQuery, UnknownDataSource
from parking.domain.ports import DataAnalyzer, ExternalDataSource


class FakeSource(ExternalDataSource):
    def __init__(self, rows):
        self.rows, self.calls, self.fail = rows, 0, False

    def fetch(self, limit=1000, offset=0, where=None):
        self.calls += 1
        if self.fail:
            raise ExternalServiceUnavailable("down")
        return self.rows


class FakeAnalyzer(DataAnalyzer):
    def summarize(self, rows, group_by=None, filter_column=None, filter_value=None):
        return {"row_count": len(rows)}


class Now:
    t = 0.0

    def __call__(self):
        return self.t


@pytest.fixture
def now():
    return Now()


@pytest.fixture
def source():
    return FakeSource([{"i": n} for n in range(25)])


@pytest.fixture
def service(source, now):
    return OpenDataService({"parking": source}, FakeAnalyzer(), TTLCache(60, now))


def test_pagination(service):
    p = service.get_page("parking", page=3, page_size=10)
    assert p.total == 25 and [r["i"] for r in p.items] == [20, 21, 22, 23, 24]


def test_invalid_pagination(service):
    with pytest.raises(InvalidQuery):
        service.get_page("parking", page=0)
    with pytest.raises(InvalidQuery):
        service.get_page("parking", page_size=1000)


def test_unknown_source(service):
    with pytest.raises(UnknownDataSource):
        service.get_page("nope")


def test_cache_hit_within_ttl_then_refresh(service, source, now):
    service.get_page("parking")
    service.get_page("parking")
    assert source.calls == 1
    now.t = 61
    service.get_page("parking")
    assert source.calls == 2


def test_serves_stale_cache_when_api_fails(service, source, now):
    service.get_page("parking")
    now.t = 61
    source.fail = True
    page = service.get_page("parking")
    assert page.stale is True and page.total == 25


def test_error_without_cache_propagates(service, source):
    source.fail = True
    with pytest.raises(ExternalServiceUnavailable):
        service.get_page("parking")


def test_stats_uses_analyzer(service):
    s = service.get_stats("parking")
    assert s["row_count"] == 25 and s["source"] == "parking" and s["stale"] is False


def test_filter_requires_both_parts(service):
    with pytest.raises(InvalidQuery):
        service.get_stats("parking", filter_column="a")
