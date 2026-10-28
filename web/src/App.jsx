import { useEffect, useState } from "react";

import { loadKp } from "./api.js";
import {
  MONTH_MS,
  gScale,
  radialBins,
  samplesFromRows,
  toCsv,
} from "./kp.js";
import { RadialPlot } from "./RadialPlot.jsx";

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
    note: "3-hour Kp. The lap starts on the 1st of the month, UTC. This ring is the latest 30 days.",
    valueKey: "kp",
    source: "threeHour",
    windowMs: MONTH_MS,
  },
  {
    id: "year",
    title: "One year",
    lapLabel: "1 Jan",
    note: "Daily maximum of 3-hour Kp. The lap starts on 1 January UTC. Empty arc means Tachocline has not stored that day.",
    valueKey: "kp",
    source: "threeHour",
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

  return (
    <>
      <header className="site-header">
        <div className="header-inner">
          <a className="logo" href="#top">
            Tachocline
          </a>
          <nav aria-label="Primary">
            <a href="#plots">Space weather</a>
            <a href="#about">About</a>
          </nav>
          <p className="status-chip">
            <span className="live-dot" aria-hidden="true" />
            <span>
              Live
              {latest == null ? "" : ` · Kp ${Number(latest.estimated_kp).toFixed(1)}`}
              {g ? ` · ${g}` : ""}
            </span>
          </p>
        </div>
      </header>

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
            Gold through red is NOAA G1 and above. The 11-year ring waits on a
            Kp backfill.
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

        <section id="about" className="section about">
          <h2>About this page</h2>
          <p>
            The three rings are the same index at three zoom levels. Twelve
            o’clock is the start of the lap: midnight UTC, the 1st, or 1 January.
            Data fades as it ages. When the head comes around, the new lap
            replaces the old one. Missing history is an empty track, not a guess.
          </p>
          <p>
            Numbers are real-time SWPC estimates, not the definitive GFZ Kp and
            not a forecast. The write-up, sources, and limits are in{" "}
            <a href="https://github.com/howardisaacson/tachocline-industries/blob/main/docs/about/space-weather.md">
              docs/about/space-weather.md
            </a>
            . NOAA’s scale page is{" "}
            <a href="https://www.swpc.noaa.gov/noaa-scales-explanation">
              noaa-scales-explanation
            </a>
            .
          </p>
        </section>
      </main>

      <footer className="site-footer">
        <p>Tachocline Industries. Kp from NOAA SWPC, stored by the local poller.</p>
      </footer>
    </>
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
  if (!state.pages.threeHour.ok) names.push("3-hour Kp");
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
