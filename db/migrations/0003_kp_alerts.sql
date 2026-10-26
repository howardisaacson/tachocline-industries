-- Kp index and SWPC alerts (issue #32, ADR 0004, ADR 0005).
-- The runner wraps this file in one transaction. Do not add BEGIN or COMMIT.
-- 0001_solar_wind.sql already created the timescaledb extension, ingest_log,
-- and the read-only role. This file adds three tables and lets that role
-- SELECT them. It does not edit 0001 or 0002.
--
-- Keys were checked on 2026-10-25 (evening Pacific) against the live files:
--   https://services.swpc.noaa.gov/json/planetary_k_index_1m.json
--   https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json
--   https://services.swpc.noaa.gov/products/alerts.json
-- The 3-hour URL is the one linked from
-- https://www.spaceweather.gov/products/planetary-k-index
-- The alerts URL is the one linked from
-- https://www.spaceweather.gov/products/alerts-watches-and-warnings
-- The 1-minute file is listed in https://services.swpc.noaa.gov/json/
--
-- One planetary Kp value per time, so the natural key is time_tag alone.
-- Alerts can share a product code. Their key is (issue_datetime, product_id).
-- A hypertable's unique key has to include the time column.
--
-- These are real-time products. NOAA's 3-hour page calls its index estimated.
-- The 1-minute file has a separate estimated_kp field. Neither is the
-- later definitive GFZ Kp. Python's float is 64-bit, so the fractional
-- Kp columns are double precision rather than real.

CREATE TABLE planetary_kp_1m (
    time_tag timestamptz NOT NULL,
    kp_index integer,
    estimated_kp double precision,
    kp text,
    PRIMARY KEY (time_tag),
    CONSTRAINT planetary_kp_1m_kp_not_blank CHECK (kp IS NULL OR kp <> ''),
    CONSTRAINT planetary_kp_1m_counts_nonnegative CHECK (
        kp_index IS NULL OR kp_index >= 0
    )
);

SELECT create_hypertable(
    'planetary_kp_1m',
    'time_tag',
    chunk_time_interval => INTERVAL '7 days'
);

COMMENT ON TABLE planetary_kp_1m IS
    'NOAA SWPC planetary_k_index_1m. Real-time 1-minute estimated Kp, not the definitive GFZ index.';
COMMENT ON COLUMN planetary_kp_1m.time_tag IS 'Measurement time, UTC.';
COMMENT ON COLUMN planetary_kp_1m.kp_index IS
    'Integer Kp from the file. On the 2026-10-25 file it matched the whole number in the kp string.';
COMMENT ON COLUMN planetary_kp_1m.estimated_kp IS
    '1-minute estimated planetary Kp. The dashboard plots this number beside Bz.';
COMMENT ON COLUMN planetary_kp_1m.kp IS
    'Short Kp string from the file, such as 0Z or 1M. Stored, not drawn.';

CREATE TABLE planetary_kp_3h (
    time_tag timestamptz NOT NULL,
    kp double precision,
    a_running integer,
    station_count integer,
    PRIMARY KEY (time_tag),
    CONSTRAINT planetary_kp_3h_counts_nonnegative CHECK (
        (a_running IS NULL OR a_running >= 0)
        AND (station_count IS NULL OR station_count >= 0)
    )
);

SELECT create_hypertable(
    'planetary_kp_3h',
    'time_tag',
    chunk_time_interval => INTERVAL '7 days'
);

COMMENT ON TABLE planetary_kp_3h IS
    'NOAA SWPC noaa-planetary-k-index. Real-time estimated 3-hour planetary Kp.';
COMMENT ON COLUMN planetary_kp_3h.time_tag IS
    'Start of the 3-hour block, UTC. The JSON key is time_tag.';
COMMENT ON COLUMN planetary_kp_3h.kp IS
    'Estimated 3-hour planetary Kp. The JSON key is Kp.';
COMMENT ON COLUMN planetary_kp_3h.a_running IS
    'Running a index published beside Kp. The JSON key is a_running.';
COMMENT ON COLUMN planetary_kp_3h.station_count IS
    'How many magnetometer stations contributed to this row.';

CREATE TABLE swpc_alert (
    issue_datetime timestamptz NOT NULL,
    product_id text NOT NULL,
    message text,
    PRIMARY KEY (issue_datetime, product_id),
    CONSTRAINT swpc_alert_product_not_blank CHECK (product_id <> '')
);

SELECT create_hypertable(
    'swpc_alert',
    'issue_datetime',
    chunk_time_interval => INTERVAL '7 days'
);

COMMENT ON TABLE swpc_alert IS
    'NOAA SWPC alerts.json. Real-time alert, watch, and warning text. Not a measurement.';
COMMENT ON COLUMN swpc_alert.issue_datetime IS
    'Issue time from the file, UTC. The JSON value has a space and fractional seconds.';
COMMENT ON COLUMN swpc_alert.product_id IS
    'Short product code from the file, such as K04A. Not unique by itself.';
COMMENT ON COLUMN swpc_alert.message IS
    'Full message body, including the human-readable code and serial number.';

-- 0001 created the role from TI_READONLY_USER. A new table is not visible
-- to that role until it is granted. schema_migrations stays ungranted.
\getenv ti_readonly_user TI_READONLY_USER
GRANT SELECT ON TABLE planetary_kp_1m TO :"ti_readonly_user";
GRANT SELECT ON TABLE planetary_kp_3h TO :"ti_readonly_user";
GRANT SELECT ON TABLE swpc_alert TO :"ti_readonly_user";
