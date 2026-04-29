# Loop — Engineering Handbook

**Status:** Draft v0.1
**Owner:** CTO
**Audience:** every engineer on the team

This is how we build software at Loop. It is opinionated on purpose — consistency is more valuable than perfection. Update via PR, not Slack.

---

## 1. Local development setup

### 1.1 Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.12+ | `pyenv install 3.12.x` |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | 20.x LTS | `fnm install 20` |
| pnpm | 9.x | `corepack enable && corepack prepare pnpm@latest --activate` |
| Go | 1.22+ | `brew install go` (for the CLI) |
| Docker | 24+ | Docker Desktop or OrbStack |
| direnv | latest | `brew install direnv` |
| pre-commit | latest | `uv tool install pre-commit` |

Linux/macOS supported. Windows via WSL2 only.

**Environment variables** (copy `.env.example` to `.env.dev` and source via direnv):

```bash
# .env.example — every var documented below
LOOP_ENV=dev
LOOP_WORKSPACE_ID=<your-test-workspace-uuid>
LOOP_RUNTIME_PORT=8000
LOOP_GATEWAY_PORT=8001
LOOP_STUDIO_PORT=3000
LOOP_DB_URL=postgresql://loop:password@localhost:5432/loop_dev
LOOP_REDIS_URL=redis://localhost:6379/0
LOOP_QDRANT_URL=http://localhost:6333
LOOP_NATS_URL=nats://localhost:4222
LOOP_OTEL_ENDPOINT=http://localhost:4317
LOOP_OBSERVABILITY_ENABLED=true
LOG_LEVEL=DEBUG  # see §2.5
LOOP_EVAL_HARNESS_ENABLED=true
LOOP_MCP_REGISTRY_URL=http://localhost:8080
```

See `.env.example` in repo root for the full list (50+ vars). Each service reads its own subset via `pydantic_settings.BaseSettings`.

### 1.2 Bootstrap

```bash
git clone https://github.com/loop-ai/loop.git
cd loop
direnv allow            # loads .env.dev
make bootstrap          # installs deps for all packages
make up                 # starts Postgres, Redis, Qdrant, NATS, MinIO via docker-compose
make migrate            # runs alembic migrations
make seed               # creates a default workspace + demo agent
make dev                # runs runtime + gateway + studio in tmux
```

`make dev` opens a tmux session with one pane per service. `ctrl-b q` jumps between panes. `make logs SERVICE=runtime` tails one service.

### 1.3 Repository layout

```
loop/
├── packages/             # all backend packages (uv workspace)
│   ├── runtime/
│   ├── sdk-py/
│   ├── gateway/
│   ├── kb-engine/
│   ├── eval-harness/
│   ├── observability/
│   ├── mcp-client/
│   └── channels/{web,slack,whatsapp,sms,email,telegram,discord,teams,voice}
├── apps/
│   ├── studio/           # Next.js web UI
│   ├── control-plane/    # closed-source until launch
│   └── docs/             # Docusaurus
├── cli/                  # Go CLI
├── examples/             # reference agents
├── infra/
│   ├── terraform/
│   ├── helm/
│   └── docker-compose.yml
├── docs/                 # this folder
└── tools/                # codegen, scripts
```

---

## 2. Coding conventions

### 2.1 Python

- **Lint+format:** `ruff` (single tool — replaces black, isort, flake8, autoflake).
- **Type checking:** `pyright` in strict mode.
- **Async:** assume asyncio everywhere. No `requests` (use `httpx`); no `time.sleep` (use `asyncio.sleep`).
- **Pydantic v2** for every public type. No raw dicts on public APIs.
- **Loguru/structlog** for logging — never `print` outside scripts.
- **Imports:** absolute, sorted by ruff. Top-level `from __future__ import annotations`.
- **Function size:** prefer ≤ 40 lines. Refactor at 80.
- **No god classes:** if a file exceeds 600 lines, split it.
- **Errors:** use rich exception types (`LoopError` base + named subclasses). Never `raise Exception`.
- **Config:** Pydantic Settings classes; never `os.environ.get` ad-hoc.
- **Tests live next to code:** `module.py` ↔ `test_module.py` in `_tests/` siblings.

Style example:

```python
from __future__ import annotations

from typing import Self
from uuid import UUID

import structlog
from pydantic import BaseModel

logger = structlog.get_logger()

class AgentNotFound(LoopError):
    """Raised when an agent ID does not resolve in the workspace."""

class AgentRef(BaseModel):
    workspace_id: UUID
    agent_id: UUID

    @classmethod
    def from_string(cls, s: str) -> Self:
        ws, agent = s.split("/", 1)
        return cls(workspace_id=UUID(ws), agent_id=UUID(agent))
```

### 2.2 TypeScript

- **Lint+format:** `biome` (single tool).
- **Strict mode** in `tsconfig.json`. No `any` without an `// eslint-disable-next-line` justification.
- **No default exports** in libraries; named exports only.
- **Components:** function components with hooks; no class components.
- **Data fetching:** TanStack Query in Studio. No raw `fetch` in components.
- **State:** local first; Zustand for cross-cutting; never Redux.
- **Tailwind** for styling; shadcn/ui as the component foundation.

### 2.3 Go (CLI)

- **Lint:** `golangci-lint run`.
- **Errors:** wrapped with `fmt.Errorf("%w: …", err)`.
- **No global state.** Inject via constructor.
- **`cobra` + `viper`** for command and config parsing.
- **Goroutines:** every goroutine has a `context.Context` and an exit path.

### 2.4 SQL

- **Migrations:** Alembic for control plane; custom Python migrator for tenant DDL on data plane.
- **Backwards-compatible** within a major version. Never DROP a column in the same migration that stops writing to it; use a deprecation window.
- **Naming:** `snake_case` tables and columns, plural table names, `id UUID PRIMARY KEY`.
- **No application-side enums.** Use Postgres CHECK constraints.
- **Always include `created_at` and (where mutable) `updated_at`**.

### 2.5 Naming & release conventions

- **Repos:** `loop-<area>` (`loop-runtime`, `loop-cli`, `loop-studio`).
- **Branches:**
  - Feature: `<author>/<short-slug>` (e.g., `praise/runtime-streaming`). One feature per branch.
  - Release: `release/v<major>.<minor>` (e.g., `release/v0.1`). Branched from `main` when ready to cut a release.
  - Hotfix: `hotfix/v<major>.<minor>.<patch>` (e.g., `hotfix/v0.1.1`). Branched from `release/v0.1`, cherry-picked to `main` after merge.
- **Conventional Commits** required (`feat:`, `fix:`, `chore:`, `refactor:`, `test:`, `docs:`). Squash-merge into `main` with a tidy message.
- **Tagging:**
  - Release tags: `v<major>.<minor>.<patch>` (e.g., `v0.1.0`). Points to merge commit on `main` or `release/v0.1`.
  - Pre-release tags: `v<major>.<minor>.<patch>-rc.<N>` (e.g., `v0.1.0-rc.1`). Built from release branch; includes `-rc` in binary version string.
  - All tags signed with `git tag -s`.
- **Release notes process:** Auto-generated from conventional commits (Conventional Changelog). Format: features, fixes, breaking changes, authors, GitHub links. Reviewed by CTO + product lead before tag push. Posted to docs site + changelog.md + GitHub releases.

---

## 3. Branching & code review

### 3.1 Branch model

- `main` is always green and deployable.
- Feature branches → PR → review → squash-merge.
- No long-lived feature branches; rebase often.
- Hotfix branches off `main`, cherry-pick to release branches if needed.

### 3.2 Pull requests & code review checklist

A PR is reviewable when:

1. The title is a Conventional Commit and the description explains *why*, not *what*.
2. Tests cover the change. If unsure if a test is valuable, add it anyway.
3. Migrations include up + down + a unit test exercising both.
4. Docs updated (architecture, schema, ADR, handbook) **in the same PR**, not a follow-up.
5. CI is green: lint, typecheck, unit tests, integration tests, vulnerability scan, license scan.
6. PRs touching the runtime require eval-pack to pass (see `engineering/TESTING.md`).

**Code review checklist** (for reviewers; auto-reminder template added to PRs):

- [ ] Tests are present and pass; coverage does not decrease.
- [ ] Docs are updated (or PR references an earlier doc-only PR).
- [ ] No secrets in the code or logs (scan with `detect-secrets`).
- [ ] Postgres migrations are backwards-compatible (add new cols, don't DROP within same migration).
- [ ] Error handling: no bare `Exception`, all errors are typed subclasses.
- [ ] For infra changes: does it go through a `*Backend` interface? Is there a second implementation (or plan to add)?
- [ ] For runtime changes: can a customer's agent code trigger a denial-of-service? If yes, is there a hard cap?
- [ ] For high-risk areas (auth, secrets, RLS): "don't merge alone" — requires approval from Security + relevant owner.

**High-risk areas (don't merge alone):** `packages/gateway/auth.py`, `packages/runtime/secrets.py`, `packages/runtime/rls.py`, `infra/terraform/modules/kms/`, any file in `sql/` with `DROP` statements.

### 3.3 Review SLA

- First reviewer comment within 1 business day.
- Decision (approve / changes) within 2 business days.
- Author addresses feedback within 1 business day, or marks the PR as draft.

PRs older than 5 business days get a Slack ping in `#eng-stale`.

### 3.4 Codeowners

`CODEOWNERS` enforces at least one approval from the team that owns the package (see ARCHITECTURE.md §11). Cross-cutting changes need approval from each affected owner.

---

## 4. Testing

(Full strategy in `engineering/TESTING.md`. Quick reference here.)

| Layer | Coverage target | Runs |
|-------|-----------------|------|
| Unit (Python) | ≥ 85% on core packages | every PR, every commit on main |
| Unit (TS) | ≥ 80% on Studio | every PR |
| Integration | every public API path | every PR |
| End-to-end | top 10 user journeys | nightly + before deploy |
| Eval (agent quality) | every runtime PR | nightly + every runtime PR |
| Load | Quarterly + before public launches | manual |
| Chaos | Quarterly | manual |

CI gates: PR cannot merge if unit < 85%, integration fails, runtime evals regress > 5%, license scan flags non-Apache-compatible deps.

---

## 5. Observability culture & log levels

### 5.1 Logging standards

- **Every async operation gets a span.** No exceptions. Spans include: `workspace_id`, `agent_id`, `conversation_id`, `turn_id`, `user_id`, `action` (name), `latency_ms`, `status` (success/error).
- **Every error is logged with context.** Pattern: `logger.exception("msg", op="op_name", workspace_id=..., agent_id=..., error_code=...)`.
- **Don't log secrets.** Pre-commit hook blocks commits with API keys, JWTs, etc. (see §9.1 for PII patterns).
- **Every customer-visible feature has a metric.** Prometheus counters/histograms; Grafana dashboards live in `infra/grafana/` per service.
- **Alert on user-visible symptoms, not internal causes.** Alerts on error rate (>1% for 5min), latency p99 (>2s for chat), not on CPU.

### 5.2 Log-level convention

| Level | When to use | Example |
|-------|-----------|---------|
| **DEBUG** | Low-level detail; tracing; state transitions | "Loaded agent v42 from cache in 15ms", "RLS check passed for workspace {ws_id}" |
| **INFO** | Normal operational events; deployments; major state changes | "Agent v42 deployed to prod", "Conversation escalated to HITL", "Eval run started" |
| **WARN** | Recoverable issues; deprecations; performance anomalies | "LLM call retried after 500 (attempt 2/3)", "Key rotation due (rotated 91 days ago)", "Query took 500ms (p99 is 2ms)" |
| **ERROR** | Actionable failure; data corruption risk; exceptions | "Failed to fetch KB chunks after 3 retries (will degrade to fallback)", "RLS policy violation detected (cross-tenant leak?)" |
| **CRITICAL** | System-wide outage; data loss imminent | "Postgres connection pool exhausted", "Vault unreachable — cannot decrypt secrets" |

**Enforcement:** Pre-commit hook rejects commits with `logger.info("debug stuff")` (mis-leveled). Linter checks that CRITICAL logs include a PagerDuty alert trigger.

---

## 6. Performance budgets

| Concern | Budget |
|---------|--------|
| Voice end-to-end p50 | ≤ 700 ms |
| Chat first-token p50 | ≤ 600 ms |
| API p99 | ≤ 500 ms (excluding LLM-bound endpoints) |
| Trace ingest lag | ≤ 5 s |
| Studio TTI (LCP) | ≤ 1.5 s on broadband |
| Cold start (warm pool) | not user-visible |

If a PR regresses any budget in the perf bench, blocked from merge until justified or fixed.

---

## 7. Documentation

- README in every package, with a 60-second "what is this" + run command.
- Public API: docstrings on every exported symbol; rendered to docs site via mkdocs/typedoc.
- Internal docs: this folder. Rule: if you ask the same question twice, write it down here.
- Architecture changes: update `architecture/ARCHITECTURE.md` in the same PR, and write an ADR if the change is non-obvious.

---

## 8. Operations cadence & team norms

| Cadence | Activity | Time zone | Owner |
|---------|----------|-----------|-------|
| Daily | Standup async in `#eng-standup` (≤ 5 lines: what did I do, what will I do, any blockers) | — | each engineer |
| Daily | On-call incident check (one primary, one secondary) | PT | primary on-call |
| Weekly | Eng all-hands (45m, demo + roadmap + on-call handoff) | Mon 10:00 PT | CTO |
| Weekly | Deploy review (if a release is pending) | Thu 14:00 PT | Founding Eng #2 |
| Bi-weekly | Sprint planning (1h, stories → tasks) | Tue 09:00 PT | CTO + squad leads |
| Bi-weekly | Sprint retro (30m, blameless) | Fri 15:00 PT | rotating facilitator |
| Monthly | Architecture review (90m, async-first; discuss major design decisions) | 2nd Wed 10:00 PT | CTO |
| Quarterly | Off-site planning (2 days, in-person if possible) | — | all eng + product |

### 8.1 Working hours & async norms

- **Core hours:** 9 am — 4 pm PT (covers PT, CT, ET; some flexibility for APAC/EU hires).
- **Async-first:** All decisions documented in Linear stories / docs / ADRs, not Slack-only.
- **Standup format:** Post by 10 am PT. Same-day responses to async decisions. Synchronous meetings only for discussion, not information broadcast.
- **Timezone support:** EU engineers can join earlier meetings with flexibility on later ones; APAC engineers (future) get dedicated async standup time.

### 8.2 1:1 cadence & performance reviews

- **1:1 frequency:** Bi-weekly, 30 min. Rotating topics: career growth, blockers, feedback, project planning.
- **Performance reviews:** Quarterly (every Jan/Apr/Jul/Oct), written + verbal. 360 feedback collected from peers 2 weeks prior.
- **Promotion criteria:** Clear rubric in Linear per level (e.g., Senior Eng = "owns architectural decisions for ≥1 service").

### 8.3 Deprecation policy

- **Public deprecation:** 30-day notice required before breaking change. Announced in `#eng-announcements` + release notes + docs.
- **Feature flag gating:** Old behavior behind a flag (`enable_legacy_api_v1`); flag defaults to new behavior after 30 days.
- **SDK versions:** Major version bumps allowed only at release boundaries (every 6 weeks); minor versions patch-friendly.

---

## 9. Definition of done

A feature is done when:

1. Code merged to `main`.
2. Tests at all relevant layers, passing.
3. Docs (architecture, schema, handbook, public docs) updated.
4. Metrics + alerts wired.
5. Deploy to staging, soak ≥ 24h.
6. Deployed to production with feature flag.
7. Owner has watched the dashboards for one full day.
8. The feature flag is flipped on for at least one design partner.

"It works locally" is not done.

---

## 10. Tools we use

| Function | Tool |
|----------|------|
| Source | GitHub |
| CI | GitHub Actions |
| Issue tracking | Linear |
| Docs (internal) | Markdown in repo |
| Docs (external) | Docusaurus on docs.loop.example |
| Comms | Slack (`#eng`, `#eng-standup`, `#oncall`, `#wins`, `#design-partners`) |
| Calendar | Google Workspace |
| Pager | PagerDuty |
| Errors | Sentry |
| Logs | Loki |
| Metrics | Prometheus + Grafana |
| Traces | OpenTelemetry → ClickHouse + dev access via Honeycomb |
| Secrets | 1Password (humans), HashiCorp Vault (services) |
| Cloud | Cloud-agnostic. Concrete deployments on AWS / Azure / GCP / Alibaba Cloud / self-host k8s — see `architecture/CLOUD_PORTABILITY.md` |
| Design | Figma |
| Browser-testing | Playwright |

---

## 11. Hiring & onboarding

First 5 working days for a new engineer:

- **Day 1:** laptop, GitHub, Slack, Linear, cloud SSO (whichever provider hosts your env), Auth0 dev tenant. Read this handbook + ARCHITECTURE.md + SCHEMA.md + CLOUD_PORTABILITY.md.
- **Day 2:** ship a doc PR (typo, clarification, or new section). Pair with onboarding buddy.
- **Day 3:** ship a code PR (a `good-first-issue`). Pair-review.
- **Day 4:** shadow on-call.
- **Day 5:** present what they learned in Friday eng meeting.

---

## 10. Error code namespace policy

All errors returned to customers follow the pattern: `LOOP-<SERVICE>-<SEQUENCE>`.

| Service | Prefix | Examples |
|---------|--------|----------|
| Runtime | `LOOP-RT-` | `LOOP-RT-001` (agent not found), `LOOP-RT-042` (max iterations exceeded) |
| Gateway | `LOOP-GW-` | `LOOP-GW-101` (LLM provider unavailable), `LOOP-GW-102` (rate limit) |
| KB Engine | `LOOP-KB-` | `LOOP-KB-201` (document too large), `LOOP-KB-202` (unsupported format) |
| Auth/API | `LOOP-API-` | `LOOP-API-301` (invalid token), `LOOP-API-302` (insufficient scope) |
| Evals | `LOOP-EVAL-` | `LOOP-EVAL-401` (suite not found), `LOOP-EVAL-402` (scorer failed) |

**Error code registry:** Maintained in `docs/error-codes.md` (human-readable + codes). Every new error requires an entry. Codes never reused; deprecated codes moved to a legacy section.

Onboarding buddy is rotated; CTO oversees first 4 hires personally.

---

## 11. Engineering blog & knowledge sharing

- **Blog post cadence:** 1 per month (1st Monday of month).
- **Topics:** Deep dives on interesting technical decisions, postmortems, community contributions.
- **Ownership:** Rotating; assigned in sprint planning. Author drafts in repo branch; reviewed by CTO + product; published to docs.loop.example/blog.
- **Internal knowledge:** Every `TODO` or `HACK` in code triggers a Linear task + doc entry within 1 sprint. No undocumented technical debt.

## 12. Glossary references

- ARCHITECTURE.md §0 has the canonical glossary. Use the same vocabulary in code, docs, and commits.
