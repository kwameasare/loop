# RFC-NNN — Title

**Status:** Draft | In review | Accepted | Rejected | Withdrawn
**Author:** Name
**Reviewers:** Name1 (required), Name2 (required), Name3 (FYI)
**Date:** YYYY-MM-DD

## Summary

One-paragraph elevator pitch. What changes; who notices.

## Motivation

Why this is worth doing. Measurable signals (numbers > stories). What's broken or missing today.

## Goals

What does success look like? Make these testable:
- Goal 1 (e.g., "p99 KB query under 100ms with 100M chunks")
- Goal 2

## Non-goals

What this RFC explicitly does NOT do (to scope-protect the discussion).

## Proposal

The actual design. Use diagrams where helpful (ASCII OK). Be specific:
- New components / interfaces / APIs / schemas.
- Data flow.
- Failure modes and how they're handled.
- Migration plan.

### Public API surface

If this changes a public API, show the before / after as code blocks.

### Schema changes

Show DDL deltas. Reference `data/SCHEMA.md` updates.

### Performance impact

Numbers, not vibes.

### Security impact

Threat model delta. Reference `engineering/SECURITY.md` sections.

### Cloud-portability impact

Confirm: does this introduce a cloud-coupling? If yes, how is the two-cloud rule satisfied?

## Rollout plan

Sequenced steps with timing.
1. Phase 1 — feature flag, dark-launch.
2. Phase 2 — internal cohort.
3. Phase 3 — beta to design partners.
4. Phase 4 — GA.

Include a rollback plan.

## Risks

- Risk 1 — likelihood / severity / mitigation.
- Risk 2.

## Alternatives considered

Same shape as ADR-style alternatives.

## Open questions

For reviewers to weigh in on.

## References

- Related RFCs / ADRs / runbooks.
