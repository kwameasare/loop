# GitHub Copilot — Repository Instructions

Place this file at `.github/copilot-instructions.md` in the repo root. GitHub Copilot Chat (and the Coding Agent) reads it automatically and applies it to every interaction in this repo.

---

You are working on **Loop**, an open-source, agent-first, cloud-agnostic runtime for production AI agents.

## Required reading before suggestions

For any non-trivial task, read these files first:

1. `loop_implementation/AGENTS.md` — entry-point conventions.
2. `loop_implementation/skills/_base/SKILL_ROUTER.md` — task → skill decision table.
3. `loop_implementation/engineering/GLOSSARY.md` — vocabulary.
4. `loop_implementation/architecture/ARCHITECTURE.md` — system architecture.

For domain tasks, also read the matching skill file in `loop_implementation/skills/<category>/<name>.md`. Skills tell you which canonical docs to read and the steps to follow.

## Hard rules

1. **Cloud portability**: never import a cloud SDK directly from `packages/runtime/`, `packages/gateway/`, `packages/sdk-py/`, or `packages/channels/`. Use abstractions from `architecture/CLOUD_PORTABILITY.md` §4 (`ObjectStore`, `KMS`, `SecretsBackend`, `EmailSender`, etc.).
2. **Tenant isolation**: every DB-touching change respects Postgres RLS. Every test includes a cross-tenant negative case.
3. **Docs with code**: schema/ADR/architecture/API changes are in the SAME PR as the code.
4. **Conventional Commits** for PR titles (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`).
5. **Errors carry codes** per `engineering/ERROR_CODES.md` (`LOOP-XX-NNN`).
6. **Every async op gets an OTel span**.
7. **Secrets**: Vault only. Never in code, env vars in containers, logs, or commits.
8. **Eval-gated runtime PRs**: regressions > 5% block merge.
9. **Perf budgets** on hot paths: regressions > 10% block merge.

## Per-task quickstart

When you receive a request:

1. Open `loop_implementation/skills/_base/SKILL_ROUTER.md`. Find the matching skill in the Task → Skill table.
2. **Tracker BEFORE** — claim the story per `skills/meta/update-tracker.md`. Make `chore(tracker): claim S0NN` the FIRST commit on the branch.
3. Read the skill file. Read its `required_reading` files.
4. Suggest code that follows the skill's Steps in order.
5. Verify the skill's Definition-of-done before declaring complete.
6. **Tracker AFTER** — close the story (status `Done` + PR ref). Make `chore(tracker): close S0NN` the LAST commit on the branch.
7. Pair the change with `meta/write-pr.md` for the PR. Its checklist verifies claim+close commits exist.

## Style

- Python: ruff + pyright strict; asyncio everywhere; Pydantic v2; structlog; `from __future__ import annotations`.
- TypeScript: biome; strict; named exports only; TanStack Query; Tailwind + shadcn/ui.
- Go: cobra + viper; wrapped errors; no global state.
- SQL: snake_case; `workspace_id NOT NULL` + RLS on tenanted tables; CONCURRENTLY for index creation.

## Files agents should never touch

- `LICENSE`
- `.github/workflows/release.yml`
- `loop_implementation/tracker/IMPLEMENTATION_TRACKER.xlsx` (regenerate via `tools/build_tracker.py`)
- The parent folder's `.docx` and `.pptx` exports

## Forbidden services (without ADR override)

- AWS-only: Aurora-only extensions, DynamoDB, Lambda as primary compute, Step Functions, IAM-only S2S auth.
- Azure-only: Cosmos DB, Service Bus as primary bus, AAD-only auth.
- GCP-only: Spanner, Firestore as primary store, Pub/Sub as primary bus.
- Alibaba-only: MaxCompute, MNS as primary bus.

## Available skills

The full catalog is in `loop_implementation/skills/README.md` and the routing decision table is in `loop_implementation/skills/_base/SKILL_ROUTER.md`. Forty skills across: meta, architecture, coding, data, api, security, testing, observability, ux, ops, devrel.

For per-skill prompt files, see `loop_implementation/skills/platforms/github-copilot/prompts/` — Copilot Chat picks them up automatically when invoked with `/<skill-name>` in chat.
