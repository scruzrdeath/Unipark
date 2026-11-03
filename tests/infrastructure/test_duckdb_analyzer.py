import pytest

pytest.importorskip("duckdb")

from parking.domain.errors import InvalidQuery  # noqa: E402
from parking.infrastructure.analytics_duckdb import DuckDbAnalyzer  # noqa: E402

ROWS = [
    {"zona": "A", "valor": "10", "nombre": "x"},
    {"zona": "A", "valor": "20", "nombre": "y"},
    {"zona": "B", "valor": "30", "nombre": "z"},
]


def test_counts_numeric_stats_and_groups():
    s = DuckDbAnalyzer().summarize(ROWS, group_by="zona")
    assert s["row_count"] == 3
    assert s["numeric"]["valor"] == {"min": 10.0, "avg": 20.0, "max": 30.0}
    assert "nombre" not in s["numeric"]
    assert s["groups"][0] == {"value": "A", "count": 2}


def test_empty_rows():
    assert DuckDbAnalyzer().summarize([])["row_count"] == 0


def test_unknown_group_column():
    with pytest.raises(InvalidQuery):
        DuckDbAnalyzer().summarize(ROWS, group_by="nope")


def test_filter_then_stats():
    s = DuckDbAnalyzer().summarize(ROWS, filter_column="zona", filter_value="A")
    assert s["row_count"] == 2
    assert s["numeric"]["valor"]["avg"] == 15.0


def test_unknown_filter_column():
    with pytest.raises(InvalidQuery):
        DuckDbAnalyzer().summarize(ROWS, filter_column="nope", filter_value="x")
