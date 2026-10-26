-- CelesTrak GP history (issue #34, ADR 0004, ADR 0005).
-- The runner wraps this file in one transaction. Do not add BEGIN or COMMIT.
-- 0001 already created timescaledb, ingest_log, and the read-only role.
-- This file adds one table and lets that role SELECT it.
--
-- One general-perturbations record is one epoch for one catalog number.
-- The natural key is (epoch, norad_cat_id). A hypertable's unique key
-- has to include the time column.
--
-- The JSON shape was checked on 2026-10-25 against
-- https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=json
-- Field names are the OMM keywords CelesTrak documents:
-- https://celestrak.org/NORAD/documentation/gp-data-formats.php
-- The file does not carry altitude. perigee_altitude_km and
-- apogee_altitude_km are derived in Python from MEAN_MOTION and
-- ECCENTRICITY. See ingest/ti_ingest/elements.py.
--
-- TLE layout, which these OMM fields correspond to:
-- https://celestrak.org/NORAD/documentation/tle-fmt.php

CREATE TABLE satellite_gp (
    epoch timestamptz NOT NULL,
    norad_cat_id integer NOT NULL,
    object_name text NOT NULL,
    object_id text NOT NULL,
    mean_motion double precision NOT NULL,
    eccentricity double precision NOT NULL,
    inclination double precision,
    ra_of_asc_node double precision,
    arg_of_pericenter double precision,
    mean_anomaly double precision,
    bstar double precision,
    mean_motion_dot double precision,
    perigee_altitude_km double precision NOT NULL,
    apogee_altitude_km double precision NOT NULL,
    PRIMARY KEY (epoch, norad_cat_id),
    CONSTRAINT satellite_gp_catnr_positive CHECK (norad_cat_id > 0),
    CONSTRAINT satellite_gp_name_not_blank CHECK (object_name <> ''),
    CONSTRAINT satellite_gp_object_id_not_blank CHECK (object_id <> ''),
    CONSTRAINT satellite_gp_mean_motion_positive CHECK (mean_motion > 0),
    CONSTRAINT satellite_gp_eccentricity_ellipse CHECK (
        eccentricity >= 0 AND eccentricity < 1
    )
);

SELECT create_hypertable(
    'satellite_gp',
    'epoch',
    chunk_time_interval => INTERVAL '7 days'
);

COMMENT ON TABLE satellite_gp IS
    'CelesTrak GP (OMM JSON) for the starter satellite set. Real-time mean elements, not an SGP4 ephemeris.';
COMMENT ON COLUMN satellite_gp.epoch IS 'Element epoch, UTC. The JSON key is EPOCH.';
COMMENT ON COLUMN satellite_gp.norad_cat_id IS 'NORAD catalog number. The JSON key is NORAD_CAT_ID.';
COMMENT ON COLUMN satellite_gp.object_id IS
    'International designator, such as 1998-067A. The JSON key is OBJECT_ID.';
COMMENT ON COLUMN satellite_gp.mean_motion IS 'TLE mean motion, revolutions per day.';
COMMENT ON COLUMN satellite_gp.eccentricity IS 'Dimensionless eccentricity.';
COMMENT ON COLUMN satellite_gp.bstar IS
    'B* drag term from the TLE, inverse Earth radii. Stored for a later drag fit.';
COMMENT ON COLUMN satellite_gp.perigee_altitude_km IS
    'Derived: a(1-e) minus the NASA fact-sheet equatorial radius 6378.137 km. Not a column in the JSON.';
COMMENT ON COLUMN satellite_gp.apogee_altitude_km IS
    'Derived: a(1+e) minus the NASA fact-sheet equatorial radius 6378.137 km. Not a column in the JSON.';

\getenv ti_readonly_user TI_READONLY_USER
GRANT SELECT ON TABLE satellite_gp TO :"ti_readonly_user";
