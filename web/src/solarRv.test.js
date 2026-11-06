import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  SNR_MISSING,
  SOLAR_RV_AXIS_PAD_MS,
  SOLAR_RV_DAY_MS,
  SOLAR_RV_GAP_MS,
  SOLAR_RV_WINDOW_MS,
  chartGeometry,
  formatReadout,
  nearestPoint,
  segmentsOf,
  seriesFromRows,
  snrColor,
  solarRvRequestPath,
} from "./solarRv.js";

describe("solar RV request", () => {
  it("asks the API for seven days", () => {
    const now = Date.UTC(2026, 10, 5, 12);
    const path = solarRvRequestPath(now);
    const params = new URL(path, "http://localhost").searchParams;
    const from = Date.parse(params.get("from"));
    const to = Date.parse(params.get("to"));
    assert.equal(to - from, SOLAR_RV_WINDOW_MS);
    assert.equal(to, now);
    assert.equal(params.get("limit"), "5000");
    assert.match(path, /^\/api\/v1\/solar-rv\?/);
  });
});

describe("seriesFromRows", () => {
  it("drops a null velocity and keeps both instruments", () => {
    const series = seriesFromRows([
      { time_tag: "2026-11-05T18:00:00Z", instrument: "neid", rv_m_s: -640, snr: 328.7 },
      { time_tag: "2026-11-05T18:02:00Z", instrument: "neid", rv_m_s: null, snr: 10 },
      { time_tag: "2026-11-05T17:00:00Z", instrument: "expres", rv_m_s: -650, snr: null },
      { time_tag: "2026-11-05T18:00:00Z", instrument: "other", rv_m_s: -1, snr: 1 },
    ]);
    assert.deepEqual(
      series.map((item) => item.id),
      ["neid", "expres"],
    );
    assert.deepEqual(
      series[0].points.map((point) => point.rv),
      [-640],
    );
    assert.equal(series[0].points[0].snr, 328.7);
    assert.equal(series[1].points[0].snr, null);
    assert.equal(series[1].points.length, 1);
  });
});

describe("segmentsOf", () => {
  it("breaks the line when exposures are more than 30 minutes apart", () => {
    const start = Date.UTC(2026, 10, 5, 18);
    const points = [
      { time: start, rv: -640 },
      { time: start + 2 * 60 * 1000, rv: -641 },
      { time: start + 2 * 60 * 1000 + SOLAR_RV_GAP_MS + 1000, rv: -642 },
    ];
    const segments = segmentsOf(points);
    assert.equal(segments.length, 2);
    assert.equal(segments[0].length, 2);
    assert.equal(segments[1].length, 1);
  });
});

describe("chartGeometry", () => {
  it("uses the same x for the same time on both series", () => {
    const fromMs = Date.UTC(2026, 10, 1);
    const toMs = fromMs + SOLAR_RV_WINDOW_MS;
    const time = fromMs + 2 * 24 * 60 * 60 * 1000;
    const geometry = chartGeometry(
      [
        { id: "neid", name: "NEID", color: "#8eb6ff", points: [{ time, rv: -640 }] },
        { id: "expres", name: "EXPRES", color: "#e07a3d", points: [{ time, rv: -650 }] },
      ],
      { width: 640, height: 280, fromMs, toMs },
    );
    const neid = geometry.lines[0].segments[0][0];
    const expres = geometry.lines[1].segments[0][0];
    assert.equal(neid.x, expres.x);
    assert.ok(neid.y < expres.y);
  });

  it("draws the last 30 minutes of the latest day around the newest point", () => {
    const last = Date.UTC(2026, 10, 3, 22, 30);
    const recent = last - 20 * 60 * 1000;
    const earlierSameDay = last - 23 * 60 * 60 * 1000;
    const olderThanADay = last - SOLAR_RV_DAY_MS - 60 * 60 * 1000;
    const geometry = chartGeometry(
      [
        {
          id: "neid",
          name: "NEID",
          color: "#8eb6ff",
          points: [
            { time: olderThanADay, rv: -600 },
            { time: earlierSameDay, rv: -610 },
            { time: recent, rv: -640 },
            { time: last, rv: -650 },
          ],
        },
      ],
      { width: 640, height: 280, fromMs: 0, toMs: 1 },
    );
    assert.equal(geometry.fromMs, last - SOLAR_RV_AXIS_PAD_MS);
    assert.equal(geometry.toMs, last + SOLAR_RV_AXIS_PAD_MS);
    const drawn = geometry.lines[0].segments.flat();
    assert.deepEqual(
      drawn.map((point) => point.time),
      [recent, last],
    );
    const mid = 52 + (640 - 52 - 16) / 2;
    assert.ok(Math.abs(drawn[1].x - mid) < 1);
    assert.ok(drawn[0].x > 52);
    assert.ok(drawn[0].x < drawn[1].x);
  });

  it("paints a higher SNR further along the scale than a lower one", () => {
    const time = Date.UTC(2026, 10, 2, 16);
    const geometry = chartGeometry(
      [
        {
          id: "neid",
          name: "NEID",
          color: "#8eb6ff",
          points: [
            { time, rv: -640, snr: 40 },
            { time: time + 60_000, rv: -641, snr: 330 },
            { time: time + 120_000, rv: -642, snr: null },
          ],
        },
      ],
      { width: 640, height: 280, fromMs: 0, toMs: 1 },
    );
    const [low, high, missing] = geometry.lines[0].segments.flat();
    assert.equal(geometry.snrMin, 40);
    assert.equal(geometry.snrMax, 330);
    assert.equal(low.color, snrColor(40, { min: 40, max: 330 }));
    assert.notEqual(low.color, high.color);
    assert.equal(missing.color, SNR_MISSING);
  });
});

describe("nearest point readout", () => {
  it("picks the closer exposure and prints UTC time and velocity", () => {
    const time = Date.UTC(2026, 10, 2, 17, 17);
    const lines = [
      {
        id: "neid",
        name: "NEID",
        segments: [[{ time, x: 100, y: 40, rv: -640.1, snr: 328.7 }]],
      },
      {
        id: "expres",
        name: "EXPRES",
        segments: [[{ time, x: 100, y: 80, rv: -650.2, snr: null }]],
      },
    ];
    const point = nearestPoint(lines, 100, 50);
    assert.equal(point.name, "NEID");
    assert.equal(
      formatReadout(point),
      "NEID · 2026-11-02 17:17 UTC · -640.1 m/s · SNR 328.7",
    );
    assert.match(formatReadout({ ...point, snr: null }), /SNR —/);
    assert.match(formatReadout(null), /Move over the plot/);
  });
});
