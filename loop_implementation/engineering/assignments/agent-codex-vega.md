# Agent: codex-vega — gateway / dp critical path + billing accuracy

**Theme**: every dollar of LLM spend goes through the gateway. The
P1 items here are correctness + safety on that path: idempotency,
provider failover, retry hygiene, Decimal billing, error-code
distinction, rate limiting.

**Branch convention**: `agent/codex-vega/<slug>`.

---

## Item 1 — Redis-backed gateway idempotency cache (P1.1)

**File**: `packages/gateway/loop_gateway/client.py:18-44`.

**Audit finding**:
> `_IdempotencyCache` is in-process only. With multiple gateway pods
> a retried `request_id` will be re-streamed and double-billed.

**Acceptance**:
1. New `packages/gateway/loop_gateway/idempotency_redis.py`
   implementing the same `_IdempotencyCache` Protocol against
   `redis-py`'s `SETNX` with TTL.
2. Wire into `GatewayClient.__init__` via env: `LOOP_GATEWAY_REDIS_URL`
   when set ➜ Redis backend; else in-process (dev / single-pod).
3. Tests using `fakeredis` to verify atomic claim, TTL, and the
   cross-pod scenario (two GatewayClient instances against the same
   `fakeredis` server should not both stream).
4. Add `redis>=5` and `fakeredis>=2.20` to gateway `pyproject.toml`.

**Effort**: ~0.5 day, 1 PR.

---

## Item 2 — Decimal everywhere in providers (P1.2)

**Files**:
- `packages/gateway/loop_gateway/providers/openai.py:71-72`
- `packages/gateway/loop_gateway/providers/anthropic.py:75`
- `packages/gateway/loop_gateway/cost.py:151-155` (`with_markup`)

**Audit finding**:
> `with_markup` returns a `float` rounded to 5 decimals; `cost_decimal.py`
> exists but providers still call the float `with_markup`. Float drift
> compounds in rollups.

**Acceptance**:
1. Both provider modules switch to `cost_decimal.cost_for_decimal` +
   `with_markup_decimal`.
2. `GatewayDone.cost_usd` field type changes from `float` to
   `Decimal`. Pydantic 2 round-trips Decimal as a JSON string by
   default (matches the budgets shape from #191).
3. Update every consumer in `packages/data-plane`, `packages/runtime`
   to handle `Decimal` (mostly already does via the cost-rollup path).
4. Regression tests pinning the float→Decimal conversion: a stream of
   1M turns of `0.0000001` accumulates to `0.1` exactly with Decimal
   and to `~0.0999...` with float; the test asserts the Decimal sum.

**Effort**: ~1 day, 1 PR.

---

## Item 3 — `ProviderFailoverRunner` wired into dp-runtime (P1.6)

**Files**:
- `packages/gateway/loop_gateway/provider_routing.py:221-281` (already exists)
- `packages/data-plane/loop_data_plane/_runtime_config.py:84-92`

**Audit finding**:
> `build_gateway` constructs a plain `GatewayClient`, hard-coded
> OpenAI+Anthropic, no failover. Per-vendor outage = total turn
> failure.

**Acceptance**:
1. `build_gateway()` returns a `ProviderFailoverRunner` configured
   with both OpenAI + Anthropic transports + a `ProviderRouter` that
   prefers the catalog-pinned vendor first, falls back on 5xx /
   timeout / circuit-breaker-open.
2. New env knob `LOOP_GATEWAY_FAILOVER_ENABLED=1` (default on); off
   reverts to the plain `GatewayClient` for tests / sandboxes.
3. Integration test under `packages/data-plane/_tests_integration/`
   that boots two `httpx.MockTransport` providers — one returning 503
   on every call — and asserts the runner falls over to the second.

**Effort**: ~1 day, 1 PR.

---

## Item 4 — SSE cancellation propagation (P1.7)

**File**: `packages/data-plane/loop_data_plane/_turns.py:82-101`.

**Audit finding**:
> SSE stream cancellation is not propagated to the upstream provider
> call. If the client disconnects, `executor.execute(...)` continues
> to drain the provider stream, racking up cost.

**Acceptance**:
1. Wrap the `stream_turn_sse` async generator with an
   `asyncio.shield` + `request.is_disconnected()` poll on every yield.
2. On detected disconnect, cancel the inner `executor.execute(...)`
   task with a `TurnCancelledError`. The provider transport's
   `httpx.AsyncClient` context manager will tear down the upstream
   connection on unwind.
3. Audit: emit a `turn:cancelled` event with the partial token-count
   so cost rollups can still bill the prefix.
4. Tests: drive a fake provider that yields tokens slowly, simulate
   a client disconnect, assert provider-call was cancelled within
   N ms.

**Effort**: ~1 day, 1 PR.

---

## Item 5 — Retry backoff jitter + Retry-After honoring (P1.5)

**File**: `packages/gateway/loop_gateway/providers/httpx_transport.py:77,102,106`.

**Audit finding**:
> Retry backoff is `0.05 * (attempt + 1)` (linear, no jitter), capped
> by `LOOP_GATEWAY_HTTP_MAX_RETRIES` (default 2). On a synchronized
> 429 wave every gateway pod retries at the same instant.

**Acceptance**:
1. Replace linear backoff with exponential + full jitter:
   `random.uniform(0, base_ms * 2**attempt)`.
2. Honour `Retry-After` header on 429 / 503 responses (parse both
   the seconds-int and HTTP-date forms).
3. Add `LOOP_GATEWAY_HTTP_MAX_RETRY_DELAY_MS` cap (default 30 000).
4. Tests: provider returns 429 with `Retry-After: 5`; assert the
   client waits ≥5s before retry. Provider returns 429 without
   `Retry-After`; assert exponential jitter window respected.

**Effort**: ~0.5 day, 1 PR.

---

## Item 6 — Distinguished `TurnExecutionError` codes (P1.8)

**File**: `packages/data-plane/loop_data_plane/_turns.py:25-29`.

**Audit finding**:
> `TurnExecutionError(RuntimeError)` carries a class-level
> `code = "LOOP-RT-501"` only. Every failure (rate limit, bad model,
> upstream 5xx, BYO-key missing) maps to the same 502.

**Acceptance**:
1. Subclass hierarchy:
   - `BudgetExceededError("LOOP-RT-401", 429)`
   - `UpstreamProviderError("LOOP-RT-402", 502)` — wraps 5xx from provider
   - `BadTurnRequestError("LOOP-RT-403", 400)` — schema/validation issues
   - `MissingBYOKeyError("LOOP-RT-404", 401)` — workspace has no key for the requested vendor
2. Each raise site in the dp+runtime updates to the right subclass.
3. The runtime's HTTP error mapping uses the per-class `code` +
   `status` so callers see distinct responses.
4. Update `tests/test_runtime_app.py` + audits for each path.

**Effort**: ~1 day, 1 PR.

---

## Item 7 — Streaming-error envelope redaction (P0.3 from core-backend audit)

**File**: `packages/data-plane/loop_data_plane/_turns.py:96-101, 117-118`.

**Audit finding**:
> Streaming path emits the upstream message verbatim in an `error`
> SSE frame. Provider error messages frequently echo prompt fragments,
> account-id strings, and full upstream stack traces — leaking to any
> HTTP caller.

**Acceptance**:
1. Replace `message=str(exc)` with the same redaction the cp uses:
   look up the exception type in a registry → return
   `{code, message: "<class default>", request_id}`. Full details go
   to `logger.error` server-side only.
2. Tests covering: provider 5xx with sensitive body → SSE error frame
   does NOT include the body; provider 401 → maps to LOOP-GW-101
   with no leak.

**Effort**: ~0.5 day, 1 PR.

---

## Item 8 — Rate-limiting wired into FastAPI (P1.11)

**Files**:
- `packages/gateway/loop_gateway/rate_limit.py` (already exists)
- `packages/gateway/loop_gateway/plan_limits.py` (already exists)
- cp + dp + gateway FastAPI apps need middleware

**Audit finding**:
> No rate-limiting wired into FastAPI request path. A single API key
> can hammer `/v1/turns` with no per-workspace cap.

**Acceptance**:
1. New `loop_control_plane/middleware_rate_limit.py` —
   `RateLimitMiddleware` keyed by (workspace_id, route_template),
   token-bucket via Redis (falls back to in-process for dev).
2. Per-plan defaults in `plan_limits.py`; a workspace's plan name
   determines the per-route quota.
3. Wire into both `cp.app.create_app` and `dp.runtime_app.create_app`.
4. Integration tests: 1000 RPS to `/v1/turns/stream` from one
   workspace lands ~10/s through; HTTP 429 with `Retry-After` header
   on the rest.

**Effort**: ~1 day, 1 PR.

---

## Item 9 — `COST_TABLE` TTL + sync hook (P1.3)

**File**: `packages/gateway/loop_gateway/cost.py`.

**Audit finding**:
> `COST_TABLE` is a static module-level dict last updated 2026-04. No
> publication date / TTL / refresh hook tied to the model catalog.
> New frontier models will be under-billed.

**Acceptance**:
1. Add `COST_TABLE_REFRESHED_AT` constant (manual edit at bump time).
2. New `cost_health_check()` function that flags entries older than
   90 days as "stale".
3. CI workflow `cost-table-staleness.yml` runs weekly and opens an
   issue if any entry is >60 days old.
4. Test pinning the format of the constant.

**Effort**: ~0.5 day, 1 PR.

---

## Item 10 — `FALLBACK_MODELS` consistency + tighten (P1.4)

**File**: `packages/gateway/loop_gateway/model_catalog.py:135-146,269`.

**Audit finding**:
> `FALLBACK_MODELS["openai"]["balanced"]` includes `gpt-4-turbo` but
> `_BEST_MARKERS` puts `-turbo` in `best`. Bundled fallback
> contradicts the classifier. `FALLBACK_MODELS["openai"]["best"]` is
> identical to `balanced`.

**Acceptance**:
1. Remove `gpt-4-turbo` from balanced; add to best.
2. Populate `best` list with actual frontier ids
   (`gpt-4o`/`gpt-4.1`/`o3` once priced in `COST_TABLE`).
3. Add a contract test asserting `FALLBACK_MODELS[v][p][0]`'s
   classifier output equals `p` for every (vendor, profile).

**Effort**: ~0.5 day, 1 PR.

---

## Item 11 — RS256 / JWKS IdP path (P1: HS256→RS256)

**File**: `packages/control-plane/loop_control_plane/_routes_auth.py:29-33`.

**Audit finding**:
> auth-exchange uses `HS256Verifier` with secret read from
> `LOOP_CP_LOCAL_JWT_SECRET`. Symmetric secret leaks to anyone who
> can verify; no JWKS rotation. Threat model claims PASETO + SAML;
> reality is symmetric HMAC.

**Acceptance**:
1. New `RS256JWKSVerifier` class against the Auth0 tenant's
   `https://<tenant>/.well-known/jwks.json`.
2. cp app picks RS256 when `LOOP_CP_AUTH_MODE=auth0`, falls back to
   HS256 when `=local-dev` (default in dev). Env-var must be
   present in production or the app refuses to start.
3. Tests with self-minted RSA + faked JWKS.

**Effort**: ~1 day, 1 PR.

---

## Item 12 — OpenAPI spec drift contract test (P1.14)

**File**: new `tests/test_openapi_drift.py`.

**Audit finding**:
> `loop_implementation/api/openapi.yaml` documents 30+ endpoints. The
> P0.4 batch closed most of them; need a contract test that diffs
> spec ↔ FastAPI `app.openapi()`.

**Acceptance**:
1. Test loads `openapi.yaml`, loads `cp.app.openapi()`, computes the
   set difference of route paths. Failing assertion lists the
   delta.
2. Allowlist file `tests/openapi_drift_allowlist.txt` for routes the
   spec INTENTIONALLY omits (none today; preserved as the
   pressure-relief valve).

**Effort**: ~0.5 day, 1 PR.

---

## Item 13 — Routes enforce `required_role` (security audit P1.11)

**Audit finding**:
> Every `_routes_*.py` calls `authorize_workspace_access(...)` with
> `required_role=None`. A `VIEWER` can `DELETE /v1/agents/{id}`.

**Acceptance**:
1. Audit every existing mutating route in `_routes_agents.py`,
   `_routes_workspaces.py` (the pre-P0.4 bulk) and pass
   `required_role=Role.ADMIN` (or OWNER) where appropriate. The new
   P0.4 routes already do this.
2. Add a new test `tests/test_role_enforcement.py` that walks every
   FastAPI route via `app.routes` and asserts each mutating method
   is gated.

**Effort**: ~0.5 day, 1 PR.

---

## Item 14 — `audit_completeness` route-walking test (P0.7a follow-on)

**Audit finding**: the AUDIT_COMPLETENESS doc was paper-only. Replace
with a runtime test.

**Acceptance**:
1. New `tests/test_audit_completeness.py` that walks every mutating
   FastAPI route and inspects the source for a `record_audit_event`
   call. Uses `ast` to parse and check.
2. Allowlist: routes that legitimately don't audit (read-only,
   health checks).

**Effort**: ~0.5 day, 1 PR.

---

## Acceptance summary for codex-vega

14 items, ~10-12 PRs, ~9-10 days. After your work:

- [x] Multi-pod gateway dedup is real (Redis).
- [x] Billing flows through Decimal end-to-end.
- [x] Per-vendor outage doesn't kill turns.
- [x] Client disconnect tears down upstream.
- [x] Retry storm safe (jitter + Retry-After).
- [x] Errors map to distinct codes; no upstream-message leakage.
- [x] Per-workspace rate limits enforced.
- [x] Cost table staleness alerts.
- [x] Fallback list classifier-consistent.
- [x] IdP path is RS256 with JWKS rotation.
- [x] OpenAPI spec ↔ FastAPI contract test in CI.
- [x] Every mutating route enforces a role gradient.
- [x] Audit emission is enforced by a route-walking test.
