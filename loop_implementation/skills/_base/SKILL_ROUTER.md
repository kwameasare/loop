---
name: skill-router
description: Base skill — read this first. Routes you to the specific skill that fits your current task. Every other skill depends on this one being read first.
when_to_use: |
  ALWAYS, before any other skill. Read this first whenever you receive a new task.
  This skill is your decision tree for picking the right specific skill.
required_reading:
  - README.md
  - AGENTS.md
  - architecture/ARCHITECTURE.md
  - engineering/GLOSSARY.md
applies_to: meta
owner: CTO
last_reviewed: 2026-04-29
---

# Skill router (read this first)

## Why this skill exists

Every other skill assumes you've read this one. It is the deterministic map from "task description" → "specific skill to apply." Without it, agents reinvent the wheel and miss conventions.

---

## How to use this skill

1. Read this file end-to-end (it is short).
2. Identify your task in the Task → Skill table below.
3. **Run the tracker lifecycle PRE step (claim the story).** See "Tracker lifecycle protocol" below. If you skip this, the rest of the team can't see what you're doing.
4. Open the matched specific skill. Read it end-to-end before touching code.
5. Read every doc listed in that skill's `required_reading`.
6. Follow that skill's Steps in order.
7. Verify against the skill's Definition of done.
8. **Run the tracker lifecycle POST step (close the story)** as the LAST commit of your PR.
9. If your task spans multiple skills, run them in order and combine their checklists.
10. If no skill matches, **stop**. Add a TODO note to `tracker/TRACKER.md` and request human guidance. Do not improvise.

---

## Canonical reading order before any task

These three files are read **every** time, no matter the task:

1. `README.md` — folder index + status.
2. `engineering/GLOSSARY.md` — vocabulary; cite this if a term is ambiguous.
3. `AGENTS.md` — entry-point conventions, what's allowed without asking.

Then, the skill-specific `required_reading`.

---

## Task → Skill decision table

| Task description | Skill |
|------------------|-------|
| Modify the agent runtime (TurnExecutor, reasoning loop, hard caps) | `coding/implement-runtime-feature.md` |
| Change LLM gateway behavior (caching, providers, cost) | `coding/implement-llm-gateway-change.md` |
| Add or modify an MCP tool | `coding/implement-mcp-tool.md` |
| Add or modify a channel (web, Slack, WhatsApp, voice, …) | `coding/implement-channel-adapter.md` |
| Touch RAG / KB ingestion / retrieval / embeddings | `coding/implement-kb-feature.md` |
| Add a new eval scorer | `coding/implement-eval-scorer.md` |
| Build or change a Studio screen / component | `coding/implement-studio-screen.md` |
| Add a `loop` CLI subcommand (Go) | `coding/implement-cli-command.md` |
| Build supervisor / pipeline / agent-graph orchestration | `coding/implement-multi-agent-pattern.md` |
| Add a Postgres migration | `data/add-postgres-migration.md` |
| Modify a public Pydantic type | `data/add-pydantic-type.md` |
| Update `data/SCHEMA.md` (any backend) | `data/update-schema.md` |
| Add a REST endpoint | `api/add-rest-endpoint.md` |
| Add a streaming event type | `api/add-streaming-event.md` |
| Edit `api/openapi.yaml` | `api/update-openapi.md` |
| Introduce a new error code | `security/add-error-code.md` |
| Update threat model / new attack surface | `security/update-threat-model.md` |
| Add an audit-loggable event | `security/add-audit-event.md` |
| Touch secrets / keys / encryption | `security/secrets-kms-check.md` |
| Write a unit test | `testing/write-unit-test.md` |
| Write an integration test | `testing/write-integration-test.md` |
| Write a Playwright/journey e2e test | `testing/write-e2e-test.md` |
| Author or modify an eval suite | `testing/write-eval-suite.md` |
| Hot-path / load-relevant change | `testing/perf-check.md` |
| Add an OTel span | `observability/add-otel-span.md` |
| Add a Prometheus metric | `observability/add-metric.md` |
| Codify response to a recurring failure | `observability/add-runbook.md` |
| Add a Studio React component | `ux/add-studio-component.md` |
| Add a design token (color, spacing, typography) | `ux/add-design-token.md` |
| Author user-facing copy (UI, errors, docs) | `ux/write-ui-copy.md` |
| Promote an agent version to canary or prod | `ops/deploy-agent-version.md` |
| Roll back a bad deploy | `ops/rollback-deploy.md` |
| Triage a SEV1/SEV2 incident | `ops/triage-incident.md` |
| Run a scheduled DR drill | `ops/dr-drill.md` |
| Make a non-trivial technical decision | `architecture/propose-adr.md` |
| Change system architecture (container, component, flow) | `architecture/update-architecture.md` |
| Touch any cloud-native code | `architecture/cloud-portability-check.md` |
| Open a PR | `meta/write-pr.md` (always; comes after the primary skill) |
| Mark a story done / regenerate tracker / claim a fresh story | `meta/update-tracker.md` |
| Pick up an `In progress` story another agent abandoned | `meta/resume-task.md` |
| Cross-doc consistency check after large changes | `meta/verify-doc-consistency.md` |
| Write a docs page | `devrel/write-docs-page.md` |
| Publish an MCP server to the Loop Hub | `devrel/publish-mcp-server.md` |

---

## Multi-skill tasks

Most tasks span at least two skills:

- *"Add a `/v1/budgets/{id}/snooze` endpoint"* → `api/add-rest-endpoint.md` + `data/add-postgres-migration.md` (if it touches DB) + `security/add-audit-event.md` + `testing/write-integration-test.md` + `meta/write-pr.md`.
- *"Implement the operator inbox"* → `coding/implement-studio-screen.md` + `api/add-rest-endpoint.md` + `data/add-pydantic-type.md` + `ux/add-studio-component.md` + `ux/write-ui-copy.md` + `meta/write-pr.md`.
- *"Add Discord channel"* → `coding/implement-channel-adapter.md` + `data/add-postgres-migration.md` (if it adds tables) + `security/secrets-kms-check.md` + `testing/write-integration-test.md` + `testing/write-e2e-test.md`.
- *"Move from pgvector to a sharded Qdrant cluster"* → `architecture/propose-adr.md` (new ADR) + `architecture/update-architecture.md` + `coding/implement-kb-feature.md` + `data/update-schema.md` + `testing/perf-check.md`.

When skills overlap, follow them in this order:

1. **Decision** (architecture/propose-adr) if the change is non-trivial.
2. **Data** (data/* skills) — schema must settle first.
3. **API** (api/* skills) — public contract.
4. **Coding** (coding/* skills) — implementation.
5. **Testing** (testing/* skills) — every layer.
6. **Security** + **Observability** (cross-cutting; threaded through coding).
7. **UX** (ux/* skills) — once data + API are stable.
8. **Meta** (meta/* skills) — PR + tracker last.

---

## When no skill applies

If your task does not match any skill:

1. Check if it's actually multiple sub-tasks that each have a skill (most tasks split this way).
2. Check if it's an operational task that should be a runbook (`engineering/RUNBOOKS.md`) rather than a skill.
3. Check if it's a one-off or recurring. One-off → propose the change directly with a TODO. Recurring → propose a new skill (see "Adding a new skill" in `skills/README.md`).

Default: **do not improvise**. Open a TODO and request guidance.

---

## Tracker lifecycle protocol (mandatory)

The tracker is how the team coordinates. **Every task touches it three times:**

### BEFORE — claim or resume the story

Before reading any code or writing any code:

1. Find the story in `tracker/TRACKER.md`. If none exists, create one (`meta/update-tracker.md` §"Add a new story"). Don't start work without a story.
2. **Check existing claims.** If the story is already `In progress` (someone else's Owner), do NOT double-claim:
   - If the **Heartbeat** in the structured Notes is **fresh** (< 4 h ago for AI agents; < 7 d for humans), pick a different story or wait — the Owner is still active.
   - If **stale** (> threshold) **or you were explicitly handed the task**, apply **`meta/resume-task.md`** instead of this BEFORE step. That skill walks you through reading the partial work, syncing the branch, and resuming from the last completed checkpoint.
   - If the Notes cell is empty / non-structured / from a previous protocol version, follow the orphan-recovery flow in `meta/resume-task.md` §6.
3. (Fresh claim path only.) Edit `tools/build_tracker.py` to set status `In progress` + Owner + the structured Notes block (Branch, Skill, Last step, Heartbeat, Open questions, Blockers, Commits). See `meta/update-tracker.md` §"Canonical Notes-cell format."
4. Regenerate the four output companions:
   ```bash
   python tools/build_tracker.py
   python tools/tracker_to_machine.py
   python scripts/recalc.py tracker/IMPLEMENTATION_TRACKER.xlsx
   ```
5. Either open a separate `chore(tracker): claim S0NN` PR (merge fast) OR make this the FIRST commit of your feature branch.
6. **Push immediately.** A claim with no pushed branch can't be resumed by another agent — always `git push` so a successor can fetch your work.

### DURING — heartbeat checkpoints + status changes

**Mandatory for tasks > 1 h:** issue a `chore(tracker): checkpoint S0NN step <N>/<M> — <one-liner>` commit at every numbered skill step or ~30 min, whichever comes first. Push after each. Update the Notes cell with the new `Last step:` and `Heartbeat:` so a successor agent can resume cleanly if you get rate-limited / disconnected.

Only flip status mid-task if:
- **Blocked** → flip status to `Blocked`, populate `Blockers:` in structured Notes, hand back to queue.
- **Scope changed** → close + replace the story, or split it.
- **Handing off** → flip to `Handing off`, blank Owner, push.

Never leave uncommitted work overnight or before a pause. `chore(tracker): wip S0NN — paused at <reason>` is acceptable.

### AFTER — close the story

Before opening the PR for review (not after merge):

1. Edit `tools/build_tracker.py` to set status `Done` and add `PR #<number> (<date>)` to the notes cell.
2. Regenerate the four output companions.
3. Make this the **LAST commit** of your feature PR. Title: `chore(tracker): close S0NN`.
4. Your PR now contains: claim → work → close. Full lifecycle in one branch.

If the merged PR is later rolled back, open `chore(tracker): reopen S0NN` immediately.

**Full details + status vocabulary + automation roadmap:** `meta/update-tracker.md`.

---

## Hard rules every skill assumes

These rules cut across every skill. Violate any and the PR is rejected:

1. **Cloud-portability.** Never import a cloud SDK directly from `packages/runtime/`, `packages/gateway/`, or `packages/sdk-py/`. Go through the abstractions in `architecture/CLOUD_PORTABILITY.md` §4. (See `architecture/cloud-portability-check.md`.)
2. **Tenant isolation.** Every database-touching change must respect Postgres RLS. Every test must include a cross-tenant negative case.
3. **Docs-with-code.** Any change that touches architecture, schema, ADRs, or the API spec updates the relevant doc **in the same PR**.
4. **Definition of done.** Code merged is not done. See `engineering/HANDBOOK.md` §9.
5. **Conventional Commits.** PR titles. Always.
6. **Errors have codes.** Every new error class gets a `LOOP-XX-NNN` per `engineering/ERROR_CODES.md`.
7. **Trace everything.** Every async operation gets an OTel span.
8. **Secrets.** Never in code, env vars in containers, logs, or commits. Vault only.
9. **Eval-gating.** Runtime PRs run the eval suite; regressions block merge.
10. **Performance budgets.** Hot-path PRs run the bench rig; regressions ≥10% block merge.
11. **Tracker lifecycle.** Every PR contains a tracker claim (first commit) and a tracker close (last commit) — see "Tracker lifecycle protocol" above. PRs without tracker touches are rejected.
12. **Resumption-friendly work.** Long tasks (> 1 h) commit checkpoints every numbered step / 30 min. Never leave uncommitted work. Notes cell follows the canonical structured format so any agent (different vendor, different shift) can resume from `meta/resume-task.md`.

---

## When skills conflict with each other

Priority order: **ADRs > GLOSSARY > ARCHITECTURE > SCHEMA > openapi.yaml > skills > everything else.**

If two skills disagree, the higher-priority canonical doc wins. Open a PR to fix the disagreement in the lower-priority doc.

---

## References

- [`README.md`](../../README.md) — folder index.
- [`AGENTS.md`](../../AGENTS.md) — agent entry conventions.
- [`engineering/GLOSSARY.md`](../../engineering/GLOSSARY.md) — vocabulary.
- [`adrs/README.md`](../../adrs/README.md) — decision log (28 ADRs).
- [`engineering/HANDBOOK.md`](../../engineering/HANDBOOK.md) — coding conventions.
- [`engineering/RUNBOOKS.md`](../../engineering/RUNBOOKS.md) — operational procedures.
