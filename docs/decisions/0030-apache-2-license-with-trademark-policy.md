# 0030. License the code under Apache 2.0 and keep the name and logo out of that grant

- **Status:** Proposed
- **Date:** 2026-11-01
- **Deciders:** Howard Isaacson

This is a project decision, not legal advice. If the name later has commercial value, an IP attorney should review it.

## Context

The repository is public and has had no `LICENSE` file. Without one, visitors have no permission to copy the code. `assets/brand/LICENSE-ASSETS.md` said brand files had “the same rights as the rest of this repository,” which pointed at nothing.

A software license covers copyright in the code. It does not, by itself, reserve a project name or a logo. Those are trademark questions. Issue #97 asks for a license that lets people learn from and reuse the code, while keeping **Tachocline Industries** and the TI logo for this project.

Numbers 0028 and 0029 are already used on open pull requests, so this record is 0030.

## Options considered

### A. Apache License 2.0 for code

- Pros: permissive reuse; a patent grant; **section 6 says the license grants no trademark rights**; a `NOTICE` file is the usual place for attribution.
- Cons: longer than MIT; contributors should read section 6 so they do not assume the name travels with the code.

### B. MIT

- Pros: short and familiar.
- Cons: silent on trademarks, so the name question would need a separate clause anyway.

### C. MPL 2.0 or GPL 3.0

- Pros: copyleft keeps improvements shared; GPL 3.0 section 7 can carry an extra trademark term.
- Cons: harder for a portfolio reader to reuse a snippet in another project.

### D. No license (all rights reserved)

- Pros: nothing to write.
- Cons: the public repo still looks reusable, but legally it is not. Forks and interviewers who copy a file would be guessing.

Documentation can sit under a different grant. **CC BY 4.0** lets someone quote or reuse an About page with attribution, which fits a teaching portfolio better than leaving the prose under Apache only.

## Decision

We will use **option A** for source code, SQL, and configuration.

Original prose under `docs/` is under **CC BY 4.0**.

The name **Tachocline Industries** and the TI logo are **not** included in either grant. [`TRADEMARKS.md`](../../TRADEMARKS.md) says forks must rename and rebrand, and that “based on Tachocline Industries” is allowed. The site footer and the README state both grants and point at that file.

Third-party files keep their own terms. Brand files are listed in `assets/brand/LICENSE-ASSETS.md` as excluded from Apache 2.0.

## Consequences

- Easier: someone can reuse a poller or a React component and say where it came from.
- Harder: new files must follow the split (code vs prose vs brand). A fork that keeps the logo is outside the license even if the code is unchanged.
- A USPTO registration is not part of this decision. A 2026-11-01 web search found no registration for this exact name and did find an unrelated Indian company using “Tachocline.” That note lives in `TRADEMARKS.md`.

## How to explain this in an interview

“The repo is Apache 2.0 so people can reuse the code, including a patent grant. Section 6 withholds trademark rights, and a separate TRADEMARKS.md says the name and logo stay with this project: a fork must rebrand, but it may say it is based on Tachocline Industries. The write-ups are CC BY 4.0. The Phil Hart eclipse photo, when present, stays under its own CC BY-NC-SA terms.”

## Learn more

- [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) (section 6 is Trademarks)
- [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/)
- [choosealicense.com](https://choosealicense.com/licenses/)
- [USPTO trademark basics](https://www.uspto.gov/trademarks/basics)
