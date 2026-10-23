# 0010. Use git and GitHub from day one

- **Status:** Accepted
- **Date:** 2026-10-20
- **Deciders:** Howard Isaacson

## Context
Howard wants a GitHub repo from the beginning. Recruiters and interviewers look at GitHub: commit history, README, pull requests, and CI badges show *how* someone works, not just the end result. Version control also lets us undo mistakes, review changes, and run automated checks. The working folder is currently in Dropbox (`~/Dropbox/TI/`).

Key terms:
- **git:** a version-control tool that records snapshots (commits) of the code.
- **GitHub:** a hosting service for git repos, adding pull requests (PRs), issues, and Actions.
- **Branch protection:** rules that stop direct pushes to `main` or require checks to pass first.
- **GitHub Actions (CI):** automated jobs (lint, tests) that run on every push or PR.

## Options considered
### A. Public repo from day one
- Pros: visible to recruiters immediately; the history itself is portfolio evidence; free Actions minutes for public repos; signals openness.
- Cons: early mess is visible; any leaked secret is exposed instantly (mitigated by `.env` + `.gitignore` + GitHub secret scanning).
### B. Private repo now, public at the first milestone
- Pros: freedom to experiment; flip to public when Phase 1 works.
- Cons: easy to keep postponing; you lose "built in public" credibility.
### C. No GitHub yet (local git or Dropbox only)
- Pros: none worth having.
- Cons: no off-site history, no CI, no portfolio signal; Dropbox is not version control.

## Decision
We will use **git + GitHub from day one** (repo `tachocline`). Recommendation: **public from the start**, because the documented ADR trail is part of the portfolio. Private-until-Phase-1 is an acceptable alternative if Howard prefers; that choice is his to make when accepting this ADR.
- `main` is **protected**: changes arrive by PR, and CI must pass. As the only developer, Howard may self-merge.
- **GitHub Actions** runs `ruff` and `pytest` on every PR (Phase 1).
- Enable **secret scanning / push protection**. Keep secrets in `.env`, never in git.
- **Dropbox caveat:** Dropbox may corrupt `.git/` or create "conflicted copy" files if two machines touch it, and it syncs heavy folders needlessly. Use one machine at a time, mark `node_modules/.venv/data` as ignored by Dropbox, push often, and ideally move the clone to `~/code/` (see AGENTS.md §9). GitHub, not Dropbox, is the backup.

## Consequences
- Easier: undo, review, CI, sharing, a visible portfolio.
- Harder: learning the git and PR workflow (branches, rebasing, resolving conflicts). That is itself an interview-relevant skill.
- Public repos need a little care about what's in commit history.

## How to explain this in an interview
"The project was on GitHub from the first commit, with a protected main branch, PR-based changes, and GitHub Actions running lint and tests. Even as a solo developer I used PRs because they force small, reviewable changes and leave a readable history alongside my decision records."

## Learn more
- [Pro Git book](https://git-scm.com/book/en/v2) (official, free)
- GitHub Docs, [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) and [GitHub Actions](https://docs.github.com/en/actions)
- GitHub Docs, [Secret scanning](https://docs.github.com/en/code-security/secret-scanning/introduction/about-secret-scanning); Dropbox, [Ignored files](https://help.dropbox.com/sync/ignored-files)
