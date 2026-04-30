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
