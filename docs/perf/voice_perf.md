# Voice Performance Gate

S654 adds a nightly voice latency acceptance gate for the public 700 ms
p50 commitment.

- Script: `scripts/voice_perf.py`
- Workflow: `.github/workflows/voice-perf.yml`
- Report: `bench/results/voice_perf.json`
- Threshold: fail when end-to-end p50 is above 700 ms

The benchmark uses deterministic synthetic turns recorded through
`loop_voice.LatencyTracker`. This keeps the CI signal stable while still
exercising the same percentile and budget primitives used by the voice
runtime.
