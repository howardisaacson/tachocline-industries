import { useState } from "react";

import { angleDeg, gScale } from "./kp.js";

const SIZE = 200;
const CENTER = 100;
const RING = 78;

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

export function RadialPlot({
  title,
  lapLabel,
  plot,
  geometry,
  nowMs,
  fixedScale,
  onSelect,
}) {
  const [active, setActive] = useState(null);
  const scale = fixedScale ? 9 : Math.max(geometry.max, 1);
  const head = polar(angleDeg(nowMs, nowMs, plot), RING);
  const shown = active ?? newest(geometry.bins);

  function selectFromPointer(event) {
    if (geometry.bins.length === 0) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left - rect.width / 2;
    const y = event.clientY - rect.top - rect.height / 2;
    const pointer = (Math.atan2(x, -y) * 180) / Math.PI;
    const angle = (pointer + 360) % 360;
    let best = geometry.bins[0];
    let bestDistance = 360;
    for (const bin of geometry.bins) {
      const raw = Math.abs(bin.angleDeg - angle);
      const distance = Math.min(raw, 360 - raw);
      if (distance < bestDistance) {
        best = bin;
        bestDistance = distance;
      }
    }
    setActive(best);
    onSelect?.(best);
  }

  const label =
    shown == null
      ? `${title}. No stored Kp on this lap. Angle is time, clockwise from ${lapLabel}. Radius is Kp.`
      : `${title}. Selected Kp ${shown.value.toFixed(2)} at ${new Date(shown.time).toISOString()}. Angle is time, clockwise from ${lapLabel}. Radius is Kp.`;

  return (
    <div className="plot-frame">
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        role="img"
        aria-label={label}
        onPointerMove={selectFromPointer}
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
          return (
            <circle
              key={`point-${bin.index}`}
              cx={at.x}
              cy={at.y}
              r="2.2"
              fill={stormColor(bin.value)}
              fillOpacity={opacity}
            />
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
            />
          );
        })}
        <circle cx={head.x} cy={head.y} r="3.5" className="now-head" />
      </svg>
      <p className="readout">
        {shown == null
          ? "No stored value on this lap."
          : `${new Date(shown.time).toISOString().slice(0, 16).replace("T", " ")} UTC · Kp ${shown.value.toFixed(2)}${gScale(shown.value) ? ` · ${gScale(shown.value)}` : ""}`}
      </p>
    </div>
  );
}

function newest(bins) {
  return bins.reduce(
    (latest, bin) => (latest == null || bin.time > latest.time ? bin : latest),
    null,
  );
}
