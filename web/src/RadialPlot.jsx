import { useEffect, useRef, useState } from "react";

import { angleDeg, gScale } from "./kp.js";
import {
  CART,
  CENTER,
  RING,
  SIZE,
  easeDial,
  morphNow,
  morphPoint,
  prefersReducedMotion,
} from "./plotLayout.js";

const ANIM_MS = 1000;

function stormColor(kp) {
  const scale = gScale(kp);
  if (scale === "G1") return "#c6b15a";
  if (scale === "G2") return "#d08a3a";
  if (scale === "G3") return "#d4653a";
  if (scale === "G4" || scale === "G5") return "#e24b4b";
  return "#f0f0fa";
}

function segments(bins, binCount) {
  const byIndex = new Map(bins.map((bin) => [bin.index, bin]));
  const lines = [];
  for (const bin of bins) {
    const next = byIndex.get((bin.index + 1) % binCount);
    if (next) lines.push([bin, next]);
  }
  return lines;
}

function formatUtc(ms) {
  return new Date(ms).toISOString().slice(0, 16).replace("T", " ");
}

function formatKp(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  const scale = gScale(value);
  return scale
    ? `Kp ${Number(value).toFixed(2)} · ${scale}`
    : `Kp ${Number(value).toFixed(2)}`;
}

function nearestByAngle(bins, angle) {
  let best = bins[0];
  let bestDistance = 360;
  for (const bin of bins) {
    const raw = Math.abs(bin.angleDeg - angle);
    const distance = Math.min(raw, 360 - raw);
    if (distance < bestDistance) {
      best = bin;
      bestDistance = distance;
    }
  }
  return best;
}

function nearestByIndex(bins, binCount, clientX, rect) {
  const frac = (clientX - rect.left) / rect.width;
  // Map SVG plot width: approximate using viewBox aspect (square).
  const svgX = frac * SIZE;
  const plotFrac = (svgX - CART.left) / (CART.right - CART.left);
  const index = Math.min(
    binCount - 1,
    Math.max(0, Math.floor(plotFrac * binCount)),
  );
  let best = bins[0];
  let bestDistance = Infinity;
  for (const bin of bins) {
    const distance = Math.abs(bin.index - index);
    if (distance < bestDistance) {
      best = bin;
      bestDistance = distance;
    }
  }
  return best;
}

export function RadialPlot({
  title,
  lapLabel,
  plot,
  geometry,
  nowMs,
  fixedScale,
  onSelect,
  onDownloadCsv,
}) {
  const [active, setActive] = useState(null);
  const [cartesian, setCartesian] = useState(false);
  const [progress, setProgress] = useState(0);
  const animRef = useRef(null);
  const progressRef = useRef(0);
  const scaleMax = fixedScale ? 9 : Math.max(geometry.max, 1);
  const nowAngle = angleDeg(nowMs, nowMs, plot);
  const atNow = newest(geometry.bins);
  const shown = active ?? atNow;
  const radialWeight = 1 - easeDial(progress);
  const cartWeight = easeDial(progress);

  useEffect(() => {
    progressRef.current = progress;
  }, [progress]);

  useEffect(
    () => () => {
      if (animRef.current != null) cancelAnimationFrame(animRef.current);
    },
    [],
  );

  function animateTo(target) {
    if (animRef.current != null) cancelAnimationFrame(animRef.current);
    if (prefersReducedMotion()) {
      progressRef.current = target;
      setProgress(target);
      return;
    }
    const from = progressRef.current;
    const started = performance.now();
    function frame(now) {
      const u = Math.min(1, (now - started) / ANIM_MS);
      const next = from + (target - from) * u;
      progressRef.current = next;
      setProgress(next);
      if (u < 1) {
        animRef.current = requestAnimationFrame(frame);
      } else {
        animRef.current = null;
        progressRef.current = target;
        setProgress(target);
      }
    }
    animRef.current = requestAnimationFrame(frame);
  }

  function toggleView() {
    const next = !cartesian;
    setCartesian(next);
    animateTo(next ? 1 : 0);
  }

  function selectFromPointer(event) {
    if (geometry.bins.length === 0) return;
    const rect = event.currentTarget.getBoundingClientRect();
    let best;
    if (progress > 0.5) {
      best = nearestByIndex(
        geometry.bins,
        geometry.binCount,
        event.clientX,
        rect,
      );
    } else {
      const x = event.clientX - rect.left - rect.width / 2;
      const y = event.clientY - rect.top - rect.height / 2;
      const pointer = (Math.atan2(x, -y) * 180) / Math.PI;
      best = nearestByAngle(geometry.bins, (pointer + 360) % 360);
    }
    setActive(best);
    onSelect?.(best);
  }

  const label =
    shown == null
      ? `${title}. No stored Kp on this lap.`
      : `${title}. Selected Kp ${shown.value.toFixed(2)} at ${new Date(shown.time).toISOString()}.`;

  const viewLabel = cartesian ? "radial clock" : "time-series chart";
  const readoutText =
    shown == null
      ? "No stored value on this lap."
      : `${formatUtc(shown.time)} UTC · ${formatKp(shown.value)}`;

  const head = morphNow(nowAngle, progress);
  const points = geometry.bins.map((bin) => ({
    bin,
    at: morphPoint(bin, scaleMax, geometry.binCount, progress),
  }));

  return (
    <div className="plot-frame">
      <button
        type="button"
        className="view-toggle"
        aria-label="Change Data View"
        aria-pressed={cartesian}
        title={`Change Data View (${viewLabel})`}
        onClick={toggleView}
      >
        <span className="view-toggle-label">Change Data View</span>
      </button>
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        role="img"
        aria-label={label}
        onPointerMove={selectFromPointer}
      >
        {/* Radial rings fade out as the dial unwinds. */}
        {[1, 2, 3].map((step) => (
          <circle
            key={`ring-${step}`}
            cx={CENTER}
            cy={CENTER}
            r={(RING * step) / 3}
            className="ring"
            opacity={radialWeight}
          />
        ))}
        {/* Cartesian grid fades in. */}
        {[1, 2, 3].map((step) => {
          const y =
            CART.bottom - ((step / 3) * (CART.bottom - CART.top));
          return (
            <line
              key={`grid-${step}`}
              x1={CART.left}
              y1={y}
              x2={CART.right}
              y2={y}
              className="ring"
              opacity={cartWeight}
            />
          );
        })}
        <line
          x1={CART.left}
          y1={CART.bottom}
          x2={CART.right}
          y2={CART.bottom}
          className="ring"
          opacity={cartWeight}
        />
        <line
          x1={CART.left}
          y1={CART.top}
          x2={CART.left}
          y2={CART.bottom}
          className="ring"
          opacity={cartWeight}
        />
        <text
          x={CENTER}
          y={CENTER - RING - 6}
          className="tick"
          textAnchor="middle"
          opacity={radialWeight}
        >
          {lapLabel}
        </text>
        <text
          x={CENTER + 8}
          y={CENTER - 6}
          className="tick"
          opacity={radialWeight}
        >
          {fixedScale ? "0–9" : `max ${geometry.max.toFixed(1)}`}
        </text>
        <text
          x={CART.left}
          y={CART.bottom + 14}
          className="tick"
          opacity={cartWeight}
        >
          {lapLabel}
        </text>
        <text
          x={CART.right}
          y={CART.bottom + 14}
          className="tick"
          textAnchor="end"
          opacity={cartWeight}
        >
          now →
        </text>
        <text
          x={CART.left - 4}
          y={CART.top + 4}
          className="tick"
          textAnchor="end"
          opacity={cartWeight}
        >
          {fixedScale ? "9" : geometry.max.toFixed(1)}
        </text>
        <text
          x={CART.left - 4}
          y={CART.bottom}
          className="tick"
          textAnchor="end"
          opacity={cartWeight}
        >
          0
        </text>
        {points.map(({ bin, at }) => {
          const opacity = Math.max(
            0.28,
            1 - 0.72 * (bin.ageMs / geometry.periodMs),
          );
          const isActive = shown != null && shown.index === bin.index;
          return (
            <circle
              key={`point-${bin.index}`}
              cx={at.x}
              cy={at.y}
              r={isActive ? 3.4 : 2.2}
              fill={stormColor(bin.value)}
              fillOpacity={opacity}
              className={isActive ? "plot-point plot-point-active" : "plot-point"}
            />
          );
        })}
        {segments(geometry.bins, geometry.binCount).map(([start, end]) => {
          const from = morphPoint(start, scaleMax, geometry.binCount, progress);
          const to = morphPoint(end, scaleMax, geometry.binCount, progress);
          const age = Math.min(start.ageMs, end.ageMs) / geometry.periodMs;
          const opacity = Math.max(0.28, 1 - 0.72 * age);
          const kp = Math.max(start.value, end.value);
          return (
            <line
              key={`${start.index}-${end.index}`}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke={stormColor(kp)}
              strokeOpacity={opacity}
              strokeWidth="2"
            />
          );
        })}
        {/* Now marker: rim head radially, baseline tick when Cartesian. */}
        <circle cx={head.x} cy={head.y} r="3.5" className="now-head" />
        {cartWeight > 0.05 ? (
          <line
            x1={head.x}
            y1={CART.top}
            x2={head.x}
            y2={CART.bottom}
            className="now-guide"
            opacity={cartWeight * 0.7}
          />
        ) : null}
      </svg>
      <div className="plot-meta">
        <p className="readout">{readoutText}</p>
        {onDownloadCsv ? (
          <button
            type="button"
            className="button button-csv"
            onClick={onDownloadCsv}
          >
            Download CSV
          </button>
        ) : null}
      </div>
    </div>
  );
}

function newest(bins) {
  return bins.reduce(
    (latest, bin) => (latest == null || bin.time > latest.time ? bin : latest),
    null,
  );
}
