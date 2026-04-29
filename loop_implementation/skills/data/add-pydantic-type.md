---
name: add-pydantic-type
description: Use when adding or modifying a public Pydantic type (anything in packages/sdk-py/loop/types.py or any model exported from the SDK).
when_to_use: |
  - Adding a new public BaseModel.
  - Adding/removing a field on a public model.
  - Changing a field's type, default, or validation.
  - Adding a new enum value to a public enum.
required_reading:
  - data/SCHEMA.md                  # §9 Pydantic models (canonical types)
  - api/openapi.yaml                # the schemas mirror Pydantic
  - engineering/HANDBOOK.md         # §2.1 Python; §2.5 release conventions
applies_to: data
owner: Founding Eng #1 (Runtime)
last_reviewed: 2026-04-29
---

# Add / modify Pydantic public type

## Trigger

You're touching `packages/sdk-py/loop/types.py` or anything exported from the SDK. **Every breaking change here bumps the SDK major version.**

## Required reading

1. `data/SCHEMA.md` §9 — the canonical type list.
2. `api/openapi.yaml` — REST schemas must stay in sync.
3. `engineering/HANDBOOK.md` §2.5 — release tagging.

## Steps

1. **Decide breaking vs non-breaking:**
   - **Non-breaking:** adding optional fields with defaults, adding enum values that consumers default-handle gracefully, widening a union.
   - **Breaking:** removing fields, renaming, narrowing types, making optional → required, removing enum values.
2. **Non-breaking change path:**
   - Add the field with a sensible default.
   - Add a unit test asserting the new field's default + serialization.
   - Update `data/SCHEMA.md` §9 inline with the type change.
   - Regenerate the TypeScript SDK: `pnpm sdk:codegen`.
   - Regenerate the OpenAPI YAML: `uv run python -m loop.sdk.export_openapi`.
   - Bump SDK minor version in `pyproject.toml`.
3. **Breaking change path:**
   - **Always** open an ADR or RFC first. Use `engineering/templates/RFC_TEMPLATE.md`.
   - Deprecation flow:
     1. Add the new field/type alongside the old.
     2. Mark the old as deprecated (`@deprecated` decorator + warning in docstring).
     3. Update SDKs, docs, examples to use the new.
     4. Wait ≥ 30 days (ADR-024 deprecation policy).
     5. Remove the old in a major-version PR.
   - Bump SDK major version.
4. **Validation rules:** use Pydantic v2 validators sparingly. If a field has invariants, write a `@field_validator` and unit-test it.
5. **Discriminated unions:** use the `Annotated[..., Field(discriminator='type')]` pattern. Mirror in OpenAPI as `oneOf` + `discriminator.propertyName`.
6. **Defaults:** use `Field(default_factory=...)` for mutable defaults (lists, dicts).
7. **Tests:**
   - Round-trip: serialize → deserialize → equal.
   - Schema: `Type.model_json_schema()` matches expected structure.
   - Deprecation warning for renamed fields.
8. **Docs:**
   - `data/SCHEMA.md` §9: update the canonical example.
   - `api/openapi.yaml`: regenerate.
   - SDK changelog (`packages/sdk-py/CHANGELOG.md`).
9. **PR.** Apply `meta/write-pr.md`. Title: `feat(sdk):` for non-breaking; `feat(sdk)!:` (with `!` for breaking, per Conventional Commits). Tag Eng #1.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Decision made: breaking vs non-breaking, documented.
- [ ] If breaking: ADR/RFC linked.
- [ ] Deprecation followed (if breaking).
- [ ] Round-trip + schema tests added.
- [ ] OpenAPI regenerated.
- [ ] TS SDK regenerated.
- [ ] SDK version bumped.
- [ ] SCHEMA.md, openapi.yaml, SDK CHANGELOG updated in same PR.

## Anti-patterns

- ❌ Renaming a public field without deprecation.
- ❌ Mutable defaults (`field: list = []`) — always `default_factory`.
- ❌ Hand-editing the OpenAPI YAML to match Pydantic. Always regenerate.
- ❌ Adding a field without a default to a non-empty model — breaks every existing serialized payload.

## Related skills

- `architecture/propose-adr.md` for breaking changes.
- `api/update-openapi.md` (after regen).
- `meta/write-pr.md`.

## References

- `data/SCHEMA.md` §9.
- ADR-024 (deprecation policy).
- `engineering/HANDBOOK.md` §2.5.
