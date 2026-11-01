import { useEffect, useId, useRef, useState } from "react";

import { angleDeg, gScale } from "./kp.js";

const SIZE = 200;
const CENTER = 100;
const RING = 78;
const HIT_RADIUS = 8;

function polar(angle, radius) {
  const radians = (angle * Math.PI) / 180;
  return {
    x: CENTER + radius * Math.sin(radians),
    y: CENTER - radius * Math.cos(radians),
  };
}

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

function nearestBin(bins, angle) {
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

function pointerAngle(event) {
  const rect = event.currentTarget.getBoundingClientRect();
  const x = event.clientX - rect.left - rect.width / 2;
  const y = event.clientY - rect.top - rect.height / 2;
  const pointer = (Math.atan2(x, -y) * 180) / Math.PI;
  return (pointer + 360) % 360;
}

function tooltipStyle(point, frameWidth) {
  if (point == null || frameWidth <= 0) return { display: "none" };
  const left = (point.x / SIZE) * frameWidth;
  const top = (point.y / SIZE) * frameWidth;
  const flipX = left > frameWidth * 0.62;
  return {
    left: `${left}px`,
    top: `${top}px`,
    transform: flipX
      ? "translate(-100%, -120%) translateX(-8px)"
      : "translate(8px, -120%)",
  };
}

export function RadialPlot({
  title,
  lapLabel,
  plot,
  geometry,
  nowMs,
  fixedScale,
  onSelect,
}) {
  const tooltipId = useId();
  const frameRef = useRef(null);
  const [active, setActive] = useState(null);
  const [hover, setHover] = useState(null);
  const [frameWidth, setFrameWidth] = useState(0);
  const scale = fixedScale ? 9 : Math.max(geometry.max, 1);
  const head = polar(angleDeg(nowMs, nowMs, plot), RING);
  const atNow = newest(geometry.bins);
  const shown = hover?.bin ?? active ?? atNow;

  useEffect(() => {
    const node = frameRef.current;
    if (node == null || typeof ResizeObserver === "undefined") return undefined;
    const sync = () => setFrameWidth(node.clientWidth);
    sync();
    const observer = new ResizeObserver(sync);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  function showBin(bin, point) {
    setActive(bin);
    setHover({
      kind: "bin",
      bin,
      point,
      timeMs: bin.time,
      value: bin.value,
    });
    onSelect?.(bin);
  }

  function showNow() {
    setHover({
      kind: "now",
      bin: atNow,
      point: head,
      timeMs: nowMs,
      value: atNow?.value ?? null,
    });
    if (atNow) {
      setActive(atNow);
      onSelect?.(atNow);
    }
  }

  function selectFromPointer(event) {
    if (geometry.bins.length === 0) return;
    const bin = nearestBin(geometry.bins, pointerAngle(event));
    const point = polar(bin.angleDeg, (bin.value / scale) * RING);
    showBin(bin, point);
  }

  const label =
    shown == null
      ? `${title}. No stored Kp on this lap. Angle is time, clockwise from ${lapLabel}. Radius is Kp.`
      : `${title}. Selected Kp ${shown.value.toFixed(2)} at ${new Date(shown.time).toISOString()}. Angle is time, clockwise from ${lapLabel}. Radius is Kp.`;

  const tooltipText =
    hover == null
      ? null
      : hover.kind === "now"
        ? `Now · ${formatUtc(hover.timeMs)} UTC · ${formatKp(hover.value)}`
        : `${formatUtc(hover.timeMs)} UTC · ${formatKp(hover.value)}`;

  const readoutText =
    hover != null
      ? tooltipText
      : shown == null
        ? "No stored value on this lap."
        : `${formatUtc(shown.time)} UTC · ${formatKp(shown.value)}`;

  return (
    <div className="plot-frame" ref={frameRef}>
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        role="img"
        aria-label={label}
        aria-describedby={hover ? tooltipId : undefined}
        onPointerMove={selectFromPointer}
        onPointerLeave={() => setHover(null)}
      >
        {[1, 2, 3].map((step) => (
          <circle
            key={step}
            cx={CENTER}
            cy={CENTER}
            r={(RING * step) / 3}
            className="ring"
          />
        ))}
        <text x={CENTER} y={CENTER - RING - 6} className="tick" textAnchor="middle">
          {lapLabel}
        </text>
        <text x={CENTER + 8} y={CENTER - 6} className="tick">
          {fixedScale ? "0–9" : `max ${geometry.max.toFixed(1)}`}
        </text>
        {geometry.bins.map((bin) => {
          const at = polar(bin.angleDeg, (bin.value / scale) * RING);
          const opacity = Math.max(0.28, 1 - 0.72 * (bin.ageMs / geometry.periodMs));
          const isActive = shown != null && shown.index === bin.index;
          return (
            <g key={`point-${bin.index}`}>
              <circle
                cx={at.x}
                cy={at.y}
                r={isActive ? 3.4 : 2.2}
                fill={stormColor(bin.value)}
                fillOpacity={opacity}
                className={isActive ? "plot-point plot-point-active" : "plot-point"}
              />
              <circle
                cx={at.x}
                cy={at.y}
                r={HIT_RADIUS}
                className="plot-hit"
                onPointerEnter={(event) => {
                  event.stopPropagation();
                  showBin(bin, at);
                }}
                onPointerMove={(event) => {
                  event.stopPropagation();
                  showBin(bin, at);
                }}
              >
                <title>{`${formatUtc(bin.time)} UTC · ${formatKp(bin.value)}`}</title>
              </circle>
            </g>
          );
        })}
        {segments(geometry.bins, geometry.binCount).map(([start, end]) => {
          const from = polar(start.angleDeg, (start.value / scale) * RING);
          const to = polar(end.angleDeg, (end.value / scale) * RING);
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
              pointerEvents="none"
            />
          );
        })}
        <circle cx={head.x} cy={head.y} r="3.5" className="now-head" />
        <circle
          cx={head.x}
          cy={head.y}
          r={HIT_RADIUS + 2}
          className="plot-hit now-head-hit"
          onPointerEnter={(event) => {
            event.stopPropagation();
            showNow();
          }}
          onPointerMove={(event) => {
            event.stopPropagation();
            showNow();
          }}
        >
          <title>{`Now · ${formatUtc(nowMs)} UTC · ${formatKp(atNow?.value ?? null)}`}</title>
        </circle>
      </svg>
      {tooltipText ? (
        <div
          id={tooltipId}
          className="plot-tooltip"
          role="tooltip"
          style={tooltipStyle(hover.point, frameWidth)}
        >
          {tooltipText}
        </div>
      ) : null}
      <p className="readout">{readoutText}</p>
    </div>
  );
}

function newest(bins) {
  return bins.reduce(
    (latest, bin) => (latest == null || bin.time > latest.time ? bin : latest),
    null,
  );
}
