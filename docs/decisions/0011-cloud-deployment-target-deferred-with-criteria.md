# 0011. Cloud deployment target: defer the choice, define the criteria now

- **Status:** Proposed
- **Date:** 2026-10-20
- **Deciders:** Howard Isaacson

## Context
We build locally first ([ADR 0002](0002-build-locally-first-with-docker-compose.md)). Eventually the site must be public, and Howard wants **cloud skills on his resume**. The big three (AWS, Google Cloud, Azure) dominate job postings, while simpler hosts (Fly.io, Render) deploy containers with far less setup. Prices, free tiers, and services change often, so choosing now risks deciding on stale information.

## Options considered
### A. AWS
- Pros: largest market share, the most-requested cloud skill; mature managed Postgres (RDS) and container services (ECS/App Runner); well-known certifications.
- Cons: steep learning curve (IAM, VPCs); easy to misconfigure costs.
### B. Google Cloud (GCP)
- Pros: Cloud Run makes running containers simple; BigQuery is strong for analytics and data roles; generally a clean developer experience.
- Cons: fewer job postings than AWS in many markets.
### C. Microsoft Azure
- Pros: strong in enterprises; good Postgres offering.
- Cons: less common in startups and data-science roles near Berkeley/Bay Area (impression, unverified).
### D. Fly.io / Render (container PaaS)
- Pros: deploy the existing Docker setup in minutes; cheap or free for small apps; lets us focus on the product.
- Cons: weaker resume signal ("cloud" usually means AWS/GCP/Azure); less to learn about IAM, networking, and infrastructure as code.

## Decision
**Defer** the provider choice to a new ADR at the start of the deployment phase (Roadmap Phase 4). That ADR must score options against these **criteria**:
1. **Resume value** for target roles: check current job postings Howard is applying to and count which cloud they name.
2. **Monthly cost** at our size; must fit within free tier or credits or a set budget, **with billing alerts** configured.
3. **Managed PostgreSQL with TimescaleDB** support (or a clear path: self-hosted container, Tiger Cloud, etc.).
4. **Runs our Docker images** with little rewriting (Cloud Run, ECS/App Runner, Container Apps, Fly).
5. **Infrastructure as code** possible (e.g., Terraform/OpenTofu), a resume skill in itself.
6. **Scheduled jobs** for pollers, plus logs and monitoring.
7. **Learning curve** versus time available.

Working hypothesis (not decided): **GCP (Cloud Run + Cloud SQL or a Postgres VM)** or **AWS (App Runner/ECS + RDS)**, deployed with Terraform. Fly.io remains the fast fallback for an early public demo.

Meanwhile, keep the app **cloud-portable**: configuration via environment variables, stateless containers, no hard-coded `localhost`.

## Consequences
- Easier: no cost or complexity now; the decision later uses real job-posting data.
- Harder: the site isn't public until Phase 4 (screenshots and video meanwhile).
- Risk: portability assumptions break. The criteria and twelve-factor style config mitigate this.

## How to explain this in an interview
"I deliberately deferred the cloud choice until I had a working system, but wrote down the criteria up front: resume relevance from real job postings, cost with billing alerts, managed Postgres, container support, and infrastructure as code. Keeping the app containerised and configured by environment variables meant moving to AWS or GCP was a deployment task, not a rewrite."

## Learn more
- [AWS Free Tier](https://aws.amazon.com/free/), [Google Cloud Free Program](https://cloud.google.com/free), [Azure free services](https://azure.microsoft.com/en-us/pricing/free-services)
- [Google Cloud Run docs](https://cloud.google.com/run/docs); [Fly.io docs](https://fly.io/docs/); [Render docs](https://render.com/docs)
- The Twelve-Factor App, [Dev/prod parity](https://12factor.net/dev-prod-parity)
