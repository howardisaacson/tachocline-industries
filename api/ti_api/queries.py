"""SELECT statements for the read-only API.

Values go through ``%s`` placeholders. A limit is a parameter, not a
piece of the SQL text, so a caller cannot change the statement by
putting SQL in the query string.
"""

SOLAR_WIND_SQL = """
SELECT time_tag, source, active,
       proton_speed, proton_density, proton_temperature
FROM solar_wind
WHERE time_tag >= %s AND time_tag < %s
ORDER BY time_tag DESC
LIMIT %s
""".strip()

SOURCES_SQL = """
SELECT source, count(*)::int AS rows, max(time_tag) AS latest
FROM solar_wind
GROUP BY source
ORDER BY source
LIMIT %s
""".strip()

INGEST_LOG_SQL = """
SELECT source, started_at, finished_at, http_status,
       rows_received, rows_upserted, rows_rejected, error
FROM ingest_log
ORDER BY finished_at DESC NULLS LAST
LIMIT %s
""".strip()

HEALTH_SQL = "SELECT 1 AS ok"

MAG_SQL = """
SELECT time_tag, source, active,
       bt, bx_gse, by_gse, bz_gse, bx_gsm, by_gsm, bz_gsm
FROM rtsw_mag_1m
WHERE time_tag >= %s AND time_tag < %s
ORDER BY time_tag DESC
LIMIT %s
""".strip()

# A missing energy filter is SQL NULL. ``NULL IS NULL`` is true, so every
# channel in the window is returned. A channel name has to match exactly.
GOES_SQL = """
SELECT time_tag, satellite, energy, flux, observed_flux,
       electron_correction, electron_contamination
FROM goes_xray_flux
WHERE time_tag >= %s AND time_tag < %s
  AND (%s::text IS NULL OR energy = %s)
ORDER BY time_tag DESC
LIMIT %s
""".strip()

KP_1M_SQL = """
SELECT time_tag, kp_index, estimated_kp, kp
FROM planetary_kp_1m
WHERE time_tag >= %s AND time_tag < %s
ORDER BY time_tag DESC
LIMIT %s
""".strip()

KP_3H_SQL = """
SELECT time_tag, kp, a_running, station_count
FROM planetary_kp_3h
WHERE time_tag >= %s AND time_tag < %s
ORDER BY time_tag DESC
LIMIT %s
""".strip()

ALERTS_SQL = """
SELECT issue_datetime, product_id, message
FROM swpc_alert
WHERE issue_datetime >= %s AND issue_datetime < %s
ORDER BY issue_datetime DESC
LIMIT %s
""".strip()

PERIGEE_SQL = """
SELECT epoch, norad_cat_id, object_name, object_id,
       perigee_altitude_km, apogee_altitude_km
FROM satellite_gp
WHERE epoch >= %s AND epoch < %s
  AND (%s::int IS NULL OR norad_cat_id = %s)
ORDER BY epoch DESC
LIMIT %s
""".strip()
