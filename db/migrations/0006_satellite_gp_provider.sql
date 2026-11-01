-- Which poller wrote each element set (issues #105 and #109).
-- The runner wraps this file in one transaction. Do not add BEGIN or COMMIT.
--
-- satellite_gp used to mix CelesTrak and Space-Track in one table with no
-- tag. A public route cannot tell them apart without this column.
-- Existing rows are labeled celestrak only when ingest_log has no successful
-- gp-hist-* run. A machine that already loaded Space-Track history labels
-- the old rows unknown, and the public API does not return unknown.

ALTER TABLE satellite_gp
    ADD COLUMN provider text;

UPDATE satellite_gp
SET provider = CASE
    WHEN EXISTS (
        SELECT 1
        FROM ingest_log
        WHERE source LIKE 'gp-hist-%'
          AND error IS NULL
          AND rows_upserted > 0
    ) THEN 'unknown'
    ELSE 'celestrak'
END
WHERE provider IS NULL;

ALTER TABLE satellite_gp
    ALTER COLUMN provider SET NOT NULL;

ALTER TABLE satellite_gp
    ADD CONSTRAINT satellite_gp_provider_known
    CHECK (provider IN ('celestrak', 'spacetrack', 'unknown'));

COMMENT ON COLUMN satellite_gp.provider IS
    'celestrak, spacetrack, or unknown. Public API routes return celestrak only. A later CelesTrak write may replace spacetrack; a Space-Track write must not replace celestrak.';
