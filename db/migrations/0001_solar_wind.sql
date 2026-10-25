-- Solar-wind storage (issue #25, ADR 0003, ADR 0004, ADR 0005).
-- The runner wraps this file in one transaction. Do not add BEGIN or COMMIT.
--
-- A primary key names the columns that identify one row. Two spacecraft can
-- report the same minute, so the key is (time_tag, source): one row per
-- minute per spacecraft. Re-inserting that pair is a conflict, which is
-- what a later upsert (issue #27) will use.
--
-- A hypertable is still a Postgres table. Timescale splits it into chunks
-- by time_tag. Every unique key on a hypertable has to include that time
-- column, so time_tag is part of the primary key.
--
-- Column names are the SWPC JSON keys this repo already documents
-- (docs/research/data_sources.md). Wind columns match the starter table
-- there. Magnetic-field columns are bt plus Bx/By/Bz in GSE and GSM.
-- Those keys were checked on 2026-10-25 against rtsw_wind_1m.json and
-- rtsw_mag_1m.json. Not stored yet: alpha particles, proton velocity
-- components, angles, and quality flags. Issue #27 can add them in a
-- new migration if the pydantic models need them.
--
-- Measurement columns are nullable. The feed leaves gaps, and ADR 0003
-- says we keep the row and handle nulls.

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE solar_wind (
    time_tag timestamptz NOT NULL,
    source text NOT NULL,
    active boolean NOT NULL,
    proton_speed real,
    proton_density real,
    proton_temperature real,
    PRIMARY KEY (time_tag, source),
    CONSTRAINT solar_wind_source_not_blank CHECK (source <> '')
);

-- Seven days is Timescale's default chunk for timestamptz. It is written
-- here so the interval is visible. One chunk is about a week of 1-minute
-- rows from every spacecraft in the file.
SELECT create_hypertable(
    'solar_wind',
    'time_tag',
    chunk_time_interval => INTERVAL '7 days'
);

COMMENT ON TABLE solar_wind IS
    'NOAA SWPC rtsw_wind_1m plasma. Real-time rows, not a final science archive.';
COMMENT ON COLUMN solar_wind.time_tag IS 'Measurement time, UTC.';
COMMENT ON COLUMN solar_wind.source IS
    'Spacecraft id from the feed, such as SOLAR1, ACE, or IMAP.';
COMMENT ON COLUMN solar_wind.active IS
    'True for the spacecraft SWPC forecasters are using.';
COMMENT ON COLUMN solar_wind.proton_speed IS 'Solar-wind proton speed, km/s.';
COMMENT ON COLUMN solar_wind.proton_density IS
    'Proton density, protons per cubic centimeter.';
COMMENT ON COLUMN solar_wind.proton_temperature IS 'Proton temperature, kelvin.';

-- Same natural key as solar_wind. The research note names this table
-- rtsw_mag_1m, after the SWPC file.
CREATE TABLE rtsw_mag_1m (
    time_tag timestamptz NOT NULL,
    source text NOT NULL,
    active boolean NOT NULL,
    bt real,
    bx_gse real,
    by_gse real,
    bz_gse real,
    bx_gsm real,
    by_gsm real,
    bz_gsm real,
    PRIMARY KEY (time_tag, source),
    CONSTRAINT rtsw_mag_1m_source_not_blank CHECK (source <> '')
);

SELECT create_hypertable(
    'rtsw_mag_1m',
    'time_tag',
    chunk_time_interval => INTERVAL '7 days'
);

COMMENT ON TABLE rtsw_mag_1m IS
    'NOAA SWPC rtsw_mag_1m interplanetary magnetic field, nanotesla.';
COMMENT ON COLUMN rtsw_mag_1m.time_tag IS 'Measurement time, UTC.';
COMMENT ON COLUMN rtsw_mag_1m.source IS
    'Spacecraft id from the feed, such as SOLAR1, ACE, or IMAP.';
COMMENT ON COLUMN rtsw_mag_1m.active IS
    'True for the spacecraft SWPC forecasters are using.';
COMMENT ON COLUMN rtsw_mag_1m.bt IS 'Magnetic-field magnitude, nT.';
COMMENT ON COLUMN rtsw_mag_1m.bz_gsm IS
    'GSM Z component, nT. Southward (negative) Bz is the storm driver the dashboard will chart.';

-- Run health, not a measurement. A few rows per hour do not need a
-- hypertable. The primary key is a surrogate id because two feeds can
-- start at the same instant. Column list follows ADR 0004: source,
-- start/end time, HTTP status, rows received/upserted/rejected, error.
-- source here is the feed name (rtsw_wind_1m), not the spacecraft id.
CREATE TABLE ingest_log (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source text NOT NULL,
    started_at timestamptz NOT NULL,
    finished_at timestamptz,
    http_status integer,
    rows_received integer,
    rows_upserted integer,
    rows_rejected integer,
    error text,
    CONSTRAINT ingest_log_source_not_blank CHECK (source <> ''),
    CONSTRAINT ingest_log_time_order CHECK (
        finished_at IS NULL OR finished_at >= started_at
    ),
    CONSTRAINT ingest_log_counts_nonnegative CHECK (
        (rows_received IS NULL OR rows_received >= 0)
        AND (rows_upserted IS NULL OR rows_upserted >= 0)
        AND (rows_rejected IS NULL OR rows_rejected >= 0)
    )
);

-- "Minutes since last good ingest" filters by feed and orders by start time.
CREATE INDEX ingest_log_source_started_at_idx
    ON ingest_log (source, started_at DESC);

COMMENT ON TABLE ingest_log IS
    'One row per poller run (ADR 0004). source is the feed name, not the spacecraft id.';
COMMENT ON COLUMN ingest_log.http_status IS
    'HTTP status from the fetch. Null when the request never got a response.';
COMMENT ON COLUMN ingest_log.error IS
    'Null after a successful run. Set when the run failed.';

-- Read-only login for Grafana and the API (ADR 0007).
-- The name and password come from TI_READONLY_USER and
-- TI_READONLY_PASSWORD. psql's \getenv copies them out of the environment
-- (\getenv needs psql 15; the migrate image installs that client).
-- They are not written in this file, and they are not psql arguments.
-- The local dummy password lives in .env.example.
--
-- CREATE ROLE is transactional here, same as CREATE TABLE. If this file
-- fails, the role rolls back with the tables. CREATE DATABASE cannot do
-- that; this is not that command.
-- A later migration that adds a table has to GRANT SELECT on it too.
-- schema_migrations is the runner's bookkeeping table and is not granted.

\getenv ti_readonly_user TI_READONLY_USER
\getenv ti_readonly_password TI_READONLY_PASSWORD
\getenv ti_database PGDATABASE

CREATE ROLE :"ti_readonly_user"
    WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION
    PASSWORD :'ti_readonly_password';

-- CONNECT and USAGE are granted explicitly so the role does not depend
-- on whatever PUBLIC is allowed to do. SELECT is the only table privilege.
GRANT CONNECT ON DATABASE :"ti_database" TO :"ti_readonly_user";
GRANT USAGE ON SCHEMA public TO :"ti_readonly_user";
GRANT SELECT ON TABLE
    solar_wind,
    rtsw_mag_1m,
    ingest_log
    TO :"ti_readonly_user";
