---
name: implement-studio-screen
description: Use when building or modifying a screen in Loop Studio (Next.js + React + Tailwind + shadcn/ui).
when_to_use: |
  - Adding a new top-level Studio screen (e.g., a new dashboard, a new settings panel).
  - Adding a tab inside Agents Detail (Conversations / Versions / Evals / Cost / Settings).
  - Building or modifying the trace waterfall.
  - Implementing the operator inbox.
  - Adding a chart, table, or interactive component.
required_reading:
  - ux/00_CANONICAL_TARGET_UX_STANDARD.md              # canonical target UX/UI standard
  - api/openapi.yaml             # data shapes
  - engineering/HANDBOOK.md      # §2.2 TypeScript conventions
  - engineering/COPY_GUIDE.md    # any user-facing string
  - engineering/PERFORMANCE.md   # §1.1 LCP / TTI budgets
applies_to: coding
owner: Founding Eng #5 (Studio)
last_reviewed: 2026-04-29
---

# Implement Studio screen

## Trigger

Touching `apps/studio/`. Studio is the public face of Loop's quality story; a slow or buggy screen costs adoption.

## Required reading

1. `ux/00_CANONICAL_TARGET_UX_STANDARD.md` end-to-end (your screen must conform to the canonical target UX standard).
2. `api/openapi.yaml` for the endpoints you'll consume.
3. `engineering/COPY_GUIDE.md` for tone.

## Steps

1. **Pick the file location.**
   - Top-level screens: `apps/studio/app/<route>/page.tsx`.
   - Components: `apps/studio/components/<feature>/<Name>.tsx`. Function components only; named exports.
   - Hooks: `apps/studio/hooks/use<Name>.ts`.
2. **Data fetching.** TanStack Query only. No raw `fetch` in components.
   - Generated client lives in `apps/studio/lib/api/`. Re-generate from `api/openapi.yaml` via `pnpm openapi:generate`.
3. **State management.** Local first. Cross-cutting → Zustand. Never Redux.
4. **Styling.** Tailwind utility classes + shadcn/ui primitives. Follow `ux/00_CANONICAL_TARGET_UX_STANDARD.md` §28-29 for visual language, motion, and tactility; never use raw hex where a token exists.
5. **Dark mode.** Default. Both modes must look right. Test by toggling.
6. **Density modes.** Tables respect compact/normal/comfortable modes where the current Studio design system supports them.
7. **Empty / loading / error states.** Every screen has all three:
   - Empty: copy follows `ux/00_CANONICAL_TARGET_UX_STANDARD.md` §32 and Appendix C.
   - Loading: skeleton (no spinners on full pages).
   - Error: inline, with retry, and a `cmd-shift-c` shortcut to copy a debug bundle.
8. **Live updates.** Use WebSocket only for genuinely live surfaces such as operator inbox, conversation detail, trace tail, production tail, cost dashboard, and deploy watch. Others use polling.
9. **Keyboard shortcuts.** Add discoverable shortcuts for expert flows. Show in `?` help.
10. **Accessibility.** WCAG 2.2 AA and `ux/00_CANONICAL_TARGET_UX_STANDARD.md` §30. Visible focus rings; ARIA labels on icon-only buttons; reduced-motion respected.
11. **Internationalization.** Strings via `apps/studio/locales/<lang>.json`. No literals in components.
12. **Performance budgets** (`engineering/PERFORMANCE.md` §1.1):
    - LCP ≤ 1.0s (broadband).
    - Trace open ≤ 400ms p50.
    - Bundle: ≤ 250KB initial JS, ≤ 1MB total.
13. **Tests:**
    - Vitest unit for hooks and pure components.
    - Playwright e2e for the journey if it's a top-10 user journey (`engineering/TESTING.md` §4).
    - Lighthouse CI gates LCP/TBT/CLS.
14. **Docs.** Update `ux/00_CANONICAL_TARGET_UX_STANDARD.md` when the change affects the target UX standard.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Conforms to 00_CANONICAL_TARGET_UX_STANDARD.md.
- [ ] Empty / loading / error states present.
- [ ] Keyboard shortcuts added to catalog.
- [ ] WCAG 2.2 AA — focus, ARIA, contrast checked.
- [ ] i18n: strings in `locales/`.
- [ ] Bundle budgets met.
- [ ] Lighthouse CI passes.
- [ ] Vitest + Playwright tests.
- [ ] Live updates pattern correct (WS or poll).

## Anti-patterns

- ❌ Inline color hex codes. Always tokens.
- ❌ Spinners on full pages. Skeletons only.
- ❌ String literals in components. Always `t('key')`.
- ❌ Raw `fetch` in components. TanStack Query only.
- ❌ Default exports. Named only.
- ❌ Class components.
- ❌ Marketing voice in errors. Apply COPY_GUIDE.

## Related skills

- `ux/add-studio-component.md` if adding shared components.
- `ux/add-design-token.md` if a token is needed.
- `ux/write-ui-copy.md` for any user-facing string.
- `api/update-openapi.md` if Studio drives a new API need.
- `testing/write-e2e-test.md`.

## References

- `ux/00_CANONICAL_TARGET_UX_STANDARD.md` (whole doc).
- `engineering/COPY_GUIDE.md`.
- `engineering/PERFORMANCE.md` §1.1.
