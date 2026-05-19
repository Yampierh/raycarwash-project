# Skills Reference — RayCarWash

> **Purpose:** Codified professional expertise for reuse across sprints. Each skill is a self-contained guide for a specific engineering discipline.
> **Created:** 2026-05-19
> **Usage:** Load the relevant skill before starting a task. Skills are referenced by `docs/skills/{NN}-{name}.md`.

---

## Skill Map

| # | Skill | Discipline | When to Use |
|---|-------|-----------|-------------|
| 01 | [`01-backend-api-security.md`](./01-backend-api-security.md) | Security | Before writing any new API endpoint. Covers rate limiting, idempotency, validation, PII, CORS. |
| 02 | [`02-backend-performance.md`](./02-backend-performance.md) | Performance | When designing aggregate queries, materialized views, or cache strategy. Especially for dashboard endpoints. |
| 03 | [`03-backend-observability.md`](./03-backend-observability.md) | Observability | When adding new endpoints or workers. Covers metrics, structured logging, tracing, audit. |
| 04 | [`04-api-contracts-quality.md`](./04-api-contracts-quality.md) | Quality | Before finalizing any API contract. SCAM checklist: Security, Contracts, Audit, Metrics. |
| 05 | [`05-codebase-migrations.md`](./05-codebase-migrations.md) | DevOps | When restructuring directories, renaming packages, or updating build scripts across the monorepo. |

---

## How to Use a Skill

Each skill has:
- **Overview** — what it covers and when to load it
- **Prerequisites** — what files to read first (AGENTS.md, execution_protocol.md, relevant plan docs)
- **Checklist** — step-by-step verification items per task type
- **Common Pitfalls** — mistakes this team has made before (with references to audit findings)
- **Examples** — real examples from this codebase

---

## Skill Lifecycle

1. **Creation** — When a pattern repeats across 3+ sprints, codify it as a skill
2. **Review** — Skills are reviewed quarterly against new audit findings
3. **Deprecation** — When a skill no longer applies (tooling changes, architecture rewrite)

---

## Cross-Reference: Skills ↔ Plans

| Skill | Related Plans | Related Audit Findings |
|-------|--------------|----------------------|
| 01 — API Security | 19, 20, 21, 22 | H1 (idempotency), H2 (rate limits), H4 (validation), H6 (data exposure), H7 (enum injection) |
| 02 — Performance | 19, 20, 22 | H3 (dashboard indexes), H5 (cache strategy) |
| 03 — Observability | 19, 20, 21 | H8 (headers/metrics) |
| 04 — Contracts Quality | 19, 20, 21 | All findings (prevention) |
| 05 — Codebase Migrations | 12, 11, 13, 14, 15, 16, 17 | — (operational) |
