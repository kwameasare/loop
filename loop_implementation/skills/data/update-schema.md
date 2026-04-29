---
name: update-schema
description: Use whenever data/SCHEMA.md must be updated — after a Postgres migration, a Qdrant collection change, a Redis key change, a ClickHouse table change, an S3 layout change, or a Pydantic type change.
when_to_use: |
  - You ran `data/add-postgres-migration` and the DDL is merged.
  - You added a Qdrant collection or changed a payload schema.
  - You added or changed a Redis key namespace.
  - You added a ClickHouse table or materialized view.
  - You changed the S3 layout for code/recordings/exports.
  - You modified a public Pydantic type (also see `data/add-pydantic-type.md`).
required_reading:
  - data/SCHEMA.md
  - engineering/HANDBOOK.md  # §2.4 SQL conventions + §10 docs-with-code
applies_to: data
owner: Founding Eng #2 (Infra)
last_reviewed: 2026-04-29
---

# Update SCHEMA.md

## Trigger

Every backend change updates SCHEMA.md in the SAME PR. SCHEMA.md is the single source of truth for storage; allowing it to drift = silent breakage.

## Required reading

`data/SCHEMA.md`. Skim every section before you edit.

## Steps

1. **Find the right section** — §1 storage map, §2 control-plane, §3 data-plane, §4 Qdrant, §5 Redis, §6 ClickHouse, §7 S3, §8 NATS, §9 Pydantic, §10 migration policy, §11 classification, §12 references.
2. **Postgres tables** (most common path):
   - Add the `CREATE TABLE` block exactly as it appears in the migration. Include constraints, indexes, RLS policies inline.
   - Use ALL CAPS for SQL keywords; lowercase for identifiers.
   - 4-space indent for column lists.
3. **Qdrant collections**:
   - Update §4 with name pattern, vector dim, distance, quantization, payload shape.
   - Payload examples in JSON.
4. **Redis keys**:
   - Update §5 keyspace table: pattern, TTL, purpose.
5. **ClickHouse tables**:
   - Update §6 with full DDL (engine, partition, order-by, TTL).
6. **S3 layout**:
   - Update §7 tree.
7. **Pydantic types**:
   - §9 must mirror what's exported from the SDK. Verify by `python -c "from loop.types import *; print(...)"`.
8. **Cross-references**: if your change affects RLS, classification, or retention, update §11 too.
9. **Migration changelog**: append to `data/CHANGELOG.md` (create if missing) with date + migration ID + summary.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] DDL block included verbatim from the migration.
- [ ] Indexes + constraints + RLS shown.
- [ ] `workspace_id NOT NULL` present on tenanted tables.
- [ ] Cross-references (Pydantic, retention, classification) updated.
- [ ] Migration changelog appended.
- [ ] Same PR as the migration.

## Anti-patterns

- ❌ Following-up the migration in a separate PR. Same PR or it doesn't merge.
- ❌ Summarizing the DDL instead of pasting it.
- ❌ Forgetting to add the RLS policy in the doc when it's in the migration.
- ❌ Skipping the changelog.

## Related skills

- `data/add-postgres-migration.md`, `data/add-pydantic-type.md`.

## References

- `data/SCHEMA.md`.
- `engineering/HANDBOOK.md` §10.
