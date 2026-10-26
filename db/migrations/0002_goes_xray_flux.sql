-- GOES X-ray flux (issue #31, ADR 0004, ADR 0005).
-- The runner wraps this file in one transaction. Do not add BEGIN or COMMIT.
-- 0001_solar_wind.sql already created the timescaledb extension, ingest_log,
-- and the read-only role. This file adds one measurement table and lets
-- that role SELECT it.
--
-- One minute from the primary GOES satellite has two rows, one per energy
-- band (0.05-0.4 nm and 0.1-0.8 nm). The natural key is
-- (time_tag, satellite, energy): one row per minute, per satellite, per
-- band. Re-inserting that triple is a conflict, which the upsert uses.
-- A hypertable's unique key has to include the time column, so time_tag
-- is part of the primary key.
--
-- Keys were checked on 2026-10-25 against
-- https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json
-- The file spells the contamination flag electron_contaminaton. The
-- column uses the corrected word. flux is the electron-corrected value,
-- watts per square metre. observed_flux is the value before that
-- correction. Python's float is 64-bit, so these three numbers are
-- double precision rather than real: a real column would round them.
--
-- Measurement columns are nullable. This sample had no nulls. A later
-- gap should still keep the row, the same rule as solar wind.

CREATE TABLE goes_xray_flux (
    time_tag timestamptz NOT NULL,
    satellite integer NOT NULL,
    energy text NOT NULL,
    flux double precision,
    observed_flux double precision,
    electron_correction double precision,
    electron_contamination boolean,
    PRIMARY KEY (time_tag, satellite, energy),
    CONSTRAINT goes_xray_flux_satellite_positive CHECK (satellite > 0),
    CONSTRAINT goes_xray_flux_energy_not_blank CHECK (energy <> '')
);

SELECT create_hypertable(
    'goes_xray_flux',
    'time_tag',
    chunk_time_interval => INTERVAL '7 days'
);

COMMENT ON TABLE goes_xray_flux IS
    'NOAA SWPC primary GOES X-ray flux (xrays-6-hour). Real-time rows, not a flare alert.';
COMMENT ON COLUMN goes_xray_flux.time_tag IS 'Measurement time, UTC.';
COMMENT ON COLUMN goes_xray_flux.satellite IS
    'GOES satellite number from the file, such as 18.';
COMMENT ON COLUMN goes_xray_flux.energy IS
    'Channel label from the file, such as 0.1-0.8nm. Flare class uses that long channel.';
COMMENT ON COLUMN goes_xray_flux.flux IS
    'Electron-corrected X-ray flux, watts per square metre.';
COMMENT ON COLUMN goes_xray_flux.observed_flux IS
    'X-ray flux before the electron correction, watts per square metre.';
COMMENT ON COLUMN goes_xray_flux.electron_correction IS
    'Amount subtracted from observed_flux to produce flux, watts per square metre.';
COMMENT ON COLUMN goes_xray_flux.electron_contamination IS
    'Upstream JSON key electron_contaminaton (SWPC spelling). True when electrons contaminate the X-ray diode.';

-- 0001 created the role from TI_READONLY_USER. A new table is not visible
-- to that role until it is granted. schema_migrations stays ungranted.
\getenv ti_readonly_user TI_READONLY_USER
GRANT SELECT ON TABLE goes_xray_flux TO :"ti_readonly_user";
