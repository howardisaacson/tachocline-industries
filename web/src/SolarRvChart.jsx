import { useEffect, useRef, useState } from "react";

import { chartGeometry } from "./solarRv.js";

/**
 * Time-on-x radial-velocity chart. The SVG is sized to the container in
 * CSS pixels so the axis labels stay readable on a phone.
 */
export function SolarRvChart({ series, fromMs, toMs }) {
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

  const height = width > 0 && width < 640 ? 260 : 320;
  const geometry =
    width > 0 ? chartGeometry(series, { width, height, fromMs, toMs }) : null;

  return (
    <div className="perigee-frame" ref={frame}>
      {geometry ? (
        <svg
          width={width}
          height={height}
          role="img"
          aria-label="Sun-as-a-star radial velocity in meters per second for the last 7 days"
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
            <g key={line.id}>
              {line.segments.map((segment) =>
                segment.length > 1 ? (
                  <polyline
                    key={segment[0].time}
                    fill="none"
                    stroke={line.color}
                    strokeWidth="1.75"
                    points={segment.map((point) => `${point.x},${point.y}`).join(" ")}
                  />
                ) : null,
              )}
              {line.segments.flat().map((point) => (
                <circle key={point.time} cx={point.x} cy={point.y} r="2.5" fill={line.color}>
                  <title>
                    {line.name} {point.rv.toFixed(1)} m/s
                  </title>
                </circle>
              ))}
            </g>
          ))}
          {geometry.empty ? (
            <text x={width / 2} y={height / 2} textAnchor="middle" className="axis-label">
              No radial velocity in this window
            </text>
          ) : null}
        </svg>
      ) : null}
    </div>
  );
}
