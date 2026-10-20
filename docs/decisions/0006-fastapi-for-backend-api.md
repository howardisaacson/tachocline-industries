# 0006. FastAPI for the backend API

- **Status:** Proposed
- **Date:** 2026-10-18
- **Deciders:** Howard Isaacson

## Context
Grafana can read the database directly ([ADR 0007](0007-grafana-now-react-later-for-frontend.md)), but a public website and a React frontend should **not** connect to the database. They need an **API**: a web service that answers HTTP requests like `GET /api/solar-wind?from=2026-10-18T00:00Z` with JSON. An API hides database details, controls what is exposed, and lets other people (or a recruiter) use our cleaned data. I write Python; the pollers are Python.

Key terms:
- **REST API:** URLs represent resources (e.g., `/solar-wind`), and HTTP methods (GET, POST) act on them.
- **Endpoint:** one URL + method.
- **OpenAPI:** a standard, machine-readable description of an API that tools turn into interactive docs.

## Options considered
### A. FastAPI (Python)
- Pros: request and response validation via type hints and pydantic (the same library as the pollers); **automatic interactive docs** at `/docs`; async support; fast-growing and widely used in data/ML teams.
- Cons: still on 0.x version numbers (0.146 as of Oct 2026), so occasional minor breaking changes; smaller ecosystem than Django for full websites.
### B. Flask (Python)
- Pros: simple, mature, huge community.
- Cons: validation and API docs need add-on libraries; less built-in structure.
### C. Django + Django REST Framework (Python)
- Pros: "batteries included" (admin site, ORM, auth); excellent for full web apps.
- Cons: heavy for a read-mostly data API; its ORM and migrations would overlap with our SQL-first approach.
### D. Node.js + Express (JavaScript)
- Pros: same language as the React frontend; very common in web companies.
- Cons: a second backend language while I'm still learning JavaScript; we couldn't share Python validation models with the pollers.

## Decision
We will build the API with **FastAPI**, run with Uvicorn as its own Docker Compose service. Initial endpoints are read-only: `GET /api/health`, `GET /api/solar-wind`, `GET /api/sources`, `GET /api/ingest-log`. Queries run against the TimescaleDB views and aggregates. Pydantic response models define the public contract. The OpenAPI docs at `/docs` will be linked from the site.

## Consequences
- Easier: one language for backend and pipeline; a self-documenting API to show interviewers; easy testing with pytest and FastAPI's test client.
- Harder: learning HTTP basics (status codes, query parameters, CORS so the React app can call it).
- Must add sensible limits (max time range, pagination) so one request can't scan the whole table.

## How to explain this in an interview
"The frontend never touches the database. It calls a FastAPI service that exposes a few read-only REST endpoints. I picked FastAPI because it validates requests and responses with the same pydantic models my pollers use and generates OpenAPI docs automatically, so the API is typed, tested, and self-documenting."

## Learn more
- [FastAPI documentation](https://fastapi.tiangolo.com/) and [Tutorial](https://fastapi.tiangolo.com/tutorial/)
- [OpenAPI Initiative](https://www.openapis.org/)
- MDN, [An overview of HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview)
