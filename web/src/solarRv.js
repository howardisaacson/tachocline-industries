// Sun-as-a-star radial velocity for the home page.
// The browser only sees GET /api/v1/solar-rv. Velocities are meters per second.

export const SOLAR_RV_WINDOW_MS = 7 * 24 * 60 * 60 * 1000;
export const SOLAR_RV_DAY_MS = 24 * 60 * 60 * 1000;
export const SOLAR_RV_LIMIT = 5000;
// A line across a night would invent velocities the archive did not measure.
export const SOLAR_RV_GAP_MS = 30 * 60 * 1000;
// The drawn axis is this far before and after the newest exposure.
export const SOLAR_RV_AXIS_PAD_MS = 30 * 60 * 1000;

export const SOLAR_INSTRUMENTS = [
  { id: "neid", name: "NEID", color: "#8eb6ff" },
  { id: "expres", name: "EXPRES", color: "#e07a3d" },
];

// Shortened viridis: low SNR stays visible on black, high SNR is yellow.
// https://bids.github.io/colormap/ — viridis is ordered so colorblind readers
// still see low versus high. These four stops are samples of that map.
export const SNR_STOPS = ["#3b528b", "#21918c", "#5ec962", "#fde725"];
export const SNR_MISSING = "#9aa0b4";

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
    const snr = row.snr == null ? Number.NaN : Number(row.snr);
    if (!Number.isFinite(time) || !Number.isFinite(rv)) continue;
    points.push({ time, rv, snr: Number.isFinite(snr) ? snr : null });
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

/** Exposures in the 24 hours ending at the newest point. Older rows stay out. */
export function pointsInLatestDay(series) {
  const times = (series ?? []).flatMap((item) => item.points.map((point) => point.time));
  if (times.length === 0) return series ?? [];
  const last = Math.max(...times);
  const start = last - SOLAR_RV_DAY_MS;
  return series.map((item) => ({
    ...item,
    points: item.points.filter((point) => point.time >= start && point.time <= last),
  }));
}

/**
 * X-axis limits: 30 minutes before the newest exposure and 30 minutes after it.
 * `fallback` is used when the series has no points.
 */
export function timeDomain(series, fallback) {
  const times = (series ?? []).flatMap((item) => item.points.map((point) => point.time));
  if (times.length === 0) return fallback;
  const last = Math.max(...times);
  return {
    fromMs: last - SOLAR_RV_AXIS_PAD_MS,
    toMs: last + SOLAR_RV_AXIS_PAD_MS,
  };
}

/**
 * Pixel geometry for an SVG that is `width` by `height` CSS pixels.
 * A larger velocity is a smaller y. Only the latest day is considered, and
 * only points inside the 30-minute axis are drawn.
 */
export function chartGeometry(series, { width, height, fromMs, toMs }) {
  const day = pointsInLatestDay(series);
  const domain = timeDomain(day, { fromMs, toMs });
  const span = Math.max(1, domain.toMs - domain.fromMs);
  const kept = day.map((item) => ({
    ...item,
    points: item.points.filter(
      (point) => point.time >= domain.fromMs && point.time <= domain.toMs,
    ),
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
  const domainSnr = snrDomain(kept);
  const innerW = Math.max(1, width - PAD.left - PAD.right);
  const innerH = Math.max(1, height - PAD.top - PAD.bottom);
  const xOf = (time) => PAD.left + ((time - domain.fromMs) / span) * innerW;
  const yOf = (rv) => PAD.top + ((maxRv - rv) / (maxRv - minRv)) * innerH;
  const yTicks = [0, 1, 2, 3, 4].map((step) => {
    const rv = minRv + ((maxRv - minRv) * step) / 4;
    return { rv, y: yOf(rv), label: String(Math.round(rv)) };
  });
  const xTicks = [0, 0.5, 1].map((fraction) => {
    const time = domain.fromMs + span * fraction;
    return { time, x: xOf(time), label: utcAxisLabel(time, span) };
  });
  return {
    empty: all.length === 0,
    fromMs: domain.fromMs,
    toMs: domain.toMs,
    snrMin: domainSnr?.min ?? null,
    snrMax: domainSnr?.max ?? null,
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
          snr: point.snr ?? null,
          color: snrColor(point.snr, domainSnr),
        })),
      ),
    })),
    yTicks,
    xTicks,
  };
}

/** The point closest to a pointer, in SVG pixels. Null when the plot is empty. */
export function nearestPoint(lines, x, y) {
  let best = null;
  let bestDistance = Infinity;
  for (const line of lines ?? []) {
    for (const point of line.segments.flat()) {
      const distance = (point.x - x) ** 2 + (point.y - y) ** 2;
      if (distance < bestDistance) {
        bestDistance = distance;
        best = { ...point, id: line.id, name: line.name };
      }
    }
  }
  return best;
}

/** Lowest and highest SNR among points that published one. Null when none did. */
export function snrDomain(series) {
  const values = (series ?? [])
    .flatMap((item) => item.points.map((point) => point.snr))
    .filter((value) => Number.isFinite(value));
  if (values.length === 0) return null;
  return { min: Math.min(...values), max: Math.max(...values) };
}

/**
 * Linear color from the lowest SNR on the chart to the highest.
 * A missing SNR is gray. It is not painted as zero.
 */
export function snrColor(snr, domain) {
  if (!Number.isFinite(snr) || domain == null) return SNR_MISSING;
  const span = domain.max - domain.min;
  const t = span < 1e-9 ? 0.5 : (snr - domain.min) / span;
  return mixStops(SNR_STOPS, Math.min(1, Math.max(0, t)));
}

/** One line under the chart. The clock is UTC, matching the axis. */
export function formatReadout(point) {
  if (point == null) return "Move over the plot to read UTC time, velocity, and SNR.";
  const stamp = new Date(point.time).toISOString().slice(0, 16).replace("T", " ");
  return `${point.name} · ${stamp} UTC · ${point.rv.toFixed(1)} m/s · ${formatSnr(point.snr)}`;
}

function formatSnr(snr) {
  if (!Number.isFinite(snr)) return "SNR —";
  const rounded = Math.round(snr * 10) / 10;
  const text = Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
  return `SNR ${text}`;
}

function mixStops(stops, t) {
  const scaled = t * (stops.length - 1);
  const index = Math.min(stops.length - 2, Math.floor(scaled));
  return mixHex(stops[index], stops[index + 1], scaled - index);
}

function mixHex(start, end, t) {
  const left = hexChannels(start);
  const right = hexChannels(end);
  const channels = left.map((channel, index) =>
    Math.round(channel + (right[index] - channel) * t)
      .toString(16)
      .padStart(2, "0"),
  );
  return `#${channels.join("")}`;
}

function hexChannels(hex) {
  return [1, 3, 5].map((offset) => Number.parseInt(hex.slice(offset, offset + 2), 16));
}

function utcAxisLabel(ms, span) {
  const date = new Date(ms);
  const month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][
    date.getUTCMonth()
  ];
  const day = `${month} ${date.getUTCDate()}`;
  const hour = String(date.getUTCHours()).padStart(2, "0");
  if (span < 6 * 60 * 60 * 1000) {
    const minute = String(date.getUTCMinutes()).padStart(2, "0");
    return `${day} ${hour}:${minute}`;
  }
  if (span >= 36 * 60 * 60 * 1000) return day;
  return `${day} ${hour}h`;
}
