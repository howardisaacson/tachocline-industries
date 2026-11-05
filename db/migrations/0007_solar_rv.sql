-- Sun-as-a-star radial velocity from the NExScI Solar RV Archive (ADR 0037).
-- The runner wraps this file in one transaction. Do not add BEGIN or COMMIT.
-- 0001 already created timescaledb and the read-only role.
--
-- Checked 2026-11-05 against https://neid.ipac.caltech.edu/TAP/sync
-- Tables neidsolarl2 and expressolarl2. ccfrvmod is km/s on both.
-- NEID dvrms is km/s. EXPRES e_v is cm/s. This table stores m/s.
-- The poller keeps 14 days and deletes older rows. It does not download FITS.
--
-- A missing RV is stored as NULL. That is a gap, not a zero.
-- The speed and error checks are unit guards. A centimeter-per-second
-- value stored as meters per second would fail them.

CREATE TABLE solar_rv (
    time_tag timestamptz NOT NULL,
    instrument text NOT NULL,
    rv_m_s double precision,
    rv_error_m_s double precision,
    snr double precision,
    exptime_s double precision,
    archive_jd double precision,
    archive_time_scale text NOT NULL,
    PRIMARY KEY (time_tag, instrument),
    CONSTRAINT solar_rv_instrument CHECK (instrument IN ('neid', 'expres')),
    CONSTRAINT solar_rv_time_scale CHECK (
        (instrument = 'neid' AND archive_time_scale = 'BJD')
        OR (instrument = 'expres' AND archive_time_scale = 'JD')
    ),
    CONSTRAINT solar_rv_speed CHECK (
        rv_m_s IS NULL OR (rv_m_s > -5000 AND rv_m_s < 5000)
    ),
    CONSTRAINT solar_rv_error CHECK (
        rv_error_m_s IS NULL OR (rv_error_m_s >= 0 AND rv_error_m_s <= 100)
    ),
    CONSTRAINT solar_rv_snr CHECK (snr IS NULL OR snr >= 0),
    CONSTRAINT solar_rv_exptime CHECK (exptime_s IS NULL OR exptime_s >= 0),
    CONSTRAINT solar_rv_jd CHECK (
        archive_jd IS NULL OR (archive_jd > 2400000 AND archive_jd < 3000000)
    )
);

SELECT create_hypertable(
    'solar_rv',
    'time_tag',
    chunk_time_interval => INTERVAL '7 days'
);

COMMENT ON TABLE solar_rv IS
    'NEID and EXPRES Sun-as-a-star Level 2 radial velocity. Meters per second. Not a spectrum.';
COMMENT ON COLUMN solar_rv.time_tag IS
    'obsdate from the archive, UTC. The clock the public plot uses.';
COMMENT ON COLUMN solar_rv.instrument IS
    'neid or expres.';
COMMENT ON COLUMN solar_rv.rv_m_s IS
    'ccfrvmod converted from km/s to m/s. NULL when the archive omitted it.';
COMMENT ON COLUMN solar_rv.rv_error_m_s IS
    'NEID dvrms from km/s, or EXPRES e_v from cm/s. NULL when that column was empty.';
COMMENT ON COLUMN solar_rv.snr IS
    'extsnr, per pixel. NEID defaults to 5530 angstroms when the request names no wavelength.';
COMMENT ON COLUMN solar_rv.exptime_s IS
    'Exposure length in seconds.';
COMMENT ON COLUMN solar_rv.archive_jd IS
    'ccfjdsum. BJD for NEID. JD of the geometric midpoint for EXPRES.';
COMMENT ON COLUMN solar_rv.archive_time_scale IS
    'BJD or JD. Names the clock in archive_jd. The plot uses time_tag.';

\getenv ti_readonly_user TI_READONLY_USER
GRANT SELECT ON TABLE solar_rv TO :"ti_readonly_user";
