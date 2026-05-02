# Voice latency budget (S048)

Loop's public commitment for live voice agents is **≤ 700 ms p50**
turn-around (caller stops speaking → agent starts speaking) on a
North-America point-of-presence. This document is the single source
of truth for how that budget is decomposed, measured, and defended.

## Why 700 ms

- Below ~800 ms users perceive the agent as "snappy"; above ~1.2 s
  they start to talk over it. 700 ms gives us margin against jitter
  while staying clearly inside the snappy band.
- Competitor benchmarks (Vapi, Bland, Retell as of Q1 2026) sit in
  the 800–1200 ms p50 range — 700 ms is a defensible differentiator.

## Budget decomposition

The budget is enforced in code via `loop_voice.DEFAULT_BUDGET`
(see [latency.py](../scaffolding/packages/voice/loop_voice/latency.py)):

| Stage              | p50 ms | p95 ms | Notes                                  |
| ------------------ | -----: | -----: | -------------------------------------- |
| `network_in`       |     20 |     45 | Caller → nearest LiveKit edge          |
| `asr_final`        |    160 |    280 | Streaming ASR finalisation             |
| `agent`            |    280 |    520 | LLM TTFT + tool-call round-trips       |
| `tts_first_byte`   |    160 |    260 | TTS first audio chunk                  |
| `network_out`      |     20 |     45 | LiveKit edge → caller                  |
| **end-to-end**     |    640 |   1150 | Sum, with 60 ms p50 / 50 ms p95 buffer |

<!-- S651 -->
`VoiceSession` supports a streaming-agent path for the TTS portion of
the budget: when the caller's transcript is final, the session starts
TTS pre-warm immediately, consumes the agent reply as text chunks, and
flushes complete sentence-boundary chunks to TTS before the full reply
has finished. The compatibility path that waits for a complete string
reply is unchanged.

The S651 deterministic contract in
`bench/results/voice_tts_sentence_streaming.json` models the old
full-reply first-audio p50 at 420 ms and the sentence-streaming path at
180 ms, a 240 ms / 57.1% cut while staying inside the 700 ms voice p50
budget.

<!-- S652 -->
ASR/TTS websocket providers can be wrapped with
`loop_voice.WarmWebSocketPool`. The pool exposes `prewarm()` for
pre-handshaking a provider socket before the first turn, `keepalive()`
for idle provider keep-alives, and `close_idle()` for deterministic idle
teardown after the configured timeout. Existing adapters keep their
`open_ws` injection point; production passes `pool.open`, so Deepgram,
ElevenLabs, and Cartesia can share the same pooling contract.

The S652 contract in `bench/results/voice_connection_pooling.json`
models cold provider handshake p50 at 90 ms and prewarmed acquisition at
0 ms for the first ASR/TTS socket, removing the handshake from the
caller-visible voice budget.

<!-- S653 -->
Voice ASR/TTS provider websockets can be pinned to the nearest supported
Loop voice POP with `loop_voice.resolve_voice_endpoint()`. The selector
uses a committed latency map across `{us-east, us-west, eu-west,
ap-south}` and returns the provider edge `base_url` that existing
Deepgram, ElevenLabs, and Cartesia adapters already accept.

The S653 contract in `bench/results/voice_regional_latency_map.json`
keeps the source-region latency matrix under review. Unknown caller
regions or missing provider endpoints raise instead of silently sending
live audio across an arbitrary region.

<!-- S654 -->
`scripts/voice_perf.py` is the release-train acceptance gate for the
public 700 ms p50 commitment. It writes
`bench/results/voice_perf.json`, fails non-zero when the synthetic
end-to-end p50 exceeds 700 ms, and is scheduled nightly by
`.github/workflows/voice-perf.yml` with on-call paging on failure.

## Measurement

Every voice turn that flows through `VoiceSession` is timestamped at
each stage boundary and emitted as a `LatencyMeasurement`. The
runtime keeps a process-local `LatencyTracker`; metrics are flushed
to the OTEL collector as a histogram per stage
(`loop.voice.turn.duration_ms`, attribute `stage=...`).

## Enforcement

- **CI**: `perf-check.md` skill drives a synthetic 100-turn run on
  every release branch. `LatencyTracker.breaches(DEFAULT_BUDGET)` must
  return an empty tuple — any breach fails the build.
- **Production**: an alert fires if the rolling 1-hour p50 of
  `loop.voice.turn.duration_ms` (sum across stages) exceeds 700 ms
  for two consecutive evaluation windows. Runbook:
  [RUNBOOKS.md#voice-latency-regression](RUNBOOKS.md).

## Levers we have

If a build slips past budget the playbook is, in order:

1. **Agent stage** — switch model from `gpt-4.1` to `gpt-4.1-mini`
   for tool-routing turns; cap tool-call fan-out at 2.
2. **TTS** — drop voice from neural to streaming-neural; reduce
   first-chunk size to 80 ms.
3. **ASR** — raise streaming partial confidence threshold so we
   commit finals earlier (small accuracy cost).
4. **Network** — pin caller to the nearest of {us-east, us-west,
   eu-west, ap-south}; refuse cross-region routing.

We never silently downgrade audio quality below the user's plan
tier; every lever above either ships behind a per-tenant flag or is
on by default for free-tier only.

## Out of scope

- **Phone PSTN**: budget includes only the WebRTC leg. PSTN adds
  ~80 ms one-way which is documented in
  [PERFORMANCE.md](PERFORMANCE.md) and counts against the public 1.2 s
  outer commitment, not the 700 ms p50.
- **First turn after cold start**: warm-up turn is excluded from
  p50 calculation (capped at 1500 ms separately).
