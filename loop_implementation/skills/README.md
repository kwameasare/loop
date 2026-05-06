# Loop — Skills

A **skill** is a portable, reusable instruction set that guides an AI coding agent through a single recurring task — *"add a REST endpoint,"* *"write an eval suite,"* *"propose a new ADR,"* *"triage a SEV1."*

Loop ships a single canonical set of skills that every AI tool can use. Per-platform adapters in `platforms/` translate the canonical skills into each tool's expected file layout.

---

## Why skills

The implementation docs (`architecture/`, `data/`, `engineering/`, `adrs/`, `ux/`, etc.) define **what** Loop is. The skills define **how to make a change to it without breaking anything**. They're the missing layer between *"read the docs"* and *"open a PR."*

Without skills, every AI agent reinvents the same procedure for every task — sometimes correctly, often not. With skills, every task has a known-good checklist, the right docs are read in the right order, and the PR comes out conforming to the team's conventions.

---

## How to use these skills

### As a human

Open `_base/SKILL_ROUTER.md`. It's a directory of skills with triggers. Find the skill that matches your task, open it, follow the steps.

### As an AI agent

1. **Always read `_base/SKILL_ROUTER.md` first.** It tells you which skill applies to your task.
2. Read the matched skill end-to-end before touching code.
3. Read the `required_reading` files listed in the skill's frontmatter.
4. Follow the skill's steps in order. Don't skip the checklist.
5. Verify against the skill's `definition_of_done` before opening the PR.

### As a tool integrator

The canonical skills live in this folder. Every adapter format in `platforms/` is generated **from** these files; never edit the adapters directly — re-generate them.

---

## Canonical skill format

Every skill is a single Markdown file with YAML frontmatter:

```markdown
---
name: <kebab-case-name>
description: <one-line trigger sentence — what task pulls in this skill>
when_to_use: |
  <multi-line trigger criteria>
required_reading:
  - path/to/doc.md
  - path/to/other-doc.md
applies_to: [coding|data|api|security|testing|ops|ux|devrel|meta|architecture]
owner: <role name>
last_reviewed: YYYY-MM-DD
---

# <Skill title>

## Trigger
...

## Required reading
...

## Steps
1. ...

## Definition of done
- [ ] ...

## Anti-patterns
...

## References
- ...
```

This is **identical to Anthropic Claude Skills frontmatter** — every file in this folder is a Claude Skill out of the box.

For other tools, see the respective entry under `platforms/`.

---

## Skill catalog

### Base / meta

| Skill | Trigger |
|-------|---------|
| [`_base/SKILL_ROUTER.md`](_base/SKILL_ROUTER.md) | Always — read this before any other skill. Routes you to the right one. |
| [`meta/write-pr.md`](meta/write-pr.md) | Opening a pull request. |
| [`meta/update-tracker.md`](meta/update-tracker.md) | Marking a story done, regenerating tracker companions. |
| [`meta/verify-doc-consistency.md`](meta/verify-doc-consistency.md) | After significant doc changes. |

### Architecture & decisions

| Skill | Trigger |
|-------|---------|
| [`architecture/propose-adr.md`](architecture/propose-adr.md) | Making a non-trivial technical decision. |
| [`architecture/update-architecture.md`](architecture/update-architecture.md) | Changing system architecture (containers, components, flows). |
| [`architecture/cloud-portability-check.md`](architecture/cloud-portability-check.md) | Touching any cloud-native code path. |

### Coding

| Skill | Trigger |
|-------|---------|
| [`coding/implement-runtime-feature.md`](coding/implement-runtime-feature.md) | Changes to `packages/runtime/` (TurnExecutor, reasoning loop, memory). |
| [`coding/implement-llm-gateway-change.md`](coding/implement-llm-gateway-change.md) | Changes to `packages/gateway/` (caching, providers, cost). |
| [`coding/implement-mcp-tool.md`](coding/implement-mcp-tool.md) | Adding an MCP tool (in-process or out-of-process). |
| [`coding/implement-channel-adapter.md`](coding/implement-channel-adapter.md) | Adding/modifying a channel (web, WhatsApp, Slack, etc.). |
| [`coding/implement-kb-feature.md`](coding/implement-kb-feature.md) | Changes to ingestion, chunking, retrieval, or embeddings. |
| [`coding/implement-eval-scorer.md`](coding/implement-eval-scorer.md) | Adding/modifying eval scorers. |
| [`coding/implement-studio-screen.md`](coding/implement-studio-screen.md) | Building or changing a Studio (Next.js) screen. |
| [`coding/implement-cli-command.md`](coding/implement-cli-command.md) | Adding/modifying a `loop` CLI subcommand (Go). |
| [`coding/implement-multi-agent-pattern.md`](coding/implement-multi-agent-pattern.md) | Supervisor/Pipeline/Parallel/AgentGraph orchestration. |

### Data

| Skill | Trigger |
|-------|---------|
| [`data/add-postgres-migration.md`](data/add-postgres-migration.md) | DDL change to control- or data-plane Postgres. |
| [`data/add-pydantic-type.md`](data/add-pydantic-type.md) | Modifying a public SDK type. |
| [`data/update-schema.md`](data/update-schema.md) | Updating `data/SCHEMA.md` after any schema change. |

### API

| Skill | Trigger |
|-------|---------|
| [`api/add-rest-endpoint.md`](api/add-rest-endpoint.md) | Adding a REST endpoint (FastAPI + OpenAPI + tests). |
| [`api/add-streaming-event.md`](api/add-streaming-event.md) | Adding a new SSE/WS event type. |
| [`api/update-openapi.md`](api/update-openapi.md) | Changing the OpenAPI spec (any schema or path). |

### Security

| Skill | Trigger |
|-------|---------|
| [`security/add-error-code.md`](security/add-error-code.md) | Introducing a new `LOOP-XX-NNN` code. |
| [`security/update-threat-model.md`](security/update-threat-model.md) | New attack surface (channel, integration, public endpoint). |
| [`security/add-audit-event.md`](security/add-audit-event.md) | Action that should appear in the audit log. |
| [`security/secrets-kms-check.md`](security/secrets-kms-check.md) | Touching secrets, keys, or encryption. |

### Testing

| Skill | Trigger |
|-------|---------|
| [`testing/write-unit-test.md`](testing/write-unit-test.md) | Default for any code change. |
| [`testing/write-integration-test.md`](testing/write-integration-test.md) | Touching a public API path. |
| [`testing/write-e2e-test.md`](testing/write-e2e-test.md) | New top-level user journey. |
| [`testing/write-eval-suite.md`](testing/write-eval-suite.md) | Authoring or modifying agent eval suites. |
| [`testing/perf-check.md`](testing/perf-check.md) | Hot path or load-relevant change. |

### Observability

| Skill | Trigger |
|-------|---------|
| [`observability/add-otel-span.md`](observability/add-otel-span.md) | Adding tracing to a code path. |
| [`observability/add-metric.md`](observability/add-metric.md) | Adding a Prometheus metric. |
| [`observability/add-runbook.md`](observability/add-runbook.md) | Codifying response to a recurring failure. |

### UX / Studio

| Skill | Trigger |
|-------|---------|
| [`ux/design-studio-surface.md`](ux/design-studio-surface.md) | New or redesigned Studio screen, workflow, or high-impact interaction. |
| [`ux/review-studio-ux.md`](ux/review-studio-ux.md) | UX/UI review against the canonical target standard. |
| [`ux/add-studio-component.md`](ux/add-studio-component.md) | Reusable Studio component or target-standard primitive. |
| [`ux/add-design-token.md`](ux/add-design-token.md) | Color, spacing, typography, motion, density, or status token. |
| [`ux/write-ui-copy.md`](ux/write-ui-copy.md) | Any user-facing string. |

### Ops

| Skill | Trigger |
|-------|---------|
| [`ops/deploy-agent-version.md`](ops/deploy-agent-version.md) | Promoting an agent version to canary or prod. |
| [`ops/rollback-deploy.md`](ops/rollback-deploy.md) | Reverting a bad deploy. |
| [`ops/triage-incident.md`](ops/triage-incident.md) | SEV1/SEV2 acknowledgement and mitigation. |
| [`ops/dr-drill.md`](ops/dr-drill.md) | Running a scheduled DR drill. |

### DevRel

| Skill | Trigger |
|-------|---------|
| [`devrel/write-docs-page.md`](devrel/write-docs-page.md) | Adding a docs site page. |
| [`devrel/publish-mcp-server.md`](devrel/publish-mcp-server.md) | Publishing an MCP server to the Loop Hub. |

---

## Per-platform adapters

The skills folder is the source of truth. Per-platform adapters wrap the same content for tools that expect specific file layouts:

| Platform | Adapter location | What it does |
|----------|------------------|---------------|
| **Anthropic Claude Skills** (Claude Code, Claude Desktop, Claude Agent SDK) | `platforms/claude/README.md` | Each `*.md` here is already a Claude Skill — no transformation needed. |
| **OpenAI Codex / Agents SDK / ChatGPT custom GPTs** | `platforms/codex/README.md` | Single system-prompt file referencing the canonical skills. |
| **GitHub Copilot** (Chat + Coding Agent) | `platforms/github-copilot/copilot-instructions.md` + `prompts/*.prompt.md` | Repo-level + per-skill prompt files. |
| **Cursor** | `platforms/cursor/.cursorrules` + `rules/*.mdc` | Root rules + per-skill rule files. |
| **Aider** | `platforms/aider/CONVENTIONS.md` | Single conventions file. |
| **Windsurf / Codeium** | `platforms/windsurf/.windsurfrules` | Single rules file. |
| **Continue.dev** | `platforms/continue/rules/*.md` | Per-skill rule files in the Continue rules folder. |
| **Generic / unknown** | `AGENTS.md` (parent folder) | The standard AGENTS.md spec — every modern AI tool reads it. |

Install instructions per platform are in each adapter's README.

---

## Skill maintenance

- Treat skills as code. They live in version control; PRs follow the same review process.
- Update the skill **in the same PR** as the related code change if the change makes the skill stale.
- Re-review each skill quarterly. Update `last_reviewed` in the frontmatter.
- A skill that's never been used is a candidate for deletion. Track usage informally — when a PR cites a skill, note it in the skill's References.

---

## Adding a new skill

1. Pick the right category folder.
2. Copy `engineering/templates/SKILL_TEMPLATE.md` (or another existing skill) as a starting point.
3. Fill out frontmatter + Trigger + Required reading + Steps + Definition of done + Anti-patterns + References.
4. Add an entry to this README's catalog table.
5. Add an entry to `_base/SKILL_ROUTER.md`.
6. Re-run `tools/build_platform_adapters.py` to regenerate adapter files.
7. Open a PR; tag the relevant module owner.
