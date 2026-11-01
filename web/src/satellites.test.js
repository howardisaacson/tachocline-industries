import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  PERIGEE_WINDOW_MS,
  TRACKED_SATELLITES,
  chartGeometry,
  perigeeRequestPath,
  seriesFromRows,
} from "./satellites.js";

describe("perigee request", () => {
  it("asks the API for seven days and stays under its row cap", () => {
    const now = Date.UTC(2026, 10, 1, 12);
    const path = perigeeRequestPath(now);
    const params = new URL(path, "http://localhost").searchParams;
    const from = Date.parse(params.get("from"));
    const to = Date.parse(params.get("to"));
    assert.equal(to - from, PERIGEE_WINDOW_MS);
    assert.equal(to, now);
    assert.equal(params.get("limit"), "2000");
    assert.match(path, /^\/api\/v1\/satellite-perigee\?/);
  });
});

describe("seriesFromRows", () => {
  it("keeps the five tracked objects and drops anything else", () => {
    const series = seriesFromRows([
      { epoch: "2026-11-01T00:00:00Z", norad_cat_id: 25544, perigee_altitude_km: 410 },
      { epoch: "2026-10-31T00:00:00Z", norad_cat_id: 25544, perigee_altitude_km: 420 },
      { epoch: "2026-11-01T00:00:00Z", norad_cat_id: 99999, perigee_altitude_km: 100 },
    ]);
    assert.equal(series.length, TRACKED_SATELLITES.length);
    assert.deepEqual(
      series[0].points.map((point) => point.km),
      [420, 410],
    );
    assert.equal(series.find((sat) => sat.noradCatId === 99999), undefined);
    assert.equal(series.find((sat) => sat.noradCatId === 28485).points.length, 0);
  });
});

describe("chartGeometry", () => {
  it("puts a higher perigee above a lower one, and a later epoch to the right", () => {
    const fromMs = Date.UTC(2026, 10, 1);
    const toMs = fromMs + PERIGEE_WINDOW_MS;
    const series = seriesFromRows([
      { epoch: "2026-11-01T00:00:00Z", norad_cat_id: 25544, perigee_altitude_km: 400 },
      { epoch: "2026-11-02T00:00:00Z", norad_cat_id: 25544, perigee_altitude_km: 500 },
      { epoch: "2026-11-01T00:00:00Z", norad_cat_id: 28485, perigee_altitude_km: 220 },
    ]);
    const geometry = chartGeometry(series, { width: 640, height: 320, fromMs, toMs });
    const iss = geometry.lines.find((line) => line.noradCatId === 25544);
    const swift = geometry.lines.find((line) => line.noradCatId === 28485);
    assert.ok(iss.points[1].x > iss.points[0].x);
    assert.ok(iss.points[1].y < iss.points[0].y);
    assert.ok(swift.points[0].y > iss.points[0].y);
  });
});
