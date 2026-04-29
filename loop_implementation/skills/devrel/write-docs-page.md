---
name: write-docs-page
description: Use when adding a docs page (quickstart, API reference page, conceptual guide, error-code page).
when_to_use: |
  - New feature ships → docs page.
  - New error code → docs/errors/LOOP-XX-NNN.md page.
  - Customer feedback shows confusion → fill the gap.
required_reading:
  - engineering/COPY_GUIDE.md
  - apps/docs/README.md (if exists)
applies_to: devrel
owner: Eng #6 (DevRel)
last_reviewed: 2026-04-29
---

# Write docs page

## Trigger

Doc gap closes when shipped.

## Required reading

`engineering/COPY_GUIDE.md`.

## Steps

1. **Pick the right shape:**
   - Quickstart: 60-second copy-paste path. One success criterion.
   - Conceptual: explain a primitive (Agent, Tool, Memory). One diagram. Cross-link to API ref.
   - API reference: auto-generated from `api/openapi.yaml` — only override when human prose helps.
   - Error code: one per `LOOP-XX-NNN`. What/why/recovery + linked runbook.
2. **Lede in one sentence**: what is this, who is it for, what's the outcome.
3. **Code samples must run.** Tests in `apps/docs/_tested/<page>.py` execute the snippets in CI.
4. **Apply COPY_GUIDE.** Voice + tone consistency.
5. **Cross-link** to canonical docs (ARCHITECTURE, SCHEMA, ADRs) where appropriate.
6. **Search-friendly title** (include the keyword the user typed).
7. **Diagrams** as Mermaid (renders in MDX). For complex topology, screenshot from infra dashboards.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Lede in one sentence.
- [ ] Tested code samples.
- [ ] Cross-links present.
- [ ] COPY_GUIDE applied.
- [ ] Renders correctly in Docusaurus preview.

## Anti-patterns

- ❌ Code samples that don't run.
- ❌ Marketing voice in technical docs.
- ❌ Missing the user's actual search keyword.
- ❌ Pasting Markdown without preview.

## Related skills

- `ux/write-ui-copy.md`.

## References

- `engineering/COPY_GUIDE.md`.
