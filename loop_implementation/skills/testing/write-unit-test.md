---
name: write-unit-test
description: Default skill for writing unit tests. Use on every code change that touches a Python, TypeScript, or Go file.
when_to_use: |
  - Adding a new function or class.
  - Modifying existing logic.
  - Coverage on a touched file is below 85%.
required_reading:
  - engineering/TESTING.md     # §2 unit
  - engineering/HANDBOOK.md    # §2 conventions
applies_to: testing
owner: author of the code
last_reviewed: 2026-04-29
---

# Write unit test

## Trigger

Default for any code change.

## Required reading

`engineering/TESTING.md` §2.

## Steps

1. **Co-locate** test next to source. `module.py` ↔ `_tests/test_module.py`.
2. **Framework**: pytest + pytest-asyncio + hypothesis (Python); Vitest + Testing Library (TS); stdlib testing + testify (Go).
3. **What to assert:**
   - Happy path.
   - Every error path / edge case.
   - Boundary values (empty, max, off-by-one).
   - For async: cancellation behavior.
4. **No global monkey-patches.** Use `pytest-mock` and `respx` (HTTP) for stubs.
5. **Property-based** (hypothesis) for parsers, validators, anything taking arbitrary input.
6. **Fixtures**: factory functions over heavyweight fixtures. Share via `conftest.py`.
7. **Speed**: a single unit test file should complete < 1s. The whole suite ≤ 60s.
8. **Coverage**: aim ≥ 85% on the package; PR fails if below for core packages.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Happy + error + boundary covered.
- [ ] No global monkey-patches.
- [ ] No real network calls.
- [ ] Speed budget met.
- [ ] Coverage ≥ 85% on the file.

## Anti-patterns

- ❌ Mocking the function under test.
- ❌ Tests that depend on time/clock without freezing it.
- ❌ Tests that depend on test ordering.

## Related skills

- `testing/write-integration-test.md`.

## References

- `engineering/TESTING.md` §2.
