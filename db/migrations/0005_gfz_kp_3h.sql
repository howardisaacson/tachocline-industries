-- GFZ definitive 3-hour Kp (ADR 0022).
-- The runner wraps this file in one transaction. Do not add BEGIN or COMMIT.
-- 0001 already created timescaledb, ingest_log, and the read-only role.
-- This file adds one table. It does not edit 0003. planetary_kp_3h stays
-- the SWPC estimated product.
--
-- The file was checked on 2026-10-27 against
-- https://kp.gfz.de/app/files/Kp_ap_Ap_SN_F107_since_1932.txt
-- Kp in that file is CC BY 4.0. The sunspot column is CC BY-NC, so this
-- table does not store it. Eight Kp values per UT day become eight rows.
-- A missing Kp is -1 in the file and is not inserted.
-- Nowcast rows are replaced later. The upsert key is time_tag.
--
-- Cite: Matzka et al., 2021, https://doi.org/10.5880/Kp.0001
-- Chunks are 30 days. A 7-day chunk across a record that starts in 1932
-- would be thousands of chunks.

CREATE TABLE gfz_kp_3h (
    time_tag timestamptz NOT NULL,
    kp double precision NOT NULL,
    ap integer,
    definitive boolean NOT NULL,
    PRIMARY KEY (time_tag),
    CONSTRAINT gfz_kp_3h_kp_scale CHECK (kp >= 0 AND kp <= 9),
    CONSTRAINT gfz_kp_3h_ap_nonnegative CHECK (ap IS NULL OR ap >= 0)
);

SELECT create_hypertable(
    'gfz_kp_3h',
    'time_tag',
    chunk_time_interval => INTERVAL '30 days'
);

COMMENT ON TABLE gfz_kp_3h IS
    'GFZ Helmholtz Centre Kp and ap since 1932. Definitive when the file says so. Not the SWPC estimated index.';
COMMENT ON COLUMN gfz_kp_3h.time_tag IS
    'Start of the 3-hour block, UTC. The file gives eight values per UT day.';
COMMENT ON COLUMN gfz_kp_3h.kp IS
    'Planetary Kp as published, already in thirds (3.333 is 3+). Unitless, 0 to 9.';
COMMENT ON COLUMN gfz_kp_3h.ap IS
    'Three-hour equivalent amplitude ap for the same block. Null when the file has -1.';
COMMENT ON COLUMN gfz_kp_3h.definitive IS
    'True when the file flag D is 1 or 2 (Kp definitive). False is a nowcast that GFZ will replace.';

\getenv ti_readonly_user TI_READONLY_USER
GRANT SELECT ON TABLE gfz_kp_3h TO :"ti_readonly_user";
