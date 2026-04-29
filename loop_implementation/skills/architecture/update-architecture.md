---
name: update-architecture
description: Use when adding, removing, or changing a system component, sequence, deployment topology, or cross-cutting concern.
when_to_use: |
  - New container/service in the data or control plane.
  - Removed or merged service.
  - New sequence diagram (any new flow that crosses ≥ 2 services).
  - Deployment topology change.
  - NFR / budget update.
required_reading:
  - architecture/ARCHITECTURE.md
  - engineering/HANDBOOK.md  # §10 docs-with-code
applies_to: architecture
owner: CTO + module owner
last_reviewed: 2026-04-29
---

# Update architecture doc

## Trigger

Architecture changed; ARCHITECTURE.md must reflect it.

## Required reading

`architecture/ARCHITECTURE.md` end-to-end.

## Steps

1. **Glossary first** — if you're adding a new concept, also add to `engineering/GLOSSARY.md` (and §0 if material to the architecture).
2. **Identify the right level (C4):** Context (§1) / Containers (§2) / Components (§3) / Sequences (§4).
3. **Update the table or diagram in place.** Don't add a new section unless the concept warrants one.
4. **Sequence diagrams** as ASCII art (so they diff cleanly). Mermaid OK only in the docs site, not in `architecture/ARCHITECTURE.md`.
5. **NFRs** (§9) update only with explicit ADR or owner sign-off — these are commitments.
6. **Cross-link** to ADRs, runbooks, perf budgets, and security sections that the change touches.
7. **Service ownership** (§11) updated if the new service has a new owner.
8. **Same PR as the code.** Apply `engineering/HANDBOOK.md` §10.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Right C4 level updated.
- [ ] Glossary updated.
- [ ] Sequence diagrams in ASCII.
- [ ] Cross-links present.
- [ ] Owner section updated if applicable.
- [ ] Same PR as the code.

## Anti-patterns

- ❌ Adding a new section instead of updating an existing one.
- ❌ Updating ARCHITECTURE.md without the glossary.
- ❌ Mermaid in this file (use ASCII).
- ❌ Skipping the cross-link.

## Related skills

- `architecture/propose-adr.md`.

## References

- `architecture/ARCHITECTURE.md`.
