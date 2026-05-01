# Loop — Testing Strategy

**Status:** Draft v0.1
**Owner:** Founding Eng #4 (Observability + Evals)

Loop is an agent platform; correctness has two faces — the platform itself (deterministic) and the agents running on it (probabilistic). We test both, with different harnesses.

---

## 1. The pyramid

```
                  ┌──────────────┐
                  │  Manual      │  ad-hoc + UAT
                  ├──────────────┤
                  │  Chaos       │  quarterly
                  ├──────────────┤
                  │  Load        │  pre-launch
                  ├──────────────┤
                  │  E2E         │  10 journeys, nightly
                  ├──────────────┤
                  │  Eval        │  agent quality, every runtime PR
                  ├──────────────┤
                  │  Integration │  every PR, all public APIs
                  ├──────────────┤
                  │  Unit        │  every PR, ≥85% on core packages
                  └──────────────┘
```

Coverage targets and gates are listed in `engineering/HANDBOOK.md` §4. This doc explains how each layer works.

---

## 2. Unit tests

### 2.1 Python

- **Framework:** pytest + pytest-asyncio + hypothesis (property-based).
- **Layout:** `_tests/` siblings of source; `test_*.py`.
- **Fixtures:** shared in `conftest.py`; favor factory functions over heavy fixtures.
- **Mocks:** `pytest-mock` for stdlib; for HTTP, `respx`. Never global monkey-patches.
- **Speed:** entire unit suite ≤ 60 s on CI runners.

### 2.2 TypeScript

- **Framework:** Vitest + Testing Library.
- **Snapshot tests:** allowed but discouraged; prefer assertion-based.
- **MSW** for HTTP mocking.

### 2.3 Go

- **Framework:** stdlib `testing` + `testify`.
- **Table tests** preferred for command parsing.

---

## 3. Integration tests

Cover every public API path. Tests spin up real Postgres + Redis + Qdrant + NATS via docker-compose (the same `make up` developers run locally).

- **Framework:** pytest with a `pytest_plugin` that boots the stack.
- **API contract fuzzing:** Schemathesis exercises `api/openapi.yaml` against
  an in-process ASGI contract app with all response checks enabled and a 5 s
  Hypothesis deadline. This keeps the public REST spec loadable, routable, and
  response-schema-valid before the full `cp-api` server exists.
- **Fixtures:**
  - `workspace_factory` — creates a fresh tenant.
  - `agent_factory` — deploys a no-op agent.
  - `mock_llm_gateway` — replaces the real gateway with a recorded-cassette server (VCR-like).
- **What we assert:**
  - Status codes, response shapes, persisted state.
  - RLS isolation: cross-tenant queries return empty.
  - Audit log receives the expected entry.
  - Idempotency: the same request twice produces the same result.

Integration suite ≤ 5 min on CI.

---

## 4. End-to-end tests

The 10 user journeys we care about most:

1. **Sign up → create workspace → create first agent → first chat reply.**
2. Deploy a new agent version with eval gating; eval passes; promotion works.
3. Eval regresses; promotion blocks; rollback path verified.
4. Connect WhatsApp → send a message → response delivered (sandbox account).
5. Voice call: SIP → STT → LLM → TTS → audio out (with synthetic audio).
6. KB ingest a PDF → ask a question → cited chunks returned.
7. Operator inbox: bot escalates → human takes over → conversation closes.
8. Cost cap: hit soft cap → warning; hit hard cap → graceful degrade to cheaper model.
9. Self-host docker-compose: full bootstrap to first response.
10. Helm chart on k3d: full bootstrap to first response.

**Tooling:**
- Playwright for browser flows.
- pytest + httpx for API journeys.
- Pulumi-driven ephemeral cluster for k3d Helm runs (nightly).

E2E suite runs nightly + before deploy. Failures block release.

---

## 5. Eval harness — agent quality

This is Loop's signature product, so the harness is also our internal QA tool.

### 5.1 What an eval suite looks like

`tests/evals/support/suite.yaml`:

```yaml
name: support-en
agent_slug: support-en
scorers:
  - kind: llm_judge
    model: claude-sonnet-4-7
    rubric: |
      Score 1.0 if the response addresses the user's actual question,
      cites a tool result or KB chunk when relevant, and stays in scope.
      Score 0.5 if partial. 0.0 otherwise.
  - kind: hallucination
    config: { kb_id: "${kb_id}" }
  - kind: tool_call_assert
    config: { must_call: ["lookup_order"], with_args: { order_id: "*" } }
  - kind: latency_le
    config: { ms: 2000 }
  - kind: cost_le
    config: { usd: 0.01 }
cases:
  - name: where_is_my_order
    input: "Where is order 4172?"
    expected:
      tool_calls: ["lookup_order"]
      response_includes: ["status", "estimated"]
  - name: refund_request
    input: "I want a refund for order 4172"
    expected:
      tool_calls: ["lookup_order", "create_refund"]
  - name: out_of_scope
    input: "What's the meaning of life?"
    expected:
      response_includes: ["I can help with order", "support"]
      tool_calls: []
```

### 5.2 Scorers (built-in) & default thresholds

| Scorer | Pass condition | Default threshold |
|--------|----------------|-------------------|
| `llm_judge` | LLM scores ≥ threshold (avg of 3 runs, 2/3 pass) | 0.7 (range 0–1) |
| `embedding_sim` | Cosine sim to golden ≥ threshold | 0.85 |
| `regex_match` | At least one match per pattern | n/a (binary) |
| `json_schema` | Response parses against schema | n/a (binary) |
| `tool_call_assert` | Required tools called with args matching pattern | n/a (binary) |
| `latency_le` | Total turn ≤ ms threshold | 2000 ms |
| `cost_le` | Total cost ≤ usd threshold | 0.05 usd |
| `hallucination` | Every claim grounded in retrieved chunks | 0.8 (LLM-judge with retrieval grounding) |
| `toxicity` | Toxicity classifier (detoxify/perspective) < threshold | 0.1 |
| `pii_leak` | Response contains no PII patterns (email, phone, SSN, etc.) | n/a (binary fail) |
| `refusal` | Response refuses (when expected) | n/a (binary) |
| `citation_presence` | Response cites source URIs from KB | 0.8 (≥80% of claims cited) |

Thresholds are overridable per-case in the suite YAML: `scorers[].config.threshold`.

### 5.3 Run modes

- **Local:** `loop eval run my-suite --against=local` — single-pass against the dev runtime.
- **CI:** `loop eval run my-suite --against=PR-123 --baseline=main` — uses ephemeral runtime per agent version, computes per-case diffs.
- **Production replay:** automatically capture last 7 days of failed/escalated conversations as eval cases, run nightly.

### 5.4 Determinism & cassette refresh policy

LLM calls in evals **must** be deterministic enough to detect regressions. Strategy:
- Fix `temperature=0` and `top_p=0` for evaluator LLMs (Claude Sonnet by default).
- **Cassette caching:** Responses cached by `(model, prompt_hash, params_hash)` in VCR-style YAML files in `tests/fixtures/llm/` per eval suite. Persists across eval runs (not per-run).
- For LLM-judge scorers: average across 3 runs within a single eval run; require 2/3 pass (≥threshold in 2 of 3).
- **Cassette refresh cadence:** Monthly (1st of month) or on-demand if a scorer rubric changes. Refresh issued by running `loop eval record <suite> --refresh-cassettes` (requires human approval of diff). Cassettes are committed to repo; diffs reviewed in PR.
- **Test data decay:** Cassettes older than 90d emit a warning but still run (backwards compat). Owner is pinged to refresh.

### 5.5 Public registry

We host `evals.loop.example` with community-shared suites:
- `customer-support-en-v2`
- `financial-research-tools`
- `coding-agent-bench`
- ...

Customers can `loop eval install <slug>` to add a community suite to their workspace.

---

## 6. Load testing

### 6.1 Tools

- **k6** for HTTP load (chat endpoints, REST API).
- **locust** for stateful user-journey load.
- **siplaunch** + **bla** (custom) for voice-leg load.

### 6.2 Scenarios

| Scenario | Target |
|----------|--------|
| 100 concurrent chat conversations / pod | p99 first-token ≤ 2s |
| 1,000 concurrent chat workspace-wide | p99 first-token ≤ 2s, no errors |
| 10,000 turns/min sustained for 30m | error rate ≤ 0.1% |
| 50 concurrent voice calls / region | latency p50 ≤ 800ms |
| KB ingest 1 GB | < 60s end-to-end |
| Tool sandbox cold start at 100 rps | p99 ≤ 200ms |

### 6.3 Cadence

- Quarterly + before any public launch + after any architecture-impacting PR.

---

## 7. Chaos engineering & soak testing

### 7.1 Failures & test schedule

- **Postgres primary failover** (quarterly, Monday 2am PT).
- **Redis cluster partition** (quarterly, Tuesday 2am PT).
- **Qdrant unavailability** (quarterly, Wednesday 2am PT).
- **NATS partition** (quarterly, Thursday 2am PT).
- **LLM provider 5xx storm** (quarterly, Friday 2am PT).
- **Tool sandbox OOM / timeout cascade** (quarterly, Saturday 2am PT).
- **Cost-cap mid-turn hit** (monthly, 1st Monday).

Rotation assigned to Founding Eng #2 (Infra); incident commander on-call that day.

### 7.2 Soak testing

- **24-hour soak:** Monthly (2nd week, Tue–Wed). Sustained load: 100 concurrent conversations per workspace, 3 workspaces, 10 turns/min. Assert: no data loss, no trace lag > 10s, error rate ≤ 0.01%.
- **7-day soak:** Quarterly (before launch windows). Same setup but across all regions (na-east, eu-west, apac-sg). Assert: zero cross-tenant leaks, zero memory leaks (monitor pod RSS), zero database connection pool exhaustion.

### 7.3 Assertions & post-test criteria

- **No data loss.** Ever. Verify: all turns persisted, no mid-turn drops.
- **No cross-tenant leak.** Verify: workspace A cannot query workspace B's conversations via any API path.
- **Graceful degradation.** Verify: errors surface as user-friendly fallbacks (e.g., "I couldn't reach my tools, please try again") not stack traces.
- **Recovery within RTO/RPO:** Postgres ≤60s, Redis ≤30s, Qdrant ≤120s (manual failover for Qdrant if needed).
- **Post-mortem:** Every chaos event followed by blameless post-mortem; action items tracked + owned.

---

## 8. Performance benchmarks & golden files

### 8.1 Microbenchmarks & targets

- Memory loader: ≤ 50ms p99 from cold cache (episodic + KB retrieval).
- Prompt builder: ≤ 5ms (system + memory + tools + history assembly).
- Trace export overhead: ≤ 1% of turn latency (OTLP batching + serialization).
- RLS query overhead: < 5ms per tenanted table scan (measured in perf tests).

### 8.2 Bench rig & golden file format

- **Tooling:** `pytest-benchmark` for Python hot paths; `vegeta` for HTTP endpoints; `hyperfine` for CLI startup.
- **Golden files** stored in `bench/golden/{category}.json`:
  ```json
  {
    "timestamp": "2026-04-29T14:30:00Z",
    "commit": "abc123def456",
    "benchmarks": [
      {
        "name": "memory_loader_cold",
        "mean_ms": 45.2,
        "stddev_ms": 3.1,
        "p99_ms": 48.5,
        "calls": 1000
      }
    ]
  }
  ```
- **Regression detection:** PR must include `bench/` output. CI compares against golden file; >10% mean regression OR >10% p99 regression blocks merge. Requires justification or perf fix.
- **Flake allowance:** If benchmark is flaky (coefficient of variation > 15%), it's excluded from CI gates but tracked for future cleanup.
- **Budget per regression investigation:** 30 min engineering time; escalate to perf owner if unresolved.

---

## 9. Test data management & lifecycle

- **Synthetic only.** No production data in test environments (policy enforced via pre-commit hook + audit).
- **Factories:** Fixtures in `conftest.py` use Faker (names, emails, phone numbers) or hardcoded deterministic UUIDs (for assertions).
- **Recorded cassettes:** LLM responses cached in VCR-style YAML files under `tests/fixtures/llm/<suite>/`. Committed to repo; refreshed monthly or on scorer change.
- **E2E test workspaces:** Each E2E journey (10 total) runs in an ephemeral workspace created at test start, destroyed at test end. Workspace isolated to test ID via `workspace_id=<test_uuid>`. Database rows auto-purged in teardown.
- **Test data refresh policy:** Synthetic datasets (names, emails, addresses) have no TTL. Recorded cassettes (LLM responses) refreshed monthly as mentioned above. Production data never imported; if integration test needs a real API response, it's recorded once and committed.
- **Coverage exclusions policy:** Exclusions tracked in `coverage.txt` with justifications:
  ```
  src/runtime/sandbox.py:42-60    # Firecracker kernel panic — tested in chaos week, not unit
  src/gateway/fallback.py:99-102  # LLM provider failover — flaky in isolation; tested in integration
  ```
  PR gates: must justify any new exclusion; total exclusion budget ≤ 15% of codebase.

---

## 10. CI pipeline & matrix strategy

```
push → lint+typecheck → unit → integration → [eval (runtime PRs only)] → [e2e (main only)] → security scans → build artifacts
                                                                                                              ↘ deploy to staging (main only)
```

- **Time budget:** ≤ 12 minutes for `push → unit + integration + lint + typecheck` (wall time, parallelized).
- **Matrix sharding (parallelism budget):**
  - Unit tests: sharded by package (8 parallel jobs for 8 packages).
  - Integration tests: sharded by 5-cloud matrix (aws, gcp, azure, alibaba, self-host); each runs in parallel = 5 jobs.
  - Security scans: 4 jobs (sca, static, container, infra).
  - Total parallelism budget: 20 concurrent runners. If hitting ceiling, unit tests run on 4 runners instead (doubles unit time to ~4min; acceptable).
- **Required checks for merge:** lint, typecheck, unit, integration, security, eval (when applicable).
- **Optional checks (nightly):** e2e, load testing, chaos week (quarterly, not per-commit).
- **Flake quarantine:** Tests with >10% flake rate (measured over 30 days) are quarantined: moved to a `_tests/flaky/` suite, marked `@pytest.mark.flaky(max_runs=3)`, not gating PRs.

---

## 11. Test ownership

| Layer | Owner |
|-------|-------|
| Unit | Author of the code |
| Integration | Package owner |
| E2E | Founding Eng #5 (Studio) for UI journeys, package owners for API journeys |
| Eval harness | Founding Eng #4 |
| Load | Founding Eng #2 |
| Chaos | Founding Eng #2 |
| Security tests | Sec/Compliance Eng |

---

## 12. Definition of "tested enough"

- Unit coverage ≥ 85% on the package.
- Integration tests cover every public endpoint at least once.
- For runtime PRs: at least one new eval case if behavior changes.
- For UX PRs: at least one Playwright test if a new screen.
- All security CI checks pass.

If the test you'd want doesn't exist, write it before you fix the bug.
