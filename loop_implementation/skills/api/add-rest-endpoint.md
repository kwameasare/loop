---
name: add-rest-endpoint
description: Use when adding a new REST endpoint — FastAPI handler, OpenAPI schema, Pydantic models, auth scope, error responses, and tests, in one PR.
when_to_use: |
  - Adding a new path under /v1/...
  - Adding a new method to an existing path (POST/PATCH/DELETE).
  - Adding a streaming variant (?stream=true) — also see api/add-streaming-event.md.
required_reading:
  - api/openapi.yaml
  - architecture/AUTH_FLOWS.md       # §8 authorization scopes
  - engineering/SECURITY.md          # §5–§6 auth + RBAC
  - engineering/ERROR_CODES.md
  - data/SCHEMA.md                   # §9 Pydantic models
applies_to: api
owner: Founding Eng #2 (Infra)
last_reviewed: 2026-04-29
---

# Add REST endpoint

## Trigger

Any new public endpoint or new method on an existing path. Endpoints are public contract — get auth, error envelope, and OpenAPI right.

## Required reading

1. `api/openapi.yaml` — every endpoint's pattern.
2. `architecture/AUTH_FLOWS.md` §8 — scope catalog.
3. `engineering/SECURITY.md` §5–§6 — RBAC, deny-by-default, RLS context.
4. `engineering/ERROR_CODES.md` — `LOOP-API-NNN` and service-specific codes.

## Steps

1. **Design the contract first.** Add the entry to `api/openapi.yaml`:
   - Path, method, tags, summary, parameters, requestBody, responses (200, 4xx, 5xx).
   - Use existing schemas where possible (`#/components/schemas/...`).
   - Include rate-limit headers (`X-RateLimit-*`) and `Idempotency-Key` (POST) where applicable.
   - Error responses must reference `#/components/responses/<NotFound|Unauthorized|RateLimited|...>`.
2. **Pydantic models** (request + response): add to `data/SCHEMA.md` §9 if new. Apply `data/add-pydantic-type.md` for any change.
3. **Handler** in `apps/control-plane/cp_api/routes/<feature>.py`:
   ```python
   @router.post(
       "/agents/{agent_id}/something",
       response_model=Something,
       status_code=201,
       responses={401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}},
   )
   @require("agents:write")
   async def create_something(
       agent_id: UUID,
       body: SomethingCreate,
       ctx: AuthContext = Depends(get_auth_context),
       idem: str | None = Header(default=None, alias="Idempotency-Key"),
   ) -> Something:
       ...
   ```
4. **Authorization:** every endpoint gets `@require(scope, ...)`. Anonymous endpoints are an explicit exception (health, public KB search if enabled by workspace).
5. **RLS context:** the auth dependency sets `loop.workspace_id` on the connection. Verify with an integration test.
6. **Idempotency** for POST/PATCH/DELETE: support `Idempotency-Key`. Store in Redis `loop:idem:<workspace>:<key>` with 24h TTL; if replayed with different body, return `LOOP-API-002`.
7. **Pagination** (for list endpoints): cursor-based. Response includes `next_cursor` (nullable). Default limit 50, max 500.
8. **Errors:** raise `LoopError` subclasses with `LOOP-API-NNN` codes. The framework converts to RFC 9457 envelopes.
9. **Streaming** (when applicable): also apply `api/add-streaming-event.md`.
10. **Audit log:** if the endpoint is admin-relevant, apply `security/add-audit-event.md`.
11. **Tests:**
    - Unit: handler logic with stubbed deps.
    - Integration: full stack including auth, scope check, RLS, idempotency.
    - Cross-tenant negative test: token from workspace A → 404 (not 403, to avoid information leak about resource existence).
    - 4xx happy paths: bad body → 400, missing scope → 403, missing token → 401, rate-limited → 429.
12. **Docs:**
    - `api/openapi.yaml` — committed in the same PR.
    - `engineering/ERROR_CODES.md` — if new codes.
    - `engineering/ENV_REFERENCE.md` — if new config knobs.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] OpenAPI updated; CI generates client SDK matches.
- [ ] Handler decorated with `@require(scope)`.
- [ ] Idempotency-Key handled (POST/PATCH/DELETE).
- [ ] Pagination (list endpoints).
- [ ] RFC 9457 error envelope on every error path.
- [ ] Cross-tenant negative test included.
- [ ] Rate-limit headers emitted.
- [ ] Audit-log event emitted for admin actions.
- [ ] Pyright strict + ruff clean.
- [ ] Documented in OpenAPI summary + description.

## Anti-patterns

- ❌ Anonymous endpoint without explicit allow.
- ❌ Returning `403` instead of `404` for cross-tenant access (leaks existence).
- ❌ Hand-rolled error JSON. Always RFC 9457.
- ❌ Skipping `Idempotency-Key` on POST.
- ❌ Page size unbounded.
- ❌ OpenAPI spec drifting from handler. Both must change in the same PR.

## Related skills

- `api/update-openapi.md`, `api/add-streaming-event.md`.
- `data/add-pydantic-type.md`.
- `security/add-audit-event.md`, `security/add-error-code.md`.
- `testing/write-integration-test.md`.

## References

- `api/openapi.yaml`.
- `architecture/AUTH_FLOWS.md` §8.
- `engineering/SECURITY.md` §5–§6.
- `engineering/ERROR_CODES.md`.
