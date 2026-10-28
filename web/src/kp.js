// Polar Kp geometry for the public page (ADR 0020).
//
// Angle is time. Zero is at the top and time runs clockwise, like a clock.
// One lap is one day, 30 days, or 365 days. The lap starts on a fixed UTC
// boundary: midnight, the 1st of the month, or 1 January. A sample from the
// previous lap is overwritten when a newer sample lands in the same bin.

export const DAY_MS = 24 * 60 * 60 * 1000;
export const MONTH_MS = 30 * DAY_MS;
export const YEAR_MS = 365 * DAY_MS;
export const SOLAR_CYCLE_MS = 11 * YEAR_MS;
export const MINUTE_LIMIT = 2000;
export const GFZ_LIMIT = 40000;
// GFZ's file starts on this UT day. The 11-year lap is measured from it.
export const GFZ_EPOCH_MS = Date.UTC(1932, 0, 1);

const PLOTS = {
  day: { periodMs: DAY_MS, binMs: 10 * 60 * 1000, aggregate: "mean" },
  month: { periodMs: MONTH_MS, binMs: 3 * 60 * 60 * 1000, aggregate: "mean" },
  year: { periodMs: YEAR_MS, binMs: DAY_MS, aggregate: "max" },
  solar: { periodMs: SOLAR_CYCLE_MS, binMs: DAY_MS, aggregate: "max" },
};

export function lapStartMs(nowMs, plot) {
  const date = new Date(nowMs);
  const year = date.getUTCFullYear();
  const month = date.getUTCMonth();
  const day = date.getUTCDate();
  if (plot === "day") return Date.UTC(year, month, day);
  if (plot === "month") return Date.UTC(year, month, 1);
  if (plot === "year") return Date.UTC(year, 0, 1);
  if (plot === "solar") return GFZ_EPOCH_MS;
  throw new Error(`unknown plot ${plot}`);
}

// NOAA G-scale starts at Kp 5. https://www.swpc.noaa.gov/noaa-scales-explanation
export function gScale(kp) {
  if (kp == null || Number.isNaN(Number(kp)) || Number(kp) < 5) return null;
  const level = Math.min(5, Math.floor(Number(kp)) - 4);
  return `G${level}`;
}

export function kpRequestPaths(nowMs) {
  const end = new Date(nowMs).toISOString();
  const dayFrom = new Date(nowMs - DAY_MS).toISOString();
  const solarFrom = new Date(nowMs - SOLAR_CYCLE_MS).toISOString();
  return {
    minute: `/api/kp-1m?from=${encodeURIComponent(dayFrom)}&to=${encodeURIComponent(end)}&limit=${MINUTE_LIMIT}`,
    gfz: `/api/kp-gfz?from=${encodeURIComponent(solarFrom)}&to=${encodeURIComponent(end)}&limit=${GFZ_LIMIT}`,
  };
}

function positiveMod(value, period) {
  return ((value % period) + period) % period;
}

// samples are { time: epoch ms, value: number }. Nulls and points outside
// [now - period, now) are dropped. Two laps in one bin keep the newer lap.
// "mean" averages that lap. "max" keeps its largest value (the daily max).
export function radialBins({ samples, nowMs, plot }) {
  const spec = PLOTS[plot];
  if (!spec) throw new Error(`unknown plot ${plot}`);
  const { periodMs, binMs, aggregate } = spec;
  const binCount = Math.round(periodMs / binMs);
  const windowStart = nowMs - periodMs;
  const groups = new Map();

  for (const sample of samples) {
    const value = Number(sample.value);
    if (sample.value == null || Number.isNaN(value)) continue;
    if (!Number.isFinite(sample.time)) continue;
    if (sample.time < windowStart || sample.time >= nowMs) continue;
    const lap = Math.floor((sample.time - lapStartMs(nowMs, plot)) / periodMs);
    const along = positiveMod(sample.time - lapStartMs(nowMs, plot), periodMs);
    const index = Math.min(binCount - 1, Math.floor(along / binMs));
    const existing = groups.get(index);
    if (!existing || lap > existing.lap) {
      groups.set(index, {
        lap,
        sum: value,
        max: value,
        n: 1,
        time: sample.time,
      });
    } else if (lap === existing.lap) {
      existing.sum += value;
      existing.max = Math.max(existing.max, value);
      existing.n += 1;
      existing.time = Math.max(existing.time, sample.time);
    }
  }

  const bins = [];
  for (const [index, group] of groups) {
    const value = aggregate === "max" ? group.max : group.sum / group.n;
    bins.push({
      index,
      angleDeg: ((index + 0.5) / binCount) * 360,
      value,
      time: group.time,
      ageMs: nowMs - group.time,
    });
  }
  bins.sort((left, right) => left.index - right.index);
  const max = bins.reduce((highest, bin) => Math.max(highest, bin.value), 0);
  return { binCount, bins, max, periodMs };
}

export function angleDeg(timeMs, nowMs, plot) {
  const periodMs = PLOTS[plot].periodMs;
  const along = positiveMod(timeMs - lapStartMs(nowMs, plot), periodMs);
  return (along / periodMs) * 360;
}

export function samplesFromRows(rows, valueKey) {
  return rows.map((row) => ({
    time: Date.parse(row.time_tag),
    value: row[valueKey],
  }));
}

export function toCsv(bins) {
  const lines = ["time_utc,kp,g_scale"];
  for (const bin of bins) {
    const scale = gScale(bin.value) ?? "";
    lines.push(`${new Date(bin.time).toISOString()},${bin.value},${scale}`);
  }
  return `${lines.join("\n")}\n`;
}
