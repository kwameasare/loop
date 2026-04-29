---
name: add-streaming-event
description: Use when adding a new streamed event type (SSE/WebSocket) — token deltas, tool_call_start/end, retrieval, trace, degrade, complete, etc.
when_to_use: |
  - Adding a TurnEvent variant.
  - Adding a Studio live-tail event.
  - Adding a deploy progress event.
required_reading:
  - api/openapi.yaml
  - architecture/ARCHITECTURE.md   # §3.1 streaming-first
  - data/SCHEMA.md                 # §9 TurnEvent type
  - adrs/README.md                 # ADR-018 (SSE default, WS opt-in)
applies_to: api
owner: Founding Eng #1 (Runtime)
last_reviewed: 2026-04-29
---

# Add streaming event

## Trigger

You're adding a variant to `TurnEvent` or another streamed envelope.

## Required reading

1. ADR-018 (SSE default, WebSocket only when bidirectional <100ms).
2. `data/SCHEMA.md` §9 — `TurnEvent` is a discriminated union.

## Steps

1. **Pick the right channel:**
   - **SSE**: server→client unidirectional. Default for tokens, traces, deploy events.
   - **WebSocket**: bidirectional + <100ms. Voice signaling, operator-inbox live takeover.
2. **Discriminated union:** add the new variant to the `Literal[...]` of the `type` field.
   ```python
   class TurnEvent(BaseModel):
       type: Literal["token", "tool_call", "retrieval", "trace", "degrade", "complete", "<your_new_type>"]
       payload: <YourPayloadModel>
       ts: datetime
   ```
3. **Payload model:** define a Pydantic model for the payload. Apply `data/add-pydantic-type.md` if it's new.
4. **Wire format (SSE):**
   ```
   event: token
   id: <ulid>
   data: {"type":"token","payload":{"text":"hello"},"ts":"2026-04-29T14:00:00Z"}
   ```
   - `id` is a ULID for client resumability.
   - `event` mirrors `type` for consumers using EventSource APIs.
5. **Wire format (WebSocket):** identical JSON envelope, no `event:` prefix.
6. **Backpressure:** server flushes after every event. If the client is slow (lag > 5s), the server drops to a slower stream rate or disconnects with `LOOP-GW-402`.
7. **Order guarantees:** events within a single conversation_id are strictly ordered. Across conversations, no guarantee.
8. **Resumability:** clients can `?last_event_id=<ulid>` to resume from the last seen event. Server replays from NATS retention (30 min default).
9. **OpenAPI:** document the SSE schema as a string with `text/event-stream` content type. Include a description of every event type the endpoint emits.
10. **Tests:**
    - Unit: serialization round-trip per variant.
    - Integration: long-lived SSE connection that receives every event type in order.
    - Resumability test: drop, reconnect with `last_event_id`, receive deltas only.
11. **Docs:** update `api/openapi.yaml` description for the streaming endpoint. Add to `data/SCHEMA.md` §9.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] New variant in `TurnEvent`'s Literal union.
- [ ] Payload Pydantic model defined.
- [ ] SSE wire format follows the canonical shape.
- [ ] Order + resumability tested.
- [ ] OpenAPI description updated.
- [ ] Backpressure behavior covered by an integration test.

## Anti-patterns

- ❌ Inventing a new envelope shape per endpoint.
- ❌ Emitting events without `ts`.
- ❌ WebSocket for unidirectional traffic.
- ❌ Skipping backpressure handling on the server.

## Related skills

- `data/add-pydantic-type.md`.
- `api/update-openapi.md`.

## References

- ADR-018.
- `data/SCHEMA.md` §9.
