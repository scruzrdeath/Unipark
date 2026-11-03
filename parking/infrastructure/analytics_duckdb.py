"""DuckDB adapter: runs SQL over the JSON records (filters, aggregations, basic statistics)."""
from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict, List, Optional

import duckdb

from parking.domain.errors import InvalidQuery
from parking.domain.ports import DataAnalyzer


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


class DuckDbAnalyzer(DataAnalyzer):
    def summarize(self, rows: List[Dict[str, Any]], group_by: Optional[str] = None,
                  filter_column: Optional[str] = None,
                  filter_value: Optional[str] = None) -> Dict[str, Any]:
        if not rows:
            return {"row_count": 0, "numeric": {}, "groups": []}
        fd, path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(rows, fh)
            con = duckdb.connect(":memory:")
            try:
                con.execute("CREATE TABLE raw AS SELECT * FROM read_json_auto(?)", [path])
                columns = [r[0] for r in con.execute("DESCRIBE raw").fetchall()]
                if filter_column is not None:
                    if filter_column not in columns:
                        raise InvalidQuery(f"Unknown column '{filter_column}'. Available: {columns}")
                    con.execute(
                        f"CREATE TABLE t AS SELECT * FROM raw WHERE CAST({_q(filter_column)} AS VARCHAR) = ?",
                        [filter_value],
                    )
                else:
                    con.execute("CREATE TABLE t AS SELECT * FROM raw")
                row_count = con.execute("SELECT count(*) FROM t").fetchone()[0]
                numeric = self._numeric_stats(con, columns)
                groups = self._groups(con, columns, group_by) if group_by else []
            finally:
                con.close()
        finally:
            os.remove(path)
        return {"row_count": row_count, "filter": {"column": filter_column, "value": filter_value},
                "columns": columns, "numeric": numeric, "groups": groups}

    @staticmethod
    def _numeric_stats(con, columns: List[str]) -> Dict[str, Dict[str, float]]:
        out: Dict[str, Dict[str, float]] = {}
        for col in columns:
            c = _q(col)
            try:  # Socrata returns numbers as strings, so we try to cast every column
                mn, avg, mx, casts, filled = con.execute(
                    f"SELECT min(TRY_CAST({c} AS DOUBLE)), avg(TRY_CAST({c} AS DOUBLE)), "
                    f"max(TRY_CAST({c} AS DOUBLE)), count(TRY_CAST({c} AS DOUBLE)), count({c}) FROM t"
                ).fetchone()
            except duckdb.Error:
                continue  # nested/unsupported column types
            if casts and filled and casts / filled >= 0.8:
                out[col] = {"min": mn, "avg": round(avg, 4), "max": mx}
        return out

    @staticmethod
    def _groups(con, columns: List[str], group_by: str) -> List[Dict[str, Any]]:
        if group_by not in columns:
            raise InvalidQuery(f"Unknown column '{group_by}'. Available: {columns}")
        c = _q(group_by)
        rows = con.execute(
            f"SELECT CAST({c} AS VARCHAR) AS value, count(*) AS n FROM t "
            f"GROUP BY 1 ORDER BY n DESC, value LIMIT 10"
        ).fetchall()
        return [{"value": v, "count": n} for v, n in rows]
