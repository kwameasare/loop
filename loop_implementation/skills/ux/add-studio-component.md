---
name: add-studio-component
description: Use when adding a new shared React component for Studio.
when_to_use: |
  - Component will be reused across screens.
  - Component encodes a design pattern (TraceWaterfall, ConversationStream, …).
required_reading:
  - ux/00_CANONICAL_TARGET_UX_STANDARD.md          # canonical target UX/UI standard
  - engineering/HANDBOOK.md  # §2.2 TS conventions
  - engineering/COPY_GUIDE.md
applies_to: ux
owner: Founding Eng #5 (Studio)
last_reviewed: 2026-04-29
---

# Add Studio component

## Trigger

Adding a reusable component (not a one-off screen).

## Required reading

`ux/00_CANONICAL_TARGET_UX_STANDARD.md`, especially §28-32 and §37.

## Steps

1. **File**: `apps/studio/components/<feature>/<Name>.tsx`. Function component, named export, no defaults.
2. **Storybook story**: `<Name>.stories.tsx` covering: default, loading, error, empty, dense modes.
3. **Tokens only.** No raw hex, no inline px where a token exists. Follow `ux/00_CANONICAL_TARGET_UX_STANDARD.md` §28-29 for visual and motion intent.
4. **Polymorphic via `as` prop** when shape varies (e.g., link vs button).
5. **Forward refs** when the component wraps an interactive primitive.
6. **Accessibility:** ARIA labels for icon-only buttons; visible focus rings; keyboard navigation; reduced motion support.
7. **i18n:** strings via `t()`.
8. **Tests:** Vitest for behavior; Storybook a11y addon for accessibility regressions.
9. **Docs.** Update `ux/00_CANONICAL_TARGET_UX_STANDARD.md` when the component creates or changes a target UX pattern.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Tokens-only styling.
- [ ] Story covers default + states.
- [ ] A11y checks pass.
- [ ] Forward refs where applicable.
- [ ] Documented in 00_CANONICAL_TARGET_UX_STANDARD.md when it changes the target UX pattern.

## Anti-patterns

- ❌ Inline colors.
- ❌ Component that doesn't expose `className` for overrides.
- ❌ Missing keyboard support.
- ❌ Default exports.

## Related skills

- `coding/implement-studio-screen.md`, `ux/add-design-token.md`, `ux/write-ui-copy.md`.

## References

- `ux/00_CANONICAL_TARGET_UX_STANDARD.md` §28-32 and §37.
