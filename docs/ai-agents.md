# AI agents and Tachocline Industries

> **Status:** plan. Decision: [ADR 0017](decisions/0017-where-ai-agents-fit.md). Nothing here is built yet.

Two separate topics: **(a)** using AI coding agents to *build* TI, and **(b)** putting agents *inside* the product. Both are good interview material if handled honestly.

---

## (a) Agents used to build TI

**How we use them**
- **Coding agents** (Cursor, Claude Code, Grok, Codex) all follow one rulebook, [AGENTS.md](../AGENTS.md). Tool-specific files (`CLAUDE.md`, `GROK.md`, `.cursor/rules/agents.mdc`) only point to it. AGENTS.md requires agents to *teach and explain*, not just generate.
- **Drafting ADRs and research docs:** agents draft, Howard reviews and decides. ADRs stay **Proposed** until Howard accepts them.
- **Code review:** AI review on pull requests (e.g., [Cursor Bugbot](https://cursor.com/docs/bugbot), [GitHub Copilot code review](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review)) as a *second* reviewer, never the only one.
- **Research with verification:** agents check links and facts. That process already caught a real error: a citation in our orbit-decay research pointed to an unrelated arXiv paper and was corrected.

**Guardrails**
- Howard reads and understands every merged change. If he can't explain it, it doesn't merge.
- Facts and links are verified, and unverified claims are marked as such.
- No secrets in prompts; agents never get production credentials.
- Tests and CI judge correctness, not the agent's confidence.

**Talking about it in interviews (responsibly)**
- Be upfront: "I used AI coding agents heavily, under a written rulebook."
- Emphasise *your* role: framing problems, making the decisions (ADRs), reviewing, testing, and catching agent errors. Have one or two concrete examples ready, such as the bad citation that was caught.
- Show you understand the code: be ready to whiteboard any part without the tool.
- Don't overclaim. Distinguish "I designed and understand this" from "an agent generated boilerplate that I reviewed."

---

## (b) Agents in the product (candidates)

An **agent** here means an LLM that can call **tools** (functions we define, e.g. "get latest SWPC alerts", "run read-only SQL") in a loop to complete a task, as opposed to a single prompt and reply. See [Anthropic's "Building effective agents"](https://www.anthropic.com/engineering/building-effective-agents), which also advises using the simplest pattern that works, often a fixed workflow rather than a free-roaming agent.

| Agent | What it does | Data and tools | Main risks | Difficulty |
|---|---|---|---|---|
| **1. Space-weather briefing** | Turns the latest SWPC alerts, watches and warnings plus Kp/X-ray/solar-wind values into a short plain-language daily or event briefing, with citations to each source product. | SWPC `products/alerts.json` and our DB (read-only) | Misstating severity; hallucinated impacts | ★☆☆ |
| **2. Natural-language query (text-to-SQL)** | "What was the fastest solar wind this week?" becomes SQL over TimescaleDB, and the agent returns the answer plus the query it ran. | Read-only DB role, schema description, SQL tool | Wrong SQL that looks right; expensive queries; prompt injection | ★★☆ |
| **3. Ingestion anomaly triage** | When `ingest_log` shows failures, rejects or schema drift, it summarises likely causes (e.g., "endpoint returned 404; SWPC deprecated it?"), links to raw samples, and drafts an issue for Howard. It does not auto-fix. | `ingest_log`, raw files, HTTP status | False diagnoses; must not take actions on its own | ★★☆ |
| **4. Literature / research assistant** | Finds and summarises papers (e.g., storm-time thermospheric density, Starlink 2022) with real links. | [NASA ADS API](https://github.com/adsabs/adsabs-dev-api) (free token), [arXiv API](https://info.arxiv.org/help/api/index.html) | Fabricated or mismatched citations. This exact failure happened in our own research, which shows why every ID must be resolved through the API. | ★★☆ |

---

## (c) Design concerns

- **Tool calling.** Major APIs support it: [Claude](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview), [OpenAI](https://platform.openai.com/docs/guides/function-calling), [xAI](https://docs.x.ai/docs/guides/function-calling). Keep tools narrow, typed (pydantic schemas), and read-only by default.
- **MCP (Model Context Protocol).** An open standard for exposing tools and data to any compatible AI client ([modelcontextprotocol.io](https://modelcontextprotocol.io/), [server concepts](https://modelcontextprotocol.io/docs/learn/server-concepts), [Python SDK](https://github.com/modelcontextprotocol/python-sdk)). Idea: a small **TI MCP server** that wraps the FastAPI read endpoints (`get_solar_wind`, `get_alerts`, `get_satellite_altitude`). Then Claude, Cursor or another client could answer questions with live TI data. It's also a nice portfolio piece. It must reuse the API layer, never raw DB credentials.
- **Text-to-SQL guardrails.**
  - Dedicated Postgres role with `SELECT` only on curated views ([GRANT](https://www.postgresql.org/docs/current/sql-grant.html)).
  - `statement_timeout` and row limits ([client config](https://www.postgresql.org/docs/current/runtime-config-client.html)).
  - Allow-list of schemas; parse the SQL and reject anything that isn't a single `SELECT`.
  - Always show the SQL to the user; log every query.
- **Hallucination and citations.** Answers must be grounded in tool results. Each claim cites the product or record it came from, numbers come from queries rather than from the model's memory, and when the agent doesn't know it says so. Paper citations are resolved via ADS or arXiv and the title is checked against the ID.
- **Security.** Treat all fetched text (alerts, papers, user questions) as untrusted. **Prompt injection** is the #1 risk in the [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/). No tool with side effects runs without a human in the loop. API keys live server-side in `.env`.
- **Evaluation.** Build a small test set before shipping, e.g. 30 questions with known answers for text-to-SQL, or 10 past alert sets with reference briefings. Score accuracy, citation correctness and refusal behaviour, and run it in CI when prompts or models change. See [Hamel Husain on evals](https://hamel.dev/blog/posts/evals/) and [OpenAI evals guide](https://platform.openai.com/docs/guides/evals).
- **Cost and latency.**
  - Cache briefings: one generation per new alert, not per page view.
  - Use small or cheap models for routine summaries, and set per-day token and spend caps.
  - Consider local models (e.g., [Ollama](https://ollama.com/)) for development.
  - Log tokens per request and show cost on an internal Grafana panel.
- **Reusable agent skills (resource).** DOE's Genesis Mission published public "Genesis Agent Skills" from the National Labs, covering AI safety, agent evaluation and monitoring, data governance, scientific workflows and multi-agent systems ([DOE Office of Science, 2026-10-15](https://www.energy.gov/science/articles/genesis-agent-skills-release-support-innovation-across-genesis-mission)). Worth reviewing as a model for packaging TI's own agent guidance (AGENTS.md) and for evaluation and governance practices. Tracked in [links.md](links.md).
- **Governance.** Label AI-generated text on the site ("AI-generated summary of NOAA SWPC products; see the originals") and link to an About page describing model, prompt approach, evals and limitations. [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework) is a useful vocabulary.

---

## Recommendation: the first agent to build
**Space-weather briefing agent**, in **Phase 3** (after the API exists and the public site is being built), as a fixed workflow rather than a free-roaming agent:
1. Trigger: a new SWPC alert, or a daily schedule.
2. Fetch: alerts plus current Kp, X-ray class and solar-wind speed via the TI API.
3. One LLM call with tool results only. Output: a 3–5 sentence briefing with a citation per sentence (product ID or time).
4. Validate (every cited ID exists; numbers match the DB), store it, and show it on the site labelled as AI-generated.
5. An eval set of past alerts runs in CI.

Why first: it's read-only, small, cheap with caching, easy to evaluate, on-theme, and demonstrates tool use, grounding, evals and cost control. **Next:** the TI MCP server (Phase 3–4), then text-to-SQL with full guardrails (Phase 4+). The anomaly-triage and literature agents come later, as Phase 5 stretch goals.
