---
name: perf-check
description: Use whenever you touch a hot path or load-relevant code path. Confirms the bench rig is unaffected and budgets are met.
when_to_use: |
  - Touching TurnExecutor.execute, prompt builder, memory loader, gateway client, KB retrieval, channel adapters.
  - Touching Studio bundle size or LCP-sensitive paths.
  - Pre-release.
required_reading:
  - engineering/PERFORMANCE.md   # §1 budgets, §2 bench rig
applies_to: testing
owner: Founding Eng #1 + #2 + #3
last_reviewed: 2026-04-29
---

# Perf check

## Trigger

Any hot-path change. PR is blocked if budgets regress.

## Required reading

`engineering/PERFORMANCE.md` §1–§2.

## Steps

1. **Identify which budget(s)** your change touches (PERFORMANCE.md §1.1 / §1.2).
2. **Run the relevant microbench(es):**
   ```bash
   uv run pytest --benchmark-only -k <name> --benchmark-json=bench/results/<name>.json
   ```
3. **Compare to baseline.** CI auto-compares `main@<baseline_ref>`. Locally:
   ```bash
   pytest-benchmark compare bench/results/<name>.json bench/results/<name>.baseline.json
   ```
4. **Budgets:**
   - > 10% regression on `mean_ms` → blocks merge.
   - Justify in PR body if intentional (e.g., trading speed for safety).
5. **Studio perf:** Lighthouse CI runs on every PR touching `apps/studio/`. LCP budget 1.0s; bundle 250 KB initial.
6. **Voice latency:** if you touch the voice pipeline, run the voice rig (`siplaunch + bla`) and confirm p50 ≤ 700ms.
7. **Profile if regressed:**
   - Python: `py-spy record -o profile.svg -- <cmd>`. Inspect FlameGraph.
   - Memory: `memray run -m <module>`.
   - Studio: React Profiler + bundle analyzer.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Bench JSON committed to `bench/results/<name>.json`.
- [ ] No budget regression > 10% (or justified).
- [ ] Lighthouse CI green (Studio paths).
- [ ] Voice budget verified (voice paths).

## Anti-patterns

- ❌ "It's just a small change" — measure.
- ❌ Justification "we'll fix later" without a ticket.
- ❌ Skipping the bench because the test runs locally fast.

## Related skills

- `coding/implement-runtime-feature.md` and other coding skills.

## References

- `engineering/PERFORMANCE.md`.
