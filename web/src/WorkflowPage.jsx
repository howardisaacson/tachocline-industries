import { Link } from "react-router-dom";

import workflowMarkdown from "../../docs/data-science-workflow.md?raw";
import { MarkdownDoc } from "./MarkdownDoc.jsx";
import { SiteChrome } from "./SiteChrome.jsx";

const ABOUT_SLUG = "data-science-workflow";

export function WorkflowPage() {
  return (
    <SiteChrome aboutSlug={ABOUT_SLUG}>
      <main id="top" className="about-page">
        <section className="section about-doc" aria-label="How the science is done">
          <p className="eyebrow">
            Data science · <Link to={`/about/${ABOUT_SLUG}`}>About this page</Link>
            {" · "}
            Source: <code>docs/data-science-workflow.md</code>
          </p>
          <MarkdownDoc markdown={workflowMarkdown} />
        </section>
      </main>
    </SiteChrome>
  );
}
