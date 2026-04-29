---
name: write-eval-suite
description: Use when authoring or modifying eval suites for an agent.
when_to_use: |
  - Creating an initial suite for a new agent.
  - Adding cases captured from production replay.
  - Tuning per-case scorer thresholds.
  - Refreshing cassettes (monthly cadence).
required_reading:
  - engineering/TESTING.md   # §5 eval harness
  - adrs/README.md           # ADR-015, ADR-023, ADR-027
applies_to: testing
owner: agent owner + Eng #4
last_reviewed: 2026-04-29
---

# Write eval suite

## Trigger

Any agent that will be deployed to prod must have an eval suite. Production-replay capture, prompt changes, and threshold tuning all go through this skill.

## Required reading

`engineering/TESTING.md` §5; ADR-015 (eval-gated deploys), ADR-023 (determinism), ADR-027 (registry).

## Steps

1. **Suite layout:** `tests/evals/<agent_slug>/suite.yaml`.
2. **Top-level fields:**
   ```yaml
   name: support-en
   agent_slug: support-en
   scorers:
     - kind: <built-in or custom>
       config: { ... }
   cases:
     - name: <case_name>
       input: "..."
       expected:
         tool_calls: ["..."]
         response_includes_any: ["..."]
   ```
3. **Pick scorers** (TESTING.md §5.2 has the full table). At minimum:
   - `llm_judge` with a clear rubric.
   - `latency_le` with the agent's budget.
   - `cost_le` with the agent's per-turn cap.
4. **Case authoring:**
   - Start with 5–10 happy-path cases.
   - Add 5+ edge cases (out-of-scope, ambiguous, hostile, multilingual).
   - Add production-replay cases (auto-captured from last 7d failures via `loop eval capture`).
5. **Determinism:**
   - Cassettes are auto-recorded on first run; committed to `tests/fixtures/llm/<suite>.yaml`.
   - LLM-judge: `temperature=0`, `top_p=0`. 3 runs averaged.
6. **Threshold tuning:**
   - Default thresholds from TESTING.md §5.2.
   - Override per-case: `scorers[].config.threshold`.
   - Justify any threshold below the default in the suite YAML comment.
7. **Cassette refresh** (monthly cadence or on rubric change):
   ```bash
   loop eval record <suite> --refresh-cassettes
   ```
   Review the diff in PR; reviewer must sign off.
8. **Run locally:** `loop eval run <suite> --against=local`. Then in CI: `loop eval run <suite> --against=PR-NNN --baseline=main`.
9. **Eval-gated deploy** (ADR-015): when this suite is attached to an agent, deploy controller blocks promotion if regression > 5%.
10. **Public registry** (optional): publish high-quality suites under CC-BY (ADR-027).

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Suite YAML in canonical layout.
- [ ] At least 10 cases (5 happy + 5 edge).
- [ ] All built-in safety scorers present (toxicity, pii_leak).
- [ ] Latency + cost thresholds set.
- [ ] Cassettes committed and ≤ 30 days old.
- [ ] Suite passes locally before CI.
- [ ] Documented in agent's README.

## Anti-patterns

- ❌ Suite with only happy-path cases.
- ❌ Stale cassettes (> 90d) — block promotion.
- ❌ Non-deterministic scorers (temp > 0).
- ❌ Threshold overrides without justification.
- ❌ Custom scorer without sandbox.

## Related skills

- `coding/implement-eval-scorer.md` for new scorers.
- `ops/deploy-agent-version.md` for promotion.

## References

- `engineering/TESTING.md` §5.
- ADR-015, ADR-023, ADR-027.
