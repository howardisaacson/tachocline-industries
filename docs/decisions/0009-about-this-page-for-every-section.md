# 0009. "About this page" for every section

- **Status:** Accepted
- **Date:** 2026-10-18
- **Deciders:** Howard Isaacson

## Context
The site has two audiences: visitors (recruiters, interviewers, space enthusiasts) who want to understand what they're looking at, and me, preparing to answer *any* question about any part of the system. Portfolio projects often show impressive charts with no explanation of where the data comes from or how it gets there, and interviewers probe exactly that. Each page also draws on different data, pipelines, and technologies, so one generic "About" page won't do.

## Options considered
### A. A single project-wide README / About page
- Pros: least effort.
- Cons: too general; doesn't explain individual charts; goes stale.
### B. Tooltips and captions only
- Pros: unobtrusive.
- Cons: no room for data flow, trade-offs, or limitations.
### C. A structured "About this page" for every page or section, from a shared template, linking to ADRs
- Pros: consistent; each page explains its own purpose, data source, data flow, tech, and limitations; links to ADRs connect the *what* to the *why*; doubles as my interview study guide; shows communication skills.
- Cons: more writing; must be kept in sync with the code.

## Decision
Every page or section of the site will have an **"About this page"** link, written from [`../about-this-page-template.md`](../about-this-page-template.md). Sections: Purpose, What you're seeing, Data source & cadence, Data flow (a Mermaid diagram), Tech used and why (with ADR links), Known limitations, Interview talking points, Glossary.

Implementation:
- About content lives as markdown in the repo (`docs/about/<page>.md`), versioned with the code ("docs as code"). Grafana dashboards link to it from a text panel or dashboard link; the React site renders the same markdown.
- **Definition of done:** a new page or feature is not finished until its About section exists and its Data source, Data flow, and ADR links are accurate. Changes to a pipeline update the matching About page in the same pull request.
- Mermaid is used for diagrams because GitHub renders it natively in markdown.

## Consequences
- Easier: interviews (each About page is a ready-made answer); onboarding anyone who reads the repo; spotting gaps in my own understanding while writing.
- Harder: documentation overhead on every feature; risk of drift (mitigated by the definition of done and PR checklist).
- Writing "Known limitations" honestly (e.g., gaps when my laptop is off, provisional data) is a feature, not a weakness. It shows data-quality awareness.

## How to explain this in an interview
"Every page on the site has an About link that explains what it shows, where the data comes from and how often, a data-flow diagram, the tech used with links to the decision records, and known limitations. I treated documentation as part of the definition of done, so the docs evolve with the code, and it forced me to understand every piece end to end."

## Learn more
- Write the Docs, [Docs as Code](https://www.writethedocs.org/guide/docs-as-code/)
- GitHub Docs, [Creating diagrams](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams) (Mermaid in markdown); [Mermaid docs](https://mermaid.js.org/intro/)
