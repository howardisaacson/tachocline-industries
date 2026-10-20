# 0001. Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-10-18
- **Deciders:** Howard Isaacson

## Context
Tachocline Industries is a portfolio site that ingests real-time satellite data, stores it, and shows dashboards. It has two goals: (1) work well, and (2) let me explain **every** technical choice confidently in job interviews for data engineering, data science, and software engineering roles. I am learning several technologies at once (databases, Grafana, JavaScript/React, APIs, service architecture), so I need a place to write down *why* each choice was made and what else I considered.

## Options considered
### A. No formal record (decisions live in my head or commit messages)
- Pros: zero overhead.
- Cons: reasons get forgotten; commit messages describe *what* changed, not *why* versus alternatives; nothing to study before interviews.
### B. One big design document
- Pros: everything in one place.
- Cons: goes stale; hard to see when and why a decision changed; tends to become a wall of text.
### C. Architecture Decision Records (one short file per decision)
- Pros: small and focused; versioned in git next to the code; history preserved through "Superseded"; a widely recognised industry practice; doubles as interview study notes.
- Cons: some discipline needed to write one for each significant decision.

## Decision
We will record every significant architecture decision as an ADR in `docs/decisions/`, numbered sequentially, using the template in [README.md](README.md) (Nygard format plus *Options considered*, *How to explain this in an interview*, and *Learn more*). New ADRs start as **Proposed**, and Howard marks them **Accepted** after review. Changed decisions get a new ADR that supersedes the old one.

"Significant" means: hard or expensive to reverse, affects multiple parts of the system, or something an interviewer might ask "why did you choose X?" about.

## Consequences
- Easier: interview prep, revisiting old choices, showing engineering maturity to anyone reading the GitHub repo.
- Harder: a small amount of writing per decision.
- Follow-up: each page's "About this page" section ([ADR 0009](0009-about-this-page-for-every-section.md)) links to the relevant ADRs.

## How to explain this in an interview
"I used Architecture Decision Records, short markdown files in the repo, one per decision, recording the context, options with pros and cons, and consequences. It's a lightweight practice recommended by Thoughtworks and Microsoft, and it meant I could always trace why the system looks the way it does, not just what it does."

## Learn more
- Michael Nygard, [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) (the original post)
- Microsoft Azure Well-Architected, [Architecture decision record](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)
- [adr.github.io](https://adr.github.io/), community templates and tools
