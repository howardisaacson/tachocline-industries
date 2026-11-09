# 0038. Run the API and pollers on Python 3.15.2

- **Status:** Proposed
- **Date:** 2026-11-08
- **Deciders:** Howard Isaacson

## Context

Issue #59 is a learning upgrade: move the Python we actually run from 3.12 to 3.15, and write down what breaks. [ADR 0004](0004-python-scheduled-pollers-with-raw-landing-zone.md) chooses Python pollers. It does not name a minor version. CI and both app images were on the floating `python:3.12-slim-bookworm` tag and on `python-version: "3.12"`.

Python 3.15.0 shipped on 9 October 2026. Python 3.15.2, released 25 October 2026, is the current maintenance release. It is also a security release: the `ssl` module rejects certificate chains that use a set of compromised eMudhra intermediate keys, even when an application brings its own CA bundle. That matters for `pip` inside the image.

The removals in 3.15 do not touch this repo. Our code does not use the deleted `ast` constructor behavior, `importlib` `load_module`, `sre_compile`, or `typing.no_type_check_decorator`. The `datetime.strptime` change (a `%d` without a year is now an error) does not apply: the solar-RV parser uses `%Y-%m-%d %H:%M:%S`. [PEP 686](https://peps.python.org/pep-0686/) makes UTF-8 the default text encoding. We already pass `encoding="utf-8"` where a file encoding matters.

The C-extension wheels we need exist for CPython 3.15. Checked on PyPI on 2026-11-08: `pydantic-core` 2.50.1 (pulled in by pydantic 2.14.1) and `psycopg-binary` 3.3.6 both publish manylinux x86_64 `cp315` wheels. FastAPI, uvicorn, httpx, APScheduler, ruff, and pytest publish `py3-none` wheels and declare `requires-python` below 3.15. Library pins stay where `develop` has them. This record does not bump those packages.

## Options considered

### A. Stay on Python 3.12

- Pros: nothing to rebuild; 3.12 is still in bugfix support.
- Cons: the issue is to find the breakage now, not after a dependency drops 3.12. The image would also miss the 3.15.2 `ssl` backstop.

### B. Pin 3.15.2 on the same Bookworm images, and pin CI to 3.15.2

- Pros: one variable changes, the interpreter. Bookworm's `postgresql-client` stays Postgres 15, which the migrate image already documents. The patch pin matches the security release instead of a floating `3.15` tag. GitHub Actions already publishes 3.15.2.
- Cons: a later 3.15.3 is a deliberate edit. Ruff's `target-version` moves to `py315`, so new syntax will not run on 3.12.

### C. Use the floating `python:3.15-slim` tag

- Pros: one tag tracks the newest 3.15 patch.
- Cons: that tag is Debian Trixie today (`3.15.2-slim-trixie`). Changing the Debian suite in the same pull request would mix an apt change with the interpreter change. A floating tag also moves under us on the next rebuild.

## Decision

We will use **option B**.

- `api/Dockerfile` and `ingest/Dockerfile` use `python:3.15.2-slim-bookworm`.
- CI's lint and test jobs use `python-version: "3.15.2"`.
- Ruff's `target-version` is `py315`.
- ADR 0004 is unchanged: pollers are still Python, httpx, pydantic, and APScheduler 3.x.

## Consequences

- Easier: the next "what broke?" is a patch bump, not a three-version jump. `pip` in the image gets the 3.15.2 certificate check.
- Harder: a laptop venv on 3.12 will not match CI. Create the venv with 3.15.2.
- The live Compose images keep the names `tachocline-app:0.1` and `tachocline-api:0.1`. They pick up 3.15.2 the next time those images are built. This change does not by itself restart the running poller.
- One formatter change: with `target-version = "py315"`, Ruff rewrites `except (TypeError, ValueError)` to `except TypeError, ValueError` in `ingest/ti_ingest/solar_rv.py`. Parentheses around an exception list became optional in 3.14 ([PEP 758](https://peps.python.org/pep-0758/)). The tests still pass. No library pin changed.

## How to explain this in an interview

"We stayed on Bookworm and only moved the interpreter to 3.15.2, the current security patch. I checked the What's New removals against our code, then checked that pydantic-core and psycopg-binary publish cp315 wheels, because those are the packages that would fail `pip install` if the wheel were missing. The library pins did not change in the same pull request."

## Learn more

- [What's new in Python 3.15](https://docs.python.org/3/whatsnew/3.15.html)
- [Python 3.15.2 release](https://www.python.org/downloads/release/python-3152/)
- [PEP 686: Make UTF-8 mode default](https://peps.python.org/pep-0686/)
- [Official Docker image for Python](https://hub.docker.com/_/python/)
