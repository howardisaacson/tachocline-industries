import { useEffect, useRef, useState } from "react";

import { SNR_STOPS, chartGeometry, formatReadout, nearestPoint } from "./solarRv.js";

/**
 * Time-on-x radial-velocity chart. The SVG is sized to the container in
 * CSS pixels so the axis labels stay readable on a phone.
 */
export function SolarRvChart({ series, fromMs, toMs }) {
  const frame = useRef(null);
  const [width, setWidth] = useState(0);
  const [active, setActive] = useState(null);

  useEffect(() => {
    const element = frame.current;
    if (!element) return undefined;
    const measure = () => setWidth(element.clientWidth);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const height = width > 0 && width < 640 ? 260 : 320;
  const geometry =
    width > 0 ? chartGeometry(series, { width, height, fromMs, toMs }) : null;

  function selectFromPointer(event) {
    if (!geometry || geometry.empty) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * width;
    const y = ((event.clientY - rect.top) / rect.height) * height;
    setActive(nearestPoint(geometry.lines, x, y));
  }

  return (
    <div className="perigee-frame" ref={frame}>
      {geometry ? (
        <svg
          width={width}
          height={height}
          role="img"
          aria-label="Sun-as-a-star radial velocity in meters per second. Points are not connected. Point color is the spectral SNR, from the lowest on this chart to the highest. The time axis runs from 30 minutes before the newest exposure to 30 minutes after it."
          onPointerMove={selectFromPointer}
          onPointerLeave={() => setActive(null)}
        >
          {geometry.yTicks.map((tick) => (
            <g key={tick.y}>
              <line
                x1={52}
                x2={width - 16}
                y1={tick.y}
                y2={tick.y}
                stroke="rgba(240, 240, 250, 0.18)"
              />
              <text x={44} y={tick.y + 4} textAnchor="end" className="axis-label">
                {tick.label}
              </text>
            </g>
          ))}
          <text x={8} y={14} className="axis-label">
            m/s
          </text>
          {geometry.xTicks.map((tick, index) => (
            <text
              key={tick.label + tick.x}
              x={tick.x}
              y={height - 8}
              textAnchor={["start", "middle", "end"][index]}
              className="axis-label"
            >
              {tick.label}
            </text>
          ))}
          {geometry.lines.map((line) => (
            <g key={line.id}>
              {line.segments.flat().map((point) => {
                const selected = active?.id === line.id && active.time === point.time;
                return (
                  <circle
                    key={`${point.time}-${point.rv}`}
                    cx={point.x}
                    cy={point.y}
                    r={selected ? 5 : 2.5}
                    fill={point.color}
                    stroke={line.color}
                    strokeWidth="1"
                  >
                    <title>
                      {line.name} {point.rv.toFixed(1)} m/s{" "}
                      {point.snr == null ? "SNR not published" : `SNR ${point.snr.toFixed(1)}`}
                    </title>
                  </circle>
                );
              })}
            </g>
          ))}
          {geometry.empty ? (
            <text x={width / 2} y={height / 2} textAnchor="middle" className="axis-label">
              No radial velocity in this window
            </text>
          ) : null}
        </svg>
      ) : null}
      <p className="readout" aria-live="polite">
        {geometry?.empty ? "No radial velocity in this window." : formatReadout(active)}
      </p>
      {geometry && !geometry.empty && geometry.snrMin != null ? (
        <p className="snr-key">
          <span
            className="snr-ramp"
            style={{ background: `linear-gradient(90deg, ${SNR_STOPS.join(", ")})` }}
          />
          SNR {formatSnrBound(geometry.snrMin)}–{formatSnrBound(geometry.snrMax)} per pixel
        </p>
      ) : null}
    </div>
  );
}

function formatSnrBound(value) {
  const rounded = Math.round(value * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}
