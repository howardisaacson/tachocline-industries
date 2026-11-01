# 0031. Build locally from `develop`; agents may merge there, not to `main`

- **Status:** Proposed
- **Date:** 2026-11-01
- **Deciders:** Howard Isaacson

## Context

[ADR 0010](0010-use-git-and-github-from-day-one.md) put the project on git and GitHub and protected `main`: changes arrive by pull request, and CI must pass. Day-to-day work then branched from `main` and merged back to `main`. That makes the release line and the experimental line the same branch. Howard wants the Docker stack built from an integration branch, and he wants Cursor CLI to be able to land finished work there without being able to publish it on `main`.

Numbers 0028–0030 are already used on open pull requests, so this record is 0031. ADR 0010 stays Accepted. This record does not change “use git and GitHub” or “protect `main`.”

## Options considered

### A. Keep merging feature branches straight to `main`

- Pros: one branch to remember; matches the first months of the repo.
- Cons: a local `docker compose up` on `main` is the release line, so an agent merge and a release are the same act.

### B. `develop` for local integration; Howard promotes to `main`

- Pros: the machine you run is `develop`. Cursor CLI can merge a green pull request into `develop`. `main` stays the line only Howard updates.
- Cons: two long-lived branches; a forgotten promotion leaves `main` behind `develop`.

### C. Feature branches only, no integration branch

- Pros: no extra branch.
- Cons: there is no single checkout that is “what I am running” while several pull requests are open.

## Decision

We will use **option B**.

- Local builds (`docker compose`) use a checkout of **`develop`**.
- Feature branches are cut from `develop`. Pull requests target `develop`.
- **Cursor CLI may merge** a pull request into `develop` after CI passes.
- **Cursor CLI must not** merge, push, or force-push to `main`, and must not change `main`’s branch protection.
- Howard merges `develop` into `main` when he wants that history to be the release line.
- CI runs on pull requests and on pushes to `develop` and `main`.

## Consequences

- Easier: agents can finish a task on the branch the laptop actually runs, without touching the protected release branch.
- Harder: open pull requests that still target `main` need to be retargeted or left until Howard decides. `main` will lag `develop` until he promotes it.
- ADR 0010’s protection of `main` still applies.

## How to explain this in an interview

“`main` is protected and I am the only one who merges to it. Day-to-day integration is `develop`: that is the checkout I run with Docker Compose. Feature branches merge there, and the coding agent is allowed to merge into `develop` after CI, but not into `main`.”

## Learn more

- GitHub Docs, [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- GitHub Docs, [Changing the base branch of a pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/changing-the-base-branch-of-a-pull-request)
