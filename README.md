# Loop

Open-source, agent-first, cloud-agnostic runtime for production AI agents.

**Status:** large-pilot ready. All block-prod gates closed; production
hardening (live-DB integration, helm-e2e on CI matrix, partner-SDK
drift) tracked separately. License: Apache 2.0.

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
├── packages/                  # Python workspace (uv)
│   ├── control-plane/         # cp-api: FastAPI, auth, workspaces, agents, audit
│   ├── data-plane/            # dp-runtime: turn executor, SSE streaming
│   ├── runtime/               # TurnExecutor, budgets, scratchpad, multi-agent
│   ├── gateway/               # LLM gateway: failover, cost, idempotency cache
│   ├── sdk-py/                # Public Python SDK (Agent, Tool, Memory, ...)
│   ├── kb-engine/             # KB / RAG: ingest, embed, retrieve, structured SQL
│   ├── eval-harness/          # Eval scorers + replay
│   ├── memory/                # Short-term + long-term memory stores
│   ├── mcp-client/            # MCP client + auto-MCP
│   ├── mcp-servers/           # First-party MCP servers
│   ├── tool-host/             # Sandboxed tool execution
│   ├── voice/                 # Voice channel (STT, TTS, VAD)
│   └── channels/              # web, slack, teams, discord, telegram, sms, email, whatsapp
├── apps/
│   ├── studio/                # Next.js debugger / admin UI
│   └── docs/                  # Public docs site
├── infra/
│   ├── docker-compose.yml     # Local stack
│   ├── helm/loop/             # Production Helm chart + regional overlays
│   └── terraform/             # AWS / GCP / Azure / Alibaba modules
├── examples/
│   └── support_agent/         # Reference Loop agent
├── tools/                     # dev.sh, seed_dev.py, build_tracker, fixtures
├── scripts/                   # k6 perf, smoke, DR drills, cross-cloud probes
└── loop_implementation/       # Design corpus (specs, ADRs, skills, tracker)
    ├── AGENTS.md              # Mandatory reading for any AI coding agent
    ├── api/openapi.yaml       # Public API contract (CI-enforced)
    ├── architecture/
    ├── engineering/           # HANDBOOK, SECURITY, TESTING, RUNBOOKS, ...
    ├── skills/                # Per-task playbooks for AI agents
    └── tracker/
```

---

## Run a local pilot

This brings up the full stack on your laptop: Postgres + Redis +
Qdrant + NATS + MinIO + ClickHouse + OTel collector under Docker, the
control plane (cp-api) and data plane (dp-runtime) as Python uvicorns,
and the Next.js Studio UI. Total bring-up is ~5 minutes on a clean
machine.

### Prerequisites

- **Python 3.12+** with [`uv`](https://docs.astral.sh/uv/) for dep management
  (`brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Node.js 20+** with [`pnpm`](https://pnpm.io/) 9
  (`brew install node pnpm` or `corepack enable`)
- **Docker** + **Docker Compose** v2 (Docker Desktop, OrbStack, or Colima all work)
- **`tmux`** (for `make dev`; `brew install tmux`)
- An **OpenAI** *or* **Anthropic** API key (the gateway needs one upstream LLM)

### 1. Configure your environment

```bash
# Clone, then:
cp .env.example .env

# Edit .env — at minimum set:
#   LOOP_CP_LOCAL_JWT_SECRET=$(openssl rand -hex 32)
#   OPENAI_API_KEY=sk-...    (or ANTHROPIC_API_KEY=sk-ant-...)
```

If Homebrew Postgres / Redis already own ports 5432 / 6379, also set
`LOOP_DEV_POSTGRES_PORT=15432` and `LOOP_DEV_REDIS_PORT=16379` (and
update the host portion of the matching `LOOP_*_DB_URL` /
`LOOP_*_REDIS_URL` lines).

### 2. Install dependencies

```bash
make bootstrap
```

This runs `uv sync --all-packages`, `pnpm -C apps/studio install`,
and `pnpm -C apps/docs install`.

### 3. Bring up the local stack

```bash
make up           # starts Postgres, Redis, Qdrant, NATS, MinIO, ClickHouse, OTel
make migrate      # applies cp + dp Alembic migrations
```

Verify with:

```bash
make infra-smoke  # one-shot health probe of every service
```

### 4. Start cp + dp + studio

```bash
make dev          # opens a tmux session with three panes
```

- **Pane 0** — cp-api at <http://localhost:8080> (`/healthz`, `/metrics`)
- **Pane 1** — dp-runtime at <http://localhost:8081> (`/healthz`, `/metrics`)
- **Pane 2** — studio at <http://localhost:3001>

Detach with `Ctrl-b d`; reattach with `tmux attach -t loop-dev`. Each
pane reloads on file change.

If you don't have tmux, run the three commands manually in separate
terminals (each first does `set -a; . ./.env; set +a`):

```bash
# Terminal 1 — cp-api
uv run uvicorn loop_control_plane.app:app --port 8080 --reload

# Terminal 2 — dp-runtime
uv run uvicorn loop_data_plane.runtime_app:app --port 8081 --reload

# Terminal 3 — studio
pnpm -C apps/studio dev
```

### 5. Seed a workspace + agent

In a fresh terminal (cp must already be running):

```bash
make seed
```

The script mints a local HS256 JWT, exchanges it for a PASETO access
token, and idempotently creates one workspace + one agent. It prints
the token and IDs at the end:

```
✓ seed complete. To use the studio against this data:

  echo 'LOOP_TOKEN=<token>' >> apps/studio/.env.local
  pnpm -C apps/studio dev
```

Paste the `LOOP_TOKEN=` line into `apps/studio/.env.local` and reload
the studio tab — the workspace + agent should now render.

### 6. Send a turn

```bash
# Replace <ws> + <agent_id> with the IDs `make seed` printed.
TOKEN=$(grep LOOP_TOKEN apps/studio/.env.local | cut -d= -f2)
curl -N -H "authorization: Bearer ${TOKEN}" \
     -H "content-type: application/json" \
     -H "accept: text/event-stream" \
     -X POST http://localhost:8081/v1/turns \
     -d "{
        \"workspace_id\": \"<ws>\",
        \"conversation_id\": \"00000000-0000-0000-0000-000000000001\",
        \"user_id\": \"pilot-user\",
        \"input\": \"Say hi in five words.\",
        \"model\": \"gpt-4o-mini\"
     }"
```

You should see a streaming SSE response (`event: token` frames →
`event: complete` → `event: done`). If you set
`ANTHROPIC_API_KEY` instead, use `"model": "claude-3-haiku-20240307"`.

### Tear down

```bash
make down         # stops the docker stack (volumes preserved)
tmux kill-session -t loop-dev    # if make dev is still running
```

To wipe the stack (Postgres data, MinIO objects, ClickHouse traces):

```bash
docker compose --env-file .env -f infra/docker-compose.yml down -v
```

### Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `make seed` → `cp-api ... is unreachable` | cp uvicorn isn't running | start `make dev` first; wait for the pane to print `Application startup complete` |
| `make seed` → `auth exchange failed: HTTP 500` | cp uvicorn started before `LOOP_CP_LOCAL_JWT_SECRET` was set | re-export, restart pane 0 |
| `make migrate` → `connection refused on 5432` | Homebrew Postgres conflict | set `LOOP_DEV_POSTGRES_PORT=15432` in `.env` and update `LOOP_*_DB_URL` host port |
| Studio shows `null` for everything after seeding | `LOOP_TOKEN` not in `apps/studio/.env.local` | append the line `make seed` printed and refresh |
| `POST /v1/turns` → `LOOP-GW-101` | no LLM provider key | set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `.env`, restart cp + dp |
| `POST /v1/turns` → `LOOP-RT-403` | rate-limit middleware tripped | wait a few seconds (the bucket refills) or raise the cap in `loop_control_plane.rate_limit_middleware.RateLimitConfig` |
| 429 on every request | per-IP fallback bucket exhausted | seed_dev.py mints a token; use that instead of unauthenticated calls |

### What works in a pilot today

- Auth via local JWT or production RS256/JWKS (Auth0/Okta/Cognito)
- Workspace + member + role-gradient enforcement (OWNER > ADMIN > MEMBER > VIEWER)
- Agent CRUD, version pinning, deploys
- Streaming turns over SSE with cross-provider failover (LOOP-GW-301/401/402)
- Per-(workspace, route) rate limits (LOOP-RL-001) with `Retry-After`
- Audit log on every mutating route + per-tenant RLS on every data-plane table
- Decimal cost arithmetic (no float drift across high-volume turn sums)
- KB ingest + retrieval (Qdrant + structured tables)
- Eval suites + runs
- OTel traces flowing through cp → dp → gateway → upstream LLM
- All budget enforcement: per-workspace daily/hard, per-agent slice
- Idempotency replay on duplicate `request_id` within 600s

### What's gated for production (not pilot)

- Live `helm-e2e.yml` matrix run on GH Actions
- `LOOP_GATEWAY_LIVE_TESTS=1` against staging upstream provider keys
- ~30 documented OpenAPI drift items (partner SDKs would 404 on `/v1/workspaces/{id}/secrets`, `/v1/auth/refresh`, etc. — see `tests/test_openapi_drift.py`'s ratchet baseline)
- Postgres PITR drill (`scripts/dr_postgres_pitr_drill.sh`) against staging
- Shadow-traffic burn-in for several hours on the rate-limit + failover paths

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
