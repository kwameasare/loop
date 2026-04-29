---
name: add-studio-component
description: Use when adding a new shared React component for Studio.
when_to_use: |
  - Component will be reused across screens.
  - Component encodes a design pattern (TraceWaterfall, ConversationStream, …).
required_reading:
  - ux/UX_DESIGN.md          # §4 component library
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

`ux/UX_DESIGN.md` §4.

## Steps

1. **File**: `apps/studio/components/<feature>/<Name>.tsx`. Function component, named export, no defaults.
2. **Storybook story**: `<Name>.stories.tsx` covering: default, loading, error, empty, dense modes.
3. **Tokens only.** No raw hex, no inline px (use Tailwind tokens or `ux/UX_DESIGN.md` §5).
4. **Polymorphic via `as` prop** when shape varies (e.g., link vs button).
5. **Forward refs** when the component wraps an interactive primitive.
6. **Accessibility:** ARIA labels for icon-only buttons; visible focus rings; keyboard navigation; reduced motion support.
7. **i18n:** strings via `t()`.
8. **Tests:** Vitest for behavior; Storybook a11y addon for accessibility regressions.
9. **Add to `ux/UX_DESIGN.md` §4 component table.**

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Tokens-only styling.
- [ ] Story covers default + states.
- [ ] A11y checks pass.
- [ ] Forward refs where applicable.
- [ ] Added to component table in UX_DESIGN.md.

## Anti-patterns

- ❌ Inline colors.
- ❌ Component that doesn't expose `className` for overrides.
- ❌ Missing keyboard support.
- ❌ Default exports.

## Related skills

- `coding/implement-studio-screen.md`, `ux/add-design-token.md`, `ux/write-ui-copy.md`.

## References

- `ux/UX_DESIGN.md` §4–§5.
