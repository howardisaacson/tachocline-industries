// Shared polar ↔ Cartesian layout for the Kp clocks (issue #94, ADR 0029).
// progress 0 = radial, 1 = Cartesian. Same bins in both views.

export const SIZE = 200;
export const CENTER = 100;
export const RING = 78;

export const CART = {
  left: 28,
  right: 188,
  top: 18,
  bottom: 168,
};

export function prefersReducedMotion() {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Fast start, gentle stop — like a rotary dial spinning home. */
export function easeDial(t) {
  const x = Math.min(1, Math.max(0, t));
  return 1 - (1 - x) ** 3;
}

export function polar(angleDeg, radius, center = CENTER) {
  const radians = (angleDeg * Math.PI) / 180;
  return {
    x: center + radius * Math.sin(radians),
    y: center - radius * Math.cos(radians),
  };
}

export function radialPoint(bin, scaleMax) {
  const radius = (bin.value / scaleMax) * RING;
  return polar(bin.angleDeg, radius);
}

export function cartesianPoint(bin, scaleMax, binCount) {
  const frac = (bin.index + 0.5) / binCount;
  const x = CART.left + frac * (CART.right - CART.left);
  const y = CART.bottom - (bin.value / scaleMax) * (CART.bottom - CART.top);
  return { x, y };
}

/** Stagger so the unwind starts near 12 o'clock and finishes near a full turn. */
export function localProgress(globalT, angleDeg) {
  const lag = (angleDeg / 360) * 0.35;
  const span = 1 - 0.35;
  if (span <= 0) return easeDial(globalT);
  return easeDial(Math.min(1, Math.max(0, (globalT - lag) / span)));
}

export function lerp(a, b, t) {
  return a + (b - a) * t;
}

export function morphPoint(bin, scaleMax, binCount, globalT) {
  const from = radialPoint(bin, scaleMax);
  const to = cartesianPoint(bin, scaleMax, binCount);
  const t = localProgress(globalT, bin.angleDeg);
  return {
    x: lerp(from.x, to.x, t),
    y: lerp(from.y, to.y, t),
    t,
  };
}

export function nowRadial(nowAngleDeg) {
  return polar(nowAngleDeg, RING);
}

export function nowCartesian(nowAngleDeg) {
  const frac = nowAngleDeg / 360;
  return {
    x: CART.left + frac * (CART.right - CART.left),
    y: CART.bottom,
  };
}

export function morphNow(nowAngleDeg, globalT) {
  const from = nowRadial(nowAngleDeg);
  const to = nowCartesian(nowAngleDeg);
  const t = easeDial(globalT);
  return {
    x: lerp(from.x, to.x, t),
    y: lerp(from.y, to.y, t),
  };
}

/** Stable identity for tests: same bins → same plotted values in both layouts. */
export function plottedValues(bins) {
  return bins.map((bin) => ({
    index: bin.index,
    time: bin.time,
    value: bin.value,
  }));
}
