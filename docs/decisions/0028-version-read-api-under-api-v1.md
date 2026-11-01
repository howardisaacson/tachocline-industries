# 0028. Version the read API under `/api/v1`

- **Status:** Proposed
- **Date:** 2026-11-01
- **Deciders:** Howard Isaacson

## Context
[ADR 0006](0006-fastapi-for-backend-api.md) put the read-only API at unversioned paths such as `GET /api/solar-wind`. That was fine while Grafana was the main consumer and the React page was the only HTTP client. The public site, a future MCP server, and any AI agent will all call the same JSON contract. A breaking change to a response field or a query rule would then hit every caller at once.

**API versioning** means publishing a stable major version of that contract, and introducing a new major version when a change cannot stay compatible. The version is part of how callers name the API, not the Docker image tag.

## Options considered
### A. URL path versioning (`/api/v1/…`)
- Pros: visible in every request and in OpenAPI; easy to try in a browser; FastAPI supports mounting the same `APIRouter` under more than one prefix; caches and reverse proxies treat each path as a distinct resource.
- Cons: URLs get one extra segment; a later `/api/v2` means either duplicated handlers or a shared router with two mounts.

### B. Header versioning (`Accept: application/vnd.ti.v1+json`)
- Pros: the path stays short.
- Cons: hard to discover; `/docs` and a pasted curl both need extra headers; easy to forget in a new client.

### C. Query parameter (`?version=1`)
- Pros: trivial to add.
- Cons: easy to omit; mixes resource identity with a cross-cutting concern; rarely recommended for public APIs.

### D. Leave paths unversioned until the first break
- Pros: no rename today.
- Cons: the first break forces every caller to change at once, with no place to park the old contract.

## Decision
We will use **option A**. The public contract is **`/api/v1/…`**. OpenAPI and `/docs` list only those paths. The FastAPI app `version` field is `1.0.0` to match the major version in the URL.

Unversioned `/api/…` paths stay as **hidden aliases** of the same handlers (`include_in_schema=False`) so a bookmarked curl or an old note still works during the cutover. New callers, including the React page, use `/api/v1`. A future breaking change ships as `/api/v2` and leaves v1 until its callers move; aliases are removed in a later PR once nothing in-repo calls them.

This ADR does not change which tables or query limits exist. It only names the HTTP surface. [ADR 0006](0006-fastapi-for-backend-api.md) stays Accepted for the choice of FastAPI.

## Consequences
- Easier: interviewers and new clients see a versioned REST API; a v2 can coexist with v1.
- Harder: docs and the web client must say `/api/v1`; tests assert both the public paths and, while aliases remain, one alias check.
- Follow-up: remove the unversioned aliases after the cutover window; open a "Review ADR 0028" issue before treating this as Accepted.

## How to explain this in an interview
"I put a major version in the URL (`/api/v1`) so the public contract is explicit. OpenAPI only documents that prefix. Unversioned `/api` paths stayed as hidden aliases during the move so nothing broke overnight. When a response shape has to change incompatibly, I can ship `/api/v2` and leave v1 running until callers migrate."

## Learn more
- FastAPI, [Bigger Applications — include the same router with different prefixes](https://fastapi.tiangolo.com/tutorial/bigger-applications/#include-the-same-router-multiple-times-with-different-prefix)
- MDN, [REST and resource naming](https://developer.mozilla.org/en-US/docs/Glossary/REST)
- Microsoft Azure Architecture Center, [API design — versioning a RESTful web API](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design#versioning-a-restful-web-api)
