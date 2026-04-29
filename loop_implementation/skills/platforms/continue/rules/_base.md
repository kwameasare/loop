# Loop — base rule (always on)

You are working on **Loop**, an open-source, agent-first, cloud-agnostic runtime for production AI agents.

## Read first

1. `loop_implementation/AGENTS.md`
2. `loop_implementation/skills/_base/SKILL_ROUTER.md`
3. `loop_implementation/engineering/GLOSSARY.md`
4. `loop_implementation/architecture/ARCHITECTURE.md`

Use SKILL_ROUTER's Task → Skill table to pick the right specific skill, then read it and follow its Steps.

**Tracker lifecycle:** every PR has a `chore(tracker): claim S0NN` commit FIRST and a `chore(tracker): close S0NN` commit LAST. Apply `skills/meta/update-tracker.md` BEFORE and AFTER. End with `skills/meta/write-pr.md`.

## Hard rules

1. **Cloud portability** — no cloud SDK imports in `packages/runtime/`, `packages/gateway/`, `packages/sdk-py/`, `packages/channels/`. Use abstractions from `architecture/CLOUD_PORTABILITY.md` §4.
2. **Tenant isolation** — Postgres RLS; cross-tenant negative test on every DB change.
3. **Docs with code** — schema/ADR/architecture/API in the SAME PR.
4. **Conventional Commits** for PR titles.
5. **Errors carry `LOOP-XX-NNN` codes**.
6. **OTel span** on every async op.
7. **Secrets** in Vault only.
8. **Eval-gating** for runtime PRs.
9. **Perf budgets** on hot paths.

## Style

- Python: ruff + pyright strict; asyncio; Pydantic v2.
- TypeScript: biome strict; named exports; TanStack Query.
- Go: cobra + viper; wrapped errors.
- SQL: snake_case; `workspace_id NOT NULL` + RLS.

## Forbidden

- Cloud SDK imports in forbidden packages.
- Editing `LICENSE`, release workflow, xlsx tracker, parent's `.docx`/`.pptx`.
- Hard-coded concrete cloud regions.
- Token markup > 5%.
- Cross-workspace cache keys / shared sandboxes / cross-tenant queries.
