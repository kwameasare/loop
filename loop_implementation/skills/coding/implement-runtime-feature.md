---
name: implement-runtime-feature
description: Use when adding or modifying a feature in the agent runtime (TurnExecutor, reasoning loop, memory loader, hard caps, idempotency, streaming). Triggers on changes under packages/runtime/, packages/sdk-py/loop/, or anything touching the core agent execution path.
when_to_use: |
  - Modifying TurnExecutor.execute() or any of its helpers.
  - Changing how memory is loaded, persisted, or scoped.
  - Adjusting hard caps (max_iterations, max_cost_usd, max_runtime_seconds, max_tool_calls_per_turn, max_message_bytes).
  - Adding or changing a TurnEvent type emitted on the streaming channel.
  - Adding hooks (onBeforeMessage, onAfterTool, onIterationEnd, etc.).
  - Changing the idempotency model or warm-pool behavior.
required_reading:
  - architecture/ARCHITECTURE.md  # §3 components, §4.1–4.2 sequences, §9 NFRs
  - data/SCHEMA.md                # §3.1 conversations + turns, §3.2 memory
  - engineering/HANDBOOK.md       # §2.1 Python conventions, §6 perf budgets
  - engineering/PERFORMANCE.md    # §1 budgets, §1.2 hot paths
  - engineering/ERROR_CODES.md    # RT- prefix
  - engineering/SECURITY.md       # §2.1 STRIDE for runtime
  - adrs/README.md                # ADR-001, ADR-005, ADR-009, ADR-022, ADR-026
applies_to: coding
owner: Founding Eng #1 (Runtime)
last_reviewed: 2026-04-29
---

# Implement runtime feature

## Trigger

You are touching `packages/runtime/loop/runtime/` or the public types in `packages/sdk-py/loop/`. The runtime is the highest-blast-radius surface in Loop — every customer's agent runs through it. Move with care.

## Required reading

Read in order:

1. `architecture/ARCHITECTURE.md` §3 (component model) and §4 (sequence diagrams).
2. `data/SCHEMA.md` §3 (conversations, turns, memory tiers).
3. `engineering/PERFORMANCE.md` §1 (your change cannot exceed budgets).
4. `engineering/HANDBOOK.md` §2.1 (Python conventions: ruff, pyright strict, asyncio, Pydantic v2).
5. `engineering/ERROR_CODES.md` §"Runtime (RT)" — every new error class gets a code.
6. `engineering/SECURITY.md` §2.1 (the STRIDE table for the runtime; your change must not weaken any mitigation).
7. ADRs you're touching: especially ADR-001 (Python), ADR-022 (idempotency), ADR-026 (per-workspace process isolation).

## Steps

1. **Confirm scope.** Find the corresponding story ID in `tracker/TRACKER.md`. Reference it in the PR. If no story exists, propose one before writing code.
2. **If you're changing public Pydantic types** (anything in `packages/sdk-py/loop/types.py`): stop. Apply `data/add-pydantic-type.md`. This is a major SDK version bump.
3. **If you're changing reasoning-loop semantics** (iteration count, ordering of tool calls, when memory is persisted, when cost is checked): you need an ADR. Apply `architecture/propose-adr.md` first.
4. **Sketch the change in TurnExecutor.execute()** as pseudocode in the PR body before writing real code. Reviewers approve the shape, then you write it.
5. **Implement** in `packages/runtime/loop/runtime/turn_executor.py` (or new module if scope justifies). Constraints:
   - asyncio everywhere; no blocking calls. Use `httpx` not `requests`, `asyncio.sleep` not `time.sleep`.
   - All side-effecting calls go through injected dependencies in `RuntimeContext` — no global state.
   - Every async op gets an OTel span (apply `observability/add-otel-span.md`).
   - Pydantic v2 for any new struct.
   - Errors raise a `LoopError` subclass with a `LOOP-RT-NNN` code.
   - Idempotency: any change that affects whether retrying a turn is safe must preserve the `request_id`-keyed gateway cache window (ADR-022).
6. **Memory invariants:**
   - Loads use `MemoryLoader.load(event)`; persistence uses `MemoryLoader.persist_diff(event, memory)`. Do not write directly to Postgres or Redis.
   - Session memory must respect `LOOP_RUNTIME_MEMORY_TTL_SESSION_SECONDS` (default 24h).
   - User-tier writes are idempotent (UPSERT by `(workspace_id, agent_id, user_id, key)`).
   - Episodic-memory writes are append-only.
7. **Hard caps & graceful degrade:** every loop iteration checks `_over_budget(...)`. Hitting a cap emits a `TurnEvent(type="degrade", payload={"reason": ...})` and either swaps to the workspace's degrade model or terminates with a final `complete` event. Never drop mid-stream.
8. **Streaming:** emit `TurnEvent`s as they happen. The final event is always `type="complete"`. Tool-call events emit at start AND end so channels can render "calling Stripe…".
9. **Tests:**
   - Unit: cover every branch of `_over_budget`, every `TurnEvent` emission, idempotent retry behavior, error paths. Apply `testing/write-unit-test.md`.
   - Integration: at least one test that runs a full turn end-to-end against the docker-compose stack, including a tool call and a memory persist. Apply `testing/write-integration-test.md`.
   - Eval: if behavior changes (anything LLM-visible), add at least one eval case. Apply `testing/write-eval-suite.md`.
10. **Bench:** if you touched `TurnExecutor.execute`, the prompt builder, the memory loader, or the gateway client, run `pytest --benchmark-only -k <yourbench>`. Compare to `main`. Regression > 10% blocks merge. Apply `testing/perf-check.md`.
11. **Docs:**
   - If architecture changed (new component, new flow): update `architecture/ARCHITECTURE.md` in this PR.
   - If schema changed: update `data/SCHEMA.md` (apply `data/update-schema.md`).
   - If a new env var was added: update `engineering/ENV_REFERENCE.md`.
   - If a new error code was added: update `engineering/ERROR_CODES.md` (apply `security/add-error-code.md`).
12. **PR.** Apply `meta/write-pr.md`. Title with `feat(runtime):` or `fix(runtime):`. Reference the story ID. Tag Eng #1 (owner) and at least one of Eng #2 / Eng #4 as cross-team reviewer.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Story ID referenced in PR description.
- [ ] No cloud SDK imported (cloud-portability-check passes).
- [ ] Type-check (`uv run pyright`) passes in strict mode.
- [ ] Lint (`uv run ruff check`) passes.
- [ ] Unit suite passes; coverage of touched files ≥ 85%.
- [ ] Integration suite passes.
- [ ] Eval suite passes (if behavior changed).
- [ ] Bench shows no regression > 10% on relevant microbench.
- [ ] OTel span on every async op.
- [ ] Errors carry a `LOOP-RT-NNN` code.
- [ ] Architecture/schema/error-code/env-var docs updated in same PR.
- [ ] No mid-turn drops on budget cap (graceful degrade verified).
- [ ] Idempotency invariant preserved (test added).
- [ ] Memory writes go through `MemoryLoader` only.
- [ ] PR title is a Conventional Commit.

## Anti-patterns

- ❌ Sneaking in a Pydantic public-type change without bumping major SDK version.
- ❌ Adding a `time.sleep` or `requests` call. Always async.
- ❌ Reading memory directly from Postgres or Redis bypassing `MemoryLoader`.
- ❌ Hard-coding workspace IDs, region names, or model names.
- ❌ Letting a turn exceed `max_runtime_seconds` without yielding a `degrade` event.
- ❌ Throwing `Exception` or `RuntimeError` directly. Always a `LoopError` subclass with code.
- ❌ Adding a feature flag without registering it in `dp-feature-flag-service`.
- ❌ Skipping the integration test "because the unit test covers it." It doesn't.
- ❌ Logging the full prompt or response without redacting against the PII patterns from `engineering/SECURITY.md` §7.3.

## Related skills

- Often runs alongside: `coding/implement-llm-gateway-change.md`, `coding/implement-mcp-tool.md`, `data/add-pydantic-type.md`, `observability/add-otel-span.md`, `security/add-error-code.md`.
- Always followed by: `testing/write-unit-test.md`, `testing/write-integration-test.md`, `meta/write-pr.md`.

## References

- ADR-001 (Python primary), ADR-005 (Firecracker), ADR-009 (agent versioning), ADR-022 (idempotency), ADR-026 (process isolation).
- `architecture/ARCHITECTURE.md` §3, §4.
- `engineering/PERFORMANCE.md` §1.
- `engineering/ERROR_CODES.md` §3 (RT prefix).
