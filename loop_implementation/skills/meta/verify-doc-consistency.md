---
name: verify-doc-consistency
description: Use after a large change spans multiple docs to verify cross-references resolve and conventions are consistent.
when_to_use: |
  - After an audit pass.
  - Before a release.
  - After a multi-PR feature lands on main.
required_reading:
  - README.md
  - AGENTS.md
applies_to: meta
owner: CTO
last_reviewed: 2026-04-29
---

# Verify doc consistency

## Trigger

Large changes; pre-release.

## Required reading

`README.md`, `AGENTS.md`.

## Steps

1. **ADR count:** every doc that references the count says the same number. Search:
   ```bash
   grep -rn "[0-9]\+ ADR\|all [0-9]\+" loop_implementation/ | grep -v tracker
   ```
2. **ADR-NNN cross-refs:** every cited ADR exists in `adrs/README.md`.
3. **File map:** `README.md` folder tree matches `find loop_implementation -type f`.
4. **Reading order:** `AGENTS.md` canonical reading order matches the existing files.
5. **Glossary:** `engineering/GLOSSARY.md` contains every term used >2x in other docs.
6. **Schema ↔ Pydantic ↔ OpenAPI:** all three describe the same shapes.
7. **Skill catalog:** `skills/README.md` and `skills/_base/SKILL_ROUTER.md` list the same skills.
8. **Tracker:** `TRACKER.md`, `tracker.json`, `csv/*` regenerated together.
9. **Trace retention:** consistent across `engineering/SECURITY.md`, `data/SCHEMA.md`, `architecture/ARCHITECTURE.md`, `engineering/GLOSSARY.md`.
10. **Voice latency target:** consistent across `architecture/ARCHITECTURE.md` §9, `engineering/HANDBOOK.md`, `engineering/PERFORMANCE.md`, `tracker/TRACKER.md`.
11. **Cloud-portability:** no AWS-specific assumption in any non-CLOUD_PORTABILITY doc.

Run the canned check:

```bash
bash tools/verify_docs.sh
```

(If the script doesn't exist yet, create it from these checks as a one-time chore.)

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] All checks above pass.
- [ ] Discrepancies fixed in the same PR.
- [ ] `tools/verify_docs.sh` runs clean (or exists).

## Anti-patterns

- ❌ Skipping a check because "it's probably fine."
- ❌ Letting docs drift across releases.

## Related skills

- `meta/update-tracker.md`.

## References

- `README.md`, `AGENTS.md`.
