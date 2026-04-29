---
name: implement-channel-adapter
description: Use when adding a new channel (Discord, RCS, …) or modifying an existing one (web, WhatsApp, Slack, Teams, Telegram, SMS, email, voice). Triggers on changes under packages/channels/.
when_to_use: |
  - Adding a brand-new channel adapter to Loop.
  - Implementing webhook signature verification for an existing channel.
  - Implementing the `takeover()` HITL primitive on a channel.
  - Adding outbound formatting (Block Kit, Adaptive Cards, etc.).
  - Modifying voice pipeline stages (VAD, STT, TTS, barge-in).
required_reading:
  - architecture/ARCHITECTURE.md       # §3.5 channel layer, §4.1 web sequence, §4.2 voice sequence
  - architecture/AUTH_FLOWS.md         # §6 end-user channel auth, §7 webhook auth
  - architecture/NETWORKING.md         # §9 voice-specific networking
  - data/SCHEMA.md                     # §2.2 channel_configs, voice_calls
  - engineering/SECURITY.md            # §2.3 channel-adapter threat model
  - engineering/ERROR_CODES.md         # CH prefix
  - engineering/ENV_REFERENCE.md       # §4 channel adapter env vars
  - engineering/COPY_GUIDE.md          # for any user-facing string
  - ux/UX_DESIGN.md                    # operator inbox interactions for HITL
applies_to: coding
owner: Founding Eng #7 (Channel Integrations) — Eng #3 owns voice
last_reviewed: 2026-04-29
---

# Implement channel adapter

## Trigger

Touching `packages/channels/<name>/`. Channels are the DMZ-equivalent — they sit at the trust boundary. Get auth and idempotency right.

## Required reading

1. `architecture/AUTH_FLOWS.md` §6–§7. Every channel adapter MUST verify webhooks and dedupe.
2. `engineering/SECURITY.md` §2.3 — the threat table for channel adapters.
3. `engineering/ENV_REFERENCE.md` §4 — every channel has its own env subset.

## Steps

1. **Adapter contract.** Implement the protocol from `architecture/ARCHITECTURE.md` §3.5:
   ```python
   class ChannelAdapter(Protocol):
       async def receive(self) -> AsyncIterator[InboundEvent]: ...
       async def send(self, response: AgentResponse) -> None: ...
       async def takeover(self, agent_id: str, by: str) -> ConversationHandle: ...
   ```
2. **Inbound flow** (when the channel pushes):
   - Webhook endpoint at `/webhooks/<channel>/<workspace>/<agent>`.
   - Verify signature using the provider's algorithm (`AUTH_FLOWS.md` §7 table).
   - Reject unsigned in prod (`LOOP-CH-001`).
   - Dedupe by provider message_id or `Idempotency-Key` for 24h (`LOOP-CH-002`).
   - Translate provider payload → `AgentEvent` Pydantic model.
   - Publish to NATS subject `EVENTS.inbound.<workspace>.<agent>.<channel>`.
   - Return 202 within 1s.
3. **Outbound flow** (when the runtime sends):
   - Subscribe to `EVENTS.outbound.<workspace>.<agent>.<channel>`.
   - Translate `AgentResponse` → channel-native message format.
   - Stream tokens incrementally if the channel supports it (web SSE; Slack message updates; voice TTS).
   - Apply `engineering/COPY_GUIDE.md` to any auto-generated strings.
4. **End-user identity.** Each channel has its own scheme — see `AUTH_FLOWS.md` §6. Hash phone numbers / email addresses before storage if the workspace's PII config requires it.
5. **HITL takeover.** Every channel ships with a takeover path:
   - Web widget: built-in operator UI takes over the SSE stream.
   - Slack: `/takeover` slash command.
   - WhatsApp / Teams: operator can take over from the inbox; outbound messages then originate from the operator's identity (with the agent name preserved as display).
   - Voice: keyword "speak to a human" or operator click in inbox transfers the call to a human queue.
   - Audit-log every takeover with actor, target, reason.
6. **Voice channel — extra requirements** (apply when adapter type = voice):
   - Pipeline: SIP/WebRTC → VAD (Silero) → STT (Deepgram) → runtime → TTS (Cartesia/ElevenLabs).
   - Latency budget per `engineering/PERFORMANCE.md` §1.1: total ≤ 700ms p50.
   - Barge-in: detect speech during TTS, stop TTS, re-route to STT.
   - Recording: opt-in only; encrypted at rest with workspace KMS key.
   - SRTP/DTLS-SRTP for media; never plaintext.
   - Hot-keyword detection: every voice agent has at least one keyword that transfers to a human.
7. **Per-bot credential scoping.** Each agent has its own channel credentials (Slack bot token, WhatsApp BSP token, etc.). Stored in Vault, NOT in `channel_configs.config_json`. Reference via `secrets_ref`.
8. **Tests:**
   - Unit: signature verification (positive + negative), payload translation.
   - Integration: end-to-end inbound → runtime → outbound with a fixture provider.
   - E2E: real provider sandbox (Slack workspace, WhatsApp Cloud API test phone, etc.) — apply `testing/write-e2e-test.md`.
9. **Docs:**
   - Add an entry to `architecture/ARCHITECTURE.md` §3.5 channel table.
   - Add the channel's env vars to `engineering/ENV_REFERENCE.md` §4.
   - If new error conditions: add codes to `engineering/ERROR_CODES.md` §"Channels (CH)".
10. **PR:** apply `meta/write-pr.md`. Title `feat(channel-<name>): ...`. Tag Eng #7 (or #3 for voice).

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Webhook signature verified on every inbound.
- [ ] 24h idempotency dedupe in place.
- [ ] Takeover endpoint implemented and audit-logged.
- [ ] Per-bot credentials via Vault, not in config_json.
- [ ] Outbound formatting respects channel limits (length, attachment types).
- [ ] If voice: latency budget met + barge-in tested + recordings encrypted.
- [ ] Tests at unit + integration + e2e (with a real sandbox account).
- [ ] Docs: ARCHITECTURE channel table, ENV_REFERENCE, ERROR_CODES.
- [ ] No PII written to logs unredacted.
- [ ] Outbound messages stream when the channel supports it.

## Anti-patterns

- ❌ Skipping signature verification "for the test channel."
- ❌ Workspace-level channel credentials. Always per-bot.
- ❌ Long synchronous handlers. Always 202 + NATS.
- ❌ Forgetting `takeover()` — it's mandatory on every channel.
- ❌ Plaintext voice media.
- ❌ Logging the full webhook body without redaction.
- ❌ Inventing a custom message format. Translate to `AgentEvent` only.

## Related skills

- `coding/implement-runtime-feature.md` if you change `AgentEvent`.
- `security/secrets-kms-check.md` for channel credentials.
- `data/add-postgres-migration.md` if you add channel-specific tables.
- `ux/write-ui-copy.md` for any operator-facing strings.
- `testing/write-e2e-test.md` for real-provider tests.

## References

- `architecture/ARCHITECTURE.md` §3.5, §4.2 (voice sequence).
- `architecture/AUTH_FLOWS.md` §6–§7.
- `engineering/PERFORMANCE.md` §1.1 (voice budgets).
