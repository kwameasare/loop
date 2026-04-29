---
name: add-postgres-migration
description: Use when adding a Postgres DDL change — new table, new column, new index, new constraint, or a non-trivial data migration.
when_to_use: |
  - Any Alembic migration on the control-plane DB.
  - Any tenant DDL on the data-plane DB.
  - Adding RLS policies, indexes, or check constraints.
  - Backfill of existing rows.
required_reading:
  - data/SCHEMA.md                  # full schema, RLS policies, naming conventions
  - engineering/HANDBOOK.md         # §2.4 SQL conventions, §3.2 PR migration rules
  - engineering/SECURITY.md         # §6.3 tenant isolation
  - adrs/README.md                  # ADR-020 (RLS + single Postgres + workspace_id), ADR-024 (deprecation)
applies_to: data
owner: Founding Eng #2 (Infra)
last_reviewed: 2026-04-29
---

# Add Postgres migration

## Trigger

Any DDL change. Migrations have outsized blast radius; missed RLS = cross-tenant leak (a SEV1 by definition).

## Required reading

1. `data/SCHEMA.md` end-to-end. Your DDL must fit the existing model.
2. `engineering/HANDBOOK.md` §2.4 (naming, conventions) and §3.2 (PR migration rules).
3. ADR-020 (RLS + workspace_id is non-negotiable for tenanted tables).

## Steps

1. **Pick the right plane.** Control-plane (`cp_migrations/`) or data-plane (`dp_migrations/`)?
   - Control plane: workspaces, users, deploys, eval runs, billing.
   - Data plane: conversations, turns, memory, KB metadata, tool calls.
2. **Generate the migration:**
   ```bash
   uv run alembic -c packages/control-plane/alembic.ini revision -m "add <thing>"
   ```
3. **Naming + structure:**
   - File: `<YYYYMMDDHHMM>_add_<thing>.py`.
   - Functions: `upgrade()` and `downgrade()`. Both required. Both tested.
4. **Tenanted table** (any new table containing customer data):
   ```sql
   CREATE TABLE foo (
       id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       workspace_id    UUID NOT NULL,                       -- mandatory
       -- ... your columns ...
       created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
       updated_at      TIMESTAMPTZ
   );
   CREATE INDEX idx_foo_workspace ON foo(workspace_id);

   ALTER TABLE foo ENABLE ROW LEVEL SECURITY;
   CREATE POLICY tenant_isolation ON foo
     USING (workspace_id = current_setting('loop.workspace_id')::uuid);
   ```
5. **Backwards compatibility** (within a major version):
   - Adding a column: must be NULL or have a DEFAULT. Never NOT NULL without DEFAULT in the same migration.
   - Removing a column: deprecation flag for ≥30 days first (per ADR-024). Two-step: stop reading → next major bump → drop.
   - Renaming: never. Add new + keep old + dual-write + cutover read + drop old.
6. **Indexes:** create CONCURRENTLY in production migrations to avoid table locks. Alembic supports this with `op.create_index(..., postgresql_concurrently=True)`.
7. **Backfill (data migration):** chunked + idempotent. Never one big UPDATE. Use a separate Alembic data-migration step or a dedicated worker.
8. **Test the migration:**
   - Create a test DB from the previous migration tag.
   - Run `upgrade()`. Run `downgrade()`. Run `upgrade()` again.
   - Assert row counts match expectations.
9. **Update `data/SCHEMA.md`** in the same PR. Apply `data/update-schema.md`.
10. **Production rollout** (apply at deploy time):
    - Migrations apply via the deploy controller, single-leader. The PR description must include row counts and an estimated migration runtime.
    - Migrations > 30s require an explicit "long-migration" tag and a maintenance window.
11. **PR.** Apply `meta/write-pr.md`. Tag Eng #2.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Up + down migrations both implemented and tested.
- [ ] `workspace_id` + RLS policy on every tenanted table.
- [ ] Indexes created CONCURRENTLY in prod.
- [ ] Backwards-compatible (no break in same migration).
- [ ] `data/SCHEMA.md` updated in same PR.
- [ ] PR description: estimated runtime, row counts, rollback plan.
- [ ] Tested upgrade → downgrade → upgrade cycle.

## Anti-patterns

- ❌ Missing `workspace_id` on a tenanted table.
- ❌ Missing RLS policy on a tenanted table.
- ❌ NOT NULL without DEFAULT (breaks app on deploy).
- ❌ DROP COLUMN in the same migration that stops writing.
- ❌ Renaming columns/tables. Never.
- ❌ Backfilling in one big UPDATE.
- ❌ Migration that takes >30s without "long-migration" tag and notice.
- ❌ Forgetting to update SCHEMA.md.

## Related skills

- `data/update-schema.md` (always).
- `data/add-pydantic-type.md` if you're adding columns that change a public type.
- `security/add-audit-event.md` if the table is admin-relevant.

## References

- `data/SCHEMA.md`.
- ADR-020, ADR-024.
- `engineering/HANDBOOK.md` §2.4.
