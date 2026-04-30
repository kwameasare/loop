# Loop

Open-source, agent-first, cloud-agnostic runtime for production AI agents.

**Status:** Sprint 0 (bootstrap). Public beta target: M6. License: Apache 2.0.

---

## Why Loop

The agent platforms that exist today force a choice: hosted-only and
proprietary, or self-host but no observability, evals, or voice. Loop
unifies them — a Python runtime with first-class streaming, MCP tools,
voice, evals, and tracing, running on any cloud you choose, with the
control plane (Studio, deploy, billing) as the wedge product.

See [`botpress_competitor_spec.md`](botpress_competitor_spec.md) for the
full product/competitive thesis and
[`loop_implementation/`](loop_implementation/) for the design corpus.

---

## Repository layout

```
.
├── packages/                # Python workspace (uv)
│   ├── runtime/             # Hot path: TurnExecutor, streaming, budgets
│   ├── sdk-py/              # Public Python SDK (Agent, Tool, Memory, ...)
│   ├── gateway/             # LLM gateway (S007 — TBD)
│   ├── kb-engine/           # KB / RAG (S015 — TBD)
│   ├── eval-harness/        # Eval scorers + replay (S021 — TBD)
│   ├── observability/       # OTel + ClickHouse helpers (TBD)
│   ├── mcp-client/          # MCP client + auto-MCP (S011 — TBD)
│   └── channels/{web,slack,whatsapp,...}/
├── apps/
│   ├── studio/              # Next.js debugger UI (S005 — TBD)
│   └── control-plane/       # cp-api (FastAPI), deploy controller (S019 — TBD)
├── infra/
│   └── docker-compose.yml   # Local stack: Postgres, Redis, Qdrant, NATS, MinIO, ClickHouse, OTel
├── examples/
│   └── support_agent/       # Reference Loop agent
├── tools/
│   ├── build_tracker.py     # Source of truth for the implementation tracker
│   └── tracker_to_machine.py
├── scripts/
│   └── recalc.py
├── docs/
│   └── branch-protection.md
└── loop_implementation/     # Design corpus (specs, ADRs, skills, tracker)
    ├── AGENTS.md            # Mandatory reading for any AI coding agent
    ├── README.md            # Map of the design corpus
    ├── architecture/
    ├── api/
    ├── data/
    ├── engineering/         # HANDBOOK, SECURITY, TESTING, RUNBOOKS, ...
    ├── skills/              # Per-task playbooks for AI agents
    ├── tracker/             # TRACKER.md, tracker.json, csv/
    └── ux/
```

---

## Getting started

### Prerequisites

- Python 3.12+ (`uv` for dependency management)
- Node.js 20+ + pnpm 9 (Studio; not yet present)
- Go 1.22+ (CLI; not yet present)
- Docker + Docker Compose

### Quick local bootstrap (current Sprint 0 state)

```bash
# Install Python deps for the workspace members that exist today.
uv sync --all-packages

# Bring up the local stack (subset operational at Sprint 0).
docker compose -f infra/docker-compose.yml up -d

# Regenerate tracker outputs.
python tools/build_tracker.py
```

Most surfaces (Studio, CLI, full stack, evals, voice) are still TBD;
follow the sprint plan in
[`loop_implementation/tracker/TRACKER.md`](loop_implementation/tracker/TRACKER.md).

---

## Working with this repo

**Read first** if you are an AI coding agent or a contributor:

1. [`loop_implementation/AGENTS.md`](loop_implementation/AGENTS.md) — the
   contract every agent must follow.
2. [`loop_implementation/README.md`](loop_implementation/README.md) — map
   of the design corpus.
3. [`loop_implementation/skills/_base/SKILL_ROUTER.md`](loop_implementation/skills/_base/SKILL_ROUTER.md)
   — pick the right skill before starting work.
4. [`loop_implementation/engineering/HANDBOOK.md`](loop_implementation/engineering/HANDBOOK.md)
   — coding standards, PR rules, branch naming.
5. [`loop_implementation/tracker/TRACKER.md`](loop_implementation/tracker/TRACKER.md)
   — sprint plan + story status.

### Tracker workflow

The implementation tracker is generated, never hand-edited. Source of
truth lives in
[`tools/build_tracker.py`](tools/build_tracker.py); run it after every
status change and commit the regenerated outputs. Story lifecycle (claim
→ checkpoint → close) is documented in
[`loop_implementation/skills/meta/update-tracker.md`](loop_implementation/skills/meta/update-tracker.md).

### Branch + commit conventions

- Branch: `<author-handle>/<short-slug>` (e.g. `copilot/s001-repo-init`).
- Commits: Conventional Commits. First commit on the branch must be
  `chore(tracker): claim S0NN`; last commit must be
  `chore(tracker): close S0NN`.
- Merge: squash only. No merge commits.
- Pre-merge: see [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md).

### Security

Vulnerability reports → [`.github/SECURITY.md`](.github/SECURITY.md).
Threat model → [`loop_implementation/engineering/SECURITY.md`](loop_implementation/engineering/SECURITY.md).

---

## License

Apache 2.0 — see [`LICENSE`](LICENSE).

```
Copyright 2026 Loop AI, Inc.
```
