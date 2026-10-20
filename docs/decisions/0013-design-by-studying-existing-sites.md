# 0013. Design by studying existing sites, not from scratch

- **Status:** Proposed
- **Date:** 2026-10-20
- **Deciders:** Howard Isaacson

## Context
Howard doesn't want to design the site from scratch. He wants to study **5 design-renowned sites** and **5 highly rated scientific sites** and learn from them. Neither of us is a trained visual designer, and visitors bring expectations from sites they already use: Jakob's Law says users prefer your site to work like the others they know. Studying good examples is how professional designers start too (competitive analysis).

## Options considered
### A. Design from scratch
- Pros: fully original.
- Cons: slow; amateur results likely; reinvents solved problems (navigation, chart layout).
### B. Buy or use a template or theme
- Pros: fast and polished.
- Cons: generic; we learn little; may not suit data-dense scientific pages; harder to explain choices.
### C. Structured survey of exemplary sites, then our own design
- Pros: grounded in proven patterns; teaches design vocabulary; produces a written rationale for each design choice (interview-ready); combines polish (design sites) with clarity for complex data (science sites).
- Cons: research time up front; risk of copying too closely (we borrow patterns, not assets).

## Decision
Before any frontend design work (Roadmap Phase 3), produce **`docs/research/design_survey.md`** (forthcoming):
1. Pick **5 design-renowned sites** (e.g., from award galleries such as Awwwards, or product sites famous for design) and **5 highly rated scientific/data sites** (e.g., NOAA SWPC, NASA Eyes, ESA, Our World in Data, NASA Earth Observatory). Final list to be chosen with Howard.
2. Score each one, on **both mobile and desktop** ([ADR 0012](0012-responsive-design-mobile-and-desktop.md)), on: navigation, typography, colour, data visualisation, how they explain complex content, performance, accessibility, and how they handle the "about the data" problem.
3. Capture screenshots (for private study only; not committed if copyright is unclear) and record **patterns to adopt** and **anti-patterns to avoid**.
4. Summarise into a short design brief: palette (drawing on the TI solar graphic in `assets/brand/`), type scale, layout grid, chart style, component list. Significant choices become ADRs.

## Consequences
- Easier: confident, defensible design decisions; a ready answer to "how did you approach design?"
- Harder: delays the first React page by about a week of research.
- Use their patterns, not their assets, code, or copy.

## How to explain this in an interview
"I'm not a designer, so I ran a small competitive analysis: five sites known for design and five respected science-data sites, scored on mobile and desktop for navigation, typography, and how they explain data. The design brief that came out of it is documented, so every design choice traces back to an observed pattern."

## Learn more
- Nielsen Norman Group, [Competitive Usability Evaluations](https://www.nngroup.com/articles/competitive-usability-evaluations/)
- Laws of UX, [Jakob's Law](https://lawsofux.com/jakobs-law/)
- [Awwwards](https://www.awwwards.com/) (a design-award gallery to source candidates)
