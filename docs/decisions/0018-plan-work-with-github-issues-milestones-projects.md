# 0018. Plan work with GitHub Issues, Milestones, and Projects

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Howard Isaacson

## Context
The plan lives in [ROADMAP.md](../ROADMAP.md) as checkboxes. That is fine for reading but cannot show who is doing what, link work to code changes, or track progress. Howard also wants to learn the planning tools engineering teams actually use and be able to discuss them in interviews. The code is already on GitHub ([ADR 0010](0010-use-git-and-github-from-day-one.md)).

Key terms:
- **Issue:** one unit of work (task, bug, question) with a discussion thread.
- **Label:** a tag for filtering (type, area).
- **Milestone:** a group of issues with a shared goal; here, one per roadmap phase, with a progress bar.
- **Sub-issue:** a child issue under a parent, which breaks big work into PR-sized pieces.
- **Project:** a spreadsheet- or board-style planning view over issues, with custom fields (Phase, Priority, Size), views (Board, Table, Roadmap), and automations.
- **Linked PR:** writing "Closes #12" in a pull request closes issue 12 when the PR merges.

## Options considered
### A. Keep ROADMAP.md only
- Pros: zero setup; lives with the code.
- Cons: no status tracking or links to PRs; nothing to show of a planning workflow.
### B. External tool (Jira, Linear, Trello)
- Pros: Jira and Linear are common at companies.
- Cons: a separate account; disconnected from code; unnecessary for one person.
### C. GitHub Issues + Milestones + Projects, seeded from the roadmap by script
- Pros: built into the repo; issues link to commits and PRs automatically; a scripted, repeatable setup (itself a learning artefact); the same concepts transfer to Jira and Linear.
- Cons: two places describe the plan (ROADMAP.md and issues), so they need to stay in sync; some Project setup still has to be done in the web UI.

## Decision
Use **GitHub Issues, Milestones, and a user-level Project** ("Tachocline Industries Roadmap", linked only to this repo):
- Labels: `type:` (feature/docs/research/adr/chore/bug), `area:` (ingest/db/api/dashboards/web/ds/agents/infra/rust/brand), `good first issue`, `learning`.
- One **milestone per roadmap phase**. Large items are **parent issues with sub-issues**.
- Every Proposed ADR gets a **"Review ADR NNNN"** issue, closed when Howard accepts it.
- Seeded and kept in sync by idempotent scripts (`gh-setup/`, outside the repo) that write only to `howardisaacson/tachocline-industries`.
- **Issue templates** (feature, bug, ADR review) and a **PR template** with `Closes #`, ADR, About-page, and mobile/desktop checkboxes.
- **ROADMAP.md stays the high-level narrative; issues are the source of truth for status.** When scope changes, update both in the same PR.
- See [docs/github-workflow.md](../github-workflow.md) for the day-to-day workflow.

## Consequences
- Easier: visible progress, clean PR ↔ issue history, an interview-ready planning story.
- Harder: some upkeep (triaging, closing, keeping the roadmap in sync); Project views and workflows need web-UI setup.
- AI agents must reference issues in branches and PRs (AGENTS.md).

## How to explain this in an interview
"I planned the project with GitHub Issues: one milestone per phase, parent issues with sub-issues for big features, and a Project board with Phase, Priority and Size fields. Every PR closes an issue, so the history links each code change to its reason. I seeded it from the roadmap with an idempotent gh script, and the same concepts map directly onto Jira or Linear."

## Learn more
- GitHub Docs, [About Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects) and [Built-in automations](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-built-in-automations)
- GitHub Docs, [Adding sub-issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues) and [About milestones](https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/about-milestones)
- GitHub Docs, [Linking a pull request to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue)
