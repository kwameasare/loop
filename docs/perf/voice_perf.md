# Voice Performance Gate

S654 adds a nightly voice latency acceptance gate for the public 700 ms
p50 commitment.

- Script: `scripts/voice_perf.py`
- Workflow: `.github/workflows/voice-perf.yml`
- Report: `bench/results/voice_perf.json`
- Threshold: fail when end-to-end p50 is above 700 ms

The benchmark uses deterministic synthetic turns recorded through
`loop_voice.LatencyTracker` when live provider credentials are absent.
Every report now carries 100 per-turn samples with a `source` field;
live Deepgram -> agent -> ElevenLabs captures can be evaluated by
passing `--samples <json>` to `scripts/voice_perf.py`. This keeps the CI
signal stable while making synthetic provenance explicit.
