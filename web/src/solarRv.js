// Sun-as-a-star radial velocity for the home page.
// The browser only sees GET /api/v1/solar-rv. Velocities are meters per second.

export const SOLAR_RV_WINDOW_MS = 7 * 24 * 60 * 60 * 1000;
export const SOLAR_RV_LIMIT = 5000;
// A line across a night would invent velocities the archive did not measure.
export const SOLAR_RV_GAP_MS = 30 * 60 * 1000;

export const SOLAR_INSTRUMENTS = [
  { id: "neid", name: "NEID", color: "#8eb6ff" },
  { id: "expres", name: "EXPRES", color: "#e07a3d" },
];

const PAD = { left: 52, right: 16, top: 16, bottom: 32 };

export function solarRvRequestPath(nowMs) {
  const end = new Date(nowMs).toISOString();
  const start = new Date(nowMs - SOLAR_RV_WINDOW_MS).toISOString();
  const params = new URLSearchParams({
    from: start,
    to: end,
    limit: String(SOLAR_RV_LIMIT),
  });
  return `/api/v1/solar-rv?${params.toString()}`;
}

/** One series per instrument, oldest first. A null velocity is left out. */
export function seriesFromRows(rows) {
  const byId = new Map(SOLAR_INSTRUMENTS.map((item) => [item.id, []]));
  for (const row of rows ?? []) {
    const points = byId.get(row.instrument);
    if (!points) continue;
    const time = Date.parse(row.time_tag);
    const rv = row.rv_m_s == null ? Number.NaN : Number(row.rv_m_s);
    if (!Number.isFinite(time) || !Number.isFinite(rv)) continue;
    points.push({ time, rv });
  }
  return SOLAR_INSTRUMENTS.map((item) => ({
    ...item,
    points: byId.get(item.id).sort((left, right) => left.time - right.time),
  }));
}

/** Split a series where two exposures are more than maxGapMs apart. */
export function segmentsOf(points, maxGapMs = SOLAR_RV_GAP_MS) {
  const segments = [];
  let current = [];
  for (const point of points) {
    const previous = current[current.length - 1];
    if (previous && point.time - previous.time > maxGapMs) {
      segments.push(current);
      current = [];
    }
    current.push(point);
  }
  if (current.length > 0) segments.push(current);
  return segments;
}

/**
 * Pixel geometry for an SVG that is `width` by `height` CSS pixels.
 * A larger velocity is a smaller y. The x axis is the requested window.
 */
export function chartGeometry(series, { width, height, fromMs, toMs }) {
  const span = Math.max(1, toMs - fromMs);
  const kept = series.map((item) => ({
    ...item,
    points: item.points.filter((point) => point.time >= fromMs && point.time < toMs),
  }));
  const all = kept.flatMap((item) => item.points);
  let minRv = -800;
  let maxRv = -400;
  if (all.length > 0) {
    minRv = Math.min(...all.map((point) => point.rv));
    maxRv = Math.max(...all.map((point) => point.rv));
    if (maxRv - minRv < 1) {
      minRv -= 1;
      maxRv += 1;
    }
    const pad = (maxRv - minRv) * 0.08;
    minRv -= pad;
    maxRv += pad;
  }
  const innerW = Math.max(1, width - PAD.left - PAD.right);
  const innerH = Math.max(1, height - PAD.top - PAD.bottom);
  const xOf = (time) => PAD.left + ((time - fromMs) / span) * innerW;
  const yOf = (rv) => PAD.top + ((maxRv - rv) / (maxRv - minRv)) * innerH;
  const yTicks = [0, 1, 2, 3, 4].map((step) => {
    const rv = minRv + ((maxRv - minRv) * step) / 4;
    return { rv, y: yOf(rv), label: String(Math.round(rv)) };
  });
  const xTicks = [0, 0.5, 1].map((fraction) => {
    const time = fromMs + span * fraction;
    return { time, x: xOf(Math.min(time, toMs - 1)), label: utcDayLabel(time) };
  });
  return {
    empty: all.length === 0,
    lines: kept.map((item) => ({
      id: item.id,
      name: item.name,
      color: item.color,
      segments: segmentsOf(item.points).map((segment) =>
        segment.map((point) => ({
          x: xOf(point.time),
          y: yOf(point.rv),
          time: point.time,
          rv: point.rv,
        })),
      ),
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
