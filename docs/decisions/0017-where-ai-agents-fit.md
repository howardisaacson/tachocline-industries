# 0017. Where AI agents fit in TI

- **Status:** Accepted
- **Date:** 2026-10-20
- **Deciders:** Howard Isaacson

## Context
AI agents show up in TI in two ways. First, Howard already **builds** with coding agents (Cursor, Claude, Grok) governed by [AGENTS.md](../../AGENTS.md). Second, agents could be **part of the product**: summarising space-weather alerts, answering questions over our data, triaging pipeline failures, or finding papers. Agent skills are in demand, but agents also add risks: hallucination, prompt injection, cost, and evaluation difficulty. Details and candidates are in [`docs/ai-agents.md`](../ai-agents.md).

An **agent** here means an LLM that calls defined **tools** (functions) in a loop to finish a task. **MCP** (Model Context Protocol) is an open standard for exposing tools and data to AI clients.

## Options considered
### A. No agents in the product
- Pros: no added risk or cost.
- Cons: misses a high-demand skill and a natural fit (alerts are text-heavy).
### B. Ambitious general agent (chat over everything, autonomous actions)
- Pros: impressive demo.
- Cons: hard to evaluate; large hallucination and injection surface; cost unpredictable; hard to defend.
### C. Small, read-only, evaluated agents added incrementally
- Pros: each one is testable and grounded in our own data; cost is controlled; it shows good judgement.
- Cons: less flashy at first.

## Decision
Adopt option C.
- **Building:** coding agents follow AGENTS.md. Howard reviews and understands every merged change, AI code review is a second reviewer only, and facts and links are verified.
- **Product principles:** tools are read-only by default and go through the FastAPI layer (never raw DB credentials); answers are grounded in tool results with citations; untrusted text is treated as data; no side effects without a human; an eval set exists before anything ships and runs in CI; caching plus spend caps; AI output is labelled and every agent page gets an About page.
- **First agent:** a **space-weather briefing** workflow (SWPC alerts plus current Kp, X-ray and solar wind → a short cited briefing), in **Phase 3**.
- **Next:** a TI **MCP server** wrapping the read API (Phase 3–4); then **text-to-SQL** with a SELECT-only role on curated views, `statement_timeout`, row limits and SQL shown to the user (Phase 4+). Anomaly triage and the ADS/arXiv literature agent are Phase 5 stretch goals.
- Model and provider choice gets its own ADR when the first agent is built.

## Consequences
- Easier: a credible, safe agent story; reuse of the API layer.
- Harder: building evals and guardrails; ongoing API cost (small with caching); keeping AI labelling and About pages accurate.

## How to explain this in an interview
"I used coding agents to build the project under a written rulebook, but I reviewed and understood every change. In the product I started with one small, read-only briefing agent that only uses data fetched through my API, cites every sentence, is labelled as AI-generated, and has an eval set in CI, rather than a general chatbot I couldn't test."

## Learn more
- Anthropic, [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- OWASP, [Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/)
