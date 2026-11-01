import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  CART,
  RING,
  cartesianPoint,
  easeDial,
  localProgress,
  morphPoint,
  plottedValues,
  radialPoint,
} from "./plotLayout.js";

const bins = [
  { index: 0, angleDeg: 15, value: 2, time: 1000, ageMs: 100 },
  { index: 5, angleDeg: 180, value: 6, time: 2000, ageMs: 50 },
  { index: 11, angleDeg: 345, value: 1.5, time: 3000, ageMs: 10 },
];

describe("easeDial", () => {
  it("starts fast and finishes gently", () => {
    assert.equal(easeDial(0), 0);
    assert.equal(easeDial(1), 1);
    // Ease-out cubic: early progress ahead of linear, late delta smaller.
    assert.ok(easeDial(0.3) > 0.3);
    assert.ok(easeDial(0.9) - easeDial(0.8) < easeDial(0.2) - easeDial(0.1));
  });
});

describe("plottedValues", () => {
  it("keeps the same identity for radial and Cartesian layouts", () => {
    const scaleMax = 6;
    const binCount = 12;
    const radial = bins.map((bin) => ({
      ...plottedValues([bin])[0],
      ...radialPoint(bin, scaleMax),
    }));
    const cartesian = bins.map((bin) => ({
      ...plottedValues([bin])[0],
      ...cartesianPoint(bin, scaleMax, binCount),
    }));
    assert.deepEqual(
      radial.map((p) => ({ index: p.index, time: p.time, value: p.value })),
      cartesian.map((p) => ({ index: p.index, time: p.time, value: p.value })),
    );
    assert.ok(cartesian[0].x >= CART.left);
    assert.ok(cartesian[2].x <= CART.right);
  });
});

describe("morphPoint", () => {
  it("matches radial at t=0 and Cartesian at t=1", () => {
    const bin = bins[1];
    const scaleMax = 6;
    const binCount = 12;
    const at0 = morphPoint(bin, scaleMax, binCount, 0);
    const at1 = morphPoint(bin, scaleMax, binCount, 1);
    const radial = radialPoint(bin, scaleMax);
    const cart = cartesianPoint(bin, scaleMax, binCount);
    assert.ok(Math.abs(at0.x - radial.x) < 1e-9);
    assert.ok(Math.abs(at0.y - radial.y) < 1e-9);
    assert.ok(Math.abs(at1.x - cart.x) < 1e-9);
    assert.ok(Math.abs(at1.y - cart.y) < 1e-9);
  });

  it("starts the unwind nearer 12 o'clock first", () => {
    const early = localProgress(0.2, 10);
    const late = localProgress(0.2, 350);
    assert.ok(early > late);
  });
});

describe("cartesianPoint", () => {
  it("puts higher Kp closer to the top of the plot", () => {
    const low = cartesianPoint(bins[0], 6, 12);
    const high = cartesianPoint(bins[1], 6, 12);
    assert.ok(high.y < low.y);
    assert.ok(high.y >= CART.top);
    assert.ok(low.y <= CART.bottom);
  });
});

describe("radialPoint", () => {
  it("puts higher Kp farther from the center", () => {
    const low = radialPoint(bins[0], 6);
    const high = radialPoint(bins[1], 6);
    const lowR = Math.hypot(low.x - 100, low.y - 100);
    const highR = Math.hypot(high.x - 100, high.y - 100);
    assert.ok(highR > lowR);
    assert.ok(highR <= RING + 1e-9);
  });
});
