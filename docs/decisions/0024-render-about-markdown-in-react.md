# 0024. Render About markdown in the React site with a small client router

- **Status:** Proposed
- **Date:** 2026-10-29
- **Deciders:** Howard Isaacson

## Context
[ADR 0009](0009-about-this-page-for-every-section.md) says every page ships with an About doc under `docs/about/`. The first public page linked to the GitHub file and also kept a short hand-written About section in React, which can drift from the markdown. Issue #41 asks the site to render those markdown files and put an About link on every page. [ADR 0021](0021-react-vite-page-with-svg-radial-plots.md) shipped one screen with no client router and left a second page for later.

## Options considered
### A. Keep linking to GitHub blob URLs
- Pros: no new frontend dependency; markdown stays in git.
- Cons: visitors leave the site; the in-page prose can still diverge; fails "rendered in the React site."
### B. Copy About text into React components
- Pros: easy to style.
- Cons: two sources of truth; every About edit becomes a UI PR for duplicated words.
### C. Import `docs/about/*.md` at build time (`?raw`) and render with `react-markdown`, plus `react-router` for `/about/:slug`
- Pros: one file remains the source of truth; Compose and `npm run dev` both see the same docs; routes match ADR 0009's one-About-per-page idea.
- Cons: the `web` image build must see `docs/about/` (Compose build context moves to the repo root); relative links inside the markdown that point at other repo files need rewriting to GitHub; Mermaid diagrams stay as fenced code until a later pass.
### D. Serve About markdown from FastAPI
- Pros: one HTTP API for docs.
- Cons: couples docs to the API container and adds a runtime dependency for static prose.

## Decision
We will use **option C**. Vite loads every `docs/about/*.md` file as a raw string at build time. The React app routes `/` to the space-weather page and `/about/:slug` to a markdown renderer. The header About link on a page goes to that page's slug. New About files appear automatically from the glob. The Compose `web` build context is the repo root so the image can copy `docs/about/` without duplicating the text into `web/`.

## Consequences
- Easier: About edits in `docs/about/` show up on the next frontend build; Playwright can open `/about/space-weather` without the database.
- Harder: the web Docker build context is wider; relative markdown links to ADRs and research notes are rewritten to GitHub blob URLs so they still resolve outside the SPA.
- ADR 0021's "no client-side router yet" is extended by this ADR for About routes only. Plotly and other public pages can reuse the same router later.

## How to explain this in an interview
"We keep About pages as markdown in the repo so they stay reviewable like code. The Vite build imports those files as strings and React renders them, so the site never copies the prose into JSX. A small client router exposes `/about/:slug`, and the Docker build context includes `docs/about/` so the image still has a single source of truth."

## Learn more
- Vite, [Static Asset Handling](https://vite.dev/guide/assets.html) (`import.meta.glob` and `?raw`)
- React Router, [Declarative mode](https://reactrouter.com/start/declarative/installation)
- `react-markdown`, [readme](https://github.com/remarkjs/react-markdown)
