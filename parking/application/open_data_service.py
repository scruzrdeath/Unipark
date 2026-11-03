from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional

from parking.application.cache import TTLCache
from parking.domain.errors import InvalidQuery, UnknownDataSource
from parking.domain.ports import DataAnalyzer, ExternalDataSource


@dataclass
class DataPage:
    source: str
    page: int
    page_size: int
    total: int
    items: List[Dict[str, Any]]
    stale: bool


class OpenDataService:
    """Reads Colombian open-data sources through cache (TTL), paginates and summarizes them."""

    def __init__(self, sources: Mapping[str, ExternalDataSource], analyzer: DataAnalyzer,
                 cache: TTLCache, fetch_limit: int = 1000, max_page_size: int = 100) -> None:
        self._sources = dict(sources)
        self._analyzer = analyzer
        self._cache = cache
        self._fetch_limit = fetch_limit
        self._max_page_size = max_page_size

    def source_names(self) -> List[str]:
        return sorted(self._sources)

    def _rows(self, name: str):
        source = self._sources.get(name)
        if source is None:
            raise UnknownDataSource(f"Unknown data source '{name}'. Available: {self.source_names()}")
        return self._cache.get_or_load(name, lambda: source.fetch(limit=self._fetch_limit))

    def get_page(self, name: str, page: int = 1, page_size: int = 20) -> DataPage:
        if page < 1 or not 1 <= page_size <= self._max_page_size:
            raise InvalidQuery(f"page must be >= 1 and page_size between 1 and {self._max_page_size}")
        rows, stale = self._rows(name)
        start = (page - 1) * page_size
        return DataPage(name, page, page_size, len(rows), rows[start:start + page_size], stale)

    def get_stats(self, name: str, group_by: Optional[str] = None,
                  filter_column: Optional[str] = None,
                  filter_value: Optional[str] = None) -> Dict[str, Any]:
        if (filter_column is None) != (filter_value is None):
            raise InvalidQuery("filter_column and filter_value must be given together")
        rows, stale = self._rows(name)
        stats = self._analyzer.summarize(rows, group_by, filter_column, filter_value)
        stats["source"] = name
        stats["stale"] = stale
        return stats
