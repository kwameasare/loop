---
name: implement-llm-gateway-change
description: Use when modifying the LLM gateway — providers, semantic cache, cost accounting, model aliases, retries, fallback, hard caps. Triggers on changes under packages/gateway/.
when_to_use: |
  - Adding a new LLM provider (e.g., Mistral, Groq).
  - Changing the cost accounting formula (input/output token rates, surcharges).
  - Adjusting the semantic cache (similarity threshold, TTL, key shape).
  - Changing model alias resolution (`fast` / `cheap` / `best` mappings).
  - Adding/changing the graceful-degrade path (fallback model, cap behavior).
  - Touching the `request_id` idempotency window.
required_reading:
  - architecture/ARCHITECTURE.md       # §2.2, §5.2 cache, §7.3 cost accounting
  - engineering/HANDBOOK.md             # §2.1 Python
  - engineering/PERFORMANCE.md          # §1 budgets
  - engineering/ENV_REFERENCE.md        # §3 Gateway vars
  - engineering/ERROR_CODES.md          # GW prefix
  - adrs/README.md                      # ADR-012, ADR-022, ADR-028
applies_to: coding
owner: Founding Eng #1 (Runtime)
last_reviewed: 2026-04-29
---

# Implement LLM gateway change

## Trigger

You are modifying `packages/gateway/`. The gateway is the only chokepoint for LLM cost; any change can shift the bill across the whole customer base. The 5% disclosed margin (ADR-012) is sacred.

## Required reading

1. `architecture/ARCHITECTURE.md` §5.2 (Redis cache config), §7.3 (cost accounting).
2. `engineering/ENV_REFERENCE.md` §3 (every gateway env var).
3. `engineering/ERROR_CODES.md` §"LLM Gateway (GW)".
4. `engineering/PERFORMANCE.md` §1.2 ("LLM gateway dispatch overhead ≤ 10ms p99").
5. ADR-012 (pricing model), ADR-022 (idempotency), ADR-028 (meter precision).

## Steps

1. **Provider additions** — when adding `Mistral`, `Groq`, etc.:
   - Add a `Provider` implementation under `packages/gateway/loop/gateway/providers/<name>.py`.
   - Implement: `stream()`, `cost_for(input_tokens, output_tokens, model)`, `health_check()`.
   - Register the provider's models in the model-alias registry (`packages/gateway/loop/gateway/aliases.py`).
   - Pin documented rates from the provider's pricing page; cite the URL in a comment.
2. **Cost accounting** changes (rates, surcharges, markup): tightly coupled to billing.
   - Update `packages/gateway/loop/gateway/cost.py`.
   - Verify the 5% markup is still applied exactly and disclosed in the response envelope.
   - Tests: `cost_for_model_X` round-trip, `cost_with_markup_disclosure`, `cost_breakdown_to_clickhouse`.
3. **Semantic cache** changes (key, threshold, TTL):
   - Update `packages/gateway/loop/gateway/cache.py`.
   - Cache key MUST include `(workspace_id, model, prompt_hash, params_hash)`. Cross-workspace cache hits are a P0 isolation bug.
   - Default similarity threshold = 0.97 (`LOOP_GATEWAY_CACHE_SIM_THRESHOLD`). Lowering it requires a perf-bench run + cost-savings estimate in the PR.
4. **Model alias resolution** — when adding/changing `fast`/`cheap`/`best`:
   - Aliases resolve by workspace plan + region availability + provider health.
   - Default alias mapping lives in `packages/gateway/loop/gateway/aliases.yaml`.
   - Workspace-level overrides (BYOK customers) loaded from Postgres on alias resolution.
5. **Graceful degrade**:
   - Triggered when `cost_usd_so_far + estimated_next_call > workspace.budget.hard_cap`.
   - Path: log `LOOP-RT-301`/`-302`/`-303`, swap to `LOOP_GATEWAY_FALLBACK_MODEL`, truncate history to fit, continue the turn.
   - Never raise on degrade — it must complete the turn.
6. **Hard caps** are enforced at the gateway layer, not the runtime layer (the runtime trusts the gateway). If you change cap semantics, also update `architecture/ARCHITECTURE.md` §7.3 and `engineering/SECURITY.md` §2.1.
7. **Idempotency** (`request_id`-keyed cache, ADR-022):
   - The cache window default = 600s (`LOOP_GATEWAY_REQUEST_ID_TTL_SECONDS`).
   - Any change to this window requires explicit reasoning in the PR (security + cost implication).
8. **Streaming**: every provider must stream tokens. Buffering whole responses is forbidden — we promise streaming-first.
9. **Tests**:
   - Unit per provider: stream parsing, cost calc, retry on 5xx, fallback on health-check fail.
   - Integration: full happy path against a recorded cassette.
   - Cassette refresh: see `testing/write-eval-suite.md` §"cassette refresh."
10. **Docs**: update `engineering/ENV_REFERENCE.md` §3, `architecture/ARCHITECTURE.md` §5.2 if cache shape changed, `engineering/ERROR_CODES.md` if new GW codes added.
11. **PR.** Apply `meta/write-pr.md`. Tag Eng #1 (owner). For cost-accounting changes: also tag CEO + finance.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] No cross-workspace cache key paths exist (test added).
- [ ] Markup remains 5%, disclosed in response.
- [ ] Streaming preserved (no buffered providers).
- [ ] Provider health-check + circuit breaker present.
- [ ] Per-call cost recorded to ClickHouse via `costs_turn` row.
- [ ] Fallback path returns `degrade` event, never raises.
- [ ] Idempotency cache window unchanged (or change justified).
- [ ] Pyright strict passes; ruff clean.
- [ ] Bench: dispatch overhead ≤ 10 ms p99.
- [ ] Tests at unit, integration, cassette.
- [ ] Docs updated.

## Anti-patterns

- ❌ Provider-specific code paths in the runtime. Runtime sees the gateway only.
- ❌ Caching across workspaces.
- ❌ Marking up tokens beyond 5% or hiding the markup from the response envelope.
- ❌ Buffering tokens "for performance."
- ❌ Hard-coding model strings in user-facing paths. Always go through aliases.
- ❌ Changing cost rates without citing the provider's pricing URL.

## Related skills

- Before: `architecture/propose-adr.md` for cost-model changes.
- After: `testing/write-integration-test.md`, `meta/write-pr.md`.
- Cross-cuts: `observability/add-otel-span.md`, `observability/add-metric.md` (provider health metrics), `security/add-error-code.md`.

## References

- ADR-012 (pricing), ADR-022 (idempotency), ADR-028 (precision).
- `engineering/ENV_REFERENCE.md` §3.
- `engineering/ERROR_CODES.md` §"GW".
