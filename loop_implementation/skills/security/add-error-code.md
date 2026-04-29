---
name: add-error-code
description: Use when introducing a new LOOP-XX-NNN error code.
when_to_use: |
  - Adding a new exception class.
  - Surfacing a new failure to users.
  - Mapping an existing internal error to a customer-facing code.
required_reading:
  - engineering/ERROR_CODES.md
applies_to: security
owner: Founding Eng #1 (Runtime)
last_reviewed: 2026-04-29
---

# Add error code

## Trigger

You're raising a new error class. Loop policy: every customer-visible error has a stable, documented code.

## Required reading

`engineering/ERROR_CODES.md` end-to-end.

## Steps

1. **Pick the prefix.** Use the canonical service prefix list (§2). Examples: `RT` runtime, `GW` gateway, `TH` tool-host, `KB` KB engine, `CH` channels, `EV` evals, `API` cp-api, `DEP` deploy, `BIL` billing, `INF` infra adapters.
2. **Pick the number block** (§1):
   - 001–099 input validation
   - 100–199 auth/authorization
   - 200–299 not-found / conflict
   - 300–399 rate-limit / budget
   - 400–499 upstream / dependency
   - 500–599 internal / bug
   - 600–699 security / abuse
   - 700–799 cloud-portability adapter errors
3. **Pick the next free number in the block.** Never reuse a retired code.
4. **Add the row** to `engineering/ERROR_CODES.md` §3 with: code, meaning, HTTP status, recovery suggestion.
5. **Define the exception:**
   ```python
   # packages/<service>/loop/<service>/errors.py
   class BudgetCapHit(LoopError):
       code = "LOOP-RT-301"
       http_status = 429
       title = "Workspace budget cap reached"
   ```
6. **Documentation page** (if the recovery is non-trivial): create `docs/errors/LOOP-XX-NNN.md` with: what happened, why, how to fix, related runbook links.
7. **Test:** assert the exception, code, status, and envelope shape.
8. **Observability:** every error emits an OTel attribute `loop.error.code` and a Sentry tag.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Code in the right prefix + block.
- [ ] Row added to `engineering/ERROR_CODES.md` §3.
- [ ] Exception class with `code`, `http_status`, `title`.
- [ ] Recovery doc page (if non-trivial).
- [ ] OTel + Sentry tagging.
- [ ] Test asserting envelope.

## Anti-patterns

- ❌ Reusing a retired code.
- ❌ Returning 500 with no code.
- ❌ Sanitizing an error so much the customer can't recover.
- ❌ Generic codes like `LOOP-RT-999` — every error has a real reason or it goes to `-501`.

## Related skills

- `coding/implement-runtime-feature.md`, `coding/implement-llm-gateway-change.md`, etc. (whichever service you're in).

## References

- `engineering/ERROR_CODES.md`.
