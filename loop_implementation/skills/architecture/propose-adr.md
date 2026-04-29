---
name: propose-adr
description: Use when making a non-trivial technical decision — anything that constrains future work, defines a contract between services, or commits to a vendor/library.
when_to_use: |
  - Picking a new database, message bus, vector store, or framework.
  - Changing reasoning-loop semantics, eval-gate thresholds, or pricing math.
  - Adding a forbidden cloud service (overrides ADR-016).
  - Establishing a deprecation policy or version-skew rule.
  - Reversing a previous decision.
required_reading:
  - adrs/README.md
  - engineering/templates/ADR_TEMPLATE.md
applies_to: architecture
owner: CTO + relevant module owner
last_reviewed: 2026-04-29
---

# Propose ADR

## Trigger

A decision worth writing down. If a future engineer would ask "why did we pick this?", it's an ADR.

## Required reading

`adrs/README.md` end-to-end (so you don't repeat or contradict an existing one).
`engineering/templates/ADR_TEMPLATE.md`.

## Steps

1. **Search for existing.** Make sure your decision isn't already covered or contradicted.
2. **Pick the next free ADR number.** Currently 028 is the latest accepted; next free = 029. Never reuse retired numbers.
3. **Write to the template** (`engineering/templates/ADR_TEMPLATE.md`):
   - Title: verb + noun ("Use Qdrant as default vector store").
   - Status: `Proposed`. Move to `Accepted` after review.
   - Context: forces driving the decision; cite measurable signals.
   - Decision: the answer in current-tense fact.
   - Consequences: ✅ wins, ⚠️ tradeoffs, ❌ accepted costs.
   - Alternatives: each rejected option + why.
   - Revisit conditions: when would we reconsider.
4. **Append to `adrs/README.md`** in numerical order. Update the index table at the top.
5. **Cross-link from affected docs** — `architecture/ARCHITECTURE.md` references the ADR; affected runbooks/skills update their `adrs/README.md` cite.
6. **PR review:** at minimum CTO + two seniors. Discussion in the PR; once consensus, flip Status to `Accepted` and merge.
7. **Supersede vs deprecate:** never edit an Accepted ADR after merge — write a new one that supersedes it. The new ADR's "Supersedes" header points back. The old one stays in the file with `Status: Superseded by ADR-XXX`.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Next free number picked.
- [ ] Template fully filled (no TODOs).
- [ ] Index updated in `adrs/README.md`.
- [ ] Cross-links from affected docs added.
- [ ] CTO + two seniors approved.
- [ ] Status flipped to `Accepted`.

## Anti-patterns

- ❌ Editing an existing Accepted ADR. Supersede instead.
- ❌ ADR for a one-off implementation detail. Save ADRs for decisions that will outlive the implementer.
- ❌ "Accepted" without revisit conditions.
- ❌ Conflicting with an existing ADR without explicit supersession.

## Related skills

- `architecture/update-architecture.md` (often runs after an architectural ADR).

## References

- `adrs/README.md`.
- `engineering/templates/ADR_TEMPLATE.md`.
