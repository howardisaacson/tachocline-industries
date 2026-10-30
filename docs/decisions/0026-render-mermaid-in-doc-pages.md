# 0026. Render Mermaid diagrams client-side on doc pages

- **Status:** Proposed
- **Date:** 2026-10-29
- **Deciders:** Howard Isaacson

## Context
[ADR 0024](0024-render-about-markdown-in-react.md) imports markdown into the React site. The “How the science is done” page (issue #42) must show the workflow Mermaid diagram from [`docs/data-science-workflow.md`](../data-science-workflow.md). About pages also contain Mermaid in their data-flow sections. We need a rule for how those fences become diagrams.

## Options considered
### A. Leave Mermaid as fenced code
- Pros: no new dependency.
- Cons: fails the acceptance criterion; visitors cannot see the flowchart.
### B. Pre-render SVG at build time
- Pros: no client JS for diagrams.
- Cons: extra build tooling; harder to keep one markdown source for GitHub and the site.
### C. Client-side Mermaid with `securityLevel: "strict"`
- Pros: same markdown on GitHub and in the app; matches ADR 0024’s single-source idea.
- Cons: larger JS bundle; diagrams need JavaScript; must not use loose security settings.

## Decision
We will use **option C**. Doc pages run Mermaid in the browser after `react-markdown` emits a `.mermaid` node. Configuration uses `theme: "dark"` and `securityLevel: "strict"`. Wide diagrams scroll inside a wrapper; the page viewport must still pass the 320 px no-horizontal-scroll check.

## Consequences
- Easier: authors keep writing ordinary Mermaid in markdown.
- Harder: bundle size grows; CI Playwright must wait for the SVG; without JS the fence stays as code.
- Does not change ADR 0024’s import model; it only covers diagram fences.

## How to explain this in an interview
"We keep architecture diagrams in Mermaid inside the same markdown the site renders, so GitHub and the app stay in sync. The browser runs Mermaid with strict security after React paints the page, which costs some bundle weight but avoids a second copy of the diagram."

## Learn more
- Mermaid, [Security](https://mermaid.js.org/config/usage.html#securitylevel)
- [ADR 0024](0024-render-about-markdown-in-react.md)
