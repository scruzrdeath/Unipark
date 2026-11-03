# University Parking Monitor (Proyecto 7)

Simulated IoT parking monitor with spot reservations. Hexagonal architecture (ports & adapters).

## Structure
```
parking/
  domain/          entities, state rules, errors, ports (interfaces)        <- depends on nothing
  application/     services (use cases) with constructor DI                 <- depends on domain
  infrastructure/  SQLAlchemy/MySQL, in-memory store, clock, sensors, seed  <- implements ports
  api/             FastAPI routers, schemas, web map (static/index.html)    <- calls application
  bootstrap.py     composition root (wires everything)
  main.py          uvicorn entry point
tests/             pytest (tests/test_architecture.py enforces the dependency direction)
```

## Run it (Windows: use `.venv\Scripts\activate`)
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
cp .env.example .env        # then edit DATABASE_URL (MySQL user/password)
uvicorn parking.main:app --reload
```
Open http://localhost:8000 (map) and http://localhost:8000/docs (Swagger).

Create the database once in MySQL Workbench / Shell: `CREATE DATABASE parqueaderos;`
Tables and the 20 spots (zones A and B, 10 each) are created automatically on startup.
Without `DATABASE_URL` the app runs with an in-memory store (handy for a quick demo).

## Rules implemented
- Spot states: FREE -> RESERVED -> OCCUPIED -> FREE.
- Reservation: for "now", lasts 60 real seconds (1 real second = 1 simulated minute, so 60 sim-minutes).
- Concurrency: `SELECT ... FOR UPDATE` on the spot row, so two users cannot reserve the same spot.
- Sensors (one background thread) skip RESERVED spots and spots of a confirmed reservation.
- Exit frees the spot; unused reservations expire and free the spot.

## Not yet (out of scope for v1)
Stress test, hourly statistics, sensor-vs-reservation conflict handling.

## Module 12: Colombian open data (datos.gov.co)
Two sources, both Socrata SODA APIs (no key needed for light use; optional `SODA_APP_TOKEN`):
- `parking`: dataset `nc84-cdcp` (Parqueaderos Publicos Chinchina). NOTE: `ih37-pssa` is a map-type dataset and does NOT work through /resource/ ("non-tabular"). Alternatives: `u3vn-bdcy` (parque automotor RUNT), `b9s9-jw7c` (aforos vehiculares).
- `weather`: dataset `s54a-sgyg` (Precipitacion, IDEAM)

Check what a dataset returns by opening, e.g., `https://www.datos.gov.co/resource/nc84-cdcp.json?$limit=3`.
To use another dataset change `PARKING_DATASET_ID` / `WEATHER_DATASET_ID` in `.env`.

Endpoints (see `/docs`):
- `GET /api/open-data/sources`
- `GET /api/open-data/{source}?page=1&page_size=20`  (cached, paginated)
- `GET /api/open-data/{source}/stats?group_by=<column>&filter_column=<column>&filter_value=<value>`  (DuckDB: optional filter, row count, min/avg/max of numeric columns, top groups)
  e.g. `/api/open-data/weather/stats?group_by=departamento&filter_column=municipio&filter_value=MANIZALES`

Resilience (`infrastructure/resilience.py`, `infrastructure/open_data.py`):
- Retry with exponential backoff: 3 attempts, waits 0.5 s then 1 s (only timeouts, connection errors, HTTP 429/5xx).
- Configurable timeout (`HTTP_TIMEOUT`, default 10 s).
- Circuit breaker per API: closed -> open after 3 consecutive failures -> half-open after 30 s -> closed on success.
- Cache with TTL (`CACHE_TTL_SECONDS`, default 300). If the API fails, the last cached data is served with `"stale": true`.
- Errors: 404 unknown source, 400 bad query, 503 circuit open, 502 external API failed.
