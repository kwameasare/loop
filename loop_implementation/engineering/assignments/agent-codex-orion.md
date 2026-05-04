# Agent: codex-orion — persistence + GDPR cascades

**Theme**: storage / persistence / right-to-erasure. Pairs with the
in-flight P0.2 task; do NOT duplicate the cp-service Postgres adapters
the spawned task is building. Your scope is everything OTHER than the
5 cp services (workspaces / audit / agents / refresh tokens / api keys),
which the in-flight task owns.

**Branch convention**: `agent/codex-orion/<slug>`.
**Commit trailer**: `Co-Authored-By: Claude Opus 4.7 …`.

---

## Item 1 — `loop_memory` Postgres adapter + GDPR cascade

**File**: `packages/memory/loop_memory/postgres.py` (already exists,
needs hardening).

**Audit findings to close** (peripheral audit P1):
- `memory/loop_memory/postgres.py:158-179` — `delete_user` deletes one
  key. **No `delete_all_user_data(user_id)` for GDPR right-to-erasure.**
- No per-row encryption of `value_json`. PII lands in plaintext JSONB.
- No value-size cap.

**Acceptance**:
1. Add `delete_all_for_user(*, workspace_id: UUID, user_id: str) -> int`
   that bulk-deletes every memory row (any key) for the given user
   and returns the row count. Idempotent.
2. Add `delete_all_for_workspace(workspace_id: UUID) -> int` for the
   workspace-deletion cascade (called by `data_deletion`'s worker).
3. Add a `MAX_VALUE_BYTES = 64 * 1024` constant + raise
   `MemoryError("value exceeds 64 KiB")` from `set()` if exceeded.
   Operators bump via env override.
4. Wire `cryptography.hazmat.primitives.aead.AESGCM` for column-level
   encryption: `value_json` becomes `value_ciphertext bytea` +
   `nonce bytea` + `algorithm text` (matches the pattern from
   `workspace_encryption.py` shipped in #179). Add an alembic migration
   in `packages/data-plane/loop_data_plane/migrations/versions/`.
5. Tests under `packages/memory/_tests/test_postgres_gdpr.py`:
   bulk-delete-for-user happy path, bulk-delete-for-workspace happy
   path, idempotency (re-delete returns 0), size-cap rejection,
   encrypted round-trip, cross-workspace isolation.

**Effort**: ~1 day, 1 PR.

---

## Item 2 — `loop_kb_engine` BM25 lexical-index Postgres backing

**File**: `packages/kb-engine/loop_kb_engine/kb.py:50-53`.

**Audit finding** (peripheral audit P1):
> `_lex` is a process-local dict — BM25 lexical index is not
> persisted; restart loses every lexical retrieval.

**Acceptance**:
1. New `packages/kb-engine/loop_kb_engine/lexical_postgres.py`
   exposing `PostgresLexicalIndex` with the same Protocol shape as
   the in-memory dict — `index(doc_id, terms)`, `search(query, k)`.
2. Use Postgres `tsvector` + GIN index on `(workspace_id, terms)`.
   Migration in dp's alembic.
3. Tests under `packages/kb-engine/_tests/test_lexical_postgres.py`
   covering: index a doc → query returns it; query in another
   workspace returns empty (cross-tenant isolation); deleting a doc
   removes it from the index; restart-survival (write rows, drop
   the in-process cache, re-instantiate, query still works).

**Effort**: ~1 day, 1 PR.

---

## Item 3 — KB crawler hardening

**File**: `packages/kb-engine/loop_kb_engine/crawler.py:48-69`.

**Audit findings**:
- No per-host concurrency cap.
- No robots.txt cache TTL.
- No retry on 5xx.
- No max-content-length (memory blowup on a malicious site).

**Acceptance**:
1. Per-host semaphore: max 2 concurrent fetches per origin (configurable).
2. robots.txt LRU cache with 1h TTL.
3. `tenacity`-style retry on 5xx + connection-reset, max 3 attempts,
   exponential backoff with jitter.
4. `MAX_CONTENT_BYTES = 50 * 1024 * 1024` (50 MiB), reject larger
   responses with a structured `KbCrawlError`.
5. Tests using `httpx.MockTransport` covering each constraint.

**Effort**: ~0.5 day, 1 PR.

---

## Item 4 — KB cost tracking

**Audit finding**: KB ingestion has no cost tracking (pages crawled /
tokens embedded / dollars).

**Acceptance**:
1. `packages/kb-engine/loop_kb_engine/cost_tracking.py` emits
   `UsageEvent` rows (per the existing `loop_control_plane.usage`
   shape) for: `kb.pages_crawled`, `kb.embedding_tokens`,
   `kb.embedding_usd_cents`.
2. Wire into the existing crawler + embedder pipelines.
3. Tests: end-to-end ingestion of a fixture page emits the expected
   UsageEvent rows; per-workspace isolation; assertions on the
   metric names matching what the cp's UsageRollup nightly job
   expects.

**Effort**: ~0.5 day, 1 PR.

---

## Item 5 — Channel ConversationIndex Postgres backing

**Files** (peripheral audit P1):
- `packages/channels/whatsapp/loop_channels_whatsapp/channel.py:18-50`
- `packages/channels/slack/loop_channels_slack/channel.py:18-39`
- `packages/channels/discord/loop_channels_discord/channel.py:15-33`
- `packages/channels/teams/loop_channels_teams/channel.py:15-33`

**Issue**: `ConversationIndex` (phone/user → conversation_id mapping)
is in-memory; restart drops every mid-conversation user.

**Acceptance**:
1. New `packages/channels/core/loop_channels_core/conversation_index_postgres.py`
   with `PostgresConversationIndex` implementing the same Protocol
   the four channels already use. One generic implementation; each
   channel constructs it with a per-channel namespace.
2. Migration in dp's alembic for the
   `channel_conversation_index(channel, provider_user_id,
   conversation_id, last_seen_at)` table.
3. Tests under `packages/channels/core/_tests/test_conversation_index_postgres.py`
   covering: insert + lookup, cross-channel isolation
   (`whatsapp/+15551234567` ≠ `discord/+15551234567`),
   restart-survival, conflict-on-duplicate idempotency.
4. Wire each of the 4 channels' factories so production picks
   `PostgresConversationIndex`; tests + dev still use the in-memory
   shim.

**Effort**: ~1 day, 1 PR.

---

## Item 6 — Voice room state persistence

**File**: `packages/voice/loop_voice/livekit_room.py`.

**Audit finding**: `RoomManager.rooms` in-memory only — restarting
the runtime loses room state.

**Acceptance**:
1. New `packages/voice/loop_voice/postgres_rooms.py` with
   `PostgresRoomManager` implementing the same shape.
2. Migration in dp's alembic for `voice_rooms(workspace_id, room_id,
   livekit_room_name, started_at, ended_at)`.
3. Real LiveKit `mint_token` implementation using the `livekit-api`
   library (closes the "no actual JWT-HS256 mint" P0 from peripheral
   audit too — note: this technically belongs in P0.2's voice slice
   but it's bundled here because the room state and the token mint
   are tightly coupled).
4. Tests covering create → mint → end → list-recent flow.

**Effort**: ~1.5 days, 1 PR.

---

## Item 7 — Audit payload persistence (P1.15)

**File**: `packages/control-plane/loop_control_plane/audit_events.py:155`.

**Audit finding**:
> `payload_hash = hash_payload(payload)` is hashed but the payload
> itself is discarded. So the audit row says "this hash was input"
> with no way to reproduce the payload at audit time.

**Acceptance**:
1. New `audit_event_payloads(payload_hash bytea PRIMARY KEY,
   payload_json jsonb, stored_at timestamptz)` table in cp's
   alembic.
2. `record_audit_event` writes the hash AS today AND inserts the
   payload (idempotent ON CONFLICT DO NOTHING — same payload twice
   shares the row).
3. New helper `audit_events.fetch_payload(hash) -> dict | None` for
   the SOC2 audit-replay tooling.
4. Critically: secrets-leakage defense. Add a `redact_for_audit`
   protocol — every route's `record_audit_event` call passes a
   payload that's already been redacted. Failing tests: secrets-set
   route, api-key-create route, voice-recording route. The redaction
   pattern lives in a new `audit_redaction.py`.
5. Tests covering: payload write, payload read-back by hash, redaction
   for the secret/api-key/voice flows.

**Effort**: ~1 day, 1 PR. Consider as 2 PRs (storage first, then
redaction).

---

## Item 8 — Refresh token rotation hardening

**File**: `packages/control-plane/loop_control_plane/auth_exchange.py:74`.

**Status**: rotation + reuse-detection landed in #184. Two follow-ups
remain:
1. **Family tracking**: when a refresh token is presented twice (=
   reuse detected), revoke the entire refresh-token chain for that
   user, not just the one token. Currently we just reject the second
   presentation; we should also nuke any tokens minted from that
   chain since the operator must assume compromise.
2. **30-day TTL** is per-token. Add a per-chain hard expiry of 90
   days so a long-lived chain still rolls over eventually.

**Acceptance**:
1. `RefreshTokenStore` gains `family_id` column; every token in a
   rotation chain shares the same family.
2. Reuse detection (`/v1/auth/refresh` second presentation of the
   same token) triggers `revoke_family(family_id)`.
3. Tests pin both behaviours.

**Effort**: ~0.5 day, 1 PR.

---

## Acceptance summary for codex-orion

8 PRs, ~6-7 days. After your work:

- [x] Memory has GDPR-compliant bulk-delete + AES-GCM column encryption + size cap.
- [x] KB BM25 index survives restart.
- [x] KB crawler is robust against malicious sites.
- [x] KB ingestion produces billable UsageEvents.
- [x] Every channel's conversation index survives restart.
- [x] Voice room state + LiveKit token mint are real.
- [x] Audit payload is recoverable for SOC2 replay; secrets never logged.
- [x] Refresh-token chains rotate cleanly with family revocation on reuse.
