import { Link, useParams } from "react-router-dom";

import { getAboutPage, listAboutPages } from "./aboutDocs.js";
import { MarkdownDoc } from "./MarkdownDoc.jsx";
import { SiteChrome } from "./SiteChrome.jsx";

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
        </section>
      </main>
    </SiteChrome>
  );
}
