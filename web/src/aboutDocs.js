// Vite loads every About file as a raw string at build time (ADR 0024).
// The glob path is relative to this file: web/src → docs/about.
const modules = import.meta.glob("../../docs/about/*.md", {
  query: "?raw",
  import: "default",
  eager: true,
});

const GITHUB_BLOB =
  "https://github.com/howardisaacson/tachocline-industries/blob/main";

function slugFromPath(path) {
  const match = path.match(/\/([^/]+)\.md$/);
  return match ? match[1] : null;
}

/** @returns {{ slug: string, title: string, markdown: string }[]} */
export function listAboutPages() {
  return Object.entries(modules)
    .map(([path, markdown]) => {
      const slug = slugFromPath(path);
      if (!slug || typeof markdown !== "string") return null;
      const heading = markdown.match(/^#\s+(.+)$/m);
      return {
        slug,
        title: heading ? heading[1].trim() : slug,
        markdown,
      };
    })
    .filter(Boolean)
    .sort((left, right) => left.slug.localeCompare(right.slug));
}

/** @param {string} slug */
export function getAboutPage(slug) {
  return listAboutPages().find((page) => page.slug === slug) ?? null;
}

/**
 * Repo-relative markdown links (../decisions/..., ../research/...) become
 * GitHub blob URLs so they still open outside the SPA.
 * @param {string} href
 */
export function rewriteAboutHref(href) {
  if (!href || href.startsWith("#") || href.startsWith("http://") || href.startsWith("https://") || href.startsWith("mailto:")) {
    return href;
  }
  if (href.startsWith("/about/")) {
    return href;
  }
  const cleaned = href.replace(/^\.\//, "").replace(/^(\.\.\/)+/, "");
  if (cleaned.startsWith("about/") && cleaned.endsWith(".md")) {
    const slug = cleaned.slice("about/".length, -".md".length);
    return `/about/${slug}`;
  }
  if (cleaned === "data-science-workflow.md") {
    return "/workflow";
  }
  if (
    cleaned.startsWith("decisions/") ||
    cleaned.startsWith("research/") ||
    cleaned.startsWith("about-this-page-template.md") ||
    cleaned.endsWith(".md")
  ) {
    const docsPath = cleaned.startsWith("docs/") ? cleaned : `docs/${cleaned}`;
    return `${GITHUB_BLOB}/${docsPath}`;
  }
  return href;
}
