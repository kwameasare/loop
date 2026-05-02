# cp-api 5000 RPS gate

Loop runs a k6 acceptance gate against the control-plane health path at
5000 requests per second.

The gate passes when:

- error rate stays below 0.1%;
- p95 latency stays under 100 ms;
- all response checks pass.

The workflow uploads the raw k6 summary. The committed contract lives at
`bench/results/cp_api_5000_rps.json`.
