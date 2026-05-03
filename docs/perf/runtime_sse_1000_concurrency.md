# Runtime SSE 1000-concurrency gate

Loop runs a k6 acceptance gate that holds 1000 concurrent streaming turns
against a single `dp-runtime` pod. S913 moved the gate off the historical
`helm_e2e_smoke_server.py` placeholder: the workflow now builds
`packages/data-plane/Dockerfile`, loads `loop/dp-runtime:perf` into kind,
and measures the real `loop_data_plane.runtime_app` FastAPI/Uvicorn
container. k6 runs as an in-cluster Job against `svc/loop-loop-runtime`
so the 1000-VU gate does not measure a local `kubectl port-forward`
bottleneck. A tiny OpenAI-compatible SSE fixture supplies upstream model
frames so the runtime still uses its real httpx gateway path without
spending live provider quota.

The gate passes when:

- all SSE turn requests complete without errors;
- p95 HTTP duration stays under 3 s;
- runtime pod memory stays under 4 GB.

The workflow uploads the raw k6 summary and memory probe. The committed
contract lives at `bench/results/runtime_sse_1000_concurrency.json`.
