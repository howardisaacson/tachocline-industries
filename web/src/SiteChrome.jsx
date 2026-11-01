import { Link } from "react-router-dom";

/**
 * Shared header/footer so every route has About and Links (issues #41, #86).
 * @param {{ aboutSlug: string, children: import("react").ReactNode, liveLabel?: string }} props
 */
export function SiteChrome({ aboutSlug, children, liveLabel }) {
  return (
    <>
      <header className="site-header">
        <div className="header-inner">
          <Link className="logo" to="/" aria-label="Tachocline Industries home">
            <img
              className="logo-mark"
              src="/brand/ti-logo.svg"
              width="36"
              height="36"
              alt=""
            />
            <span>Tachocline</span>
          </Link>
          <nav aria-label="Primary">
            <Link to="/">Space weather</Link>
            <Link to="/workflow">Science</Link>
            <Link to="/links">Links</Link>
            <Link to={`/about/${aboutSlug}`}>About</Link>
          </nav>
          {liveLabel ? (
            <p className="status-chip">
              <span className="live-dot" aria-hidden="true" />
              <span>{liveLabel}</span>
            </p>
          ) : (
            <p className="status-chip status-chip-quiet">
              <Link to="/about">All About pages</Link>
            </p>
          )}
        </div>
      </header>
      {children}
      <footer className="site-footer">
        <p>
          Tachocline Industries. Kp from NOAA SWPC, stored by the local poller.{" "}
          <Link to="/links">Data source links</Link>
          {" · "}
          <Link to={`/about/${aboutSlug}`}>About this page</Link>
        </p>
      </footer>
    </>
  );
}
