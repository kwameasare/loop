---
name: implement-eval-scorer
description: Use when adding or modifying an eval scorer (LLM-judge, embedding similarity, regex, JSON-schema, tool-call assert, latency, cost, hallucination, toxicity, PII leak, refusal, citation presence, custom).
when_to_use: |
  - Adding a new scorer kind to packages/eval-harness/.
  - Tuning default thresholds on an existing scorer.
  - Adding new built-in safety classifiers.
  - Allowing a customer to ship a custom scorer.
required_reading:
  - engineering/TESTING.md          # §5 eval harness
  - architecture/ARCHITECTURE.md    # §3.8 eval harness
  - data/SCHEMA.md                  # §2.4 evals tables
  - adrs/README.md                  # ADR-015, ADR-023, ADR-027
applies_to: coding
owner: Founding Eng #4 (Observability + Evals)
last_reviewed: 2026-04-29
---

# Implement eval scorer

## Trigger

Touching `packages/eval-harness/`. Evals are Loop's signature feature; a buggy scorer corrupts every customer's deploy gate.

## Required reading

1. `engineering/TESTING.md` §5 (full harness spec, scorer table, determinism policy).
2. ADR-015 (eval-gated deploys), ADR-023 (eval determinism), ADR-027 (registry license).

## Steps

1. **Scorer contract.** Implement the `Scorer` protocol:
   ```python
   class Scorer(Protocol):
       kind: ClassVar[str]                         # 'llm_judge', 'regex_match', etc.
       async def score(
           self,
           case: EvalCase,
           response: AgentResponse,
           trace: Trace,
           kb_context: list[RetrievalChunk] | None,
       ) -> ScorerResult: ...
   ```
   `ScorerResult` includes: `score: float | None`, `passed: bool`, `diagnostics: dict`, `cost_usd: float`.
2. **Determinism rules** (ADR-023):
   - Any LLM-as-judge scorer fixes `temperature=0`, `top_p=0`.
   - Cache responses by `(model, prompt_hash, params_hash)` in cassette files (`tests/fixtures/llm/`).
   - Average across 3 runs within a single eval run; require 2/3 pass.
   - Cassette refresh policy: monthly, or on-demand if rubric changes; reviewed in PR.
3. **Default threshold** (see `engineering/TESTING.md` §5.2):
   - Pick a sensible default; document the rationale in the scorer file.
   - Always overridable per-case via `scorers[].config.threshold`.
4. **Cost accounting**: every LLM-as-judge scorer reports `cost_usd` so eval-run costs are surfaced.
5. **Diagnostics**: surface the raw judgment so reviewers can see *why* a case failed:
   ```python
   ScorerResult(
       score=0.62,
       passed=False,
       diagnostics={
           "judge_response": "...",
           "matched_pattern": None,
           "expected": ...,
       },
       cost_usd=0.0021,
   )
   ```
6. **Built-in safety** (`toxicity`, `pii_leak`):
   - Use established libraries (Detoxify or Perspective for toxicity).
   - PII patterns from `engineering/SECURITY.md` §7.3.
7. **Custom scorers** (customer code):
   - Customers ship a Python file under `tests/evals/<suite>/scorers/<name>.py`.
   - Loaded into the eval-runner; runs in a Firecracker sandbox (NOT in the main eval-runner process — same isolation as MCP tools).
   - Manifest: `loop eval scorer add --suite <suite> --file <path>`.
8. **Tests**:
   - Unit: deterministic on cassette fixtures.
   - Integration: run against the demo agent's eval suite; verify results match expectations.
   - Property-based (hypothesis): regex/JSON-schema scorers should be robust to weird input.
9. **Docs**: update `engineering/TESTING.md` §5.2 scorer table with the new entry + threshold.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Determinism rules followed (temp=0, cassette, 2/3 pass).
- [ ] Default threshold documented + justifiable.
- [ ] Per-case threshold override supported.
- [ ] Cost reported for LLM-as-judge scorers.
- [ ] Diagnostics rich enough to debug a failure.
- [ ] Custom scorers run in a sandbox.
- [ ] TESTING.md table updated.
- [ ] At least 5 cassette-backed unit tests.

## Anti-patterns

- ❌ Non-deterministic scorers (random sampling, time-of-day-dependent).
- ❌ `temperature > 0` for judge LLMs.
- ❌ Hard-coded prompts inline in code; put rubrics in a YAML next to the scorer.
- ❌ Scorer that costs more than the agent turn it's scoring.
- ❌ Custom scorers running in the main process (sandbox required).

## Related skills

- `testing/write-eval-suite.md` for authoring suites that use the new scorer.
- `coding/implement-llm-gateway-change.md` if a new LLM provider is required for the judge.

## References

- ADR-015 (eval-gated deploys), ADR-023 (determinism), ADR-027 (registry).
- `engineering/TESTING.md` §5.
