// Perigee chart for the five satellites the poller already tracks.
// The browser only sees GET /api/v1/satellite-perigee. That route rejects
// a window longer than 7 days, which is also the Grafana panel's default.

export const PERIGEE_WINDOW_MS = 7 * 24 * 60 * 60 * 1000;
export const PERIGEE_LIMIT = 2000;

export const TRACKED_SATELLITES = [
  {
    noradCatId: 25544,
    name: "ISS (ZARYA)",
    color: "#f4f4f8",
    dash: "",
    trackingUrl: "https://www.n2yo.com/satellite/?s=25544",
    homeUrl: "https://www.nasa.gov/international-space-station/",
  },
  {
    noradCatId: 39084,
    name: "LANDSAT 8",
    color: "#e07a3d",
    dash: "",
    trackingUrl: "https://www.n2yo.com/satellite/?s=39084",
    homeUrl: "https://science.nasa.gov/mission/landsat-8/",
  },
  {
    noradCatId: 49260,
    name: "LANDSAT 9",
    color: "#f2c14e",
    dash: "5 4",
    trackingUrl: "https://www.n2yo.com/satellite/?s=49260",
    homeUrl: "https://science.nasa.gov/mission/landsat-9/",
  },
  {
    noradCatId: 20580,
    name: "HST",
    color: "#8eb6ff",
    dash: "",
    trackingUrl: "https://www.n2yo.com/satellite/?s=20580",
    homeUrl: "https://science.nasa.gov/mission/hubble/",
  },
  {
    noradCatId: 28485,
    name: "SWIFT",
    color: "#ff8b8b",
    dash: "",
    trackingUrl: "https://www.n2yo.com/satellite/?s=28485",
    homeUrl: "https://science.nasa.gov/mission/swift/",
  },
];

const PAD = { left: 52, right: 16, top: 16, bottom: 32 };

export function perigeeRequestPath(nowMs) {
  const end = new Date(nowMs).toISOString();
  const start = new Date(nowMs - PERIGEE_WINDOW_MS).toISOString();
  const params = new URLSearchParams({
    from: start,
    to: end,
    limit: String(PERIGEE_LIMIT),
  });
  return `/api/v1/satellite-perigee?${params.toString()}`;
}

/** One series per tracked satellite, oldest epoch first. Unknown ids are dropped. */
export function seriesFromRows(rows) {
  const byId = new Map(TRACKED_SATELLITES.map((sat) => [sat.noradCatId, []]));
  for (const row of rows ?? []) {
    const points = byId.get(row.norad_cat_id);
    if (!points) continue;
    const time = Date.parse(row.epoch);
    const km = Number(row.perigee_altitude_km);
    if (!Number.isFinite(time) || !Number.isFinite(km)) continue;
    points.push({ time, km });
  }
  return TRACKED_SATELLITES.map((sat) => ({
    ...sat,
    points: byId.get(sat.noradCatId).sort((left, right) => left.time - right.time),
  }));
}

/**
 * Pixel geometry for an SVG that is `width` by `height` CSS pixels.
 * Higher altitude is a smaller y. The x axis is the requested window.
 */
export function chartGeometry(series, { width, height, fromMs, toMs }) {
  const span = Math.max(1, toMs - fromMs);
  const kept = series.map((sat) => ({
    ...sat,
    points: sat.points.filter((point) => point.time >= fromMs && point.time < toMs),
  }));
  const all = kept.flatMap((sat) => sat.points);
  let minKm = 200;
  let maxKm = 800;
  if (all.length > 0) {
    minKm = Math.min(...all.map((point) => point.km));
    maxKm = Math.max(...all.map((point) => point.km));
    if (maxKm - minKm < 1) {
      minKm -= 1;
      maxKm += 1;
    }
    const pad = (maxKm - minKm) * 0.08;
    minKm -= pad;
    maxKm += pad;
  }
  const innerW = Math.max(1, width - PAD.left - PAD.right);
  const innerH = Math.max(1, height - PAD.top - PAD.bottom);
  const xOf = (time) => PAD.left + ((time - fromMs) / span) * innerW;
  const yOf = (km) => PAD.top + ((maxKm - km) / (maxKm - minKm)) * innerH;
  const yTicks = [0, 1, 2, 3, 4].map((step) => {
    const km = minKm + ((maxKm - minKm) * step) / 4;
    return { km, y: yOf(km), label: String(Math.round(km)) };
  });
  const xTicks = [0, 0.5, 1].map((fraction) => {
    const time = fromMs + span * fraction;
    return { time, x: xOf(Math.min(time, toMs - 1)), label: utcDayLabel(time) };
  });
  return {
    empty: all.length === 0,
    lines: kept.map((sat) => ({
      noradCatId: sat.noradCatId,
      name: sat.name,
      color: sat.color,
      dash: sat.dash,
      points: sat.points.map((point) => ({
        x: xOf(point.time),
        y: yOf(point.km),
        time: point.time,
        km: point.km,
      })),
    })),
    yTicks,
    xTicks,
  };
}

function utcDayLabel(ms) {
  const date = new Date(ms);
  const month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][
    date.getUTCMonth()
  ];
  return `${month} ${date.getUTCDate()}`;
}
