# Sprint 0 — Bootstrap (Weeks 1–6)

**Goal:** by end of week 6, a 5-engineer team can ship code into a staging cluster that runs a real (toy) agent end-to-end on web chat, with traces visible in Studio. No customers yet. Foundations only.

**Working assumption:** founding eng hires #1 (runtime), #2 (infra), #4 (obs/eval), #5 (studio) starting day 1; #3 (voice) starts week 3; #6 DevRel and #7 channel integrations start week 5.

---

## Week 1 — Foundations

| Owner | Task |
|-------|------|
| CTO | Repo init, CODEOWNERS, branch protection, CI skeleton |
| CTO | Cloud accounts on chosen launch cloud(s) — dev/staging/prod environments via Terraform (see `architecture/CLOUD_PORTABILITY.md`; the platform itself is cloud-agnostic) |
| CTO | Auth0 dev tenant, Stripe test, Sentry, Linear, PagerDuty |
| Eng #1 | Runtime package skeleton: `Agent` base class, `AgentEvent`, `TurnExecutor` shell |
| Eng #2 | docker-compose.yml: Postgres + Redis + Qdrant + NATS + MinIO |
| Eng #2 | Initial k8s manifests for dev cluster (k3d) |
| Eng #4 | OTel collector + ClickHouse local stack |
| Eng #5 | Next.js app skeleton, Tailwind + shadcn/ui setup |
| All | Read ARCHITECTURE.md + SCHEMA.md + HANDBOOK.md, file 5 doc PRs |

**Demo at week end:** `make dev` brings up the full local stack; runtime accepts a stub HTTP request and echoes; a Studio "hello world" page.

---

## Week 2 — Core types & first turn

| Owner | Task |
|-------|------|
| Eng #1 | Pydantic models: AgentEvent, AgentResponse, ContentPart, TurnEvent, ToolCall (locked, SDK-public) |
| Eng #1 | LLM gateway client (HTTP) — first wire to OpenAI + Anthropic with streaming |
| Eng #1 | TurnExecutor reasoning loop with single-iteration LLM call (no tools yet) |
| Eng #2 | Postgres migrations for control-plane + data-plane tables |
| Eng #2 | Redis session-memory KV with TTL |
| Eng #4 | Span generation in TurnExecutor, OTLP export to local ClickHouse |
| Eng #5 | Studio: agents-list page (read from cp-api stub) |

**Demo:** local CLI sends a prompt → runtime calls OpenAI → response logged + traced. Visible in Studio's conversations table.

---

## Week 3 — Tools, MCP, KB v0

| Owner | Task |
|-------|------|
| Eng #1 | MCP client integration; auto-MCP decorator for Python functions |
| Eng #1 | TurnExecutor multi-iteration loop with parallel tool dispatch |
| Eng #1 | Memory loader/persister (user + session tiers) |
| Eng #2 | Firecracker-via-Kata k8s runtime class, prewarmed pool |
| Eng #2 | Tool dispatcher service + NATS subjects |
| Eng #4 | KB engine v0: PDF ingest + Qdrant write + hybrid retrieval (BM25 placeholder + vector) |
| Eng #5 | Studio: agent-detail conversations panel + basic message stream |
| Eng #3 (start) | Spec the voice pipeline; PoC LiveKit + Deepgram + ElevenLabs in isolation |

**Demo:** the runtime calls a real out-of-process MCP server (local Stripe sandbox tool), KB query returns cited chunks, Studio shows the trace.

---

## Week 4 — Channels v0, eval harness shell

| Owner | Task |
|-------|------|
| Eng #1 | Channel layer abstraction; web channel adapter (REST + SSE out) |
| Eng #1 | Slack channel adapter (Block Kit, slash command, threaded) |
| Eng #2 | cp-api: auth0 OIDC flow, workspace mgmt, API keys, deploys |
| Eng #2 | Deploy controller v0: takes a code artifact, builds image, applies k8s |
| Eng #4 | Eval harness skeleton: scorers (LLM judge + regex + json schema + tool-call assert + latency_le + cost_le) |
| Eng #4 | `loop eval run` CLI entry-point |
| Eng #5 | Studio: trace waterfall (basic), span detail tabs |

**Demo:** end-to-end deploy: `loop deploy` → cp-api → controller → live in cluster → web widget chat works → trace shows in Studio.

---

## Week 5 — WhatsApp, alpha sign-up flow, hire #6/#7

| Owner | Task |
|-------|------|
| Eng #1 | WhatsApp channel adapter (Cloud API direct first) |
| Eng #1 | Streaming response polish: tool_call_start/end events on the SSE stream |
| Eng #2 | Stripe billing wire-up (test mode), usage rollup job nightly |
| Eng #4 | Eval harness: production-replay capture (failed turns last 7d) |
| Eng #5 | Studio: cost dashboard v0 (workspace MTD, per-agent breakdown) |
| Eng #5 | Studio: deploy timeline + rollback button |
| Eng #6 (start) | Examples repo: support-agent, shopping-assistant; first docs site pass |
| Eng #7 (start) | Plan SMS (Twilio) + Email (SES) channel adapters |
| Sec eng | Threat model walk-through with team (using `engineering/SECURITY.md`) |

**Demo:** alpha signup → `loop init` → push code → deploy → WhatsApp message ↔ bot reply. Studio shows the trace + cost.

---

## Week 6 — Polish, design partner onboarding, MVP cut

| Owner | Task |
|-------|------|
| Eng #1 | Hard caps + graceful degrade rule wiring; budget pre-flight at gateway |
| Eng #1 | HITL: takeover endpoint + operator inbox queue plumbing |
| Eng #2 | Helm chart skeleton for self-host (deferred for full feature parity to month 7) |
| Eng #4 | Eval-gated deploy: deploy controller blocks `prod` promotion if eval regresses |
| Eng #5 | Studio: operator inbox MVP (queue + takeover button + composer) |
| Eng #6 | Quickstart docs: 60-second local dev, first-deploy walkthrough |
| Eng #3 | Voice MVP target: web-RTC echo agent (caller → loop runtime → caller, sub-1.5s) |
| All | First 3 design partners onboarded; weekly office hour established |

**Demo (sprint 0 close):**
- A design partner deploys a real agent, talks to it on web + Slack + WhatsApp.
- Eval suite gates the next deploy (intentional regression in a candidate version blocks promotion).
- Voice echo demo proves the pipeline works end-to-end (still rough latency).
- Studio shows traces, costs, replays.

---

## Task dependencies & critical path

Explicit blocking relationships (story IDs mapped to week):

```
Week 1
├── S001 (CTO: repo init)                  [blocking: S002, S003, S005, S010]
├── S002 (Eng#2: docker-compose stack)   [blocking: S004, S006, S008]
├── S003 (Eng#1: runtime skeleton)        [blocking: S006, S009]
├── S004 (Eng#4: OTel + ClickHouse)       [blocking: S011]
├── S005 (Eng#5: Next.js + Tailwind)      [blocking: S012]
└── S050 (All: read docs, file 5 PRs)     [no blocking]

Week 2
├── S006 (Eng#1: Pydantic models)         [blocking: S009, S014, S015]
├── S007 (Eng#2: Postgres migrations)     [blocking: S009]
├── S008 (Eng#4: span generation)         [blocking: S016]
└── S009 (Eng#5: agents-list page)        [depends: S003, S006; blocking: S017]

Week 3
├── S010 (Eng#1: MCP integration)         [blocking: S016]
├── S011 (Eng#1: multi-turn loop)         [blocking: S016]
├── S012 (Eng#2: Firecracker pool)        [blocking: S018]
├── S013 (Eng#2: tool dispatcher)         [blocking: S016]
├── S014 (Eng#4: KB v0)                   [blocking: S019]
├── S015 (Eng#5: conversation panel)      [blocking: S019]
└── S054 (Eng#3 start: voice spec PoC)    [no blocking this sprint]

Week 4–6: No critical dependencies; parallel work.
```

**Critical path:** S001 → S002 → S006 → S009 → S017 (end-to-end demo at week end).

---

## Capacity calculation & allocation

**Total team:** 5 engineers × 6 weeks × 30 hours/week (sprint capacity, accounting for meetings + async) = **900 hours available.**

**Holiday/PTO buffer:** 1 day per engineer per sprint (6 engineers × 1 day × 6 weeks = 36 hours). Subtract from capacity: **900 - 36 = 864 hours allocated.**

**Hour allocation by week & story:**

| Story | Eng | W1 hrs | W2 hrs | W3 hrs | W4–6 hrs | Total | Notes |
|-------|-----|--------|--------|--------|---------|-------|-------|
| S001 (repo init) | CTO | 20 | 5 | 2 | 3 | 30 | One-time setup |
| S002 (docker-compose) | #2 | 25 | 5 | 0 | 0 | 30 | Done week 1; maintenance week 2+ |
| S003 (runtime skeleton) | #1 | 20 | 10 | 5 | 5 | 40 | Grows across sprint |
| S004 (OTel stack) | #4 | 25 | 5 | 5 | 5 | 40 | Baseline; tuning weeks 3+ |
| S005 (Next.js) | #5 | 20 | 5 | 0 | 0 | 25 | Boilerplate |
| S006 (Pydantic models) | #1 | 0 | 30 | 0 | 0 | 30 | Critical path; SDK-public |
| S007 (migrations) | #2 | 0 | 20 | 5 | 0 | 25 | Must be backwards-compat |
| S008 (span gen) | #4 | 0 | 20 | 5 | 5 | 30 | Tracing foundation |
| S009 (agents-list UI) | #5 | 0 | 30 | 0 | 0 | 30 | Blocked on S006 |
| S010 (MCP client) | #1 | 0 | 0 | 30 | 0 | 30 | Week 3 focus |
| S011 (multi-turn) | #1 | 0 | 0 | 25 | 10 | 35 | Core loop; may slip into W4 |
| S012 (Firecracker) | #2 | 0 | 0 | 20 | 10 | 30 | Deferred; low priority W3 |
| S013 (tool dispatcher) | #2 | 0 | 0 | 25 | 5 | 30 | Enables W3 demo |
| S014 (KB v0) | #4 | 0 | 0 | 30 | 5 | 35 | Embedding + retrieval |
| S015 (conv panel) | #5 | 0 | 0 | 30 | 5 | 35 | UI complexity high |
| S016 (trace waterfall) | #5 | 0 | 0 | 0 | 30 | 30 | Main W4–6 deliverable |
| S017 (end-to-end demo) | All | 0 | 0 | 0 | 20 | 20 | Integration effort |
| S018 (channel layer) | #1 | 0 | 0 | 0 | 30 | 30 | Web, Slack, WhatsApp |
| S019 (eval harness) | #4 | 0 | 0 | 0 | 40 | 40 | Six scorers only |
| S050 (doc reading) | All | 10 | 0 | 0 | 0 | 10 | W1 only |
| S054 (voice PoC) | #3 | 0 | 0 | 20 | 10 | 30 | Starts W3; not critical path |
| **Eng #6 (DevRel, W5+)** | #6 | 0 | 0 | 0 | 30 | 30 | Examples, docs, quickstart |
| **Eng #7 (Channels, W5+)** | #7 | 0 | 0 | 0 | 40 | 40 | SMS, Email channel adapters |

**Grand total allocated:** 795 hours. **Buffer:** 69 hours (8% margin for unknowns). **Status:** Under budget; allocation is feasible.

**Bottleneck analysis:**
- Eng #1 (runtime): highest load W3 (85 hrs). If slip, cascades to demo. Mitigation: CTO shadows W2–3; pair programming.
- Eng #5 (Studio): 95 hrs across sprint. Mitigation: use component library (shadcn) heavily; no custom design.
- Eval harness (S019): 40 hrs late in sprint. Risk if W4 slips. Mitigation: scorers are simple; parallelize with S018.

---

## Risk mitigations per week

| Week | Risk | Probability | Owner | Mitigation |
|------|------|-------------|-------|-----------|
| **W1** | Docker-compose flaky on macOS | Medium | Eng #2 | Test on Linux + macOS in CI from day 1; OrbStack on dev macs |
| **W1** | Auth0 onboarding delays CTO | Medium | CTO | Pre-CTO sets up dev tenant in week 0 (before sprint starts) |
| **W1** | Git branching / CI confusion slows down | Low | CTO | HANDBOOK has branch + CI checklists; daily standup review |
| **W2** | Pydantic model thrash (SDK-public, hard to change) | High | Eng #1 | Design in depth in week 1; doc review before code; test migration path |
| **W2** | Postgres migrations don't reverse correctly | Medium | Eng #2 | Write down migrations in CHANGELOG.md; test down() on every commit |
| **W3** | Voice PoC drags Eng #3, blocks other work | Medium | Eng #3 | Voice is NOT critical path; time-box PoC to 20 hrs; escalate if stuck |
| **W3** | MCP client complexity higher than expected | Medium | Eng #1 | ADR-003 (MCP as universal tool ABI) + architecture/ARCHITECTURE.md §3 has detailed spec; start with trivial local server |
| **W4–6** | Trace waterfall rendering 100+ spans slowly | Medium | Eng #5 | Virtualization library (react-window); test perf with synthetic 200-span trace in W3 |
| **W4–6** | Eval harness scorers don't generalize | Low | Eng #4 | Scorers are simple; test each against 3 scenarios; reserve 5 hrs for iteration |
| **W4–6** | Design partners unavailable for onboarding | Low | DevRel | Recruit by week 4; incentivize (free Pro tier, swag); have backup internal users |

---

## Scope cut decision tree (if we slip)

**If timeline pressure mounts, cut in this order (preserve critical path):**

1. **First cut (save 80 hrs):** Firecracker pool (S012) → use gVisor containers instead (simpler, less isolated, but works for MVP). Voice PoC (S054) → echo demo deferred to month 5.
2. **Second cut (save 120 hrs):** Eval harness (S019) → ship with 3 scorers instead of 6. KB v0 (S014) → defer to month 7, agents ship without knowledge base.
3. **Third cut (save 150 hrs, danger zone):** Trace waterfall (S016) → ship with list view only, no waterfall. Operator inbox (S017) → defer take-over to month 7, HITL queue is read-only.

**Never cut:** Runtime skeleton, Pydantic models, migrations, agents-list UI, end-to-end demo (these are the critical path).

---

## Design-partner onboarding checklist (week 6)

- [ ] 3 partners signed; NDA + product feedback agreement
- [ ] Workspace created + API key provisioned for each
- [ ] `loop init` walkthrough completed with each
- [ ] Reference agent deployed to each workspace
- [ ] Weekly 30-min office hour scheduled (Fridays 10am PT)
- [ ] Feedback form shared (Typeform / Google Form); weekly digest
- [ ] Slack channel created for partner communication
- [ ] Support rotation assigned (each engineer + PM shadows once)

---

## Sprint 0 retrospective template

**Run at week 6 close. Owner: CTO.**

```markdown
# Sprint 0 Retrospective

**Date:** 2026-06-09  
**Attendees:** CTO, Eng #1–7, Designer, PM  

## What went well?
- (List 3–5 things that accelerated us)
- Example: "Docker-compose stack was more stable than expected; only 2 CI flakes."
- Example: "Design partners onboarded on time and had actionable feedback."

## What didn't go well?
- (List 3–5 blockers or surprises)
- Example: "Pydantic model thrash (SDK-public) caused 3 design revisions; cost 10 extra hrs."
- Example: "Voice PoC underestimated; Deepgram latency was 250ms, not 150ms promised."

## What should we change?
- (Concrete action items for next sprint)
- Example: "Freeze SDK types earlier; design-review in week 0, not week 1."
- Example: "Add latency benchmarks to the PoC template; don't trust vendor claims."

## Metrics
- Capacity used: XXX / 900 hours (YY%)
- Stories completed: X / Y (on track? ahead? behind?)
- Bugs found in production by design partners: N
- Eval regressions: N (target: 0)
- Deploy time: avg XXms (target: ≤60s)

## Action items for sprint 1
- [ ] Item 1 (owner, due date)
- [ ] Item 2 (owner, due date)
```

---

## Eng #6 (DevRel) scope & owner roles (week 5+)

**Starting week 5, Eng #6 (DevRel) joins. Role is under-specified; clarify below:**

| Task | Primary | Secondary | Hours/week | Notes |
|------|---------|-----------|-----------|-------|
| **Quickstart docs** | Eng #6 | Eng #1 | 10 | "Deploy your first agent in 60s"; examples for all channels |
| **Examples repo** | Eng #6 | Eng #1 | 8 | support-agent, shopping-assistant; eval suites for each |
| **Blog posts** | Eng #6 | PM | 5 | "Why traces matter", "How to evaluate agents", etc. |
| **YouTube videos** (optional) | Eng #6 | Designer | 2 | 60-second demo of tracing, evaluation, HITL |
| **Community Slack** | Eng #6 | PM | 3 | Answer questions, triage feedback |
| **Design-partner onboarding** | Eng #6 | CTO | 2 | Weekly office hour, collect feedback, synthesize |

**Total: ~30 hrs/week. Eng #6 is 100% allocated to DevRel; not a general engineer.**

---

## Sprint 0 Definition of Done (the bar to call it shipped)

- [ ] `make dev` works on a clean machine in ≤ 10 minutes.
- [ ] CI < 12 min for `push → unit + integration + lint`.
- [ ] One reference agent deployable via `loop deploy`, replies on web and Slack.
- [ ] WhatsApp adapter in sandbox mode passes integration tests.
- [ ] At least one full conversation visible in Studio with full trace.
- [ ] Eval suite blocks a deploy at least once in CI.
- [ ] Three design partners onboarded; weekly office hour scheduled.
- [ ] Architecture, schema, API spec, ADRs, security, testing docs all merged on `main` and reviewed by every engineer.
- [ ] On-call rotation set up; PagerDuty drill performed.
- [ ] Voice echo demo works end-to-end (latency target deferred to month 5).

---

## Risks & mitigation (Sprint 0)

| Risk | Mitigation |
|------|------------|
| Hire #1 doesn't ship the runtime in time | CTO writes the first draft of `TurnExecutor` and the loop in week 1; eng #1 inherits |
| docker-compose stack flaky on macOS | Test on Linux + macOS in CI from week 2; use OrbStack on dev macs |
| Auth0 onboarding delays | Pre-CTO sets up the dev tenant in week 0 |
| Voice pipeline drags Eng #3 | Voice is *not* on the sprint-0 critical path; only echo demo target |
| Eval harness scope creep | Ship 6 scorers only; defer the rest to month 7 |
| Design partners want flow editor | Politely decline; point at code-first quickstart |

---

## Sprint cadence after Sprint 0

- 2-week sprints starting week 7.
- Sprint planning Monday, retro Friday before close.
- Demo Friday (open to design partners).
