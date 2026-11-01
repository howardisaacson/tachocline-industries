import { Link } from "react-router-dom";

import linksMarkdown from "../../docs/data-links.md?raw";
import { MarkdownDoc } from "./MarkdownDoc.jsx";
import { SiteChrome } from "./SiteChrome.jsx";

const ABOUT_SLUG = "data-links";

export function LinksPage() {
  return (
    <SiteChrome aboutSlug={ABOUT_SLUG}>
      <main id="top" className="about-page">
        <section className="section about-doc" aria-label="Data source links">
          <p className="eyebrow">
            Provenance · <Link to={`/about/${ABOUT_SLUG}`}>About this page</Link>
            {" · "}
            Source: <code>docs/data-links.md</code>
          </p>
          <MarkdownDoc markdown={linksMarkdown} />
        </section>
      </main>
    </SiteChrome>
  );
}
