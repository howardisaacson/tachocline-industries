import { Link, useParams } from "react-router-dom";

import { getAboutPage, listAboutPages } from "./aboutDocs.js";
import { MarkdownDoc } from "./MarkdownDoc.jsx";
import { SiteChrome } from "./SiteChrome.jsx";

const TRADEMARKS_URL =
  "https://github.com/howardisaacson/tachocline-industries/blob/develop/TRADEMARKS.md";

/**
 * Shared note under every About route. The page markdown stays the science
 * write-up; this is the license that covers that write-up and the code.
 */
function AboutLicense() {
  return (
    <div className="about-doc about-license">
      <h2>License</h2>
      <p>
        The code is under the{" "}
        <a href="https://www.apache.org/licenses/LICENSE-2.0">Apache License 2.0</a>.
        These About pages, and the other original writing under <code>docs/</code>, are
        under <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. The
        name Tachocline Industries and the TI logo are trademarks of Howard Isaacson.
        They are not included in those grants. A fork must rename and rebrand, and may
        say it is based on Tachocline Industries. The eclipse photograph on the home
        page stays under Phil Hart’s CC BY-NC-SA 4.0 license. This is not legal advice.{" "}
        <a href={TRADEMARKS_URL}>Trademark policy</a>.
      </p>
    </div>
  );
}

export function AboutIndexPage() {
  const pages = listAboutPages();
  return (
    <SiteChrome aboutSlug="space-weather">
      <main id="top" className="about-page">
        <section className="section about-doc">
          <p className="eyebrow">Documentation</p>
          <h1>About pages</h1>
          <p className="section-copy">
            Each public or Grafana section has one markdown file under{" "}
            <code>docs/about/</code>. The site renders that file; it does not
            copy the text into React.
          </p>
          <ul className="about-index">
            {pages.map((page) => (
              <li key={page.slug}>
                <Link to={`/about/${page.slug}`}>{page.title}</Link>
              </li>
            ))}
          </ul>
          <AboutLicense />
        </section>
      </main>
    </SiteChrome>
  );
}

export function AboutPage() {
  const { slug } = useParams();
  const page = getAboutPage(slug ?? "");

  if (!page) {
    return (
      <SiteChrome aboutSlug="space-weather">
        <main id="top" className="about-page">
          <section className="section about-doc">
            <h1>About page not found</h1>
            <p className="section-copy">
              No file named <code>docs/about/{slug}.md</code>. See the{" "}
              <Link to="/about">About index</Link>.
            </p>
          </section>
        </main>
      </SiteChrome>
    );
  }

  return (
    <SiteChrome aboutSlug={page.slug}>
      <main id="top" className="about-page">
        <section className="section" aria-label="About this page">
          <p className="eyebrow">
            <Link to="/about">All About pages</Link>
            {" · "}
            Source: <code>docs/about/{page.slug}.md</code>
          </p>
          <MarkdownDoc markdown={page.markdown} />
          <AboutLicense />
        </section>
      </main>
    </SiteChrome>
  );
}
