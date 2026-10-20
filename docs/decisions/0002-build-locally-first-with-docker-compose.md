# 0002. Build locally first with Docker Compose

- **Status:** Proposed
- **Date:** 2026-10-18
- **Deciders:** Howard Isaacson

## Context
I've decided to build the site on my own computer before deploying it anywhere. The system needs several moving parts running together: a database, data pollers, an API, and a dashboard tool. Installing each one directly on my laptop ("bare metal") leads to version conflicts and "works on my machine" problems, and makes a later move to a cloud server painful. I also want a setup that anyone (an interviewer, for example) can clone and run.

Key terms:
- **Container:** a lightweight, isolated package containing an app plus everything it needs to run.
- **Image:** the blueprint a container is started from (e.g., the official `postgres` image).
- **Docker Compose:** a tool that starts several containers together from one `docker-compose.yml` file.

## Options considered
### A. Install everything directly on the laptop
- Pros: no new tool to learn; slightly faster to begin.
- Cons: version clashes; hard to reset; setup steps are undocumented; doesn't match how production systems run.
### B. Deploy to the cloud from day one (AWS/GCP/a VPS)
- Pros: publicly reachable immediately; cloud experience.
- Cons: costs money; slower edit-test loop; adds networking, security, and billing to learn at the same time as everything else.
### C. Docker Compose on the laptop, deploy later
- Pros: one command (`docker compose up`) starts the whole stack; versions pinned in a file; easy to wipe and rebuild; the same containers can later run on a server; Docker is a widely requested skill.
- Cons: learning curve (images, volumes, networks); uses some RAM/disk; on macOS/Windows it runs inside a small VM.
### D. Kubernetes locally (minikube/kind)
- Pros: industry-standard orchestration.
- Cons: far too much complexity for one developer and a handful of services.

## Decision
We will develop locally with **Docker Compose**. Each component (database, Grafana, poller, API) is a service in `docker-compose.yml`. Database data lives in a named **volume**, so it survives container restarts. Secrets and API keys go in a git-ignored `.env` file. Deployment is a later decision with its own ADR.

## Consequences
- Easier: reproducible setup, a clean README ("install Docker, run one command"), a future move to a server.
- Harder: I need to learn basic Docker concepts and debug container networking (services reach each other by service name, e.g. `db:5432`, not `localhost`).
- Risk: the site isn't public until a deployment ADR is written and done. Screenshots and a demo video cover the gap.
- Pollers only collect data while my computer is on, so history will have gaps. This is acceptable for now and should be documented on the relevant About pages.

## How to explain this in an interview
"I built locally first with Docker Compose so the whole stack (Postgres, the pollers, the API, and Grafana) starts with one command and is reproducible on any machine. It kept costs at zero and the feedback loop fast, and because everything is containerised, moving it to a server later is mostly configuration, not a rewrite."

## Learn more
- Docker docs, [Docker overview](https://docs.docker.com/get-started/docker-overview/)
- Docker docs, [Docker Compose](https://docs.docker.com/compose/) and [Control startup order](https://docs.docker.com/compose/how-tos/startup-order/)
- The Twelve-Factor App, [Dev/prod parity](https://12factor.net/dev-prod-parity)
