"""Read-only HTTP API (issue #36, ADR 0006).

A route is one URL plus one method. These routes are all GET. FastAPI
builds the OpenAPI page at ``/docs`` from the type hints on the
functions. Pydantic checks each response against the model before the
bytes go out, the same way the pollers check rows on the way in.

https://fastapi.tiangolo.com/tutorial/

The database login is the read-only role. Every statement is a SELECT
in ``ti_api.queries``. A request that asks for more than seven days, or
for a ``limit`` outside the declared bounds, is rejected before a query
runs. ``GET /api/kp-3h`` is the exception: the year ring needs one call
covering 365 days of 3-hour rows, so that route allows 400 days and
3300 rows. Minute-level routes stay at seven days.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel

from ti_api.db import ConfigError, DatabaseSettings, connect
from ti_api.queries import (
    ALERTS_SQL,
    GOES_SQL,
    HEALTH_SQL,
    INGEST_LOG_SQL,
    KP_1M_SQL,
    KP_3H_SQL,
    MAG_SQL,
    PERIGEE_SQL,
    SOLAR_WIND_SQL,
    SOURCES_SQL,
)

# One minute of solar wind, times a week, is about ten thousand rows.
# The cap is lower than that so one call stays small.
MAX_SOLAR_LIMIT = 2000
DEFAULT_SOLAR_LIMIT = 500
MAX_LOG_LIMIT = 200
DEFAULT_LOG_LIMIT = 50
MAX_SOURCE_LIMIT = 100
DEFAULT_RANGE = timedelta(hours=6)
MAX_RANGE = timedelta(days=7)
# One year of 3-hour Kp is 365 * 8 = 2920 rows. 400 days and 3300 rows
# cover that ring, including a lap that starts on 1 January, without
# opening the same window on the 1-minute tables.
MAX_KP3H_RANGE = timedelta(days=400)
MAX_KP3H_LIMIT = 3300

app = FastAPI(
    title="Tachocline Industries",
    summary="Read-only access to stored space-weather and orbit rows.",
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


class MagRow(BaseModel):
    """One minute of interplanetary magnetic field, nanotesla."""

    time_tag: datetime
    source: str
    active: bool
    bt: float | None
    bx_gse: float | None
    by_gse: float | None
    bz_gse: float | None
    bx_gsm: float | None
    by_gsm: float | None
    bz_gsm: float | None


class MagPage(BaseModel):
    """Same half-open window as solar wind. Values are real-time, in nT."""

    processing_level: Literal["real-time"] = "real-time"
    time_from: datetime
    time_to: datetime
    limit: int
    rows: list[MagRow]


class GoesRow(BaseModel):
    """One GOES X-ray sample. ``flux`` is watts per square metre."""

    time_tag: datetime
    satellite: int
    energy: str
    flux: float | None
    observed_flux: float | None
    electron_correction: float | None
    electron_contamination: bool | None


class GoesPage(BaseModel):
    """Real-time X-ray flux, not a flare alert."""

    processing_level: Literal["real-time"] = "real-time"
    time_from: datetime
    time_to: datetime
    limit: int
    rows: list[GoesRow]


class Kp1mRow(BaseModel):
    """One minute of estimated planetary Kp. ``kp`` is the short string."""

    time_tag: datetime
    kp_index: int | None
    estimated_kp: float | None
    kp: str | None


class Kp3hRow(BaseModel):
    """One estimated 3-hour Kp block. Not the definitive GFZ index."""

    time_tag: datetime
    kp: float | None
    a_running: int | None
    station_count: int | None


class Kp1mPage(BaseModel):
    processing_level: Literal["real-time"] = "real-time"
    time_from: datetime
    time_to: datetime
    limit: int
    rows: list[Kp1mRow]


class Kp3hPage(BaseModel):
    processing_level: Literal["real-time"] = "real-time"
    time_from: datetime
    time_to: datetime
    limit: int
    rows: list[Kp3hRow]


class AlertRow(BaseModel):
    """One SWPC alert message. Real-time text, not a measurement."""

    issue_datetime: datetime
    product_id: str
    message: str | None


class AlertPage(BaseModel):
    processing_level: Literal["real-time"] = "real-time"
    time_from: datetime
    time_to: datetime
    limit: int
    rows: list[AlertRow]


class PerigeeRow(BaseModel):
    """Two-body altitudes in kilometers, not an SGP4 state."""

    epoch: datetime
    norad_cat_id: int
    object_name: str
    object_id: str
    perigee_altitude_km: float
    apogee_altitude_km: float


class PerigeePage(BaseModel):
    """Perigee is the series to plot. Apogee is the matching high point."""

    processing_level: Literal["real-time"] = "real-time"
    altitude: Literal["two-body kilometers above the equatorial radius"] = (
        "two-body kilometers above the equatorial radius"
    )
    time_from: datetime
    time_to: datetime
    limit: int
    rows: list[PerigeeRow]


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
    max_range: timedelta = MAX_RANGE,
) -> tuple[datetime, datetime]:
    end = _aware(time_to, "to") if time_to is not None else now.astimezone(UTC)
    start = _aware(time_from, "from") if time_from is not None else end - DEFAULT_RANGE
    if start >= end:
        raise HTTPException(status_code=422, detail="from must be earlier than to")
    if end - start > max_range:
        days = max_range.days
        raise HTTPException(
            status_code=422, detail=f"time range must be {days} days or less"
        )
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


@app.get("/api/mag", response_model=MagPage)
def mag(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
    now: Annotated[datetime, Depends(utc_now)],
    time_from: Annotated[datetime | None, Query(alias="from")] = None,
    time_to: Annotated[datetime | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_SOLAR_LIMIT)] = DEFAULT_SOLAR_LIMIT,
) -> MagPage:
    """Real-time magnetic field, nanotesla. Newest first."""
    start, end = _window(time_from, time_to, now)
    rows = _query(conn, MAG_SQL, (start, end, limit))
    return MagPage(
        time_from=start,
        time_to=end,
        limit=limit,
        rows=[MagRow.model_validate(row) for row in rows],
    )


@app.get("/api/goes-xray", response_model=GoesPage)
def goes_xray(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
    now: Annotated[datetime, Depends(utc_now)],
    time_from: Annotated[datetime | None, Query(alias="from")] = None,
    time_to: Annotated[datetime | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_SOLAR_LIMIT)] = DEFAULT_SOLAR_LIMIT,
    energy: Annotated[str | None, Query(min_length=1, max_length=32)] = None,
) -> GoesPage:
    """Real-time GOES X-ray flux. ``energy`` keeps one channel, such as ``0.1-0.8nm``."""
    start, end = _window(time_from, time_to, now)
    rows = _query(conn, GOES_SQL, (start, end, energy, energy, limit))
    return GoesPage(
        time_from=start,
        time_to=end,
        limit=limit,
        rows=[GoesRow.model_validate(row) for row in rows],
    )


@app.get("/api/kp-1m", response_model=Kp1mPage)
def kp_1m(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
    now: Annotated[datetime, Depends(utc_now)],
    time_from: Annotated[datetime | None, Query(alias="from")] = None,
    time_to: Annotated[datetime | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_SOLAR_LIMIT)] = DEFAULT_SOLAR_LIMIT,
) -> Kp1mPage:
    """Real-time 1-minute estimated Kp. Not the definitive GFZ index."""
    start, end = _window(time_from, time_to, now)
    rows = _query(conn, KP_1M_SQL, (start, end, limit))
    return Kp1mPage(
        time_from=start,
        time_to=end,
        limit=limit,
        rows=[Kp1mRow.model_validate(row) for row in rows],
    )


@app.get("/api/kp-3h", response_model=Kp3hPage)
def kp_3h(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
    now: Annotated[datetime, Depends(utc_now)],
    time_from: Annotated[datetime | None, Query(alias="from")] = None,
    time_to: Annotated[datetime | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_KP3H_LIMIT)] = DEFAULT_SOLAR_LIMIT,
) -> Kp3hPage:
    """Real-time estimated 3-hour Kp. ``time_tag`` is the block start.

    The window may be 400 days so the public year ring can load in one
    call. ``limit`` stops at 3300. The default is still 500 rows.
    """
    start, end = _window(time_from, time_to, now, MAX_KP3H_RANGE)
    rows = _query(conn, KP_3H_SQL, (start, end, limit))
    return Kp3hPage(
        time_from=start,
        time_to=end,
        limit=limit,
        rows=[Kp3hRow.model_validate(row) for row in rows],
    )


@app.get("/api/alerts", response_model=AlertPage)
def alerts(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
    now: Annotated[datetime, Depends(utc_now)],
    time_from: Annotated[datetime | None, Query(alias="from")] = None,
    time_to: Annotated[datetime | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LOG_LIMIT)] = DEFAULT_LOG_LIMIT,
) -> AlertPage:
    """Real-time SWPC alert text. The window filters ``issue_datetime``."""
    start, end = _window(time_from, time_to, now)
    rows = _query(conn, ALERTS_SQL, (start, end, limit))
    return AlertPage(
        time_from=start,
        time_to=end,
        limit=limit,
        rows=[AlertRow.model_validate(row) for row in rows],
    )


@app.get("/api/satellite-perigee", response_model=PerigeePage)
def satellite_perigee(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
    now: Annotated[datetime, Depends(utc_now)],
    time_from: Annotated[datetime | None, Query(alias="from")] = None,
    time_to: Annotated[datetime | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_SOLAR_LIMIT)] = DEFAULT_SOLAR_LIMIT,
    norad_cat_id: Annotated[int | None, Query(gt=0)] = None,
) -> PerigeePage:
    """Two-body perigee and apogee. ``norad_cat_id`` keeps one satellite."""
    start, end = _window(time_from, time_to, now)
    rows = _query(conn, PERIGEE_SQL, (start, end, norad_cat_id, norad_cat_id, limit))
    return PerigeePage(
        time_from=start,
        time_to=end,
        limit=limit,
        rows=[PerigeeRow.model_validate(row) for row in rows],
    )
