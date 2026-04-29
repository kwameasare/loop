---
name: add-design-token
description: Use when adding or changing a design token — color, spacing, radius, typography.
when_to_use: |
  - Adding a new semantic color.
  - Tightening or loosening a spacing scale.
  - Adding a radius or elevation tier.
required_reading:
  - ux/UX_DESIGN.md   # §5 design tokens
applies_to: ux
owner: Designer + Founding Eng #5
last_reviewed: 2026-04-29
---

# Add design token

## Trigger

Tokens are the boundary between "design" and "code." Add carefully — every token is forever.

## Required reading

`ux/UX_DESIGN.md` §5.

## Steps

1. **Justify**: tokens are added when ≥ 2 places use the same value. One-off colors stay inline.
2. **Naming**: semantic, not literal. `color.brand.primary`, not `color.navy_0F1E3A`.
3. **Define in two places:**
   - CSS variable in `apps/studio/app/globals.css`.
   - Tailwind config in `apps/studio/tailwind.config.ts`.
4. **Dark + light modes:** every color token has both values. Use `:root` + `[data-theme="dark"]`.
5. **Document** in `ux/UX_DESIGN.md` §5 in the relevant table.
6. **Tests:** Storybook visual snapshot on the design-system page.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Used in ≥ 2 places.
- [ ] Semantic name.
- [ ] Both modes defined.
- [ ] Listed in UX_DESIGN.md.
- [ ] Storybook snapshot updated.

## Anti-patterns

- ❌ Literal naming (`color_blue_500`).
- ❌ Single-mode token.
- ❌ Inline use of the token's underlying hex bypassing the variable.

## Related skills

- `ux/add-studio-component.md`.

## References

- `ux/UX_DESIGN.md` §5.
