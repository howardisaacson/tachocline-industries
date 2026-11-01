import { useEffect, useRef, useState } from "react";

import { chartGeometry } from "./satellites.js";

/**
 * Time-on-x perigee chart. The SVG is sized to the container in CSS pixels
 * so the axis labels stay readable on a phone (a scaled viewBox would shrink them).
 */
export function PerigeeChart({ series, fromMs, toMs }) {
  const frame = useRef(null);
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const element = frame.current;
    if (!element) return undefined;
    const measure = () => setWidth(element.clientWidth);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const height = width > 0 && width < 640 ? 260 : 340;
  const geometry =
    width > 0 ? chartGeometry(series, { width, height, fromMs, toMs }) : null;

  return (
    <div className="perigee-frame" ref={frame}>
      {geometry ? (
        <svg
          width={width}
          height={height}
          role="img"
          aria-label="Perigee altitude in kilometers for the last 7 days"
        >
          {geometry.yTicks.map((tick) => (
            <g key={tick.label}>
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
            km
          </text>
          {geometry.xTicks.map((tick) => (
            <text
              key={tick.label + tick.x}
              x={tick.x}
              y={height - 8}
              textAnchor="middle"
              className="axis-label"
            >
              {tick.label}
            </text>
          ))}
          {geometry.lines.map((line) => (
            <g key={line.noradCatId}>
              {line.points.length > 1 ? (
                <polyline
                  fill="none"
                  stroke={line.color}
                  strokeWidth="1.75"
                  strokeDasharray={line.dash || undefined}
                  points={line.points.map((point) => `${point.x},${point.y}`).join(" ")}
                />
              ) : null}
              {line.points.map((point) => (
                <circle key={point.time} cx={point.x} cy={point.y} r="2.5" fill={line.color}>
                  <title>
                    {line.name} {point.km.toFixed(1)} km
                  </title>
                </circle>
              ))}
            </g>
          ))}
          {geometry.empty ? (
            <text x={width / 2} y={height / 2} textAnchor="middle" className="axis-label">
              No perigee in this window
            </text>
          ) : null}
        </svg>
      ) : null}
    </div>
  );
}
