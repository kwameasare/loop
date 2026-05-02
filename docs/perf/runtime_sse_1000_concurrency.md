# Runtime SSE 1000-concurrency gate

Loop runs a k6 acceptance gate that holds 1000 concurrent streaming turns
against a single `dp-runtime` pod.

The gate passes when:

- all SSE turn requests complete without errors;
- p95 HTTP duration stays under 3 s;
- runtime pod memory stays under 4 GB.

The workflow uploads the raw k6 summary and memory probe. The committed
contract lives at `bench/results/runtime_sse_1000_concurrency.json`.
