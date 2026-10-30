import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  DAY_MS,
  YEAR_MS,
  gScale,
  kpRequestPaths,
  radialBins,
} from "./kp.js";

const NOW = Date.UTC(2026, 9, 27, 12, 9, 0);

describe("gScale", () => {
  it("starts at Kp 5 and stops at G5", () => {
    assert.equal(gScale(4.9), null);
    assert.equal(gScale(5), "G1");
    assert.equal(gScale(6.2), "G2");
    assert.equal(gScale(9.9), "G5");
    assert.equal(gScale(null), null);
  });
});

describe("kpRequestPaths", () => {
  it("asks for one day of minutes and eleven years of GFZ Kp", () => {
    const paths = kpRequestPaths(NOW);
    const minute = new URL(paths.minute, "http://ti.local");
    const threeHour = new URL(paths.gfz, "http://ti.local");
    const minuteSpan =
      Date.parse(minute.searchParams.get("to")) -
      Date.parse(minute.searchParams.get("from"));
    const yearSpan =
      Date.parse(threeHour.searchParams.get("to")) -
      Date.parse(threeHour.searchParams.get("from"));
    assert.equal(minute.pathname, "/api/kp-1m");
    assert.equal(minuteSpan, DAY_MS);
    assert.equal(minute.searchParams.get("limit"), "2000");
    assert.equal(threeHour.pathname, "/api/kp-gfz");
    assert.equal(yearSpan, 11 * YEAR_MS);
    assert.equal(threeHour.searchParams.get("limit"), "40000");
  });
});

describe("radialBins", () => {
  it("averages one lap and drops a gap", () => {
    const result = radialBins({
      nowMs: NOW,
      plot: "day",
      samples: [
        { time: Date.UTC(2026, 9, 27, 12, 0, 0), value: 2 },
        { time: Date.UTC(2026, 9, 27, 12, 5, 0), value: 4 },
        { time: Date.UTC(2026, 9, 27, 10, 0, 0), value: null },
      ],
    });
    assert.equal(result.bins.length, 1);
    assert.equal(result.bins[0].value, 3);
    assert.equal(result.max, 3);
  });

  it("lets the newer lap overwrite the same clock bin", () => {
    const result = radialBins({
      nowMs: NOW,
      plot: "day",
      samples: [
        { time: Date.UTC(2026, 9, 26, 12, 9, 0), value: 9 },
        { time: Date.UTC(2026, 9, 27, 12, 5, 0), value: 2 },
      ],
    });
    assert.equal(result.bins.length, 1);
    assert.equal(result.bins[0].value, 2);
  });

  it("ignores samples outside the lap window", () => {
    const result = radialBins({
      nowMs: NOW,
      plot: "day",
      samples: [{ time: NOW - DAY_MS - 60_000, value: 8 }],
    });
    assert.equal(result.bins.length, 0);
    assert.equal(result.max, 0);
  });

  it("uses the daily maximum on the year plot", () => {
    const result = radialBins({
      nowMs: NOW,
      plot: "year",
      samples: [
        { time: Date.UTC(2026, 9, 27, 0, 0, 0), value: 3 },
        { time: Date.UTC(2026, 9, 27, 6, 0, 0), value: 7 },
        { time: Date.UTC(2026, 9, 26, 0, 0, 0), value: 4 },
      ],
    });
    const today = result.bins.find((bin) => bin.time >= Date.UTC(2026, 9, 27));
    assert.equal(today.value, 7);
    assert.equal(result.bins.length, 2);
  });
});
