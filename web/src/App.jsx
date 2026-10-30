import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { loadKp } from "./api.js";
import {
  MONTH_MS,
  YEAR_MS,
  gScale,
  radialBins,
  samplesFromRows,
  toCsv,
} from "./kp.js";
import { RadialPlot } from "./RadialPlot.jsx";
import { SiteChrome } from "./SiteChrome.jsx";

const ABOUT_SLUG = "space-weather";

const PLOTS = [
  {
    id: "day",
    title: "One day",
    lapLabel: "00 UTC",
    note: "1-minute estimated Kp, averaged into 10-minute bins. The lap starts at midnight UTC.",
    valueKey: "estimated_kp",
    source: "minute",
  },
  {
    id: "month",
    title: "30 days",
    lapLabel: "1st",
    note: "GFZ 3-hour Kp. The lap starts on the 1st of the month, UTC. This ring is the latest 30 days.",
    valueKey: "kp",
    source: "gfz",
    windowMs: MONTH_MS,
  },
  {
    id: "year",
    title: "One year",
    lapLabel: "1 Jan",
    note: "Daily maximum of GFZ 3-hour Kp. The lap starts on 1 January UTC.",
    valueKey: "kp",
    source: "gfz",
    windowMs: YEAR_MS,
  },
  {
    id: "solar",
    title: "11 years",
    lapLabel: "1932",
    note: "Daily maximum of GFZ Kp across 11 years of 365 days. The lap is measured from 1 January 1932. A nowcast is still Kp, and the file replaces it later.",
    valueKey: "kp",
    source: "gfz",
  },
];

export function App() {
  const [fixedScale, setFixedScale] = useState(false);
  const [state, setState] = useState({ status: "loading" });

  useEffect(() => {
    const nowMs = Date.now();
    let cancelled = false;
    loadKp(nowMs)
      .then((pages) => {
        if (!cancelled) setState({ status: "ready", nowMs, pages });
      })
      .catch((error) => {
        if (!cancelled) setState({ status: "error", nowMs, message: error.message });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const latest = latestMinute(state);
  const g = latest == null ? null : gScale(latest.estimated_kp);
  const failures = failedFeeds(state);
  const liveLabel = [
    "Live",
    latest == null ? null : `Kp ${Number(latest.estimated_kp).toFixed(1)}`,
    g,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <SiteChrome aboutSlug={ABOUT_SLUG} liveLabel={liveLabel}>
      <main id="top">
        <section className="hero">
          <p className="eyebrow">Real-time · NOAA SWPC estimated Kp</p>
          <h1>{latest == null ? "Kp —" : `Kp ${Number(latest.estimated_kp).toFixed(2)}`}</h1>
          <p className="gscale">{g ?? "Below G1"}</p>
          <p className="lede">
            Geomagnetic activity as a clock. Angle is time, clockwise from the
            top. Distance from the center is Kp. A bright head marks now.
          </p>
          <a className="button" href="#plots">
            Explore
          </a>
        </section>

        <section id="plots" className="section">
          <div className="section-heading">
            <h2>Kp, three timescales</h2>
            <label className="scale-toggle">
              <input
                type="checkbox"
                checked={fixedScale}
                onChange={(event) => setFixedScale(event.target.checked)}
              />
              Fixed 0–9 scale
            </label>
          </div>
          <p className="section-copy">
            Each ring auto-scales so the largest stored value reaches the edge.
            Gold through red is NOAA G1 and above. The day ring is SWPC’s
            1-minute estimate. The longer rings are GFZ Kp.
          </p>
          {state.status === "loading" ? <p className="section-copy">Loading Kp…</p> : null}
          {failures.length > 0 ? (
            <p className="section-copy" role="alert">
              The API did not return Kp ({failures.join(" and ")}). That ring
              stays empty. Start the stack, then reload.
            </p>
          ) : null}
          <div className="plots">
            {PLOTS.map((plot) => (
              <PlotCard
                key={plot.id}
                plot={plot}
                state={state}
                fixedScale={fixedScale}
              />
            ))}
          </div>
        </section>

        <section className="section about">
          <h2>About this page</h2>
          <p>
            How to read the rings, where the numbers come from, and the limits
            of the real-time feed live in the About doc. The site renders that
            markdown file; this page does not copy it.
          </p>
          <p>
            <Link className="button" to={`/about/${ABOUT_SLUG}`}>
              Open About
            </Link>
          </p>
        </section>
      </main>
    </SiteChrome>
  );
}

function PlotCard({ plot, state, fixedScale }) {
  const ready = state.status === "ready";
  const rows = ready ? rowsFor(plot, state) : [];
  const samples = samplesFromRows(rows, plot.valueKey);
  const geometry = ready
    ? radialBins({ samples, nowMs: state.nowMs, plot: plot.id })
    : { binCount: 1, bins: [], max: 0, periodMs: 1 };
  const tableRows = [...geometry.bins].sort((left, right) => right.time - left.time);

  return (
    <article className="plot-card">
      <h3>{plot.title}</h3>
      <p>{plot.note}</p>
      <RadialPlot
        title={plot.title}
        lapLabel={plot.lapLabel}
        plot={plot.id}
        geometry={geometry}
        nowMs={ready ? state.nowMs : Date.UTC(2026, 0, 1)}
        fixedScale={fixedScale}
      />
      <button
        type="button"
        className="button button-small"
        onClick={() => download(`${plot.id}-kp.csv`, toCsv(tableRows))}
      >
        Download CSV
      </button>
      <div className="table-wrap">
        <table>
          <caption>{plot.title} values used in the ring</caption>
          <thead>
            <tr>
              <th scope="col">Time (UTC)</th>
              <th scope="col">Kp</th>
              <th scope="col">Scale</th>
            </tr>
          </thead>
          <tbody>
            {tableRows.length === 0 ? (
              <tr>
                <td colSpan={3}>No stored values in this window.</td>
              </tr>
            ) : (
              tableRows.map((bin) => (
                <tr key={bin.index}>
                  <td>{new Date(bin.time).toISOString().slice(0, 16).replace("T", " ")}</td>
                  <td>{bin.value.toFixed(2)}</td>
                  <td>{gScale(bin.value) ?? "—"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function rowsFor(plot, state) {
  const feed = state.pages[plot.source];
  if (!feed.ok) return [];
  const rows = feed.page.rows ?? [];
  if (plot.windowMs == null) return rows;
  const start = state.nowMs - plot.windowMs;
  return rows.filter((row) => {
    const time = Date.parse(row.time_tag);
    return time >= start && time < state.nowMs;
  });
}

function latestMinute(state) {
  if (state.status !== "ready" || !state.pages.minute.ok) return null;
  const rows = state.pages.minute.page.rows ?? [];
  return rows.reduce((latest, row) => {
    if (row.estimated_kp == null) return latest;
    if (latest == null || Date.parse(row.time_tag) > Date.parse(latest.time_tag)) {
      return row;
    }
    return latest;
  }, null);
}

function failedFeeds(state) {
  if (state.status === "error") return [state.message];
  if (state.status !== "ready") return [];
  const names = [];
  if (!state.pages.minute.ok) names.push("1-minute Kp");
  if (!state.pages.gfz.ok) names.push("GFZ Kp");
  return names;
}

function download(filename, csv) {
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
