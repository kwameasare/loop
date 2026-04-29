---
name: update-openapi
description: Use whenever api/openapi.yaml must be updated — schema changes, new endpoints, new responses, new headers.
when_to_use: |
  - Pydantic public types changed (data/add-pydantic-type.md ran).
  - Endpoint added/modified.
  - Error envelope shape changed.
  - Auth/scope changed.
required_reading:
  - api/openapi.yaml
applies_to: api
owner: Founding Eng #2 (Infra)
last_reviewed: 2026-04-29
---

# Update OpenAPI spec

## Trigger

Anything that affects the public REST surface. The spec is regenerated, never hand-rolled — but small additions are committed by humans where regen is overkill.

## Required reading

`api/openapi.yaml` end-to-end.

## Steps

1. **Regenerate from Pydantic** (preferred):
   ```bash
   uv run python -m loop.sdk.export_openapi > api/openapi.yaml.new
   diff api/openapi.yaml api/openapi.yaml.new
   mv api/openapi.yaml.new api/openapi.yaml
   ```
2. **Hand-edit only for:**
   - Adding examples (`example:` keys).
   - Adding tags + descriptions.
   - Adding security scheme definitions.
   - Server URL changes.
3. **Lint the spec:**
   ```bash
   pnpm dlx @redocly/cli lint api/openapi.yaml
   ```
   No errors. Warnings should be acknowledged in PR description.
4. **Generate clients:**
   ```bash
   pnpm openapi:generate    # produces packages/sdk-ts/* and apps/studio/lib/api/*
   ```
   Both must build clean.
5. **Schema invariants:**
   - Every error response references one of the canonical `#/components/responses/...`.
   - Every list endpoint has `next_cursor` + `limit` parameters.
   - Every POST/PATCH/DELETE accepts `Idempotency-Key` header.
   - Every endpoint has `summary` and at least one tag.
   - `oneOf` types use `discriminator.propertyName`.
6. **Commit:** `api/openapi.yaml` + the regenerated TS client + the Studio API lib in the same PR.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Spec regenerated from Pydantic.
- [ ] Lints clean.
- [ ] TS client + Studio API lib regenerated and built.
- [ ] Manual additions (examples, descriptions) preserved if you regenerated.
- [ ] All error paths reference canonical responses.
- [ ] Pagination + idempotency invariants intact.

## Anti-patterns

- ❌ Hand-editing schemas that Pydantic owns.
- ❌ Skipping client regeneration.
- ❌ Missing examples on POST endpoints (they help SDK docs).
- ❌ Inconsistent error envelope.

## Related skills

- `data/add-pydantic-type.md`.
- `api/add-rest-endpoint.md`.

## References

- `api/openapi.yaml`.
