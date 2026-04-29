---
name: add-otel-span
description: Use when adding OTel tracing to a code path. Every async operation in Loop has a span — no exceptions.
when_to_use: |
  - Adding any new async function in runtime/gateway/channels/kb-engine.
  - Wrapping a tool dispatch or external call.
  - Replacing a manual log statement with structured tracing.
required_reading:
  - architecture/ARCHITECTURE.md   # §7.5 observability stack
  - engineering/HANDBOOK.md         # §5 observability culture
applies_to: observability
owner: Founding Eng #4 (Observability)
last_reviewed: 2026-04-29
---

# Add OTel span

## Trigger

Any new async path in core services. Loop's debug story depends on universal tracing.

## Required reading

`architecture/ARCHITECTURE.md` §7.5; `engineering/HANDBOOK.md` §5.

## Steps

1. **Use the canonical helper:**
   ```python
   from loop.observability import tracer

   async with tracer.span("turn.memory.load", kind="memory") as span:
       span.set_attr("workspace_id", str(ws_id))
       span.set_attr("conversation_id", str(conv_id))
       result = await load_memory(...)
       span.set_attr("memory.session_keys", len(result.session))
   ```
2. **Span kinds (canonical):** `llm`, `tool`, `retrieval`, `memory`, `channel`. Use these exactly; dashboards filter on them.
3. **Required attrs on every span:** `workspace_id`, `agent_id`, `conversation_id`, `turn_id` (when applicable).
4. **Rich attrs you should add:**
   - LLM: `provider`, `model`, `input_tokens`, `output_tokens`, `cost_usd`.
   - Tool: `tool_name`, `tool_server`, `cost_usd`, `latency_ms`.
   - Retrieval: `kb_id`, `top_k`, `confidence_max`.
   - Channel: `channel_type`, `direction` (inbound/outbound).
5. **Errors:** the helper auto-records exceptions. Add `loop.error.code` attr per `engineering/ERROR_CODES.md`.
6. **Sampling:** prod default 100% on error spans, 10% on success in non-Enterprise plans (set via `LOOP_OTEL_SAMPLING_RATE`). Don't override in code.
7. **Backpressure:** never emit a span synchronously in a hot loop. Use the `BatchSpanProcessor`.
8. **Tests:** assert at least one span was emitted with the right kind + attrs (use the in-memory exporter fixture).

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Span uses the canonical `tracer.span()` helper.
- [ ] Required attrs present.
- [ ] Span kind from the canonical list.
- [ ] Errors carry `loop.error.code`.
- [ ] Test asserts emission.

## Anti-patterns

- ❌ Custom span kinds.
- ❌ Spans without `workspace_id`.
- ❌ Logging through both `logger.info` and a span (pick one).
- ❌ Synchronous span exports.

## Related skills

- `observability/add-metric.md`.
- `security/add-error-code.md`.

## References

- `architecture/ARCHITECTURE.md` §7.5.
