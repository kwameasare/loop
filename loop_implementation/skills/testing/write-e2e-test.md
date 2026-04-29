---
name: write-e2e-test
description: Use when adding or changing one of the top-10 user journeys.
when_to_use: |
  - New top-level user journey.
  - Significant change to an existing journey.
  - Pre-launch checklist for any major release.
required_reading:
  - engineering/TESTING.md   # §4 the 10 journeys
applies_to: testing
owner: Founding Eng #5 (Studio) or package owner
last_reviewed: 2026-04-29
---

# Write E2E test

## Trigger

A change touching the top-10 journeys (TESTING.md §4) or a brand-new top-level flow.

## Required reading

`engineering/TESTING.md` §4.

## Steps

1. **Pick the right tool:**
   - Browser flows → Playwright.
   - API journeys → pytest + httpx.
   - Helm/k3d full-stack → the Pulumi-driven ephemeral cluster.
2. **Cover the full flow** without mocks (LLM cassettes are the only allowed substitute).
3. **One journey per test file**; deterministic fixture data.
4. **Run nightly** and pre-deploy. Failures block release.
5. **Browser-test conventions:**
   - Use Page-Object pattern: `apps/studio/e2e/pages/<Name>.ts`.
   - Visual snapshots only for stable views (use `expect.toHaveScreenshot()`).
6. **Cleanup**: every E2E provisions a fresh workspace (via API) and tears it down.
7. **Reporting**: failures upload Playwright traces + DOM snapshots to the CI artifacts.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] One journey covered end-to-end.
- [ ] Page-Object structure (browser tests).
- [ ] Cassettes for LLM (no real provider calls).
- [ ] Trace+snapshot artifacts on failure.
- [ ] Clean teardown.

## Anti-patterns

- ❌ Sharing workspaces across tests.
- ❌ Hard-coded sleeps. Use Playwright's auto-wait.
- ❌ Testing through the UI when an API test is sufficient.

## Related skills

- `testing/write-integration-test.md`.

## References

- `engineering/TESTING.md` §4.
