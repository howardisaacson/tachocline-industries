"""Read-only HTTP API (issue #36, ADR 0006).

A route is one URL plus one method. These routes are all GET. FastAPI
builds the OpenAPI page at ``/docs`` from the type hints on the
functions. Pydantic checks each response against the model before the
bytes go out, the same way the pollers check rows on the way in.

https://fastapi.tiangolo.com/tutorial/

The database login is the read-only role. Every statement is a SELECT
in ``ti_api.queries``. A request that asks for more than seven days, or
for a ``limit`` outside the declared bounds, is rejected before a query
runs.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel

from ti_api.db import ConfigError, DatabaseSettings, connect
from ti_api.queries import HEALTH_SQL, INGEST_LOG_SQL, SOLAR_WIND_SQL, SOURCES_SQL

# One minute of solar wind, times a week, is about ten thousand rows.
# The cap is lower than that so one call stays small.
MAX_SOLAR_LIMIT = 2000
DEFAULT_SOLAR_LIMIT = 500
MAX_LOG_LIMIT = 200
DEFAULT_LOG_LIMIT = 50
MAX_SOURCE_LIMIT = 100
DEFAULT_RANGE = timedelta(hours=6)
MAX_RANGE = timedelta(days=7)

app = FastAPI(
    title="Tachocline Industries",
    summary="Read-only access to stored space-weather rows.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)


class HealthBody(BaseModel):
    """``database`` is ``ok`` only after ``SELECT 1`` succeeds."""

    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]


class SolarWindRow(BaseModel):
    """One minute from ``solar_wind``. Nulls are gaps in the feed."""

    time_tag: datetime
    source: str
    active: bool | None
    proton_speed: float | None
    proton_density: float | None
    proton_temperature: float | None


class SolarWindPage(BaseModel):
    """The window is half-open: ``time_from`` inclusive, ``time_to`` exclusive."""

    processing_level: Literal["real-time"] = "real-time"
    time_from: datetime
    time_to: datetime
    limit: int
    rows: list[SolarWindRow]


class SourceRow(BaseModel):
    """One spacecraft id stored in ``solar_wind.source``, not an ingest feed name."""

    source: str
    rows: int
    latest: datetime | None


class IngestLogRow(BaseModel):
    """One attempted file. ``error`` empty means the file was loaded."""

    source: str
    started_at: datetime
    finished_at: datetime | None
    http_status: int | None
    rows_received: int
    rows_upserted: int
    rows_rejected: int
    error: str | None


def utc_now() -> datetime:
    """Clock for the default solar-wind window. Tests replace this."""
    return datetime.now(UTC)


def get_connection() -> Iterator[psycopg.Connection]:
    """One connection per request. Closed when the response is finished."""
    try:
        conn = connect(DatabaseSettings.from_env())
    except (ConfigError, psycopg.Error) as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    try:
        yield conn
    finally:
        conn.close()


def _query(
    conn: psycopg.Connection, sql: str, params: tuple[object, ...]
) -> list[dict[str, object]]:
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return list(rows)


def _aware(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail=f"{name} must include a time zone, for example 2026-10-25T00:00:00Z",
        )
    return value.astimezone(UTC)


def _window(
    time_from: datetime | None,
    time_to: datetime | None,
    now: datetime,
) -> tuple[datetime, datetime]:
    end = _aware(time_to, "to") if time_to is not None else now.astimezone(UTC)
    start = _aware(time_from, "from") if time_from is not None else end - DEFAULT_RANGE
    if start >= end:
        raise HTTPException(status_code=422, detail="from must be earlier than to")
    if end - start > MAX_RANGE:
        raise HTTPException(status_code=422, detail="time range must be 7 days or less")
    return start, end


@app.get("/api/health", response_model=HealthBody)
def health(conn: Annotated[psycopg.Connection, Depends(get_connection)]) -> HealthBody:
    """Database reachability. HTTP 503 when the SELECT fails."""
    _query(conn, HEALTH_SQL, ())
    return HealthBody(status="ok", database="ok")


@app.get("/api/solar-wind", response_model=SolarWindPage)
def solar_wind(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
    now: Annotated[datetime, Depends(utc_now)],
    time_from: Annotated[datetime | None, Query(alias="from")] = None,
    time_to: Annotated[datetime | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_SOLAR_LIMIT)] = DEFAULT_SOLAR_LIMIT,
) -> SolarWindPage:
    """Real-time solar-wind minutes. Newest first, capped by ``limit``."""
    start, end = _window(time_from, time_to, now)
    rows = _query(conn, SOLAR_WIND_SQL, (start, end, limit))
    return SolarWindPage(
        time_from=start,
        time_to=end,
        limit=limit,
        rows=[SolarWindRow.model_validate(row) for row in rows],
    )


@app.get("/api/sources", response_model=list[SourceRow])
def sources(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
    limit: Annotated[int, Query(ge=1, le=MAX_SOURCE_LIMIT)] = MAX_SOURCE_LIMIT,
) -> list[SourceRow]:
    """Spacecraft ids in ``solar_wind``. Feed names are on ``/api/ingest-log``."""
    rows = _query(conn, SOURCES_SQL, (limit,))
    return [SourceRow.model_validate(row) for row in rows]


@app.get("/api/ingest-log", response_model=list[IngestLogRow])
def ingest_log(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
    limit: Annotated[int, Query(ge=1, le=MAX_LOG_LIMIT)] = DEFAULT_LOG_LIMIT,
) -> list[IngestLogRow]:
    """Newest poller attempts. ``limit`` defaults to 50 and stops at 200."""
    rows = _query(conn, INGEST_LOG_SQL, (limit,))
    return [IngestLogRow.model_validate(row) for row in rows]
