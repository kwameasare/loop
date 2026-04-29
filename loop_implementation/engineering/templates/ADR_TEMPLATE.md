# ADR-NNN — Title (verb + noun)

**Status:** Proposed | Accepted | Superseded by ADR-MMM | Deprecated
**Date:** YYYY-MM-DD
**Owner:** Name (role)
**Supersedes:** ADR-XXX (if any)

## Context

Why now? What forces are pushing this decision? Cite measurable signals (incidents, customer asks, scaling thresholds), not opinions. 4–8 sentences.

## Decision

The answer, stated as the *current* tense fact ("Loop uses X").

Be specific:
- Vendor / library / version.
- Numeric thresholds (when does this decision flip?).
- Scope (what does this NOT cover?).

## Consequences

- ✅ Win 1 (measurable benefit)
- ✅ Win 2
- ⚠️ Tradeoff 1 + mitigation
- ⚠️ Tradeoff 2 + mitigation
- ❌ Hard cost we accept

## Alternatives considered

For each rejected option:
- **Name** — one-line description — why rejected (specific reason, not "worse").

## Revisit conditions

When would we reconsider this decision? Examples:
- ARR > $X (cost crossover).
- More than N tenants over Y GB (scale crossover).
- Vendor announces deprecation / pricing change.
- Adjacent decision (ADR-XXX) flips.

## References

- Related ADRs.
- Architecture sections.
- Benchmark / RFC links.
