import { useEffect, useState } from "react";

import { PerigeeChart } from "./PerigeeChart.jsx";
import { SiteChrome } from "./SiteChrome.jsx";
import {
  PERIGEE_WINDOW_MS,
  perigeeRequestPath,
  seriesFromRows,
} from "./satellites.js";

const ABOUT_SLUG = "satellite-tracking";

export function SatellitesPage() {
  const [state, setState] = useState({ status: "loading" });

  useEffect(() => {
    const nowMs = Date.now();
    let cancelled = false;
    fetch(perigeeRequestPath(nowMs))
      .then((response) => {
        if (!response.ok) throw new Error(`${response.status} from /api/v1/satellite-perigee`);
        return response.json();
      })
      .then((page) => {
        if (!cancelled) setState({ status: "ready", nowMs, series: seriesFromRows(page.rows) });
      })
      .catch((error) => {
        if (!cancelled) setState({ status: "error", nowMs, message: error.message });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const nowMs = state.nowMs ?? Date.now();
  const series = state.status === "ready" ? state.series : seriesFromRows([]);

  return (
    <SiteChrome aboutSlug={ABOUT_SLUG}>
      <main id="top" className="satellites-page">
        <section className="section">
          <p className="eyebrow">Orbit decay · last 7 days</p>
          <h1>Satellite Tracking</h1>
          <p className="lede">
            A satellite in low Earth orbit slowly loses height because the thin
            air there drags on it. A geomagnetic storm heats that air and can
            make the drag stronger, so perigee falls faster. The station is
            reboosted, so its altitude jumps. Hubble and Swift are not, so a
            steady drop is the drag itself. These kilometers are the two-body
            perigee from the latest mean elements. They are not an SGP4
            position and not a predicted re-entry date.
          </p>
          <p className="section-copy">
            Original data:{" "}
            <a href="https://celestrak.org/" rel="noopener noreferrer">
              CelesTrak
            </a>
            . The same five series as the Grafana Perigee altitude panel.
          </p>
          {state.status === "loading" ? <p className="section-copy">Loading perigee…</p> : null}
          {state.status === "error" ? (
            <p className="section-copy" role="alert">
              The API did not return perigee ({state.message}). Start the stack, then reload.
            </p>
          ) : null}
          <PerigeeChart series={series} fromMs={nowMs - PERIGEE_WINDOW_MS} toMs={nowMs} />
          <ul className="perigee-legend">
            {series.map((sat) => {
              const latest = sat.points.at(-1);
              return (
                <li key={sat.noradCatId}>
                  <span className="swatch" style={{ background: sat.color }} />
                  <span>
                    {sat.name}
                    {latest ? ` ${latest.km.toFixed(1)} km` : ""}
                  </span>
                </li>
              );
            })}
          </ul>
          <h2>Where to read more</h2>
          <ul className="sat-links">
            {series.map((sat) => (
              <li key={sat.noradCatId}>
                <h3>{sat.name}</h3>
                <a
                  href={sat.trackingUrl}
                  rel="noopener noreferrer"
                  aria-label={`Tracking ${sat.name}`}
                >
                  Tracking
                </a>
                <a href={sat.homeUrl} rel="noopener noreferrer" aria-label={`Homepage ${sat.name}`}>
                  Homepage
                </a>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </SiteChrome>
  );
}
