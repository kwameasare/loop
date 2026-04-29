# Aider — Conventions

Pass this file via `aider --read loop_implementation/skills/platforms/aider/CONVENTIONS.md`.

For a permanent setup, add to `.aider.conf.yml`:

```yaml
read:
  - loop_implementation/AGENTS.md
  - loop_implementation/skills/_base/SKILL_ROUTER.md
  - loop_implementation/skills/platforms/aider/CONVENTIONS.md
```

---

# Loop — Aider Conventions

You are working on **Loop**, an open-source, agent-first, cloud-agnostic runtime for production AI agents.

## Always read these first

1. `loop_implementation/AGENTS.md`
2. `loop_implementation/skills/_base/SKILL_ROUTER.md`
3. `loop_implementation/engineering/GLOSSARY.md`
4. `loop_implementation/architecture/ARCHITECTURE.md`

For specific tasks, the SKILL_ROUTER's Task → Skill table tells you which skill to apply. Each skill file lists its `required_reading` and Steps.

## Hard rules

1. **Cloud portability**: no cloud SDK imports in `packages/runtime/`, `packages/gateway/`, `packages/sdk-py/`, `packages/channels/`. Use abstractions in `architecture/CLOUD_PORTABILITY.md` §4.
2. **Tenant isolation**: Postgres RLS on every tenanted table; cross-tenant negative test.
3. **Docs with code**: schema/ADR/architecture/API in the SAME PR.
4. **Conventional Commits** for PR titles.
5. **Errors carry `LOOP-XX-NNN` codes** per `engineering/ERROR_CODES.md`.
6. **OTel span** on every async op.
7. **Secrets**: Vault only.
8. **Eval-gating** for runtime PRs.
9. **Perf budgets** on hot paths.

## Style

- Python: ruff + pyright strict; asyncio; Pydantic v2; structlog; `from __future__ import annotations`.
- TypeScript: biome strict; named exports; TanStack Query; Tailwind + shadcn/ui.
- Go: cobra + viper; wrapped errors; no global state.
- SQL: snake_case; `workspace_id NOT NULL` + RLS.

## Aider-specific tips

- `/architect` mode is great for skills like `architecture/propose-adr.md` — discuss before editing.
- `/code` mode for implementation skills.
- Use `/test` to generate tests after changes.
- Use `/lint` to verify ruff + pyright before commit.
- `/diff` to see staged changes before committing.

## Forbidden edits

- `LICENSE`, `.github/workflows/release.yml`, the xlsx tracker (regenerate from `tools/build_tracker.py`), or parent folder's `.docx`/`.pptx`.

## Tracker lifecycle (mandatory)

Every PR has a tracker `claim` commit first and a tracker `close` commit last. In Aider:

```
/add tools/build_tracker.py tracker/
/architect Claim story S0NN: set status to In progress + owner
/commit                  # → chore(tracker): claim S0NN

# ... do the actual work ...

/architect Close story S0NN: set status to Done + PR ref
/commit                  # → chore(tracker): close S0NN
```

Apply `skills/meta/update-tracker.md` for full details.

## Available skills (forty)

See `loop_implementation/skills/README.md`. Categories: meta · architecture · coding · data · api · security · testing · observability · ux · ops · devrel.

Always end a task with `meta/write-pr.md` (Aider commits via `/commit`).
