# Gateway Provider Eval Suite

Loop compares provider candidates with `standard_gateway_eval_suite()`, a
deterministic 50-prompt suite spanning tool-use, memory, sales, support,
coding, retrieval, reasoning, voice, safety, and summarization tasks.

Nightly runs should record:

- Mean quality score, bounded from 0 to 1.
- P95 latency in milliseconds.
- Total routed cost in USD for the suite.
- Per-provider pass/fail using `summarize_provider_run()`.

The suite is intentionally provider-neutral. It validates the routing matrix
for Bedrock, Vertex/Gemini, Mistral, Cohere, Groq, vLLM, Together, Replicate,
and Fireworks without requiring tests to hit the network.
