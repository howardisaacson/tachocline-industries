import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  SOLAR_RV_GAP_MS,
  SOLAR_RV_WINDOW_MS,
  chartGeometry,
  segmentsOf,
  seriesFromRows,
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
      { time_tag: "2026-11-05T18:00:00Z", instrument: "neid", rv_m_s: -640 },
      { time_tag: "2026-11-05T18:02:00Z", instrument: "neid", rv_m_s: null },
      { time_tag: "2026-11-05T17:00:00Z", instrument: "expres", rv_m_s: -650 },
      { time_tag: "2026-11-05T18:00:00Z", instrument: "other", rv_m_s: -1 },
    ]);
    assert.deepEqual(
      series.map((item) => item.id),
      ["neid", "expres"],
    );
    assert.deepEqual(
      series[0].points.map((point) => point.rv),
      [-640],
    );
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
});
