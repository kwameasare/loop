---
name: write-integration-test
description: Use whenever you touch a public API path, DB write, NATS publish, or cross-service call.
when_to_use: |
  - Adding/changing a REST endpoint.
  - DB migration.
  - Cross-service flow (channel → runtime → gateway → DB).
  - Idempotency or RLS behavior change.
required_reading:
  - engineering/TESTING.md   # §3
  - data/SCHEMA.md           # §3.4 RLS
applies_to: testing
owner: package owner
last_reviewed: 2026-04-29
---

# Write integration test

## Trigger

Any public API path or cross-service flow.

## Required reading

`engineering/TESTING.md` §3.

## Steps

1. **Boot the stack:** the `pytest_plugin` in `tests/conftest.py` brings up docker-compose (Postgres + Redis + Qdrant + NATS + MinIO + ClickHouse + OTel collector) lazily on the first integration test.
2. **Fixtures:**
   - `workspace_factory` — fresh tenant, returns `(workspace_id, api_token)`.
   - `agent_factory` — deploys a no-op agent.
   - `mock_llm_gateway` — VCR-cassette-backed gateway.
3. **Assert at all layers:**
   - Status code + response shape.
   - Persisted state (Postgres rows, Redis keys, Qdrant points).
   - Audit log entry (if admin action).
   - OTel span emitted.
4. **RLS isolation test** — every endpoint that touches a tenanted table:
   - With token A, write to workspace A.
   - With token B, attempt to read it → 404, not 403.
5. **Idempotency** test (POST/PATCH/DELETE):
   - Same `Idempotency-Key` + same body → same result, single side effect.
   - Same `Idempotency-Key` + different body → 409 `LOOP-API-002`.
6. **Speed budget**: ≤ 5 minutes for the full integration suite.
7. **Cleanup:** rely on workspace-scoped teardown — every test uses a fresh workspace; the docker-compose stack persists.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Stack boot covered by `conftest.py`.
- [ ] Cross-tenant negative test included.
- [ ] Idempotency test (POST/PATCH/DELETE).
- [ ] Persistence verified at the storage layer.
- [ ] Audit log + OTel span asserted where applicable.
- [ ] Suite passes within 5 min.

## Anti-patterns

- ❌ Skipping RLS test "because the unit test covers it." It doesn't.
- ❌ Sharing state across tests.
- ❌ Real network calls to LLM providers — always cassettes.
- ❌ Test relying on docker port collisions resolving "naturally."

## Related skills

- `testing/write-unit-test.md`, `testing/write-e2e-test.md`.

## References

- `engineering/TESTING.md` §3.
