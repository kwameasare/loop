---
name: implement-multi-agent-pattern
description: Use when implementing multi-agent orchestration primitives — Supervisor, Pipeline, Parallel (fanout-fanin), AgentGraph (cyclic). For changes to packages/runtime/loop/runtime/multi_agent/.
when_to_use: |
  - Adding a new orchestration pattern.
  - Modifying handoff semantics between agents.
  - Implementing or changing the shared blackboard (Redis-backed) for multi-agent coordination.
  - Adding multi-agent debugging/visualization in Studio.
required_reading:
  - architecture/ARCHITECTURE.md     # §9.13 multi-agent
  - data/SCHEMA.md                   # session/blackboard tables
  - engineering/HANDBOOK.md          # §2.1 Python conventions
  - adrs/README.md                   # ADR-014 (episodic memory pinning)
applies_to: coding
owner: Founding Eng #1 (Runtime)
last_reviewed: 2026-04-29
---

# Implement multi-agent pattern

## Trigger

Touching `packages/runtime/loop/runtime/multi_agent/`. Multi-agent is the M9 GA milestone — get the primitives right.

## Required reading

1. `architecture/ARCHITECTURE.md` §9.13 (the four patterns: Supervisor, Pipeline, Parallel, AgentGraph).
2. The "agent" definition in `engineering/GLOSSARY.md`.

## Steps

1. **Pattern semantics — what the customer sees:**
   ```python
   # Supervisor
   supervisor = Supervisor(
       workers=[support, billing, escalation],
       routing="llm",                # or "rule" or callable
   )

   # Pipeline (sequential)
   pipeline = Pipeline([extract, classify, respond])

   # Parallel (fanout-fanin)
   fanout = Parallel(
       [sentiment, intent, language],
       merge=combine_results,
   )

   # Graph (cycles allowed)
   graph = AgentGraph()
   graph.edge(intake, triage)
   graph.edge(triage, support, when=lambda s: s.category == "support")
   graph.edge(support, intake, when=lambda s: s.needs_clarification)
   ```
2. **State sharing.** Two options, declared explicitly:
   - **Blackboard** — Redis-backed shared memory; reads/writes are typed via Pydantic. Versioned to detect concurrent updates (optimistic).
   - **Typed messages** — NATS subjects per workflow; each agent publishes to its outbox + subscribes to its inbox.
3. **Handoff visibility.** Every handoff emits a `TurnEvent(type="handoff", payload={"from": ..., "to": ..., "reason": ...})` so traces can render the cross-agent flow.
4. **Loop detection** for `AgentGraph` cycles:
   - `max_cycles` per workflow (default 5). Hitting it raises `LoopError("LOOP-RT-304")`.
   - Per-cycle state hash; if state hasn't changed, abort early.
5. **Cost accounting.** Each agent's cost rolls up into the workflow-level cost. Per-workflow budgets (`max_cost_usd_workflow`) — defaults to sum of per-agent budgets if unset.
6. **Tests:**
   - Unit: each pattern with stub agents.
   - Integration: real agents calling each other via NATS, verify handoff events.
   - Eval: at least one suite case per pattern.
7. **Studio visualization** (M9+): the Trace view's waterfall extends to show cross-agent spans grouped by agent_name.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Pattern API documented with code examples.
- [ ] State-sharing mechanism explicit (blackboard or message).
- [ ] Handoff events emitted.
- [ ] Cycle detection in graph patterns.
- [ ] Cost rolls up at workflow level.
- [ ] Studio waterfall renders correctly.

## Anti-patterns

- ❌ Hidden orchestration. The black-box LMSz is what we're explicitly NOT building.
- ❌ Cycles without `max_cycles`.
- ❌ Implicit shared state via process globals.
- ❌ Handoffs that bypass tracing.

## Related skills

- `coding/implement-runtime-feature.md`.
- `observability/add-otel-span.md`.
- `testing/write-eval-suite.md`.

## References

- `architecture/ARCHITECTURE.md` §9.13.
- ADR-014 (episodic memory region pinning).
