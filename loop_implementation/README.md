# Loop — Implementation Documentation

**Status:** v0.2 — ready to commence implementation
**Date:** 29 April 2026
**Audience:** founding engineers, AI coding agents, design partners, investors who want technical depth

This folder is the engineering team's Day-1 package for building Loop — the open-source, agent-first, **cloud-agnostic** runtime for production AI agents that competes with Botpress. It is the *implementation* counterpart to the strategic [`botpress_competitor_spec.md`](../botpress_competitor_spec.md) one folder up.

**For AI coding agents:** start at [`AGENTS.md`](AGENTS.md), then [`skills/_base/SKILL_ROUTER.md`](skills/_base/SKILL_ROUTER.md). The 40 skills in `skills/` cover every recurring task — pick the matching one from the Task → Skill table and follow its checklist. Per-platform adapter files for Claude, Codex, GitHub Copilot, Cursor, Aider, Windsurf, and Continue.dev are in [`skills/platforms/`](skills/platforms/). All canonical docs are Markdown. Don't touch `.docx`, `.pptx`, or `.xlsx` directly — they're derived exports.

**Cloud:** Loop is cloud-agnostic by construction. Runs on AWS, Azure, GCP, Alibaba Cloud, OVHcloud, or self-hosted Kubernetes — same code, same Helm chart, configured per environment. See [`architecture/CLOUD_PORTABILITY.md`](architecture/CLOUD_PORTABILITY.md) and ADR-016.

---

## What's in here

```
loop_implementation/
├── README.md                          ← you are here (humans)
├── AGENTS.md                          ← entry point for AI coding agents
│
├── architecture/
│   ├── ARCHITECTURE.md                C4-style system architecture, sequence diagrams, deployment topology, ownership matrix
│   ├── AUTH_FLOWS.md                  OIDC, API key, mTLS/SPIFFE, channel-webhook auth — sequence diagrams + token formats
│   ├── CLOUD_PORTABILITY.md           Per-cloud mapping (AWS↔Azure↔GCP↔Alibaba↔self-host) + abstraction interfaces
│   └── NETWORKING.md                  Network topology, egress, private connectivity, DNS, certs, voice routing
│
├── data/
│   └── SCHEMA.md                      Postgres DDL, Qdrant collections, Redis keys, ClickHouse tables, Pydantic models, RLS, classification, retention
│
├── api/
│   └── openapi.yaml                   OpenAPI 3.1 spec for the public REST API (importable into Postman, Stoplight, codegen)
│
├── adrs/
│   └── README.md                      28 Architecture Decision Records covering language, vector store, MCP, NATS, Firecracker, license, eval-gating, cloud-agnostic, and more
│
├── ux/
│   └── UX_DESIGN.md                   Studio IA, screens, design system, components, wireframes, accessibility
│
├── engineering/
│   ├── HANDBOOK.md                    Local dev setup, conventions, branching, code review, on-call, definition of done
│   ├── SECURITY.md                    Threat model, controls, secrets, compliance (SOC2 / HIPAA / GDPR), audit log
│   ├── TESTING.md                     Test pyramid, eval harness, scorers, CI gates, load + chaos
│   ├── PERFORMANCE.md                 Performance budgets, bench rig, profiling workflows, regression catalog
│   ├── DR.md                          Disaster recovery RTO/RPO targets, backup policies, region-loss playbook, drill cadence
│   ├── RUNBOOKS.md                    Operational runbooks (RB-001…RB-020): failover, key rotation, DSAR, region cutover, incident response
│   ├── ERROR_CODES.md                 Canonical error code registry (LOOP-XX-NNN), HTTP mapping, RFC 9457 envelope
│   ├── ENV_REFERENCE.md               Every environment variable: name, default, type, description, owner service
│   ├── GLOSSARY.md                    Single source of truth for terminology — supersedes ARCHITECTURE.md §0
│   ├── COPY_GUIDE.md                  Voice + tone for product UI strings, errors, docs, marketing
│   └── templates/                     ADR_TEMPLATE.md · RFC_TEMPLATE.md · RUNBOOK_TEMPLATE.md
│
├── tracker/
│   ├── SPRINT_0.md                    Week-by-week first 6 weeks of work, with capacity, dependencies, scope-cut tree
│   ├── TRACKER.md                     ★ Canonical AI-readable view of the whole tracker (Epics · Stories · Sprints · Hiring · Risks · Roadmap · Budgets)
│   ├── tracker.json                   Full structured export — best for programmatic consumption
│   ├── csv/                           Per-sheet CSVs (epics.csv · stories.csv · sprints.csv · hiring.csv · risks.csv · roadmap.csv · budgets.csv · overview.csv)
│   └── IMPLEMENTATION_TRACKER.xlsx    Same content as a spreadsheet (humans / Excel / Sheets)
│
├── skills/                            ★ 40 task-specific skills (Claude-Skill format) + per-platform adapters
│   ├── README.md                      Skill catalog + how to use per platform
│   ├── _base/SKILL_ROUTER.md          The base skill — read first; routes you to the right specific skill
│   ├── meta/                          write-pr · update-tracker · verify-doc-consistency
│   ├── architecture/                  propose-adr · update-architecture · cloud-portability-check
│   ├── coding/                        runtime · gateway · mcp-tool · channel · kb · eval-scorer · studio · cli · multi-agent
│   ├── data/                          postgres-migration · pydantic-type · update-schema
│   ├── api/                           rest-endpoint · streaming-event · openapi
│   ├── security/                      error-code · threat-model · audit-event · secrets-kms-check
│   ├── testing/                       unit · integration · e2e · eval-suite · perf-check
│   ├── observability/                 otel-span · metric · runbook
│   ├── ux/                            studio-component · design-token · ui-copy
│   ├── ops/                           deploy · rollback · triage-incident · dr-drill
│   ├── devrel/                        docs-page · publish-mcp-server
│   └── platforms/                     Adapter files for Claude, Codex, GitHub Copilot, Cursor, Aider, Windsurf, Continue.dev
│
└── scaffolding/                       Drop-in starter files for the monorepo
    ├── README.md
    ├── pyproject.toml                 (uv workspace root)
    ├── Makefile                       (bootstrap, up, dev, test, lint, format)
    ├── .editorconfig
    ├── .gitignore
    ├── .pre-commit-config.yaml
    ├── LICENSE                        (Apache 2.0)
    ├── .github/workflows/             (ci.yml, release.yml)
    ├── infra/docker-compose.yml       (Postgres, Redis, Qdrant, NATS, MinIO, ClickHouse, OTel — cloud-neutral local stack)
    ├── packages/sdk-py/loop/          (Agent base class, public types)
    ├── packages/runtime/loop/runtime/ (TurnExecutor skeleton)
    └── examples/support_agent/        (reference agent + eval suite)
```

---

## Reading order

If you have **30 minutes**, read in this order:

1. `architecture/ARCHITECTURE.md` — what we're building.
2. `adrs/README.md` — why we're building it this way.
3. `tracker/SPRINT_0.md` — what to do first.

If you have **a day**, add:

4. `engineering/GLOSSARY.md` — vocabulary.
5. `data/SCHEMA.md` — the data shapes.
6. `api/openapi.yaml` — the public surface.
7. `engineering/HANDBOOK.md` — how we work.
8. `engineering/ENV_REFERENCE.md` — every environment variable.
9. `engineering/ERROR_CODES.md` — error namespace.
10. `ux/UX_DESIGN.md` — the Studio plan.
11. `engineering/TESTING.md` + `engineering/PERFORMANCE.md` — the bars to clear.
12. `engineering/SECURITY.md` + `architecture/AUTH_FLOWS.md` — auth and trust.
13. `architecture/NETWORKING.md` + `architecture/CLOUD_PORTABILITY.md` — infra.
14. `engineering/DR.md` + `engineering/RUNBOOKS.md` — when things break.
15. `engineering/COPY_GUIDE.md` — how Loop talks.

If you have **a week**, also: skim every package in `scaffolding/`, run `make bootstrap && make up && make dev` on a fresh machine, file a PR fixing one thing you don't like.

---

## How these documents relate

```
                ┌──────────────────────────────────┐
                │  ../botpress_competitor_spec.md  │   strategic spec
                │      (the "why" + product wedges)│
                └──────────────────────────────────┘
                                │
                                ▼
                ┌────────────────────────────────────┐
                │  architecture/ARCHITECTURE.md      │   the "what"
                └────────────────────────────────────┘
                  │              │              │
                  ▼              ▼              ▼
      ┌──────────────┐  ┌──────────────┐  ┌────────────────┐
      │ data/SCHEMA  │  │ api/openapi  │  │ adrs/          │
      │  (storage)   │  │  (interface) │  │  (decisions)   │
      └──────┬───────┘  └──────┬───────┘  └───────┬────────┘
             │                  │                  │
             └──────────────────┴──────────────────┘
                                │
                                ▼
                ┌─────────────────────────────────────┐
                │  scaffolding/   ux/UX_DESIGN.md     │   the "how" and the "look"
                └─────────────────────────────────────┘
                                │
                                ▼
                ┌─────────────────────────────────────┐
                │  engineering/HANDBOOK / TESTING /   │   the "way of working"
                │  SECURITY                           │
                └─────────────────────────────────────┘
                                │
                                ▼
                ┌─────────────────────────────────────┐
                │  tracker/  (Sprint 0 + .xlsx)       │   what we ship and when
                └─────────────────────────────────────┘
```

Edit policy: any change to the architecture, schema, or API is a single PR that updates the relevant doc *and* the code. Out-of-band doc PRs are the second-most-common reason this folder rots; the first is shipping code without an ADR for the decision behind it.

---

## Day-1 checklist for a new engineer

- [ ] Read `architecture/ARCHITECTURE.md` end-to-end.
- [ ] Skim `adrs/README.md` (most are short).
- [ ] Run `make bootstrap && make up && make migrate && make seed && make dev`.
- [ ] Make a Studio "hello-world" PR (any small change, any package).
- [ ] Pick a story from `tracker/IMPLEMENTATION_TRACKER.xlsx → Stories` that matches your role.
- [ ] Pair-review your first PR with your onboarding buddy.
- [ ] Shadow on-call for one shift before going on rotation.

---

## Day-1 checklist for the founder/CTO

- [ ] Domain + trademark for the actual product name (Loop is a placeholder).
- [ ] Lock the Apache 2.0 license decision (see ADR-006).
- [ ] Pick the launch cloud(s) and stand up dev/staging/prod environments via `infra/terraform/envs/` (cloud-agnostic; AWS/Azure/GCP/Alibaba all supported — see `architecture/CLOUD_PORTABILITY.md`).
- [ ] Auth0 + Stripe + Sentry + Linear + PagerDuty dev tenants.
- [ ] First three engineering hires written into Sprint 0.
- [ ] Three design partners signed for closed alpha at month 4.
- [ ] Seed round narrative + data room (Series A is M9 — don't run out of runway).

---

## What to update where (cheat sheet)

| Change | Update |
|--------|--------|
| New API endpoint | `api/openapi.yaml` + `architecture/ARCHITECTURE.md` if cross-service |
| New table or column | `data/SCHEMA.md` + Alembic migration in same PR |
| New service / new package | `architecture/ARCHITECTURE.md` §2 + an ADR if non-obvious |
| New permission / role | `engineering/SECURITY.md` §6 + integration test |
| Breaking SDK type change | `data/SCHEMA.md` §9 + bump SDK major version |
| New screen or interaction | `ux/UX_DESIGN.md` + Playwright e2e |
| Discovered a hard truth about an existing decision | New ADR in `adrs/` (don't edit the old one — supersede it) |
| New eval scorer | `engineering/TESTING.md` §5 |
| New environment variable | `scaffolding/.env.example` + `engineering/HANDBOOK.md` §1 |
| Sprint plan changed | `tracker/IMPLEMENTATION_TRACKER.xlsx` + `tracker/SPRINT_0.md` if Sprint 0 |

---

## Reading order by role

**Not everyone needs to read everything.** Pick your role:

| Role | Read first (30 min) | Then (1–2h) | Deep dive (whole day) |
|------|---|---|---|
| **Founder/CTO** | README (you are here) + ARCHITECTURE.md | SPRINT_0.md, CLOUD_PORTABILITY.md | Everything except HANDBOOK §dev setup |
| **Runtime engineer** | AGENTS.md + ARCHITECTURE.md §3 | SCHEMA.md §3, TESTING.md | TurnExecutor in scaffolding/; all ADRs |
| **Infra engineer** | AGENTS.md + architecture/CLOUD_PORTABILITY.md | SCHEMA.md §5–6 (state stores), SECURITY.md | Terraform + Helm in scaffolding/; ops ADRs |
| **Voice engineer** | AGENTS.md + ARCHITECTURE.md §4.2 | ux/UX_DESIGN.md, SCHEMA.md (voice_calls table) | ADR-008 (voice as first-class), engineering/PERFORMANCE.md voice latency budget |
| **UX/Studio engineer** | AGENTS.md + ux/UX_DESIGN.md | api/openapi.yaml (contracts), SCHEMA.md (UI data shapes) | Figma design system (TBD); HANDBOOK §code review |
| **DevRel** | README + SPRINT_0.md + AGENTS.md | architecture/ARCHITECTURE.md, scaffolding/ examples | Copy templates, quickstart drafts |
| **Security/Compliance eng** | README + SECURITY.md | SCHEMA.md §8–11 (data classification), CLOUD_PORTABILITY.md | Threat model exercises; audit log design |

---

## FAQ (10+ common confusions)

### Architecture & design

**Q: Is Loop a flow editor?**  
A: No. Loop is a trace-centric debugger and operator console for agents written in Python. Builders write code in their editor; Studio shows what happened. Flow editors are deferred post-launch, if ever.

**Q: Why Python-first, not JavaScript/Go/Rust?**  
A: See ADR-001. Python dominates the AI/ML space (transformers, LangChain, etc.); agents built in other languages can integrate via MCP (Model Context Protocol). The SDK is Python; adapters for other langs come later.

**Q: How does Loop differ from Botpress?**  
A: See the parent `botpress_competitor_spec.md` (strategic context). In short: Botpress is flow-based and cloud-only; Loop is code-first, cloud-agnostic, eval-gated, and operator-focused (HITL).

**Q: Why cloud-agnostic? Isn't it harder?**  
A: Yes. See ADR-016. We do it because: (1) compliance (customers in regulated jurisdictions need on-prem), (2) data residency, (3) customer lock-in risk. The abstraction layer (ObjectStore, KMS, SecretsBackend, etc.) keeps infra code honest.

### Building agents

**Q: What does a "turn" mean?**  
A: One round trip of the agent's reasoning loop: inbound message + memory load + LLM call + tool dispatch + response + memory save + trace flush. See ARCHITECTURE.md §0 glossary.

**Q: Can I use the Loop SDK in my own code, or is it Loop-Cloud-only?**  
A: The SDK is self-hostable (open-source Apache 2.0). You can run the runtime in your own k8s cluster. Studio (the debugger) is cloud-only at launch; self-hosted Studio is month 8.

**Q: How do I add a custom tool (MCP server)?**  
A: Write an MCP server in any language. Register it in Studio or via CLI. Agents grant permission per tool. See SCHEMA.md §2.3 (mcp_servers, agent_tool_grants). Examples in scaffolding/examples/.

**Q: Where do I define agent behaviors, system prompts, tools?**  
A: All in Python code (Agent base class from the SDK). No YAML config, no drag-and-drop UI. See scaffolding/sdk-py/loop/ and examples/support_agent/.

### Data & security

**Q: Where does conversation data live?**  
A: Postgres (data plane). Encrypted at rest via per-workspace KMS key. RLS (row-level security) isolates workspaces. See SCHEMA.md §3.1 and SECURITY.md §5.

**Q: Can I bring my own Postgres / Qdrant / Redis?**  
A: Yes, if self-hosted. Helm chart allows overriding the bundled charts. See infra/helm/values.yaml. Cloud SaaS users get managed services (RDS, etc.).

**Q: How long is conversation data retained?**  
A: Indefinitely in Postgres. ClickHouse traces are hot for 90d, then archived to S3. See SCHEMA.md §6.1 (ClickHouse TTL).

**Q: How do I ensure GDPR compliance?**  
A: SCHEMA.md §9 has data_export_requests and pii_detection_rules tables. SECURITY.md §6.2 covers DSAR flow, right to deletion, data residency. SOC2 controls shipped.

### Costs & billing

**Q: How are agents charged?**  
A: Three meters: (1) platform subscription (Stripe), (2) agent-seconds (compute), (3) LLM tokens (pass-through + 5% margin). See SCHEMA.md §2.5 (costs_daily, budgets).

**Q: Can I set a hard budget cap to prevent runaway costs?**  
A: Yes. Per workspace, per agent, per conversation, per day. Hard cap rejects requests; soft cap alerts. If hit, agent gracefully degrades to a cheaper model. See SCHEMA.md §2.5, ARCHITECTURE.md §7.3.

**Q: Do I pay for a conversation if the agent never responds?**  
A: You pay for what the agent consumes: LLM tokens, tool calls, agent-seconds of runtime. If you don't use those, you don't pay. See SCHEMA.md §2.5 (costs_turn, costs_daily).

### Eval & testing

**Q: How do evals gate deployments?**  
A: You define an eval suite (cases + scorers). Deploy controller runs the suite on your new agent version vs. baseline. If score regresses, deployment blocks. See ARCHITECTURE.md §4.3, TESTING.md §2.

**Q: What if I want to override an eval gate and deploy anyway?**  
A: Allowed only by an admin role. Audit-logged. See SCHEMA.md §2.2a (audit_log) and SECURITY.md §6 (roles).

**Q: Can I use my own eval scorer (not just the 6 built-in ones)?**  
A: Yes. Write a scorer function in Python, register it. See TESTING.md §5. Custom scorers ship in your agent code.

### Deployment & operations

**Q: How do I deploy an agent?**  
A: CLI: `loop deploy --workspace <id>` uploads code, build controller creates image, k8s rolls out. Takes ~60s. See ARCHITECTURE.md §4.3, SPRINT_0.md week 4.

**Q: Can I do canary deployments (roll out to 10% of traffic)?**  
A: Yes. Deploy controller supports canary % knob. See SCHEMA.md §2.2 (deployment_events, canary_percent). Start at 10%, ramp to 100%, or rollback.

**Q: What happens if an agent crashes mid-conversation?**  
A: NATS re-delivers the event from the inbound stream (sticky routing). Runtime pod restarts, reloads memory from Postgres, hits LLM gateway request_id cache (no re-billing), resumes. See ARCHITECTURE.md §4.5.

**Q: How do I monitor my agent in production?**  
A: Studio shows real-time traces, costs, error rates. Operator inbox flags escalations. PagerDuty integration for alerts. Custom Grafana dashboards via Prometheus. See ARCHITECTURE.md §7.5.

---

## How this folder relates to the parent strategy spec

This folder (`loop_implementation/`) is the engineering team's Day-1 execution playbook. The parent `../botpress_competitor_spec.md` is the strategic context:

| Document | Scope | Owner |
|-----------|-------|-------|
| `botpress_competitor_spec.md` | Product vision, market wedges, competitive analysis, go-to-market | Founder / PM |
| `architecture/ARCHITECTURE.md` | What we're building technically | CTO + Eng #1, #2 |
| `data/SCHEMA.md` | How data flows and is stored | Eng #2 |
| `api/openapi.yaml` | Public REST contract | Arch owner + Eng #5 (Studio) |
| `adrs/` | Why we made key decisions | Team consensus |
| `ux/UX_DESIGN.md` | What Studio looks like | Eng #5 + Designer |
| `engineering/` (HANDBOOK, SECURITY, TESTING) | How we work, ship, and keep safe | Team lead + domain experts |
| `tracker/SPRINT_0.md` | What we build in the first 6 weeks | CTO + Eng leads |

**Flow:** Strategy (spec.md) → Architecture (ARCHITECTURE.md) → Implementation (scaffolding, adrs, tracker) → Delivery (CI/CD, ops).

---

## How to keep this folder up to date

**Cadence:** Every PR that touches architecture, schema, API, or security must also update the relevant doc. Out-of-band doc PRs are rare.

| Change | Update | When |
|--------|--------|------|
| New API endpoint | `api/openapi.yaml` + `architecture/ARCHITECTURE.md` | Same PR as code |
| New table or column | `data/SCHEMA.md` + Alembic migration | Same PR |
| New service / package | `architecture/ARCHITECTURE.md` §2, new ADR | Same PR |
| New permission or role | `engineering/SECURITY.md` §6 + test | Same PR |
| New UX screen | `ux/UX_DESIGN.md` + Figma | Same PR |
| Discovered bug in old decision | New ADR (never edit old ADR) | Separate PR (urgent) |
| New eval scorer | `engineering/TESTING.md` §5 | Same PR |

**Quarterly reviews:** First Monday of every quarter (all docs), CTO + tech lead + security eng. Goal: surface drift between docs and code.

**Staleness signals:**
- A doc references a Story ID (S###) that doesn't exist in the tracker.
- Two docs contradict each other on the same topic.
- A section has a TODO or TBD that's >2 weeks old.
- Code in `scaffolding/` differs from what the docs claim.

---

## Status legend

Since different docs use different status labels, here's the canonical key:

| Label | Meaning | Action |
|-------|---------|--------|
| **Draft v0.1–v0.9** | Early, incomplete, subject to major change | Read for context, don't implement yet |
| **Draft vX.0 (with date)** | Stable enough for implementation to begin | Can implement; doc changes are expected |
| **Accepted** | Reviewed by relevant team, signed off | Ship as-is; breaking changes rare |
| **Proposed** | Idea, waiting for review / ADR consensus | Read carefully; feedback likely |
| **Deprecated** | Actively replaced by newer approach | Don't use; see replacement link |

**This folder:** Most docs are "Draft v0.2" (ready to code, expect tuning). ADRs are "Accepted" or "Proposed" (see each ADR header).

---

## Document templates

When writing new docs, use these templates:

### RFC (Architecture Decision) template

```markdown
# RFC-NNN: <Short title>

**Status:** Proposed  
**Owner:** <Name> (<Role>)  
**Last updated:** YYYY-MM-DD  

## Problem statement
(1–2 paragraphs describing the gap or decision point)

## Proposed solution
(How we solve it; trade-offs)

## Alternatives considered
(Why we didn't choose X, Y, Z)

## Implementation
(Rough steps; owner; timeline estimate)

## Open questions
(Unresolved details)

## References
(Links to related docs / ADRs / issues)
```

### ADR (Architecture Decision Record) template

```markdown
# ADR-NNN: <Short title>

**Status:** Accepted | Proposed | Superseded  
**Supersedes:** (if applicable)  
**Consequences:** <1–2 sentences of impact>  

## Context
(Situation that forced the decision)

## Decision
(What we decided to do)

## Rationale
(Why this is better than alternatives)

## Consequences
(Positive and negative outcomes)

## Open questions
(Risks or unknowns)

## References
(Related docs, code, ADRs)
```

### Runbook template

```markdown
# Runbook: <Title>

**Severity:** P1 | P2 | P3  
**Owner:** <Team>  
**Last reviewed:** YYYY-MM-DD  

## Symptoms
(How you know this is happening)

## Immediate action
(First 2 steps, <5 min)

## Investigation
(Debug steps)

## Resolution
(Fix)

## Prevention
(How to avoid next time)

## Escalation
(When to page on-call manager)
```

---

## Status

| Doc | State | Last reviewed |
|-----|-------|---------------|
| AGENTS.md | v0.1 | 2026-04-29 |
| ARCHITECTURE.md | Draft v0.2 (cloud-agnostic) | 2026-04-29 |
| CLOUD_PORTABILITY.md | Draft v0.1 | 2026-04-29 |
| SCHEMA.md | Draft v0.2 (cloud-agnostic) | 2026-04-29 |
| openapi.yaml | Draft v0.2 | 2026-04-29 |
| ADRs (28 — including ADR-016 cloud-agnostic, ADR-017 RBAC, ADR-018 SSE/WS, ADR-019 chunking, ADR-020 RLS, ADR-021 sandbox runtime, ADR-022 idempotency, ADR-023 eval determinism, ADR-024 deprecation policy, ADR-025 telemetry retention, ADR-026 agent code isolation, ADR-027 eval registry license, ADR-028 pricing precision) | All Accepted | 2026-04-29 |
| UX_DESIGN.md | Draft v0.1 | 2026-04-29 |
| HANDBOOK.md | Draft v0.2 | 2026-04-29 |
| SECURITY.md | Draft v0.2 (cloud-agnostic) | 2026-04-29 |
| TESTING.md | Draft v0.1 | 2026-04-29 |
| SPRINT_0.md | Draft v0.2 | 2026-04-29 |
| TRACKER.md / tracker.json / csv/ | v0.2, AI-friendly companions of the xlsx | 2026-04-29 |
| IMPLEMENTATION_TRACKER.xlsx | v0.2, 50 stories, 7 sheets | 2026-04-29 |
| Scaffolding | Starter files, not full repo | 2026-04-29 |

These are starting points, not finals. Treat them as the team's living source of truth — and fix what's wrong.

---

## File-format philosophy

Loop's docs are written for **AI agents first, humans second**. This means:

- **Markdown is canonical** for everything. AI agents read it efficiently, humans read it cleanly, diffs are reviewable in PRs.
- **YAML / JSON are canonical** for machine-parsable formats (OpenAPI, scaffolding configs, tracker.json).
- **CSV** is provided per tracker sheet for ad-hoc data analysis and import into other tools.
- **xlsx, docx, pptx** are *exports* for human stakeholders — never edited directly. Regenerate from the canonical source.
- All large reference data (data model, ADRs, OpenAPI spec) lives in **single-file** form so agents can grep across the whole thing in one read.
