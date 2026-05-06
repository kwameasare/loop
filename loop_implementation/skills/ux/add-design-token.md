---
name: add-design-token
description: Use when adding or changing a Studio design token for color, typography, spacing, radius, elevation, motion, density, or status treatment.
when_to_use: |
  - Adding or changing a semantic color, status treatment, typography scale, spacing, radius, elevation, shadow, motion duration, easing curve, or density token.
  - Converting repeated raw values into a token.
  - Implementing visual language from the canonical target UX standard.
  - Adding accessibility-safe variants for reduced motion, high contrast, color-blind safety, or density.
required_reading:
  - ux/00_CANONICAL_TARGET_UX_STANDARD.md
  - engineering/HANDBOOK.md
applies_to: ux
owner: Product Design + Founding Eng #5
last_reviewed: 2026-05-06
---

# Add Design Token

## Trigger

Use this skill when a Studio visual or motion decision needs to become reusable code. Tokens are the bridge between the canonical target UX and implementation. Add them carefully: every token creates a vocabulary future contributors will use.

## Required Reading

1. `ux/00_CANONICAL_TARGET_UX_STANDARD.md`, especially:
   - Section 28, Visual Language
   - Section 29, Motion, Tactility, And Sound
   - Section 30, Accessibility And Inclusion
   - Section 31, Responsive Modes
   - Section 32, States And Copy
   - Section 42, Evolution
2. Existing app token files:
   - `apps/studio/src/app/globals.css` or current global CSS path
   - `apps/studio/tailwind.config.*` if present
   - existing component styles that use the relevant token family

## Token Decision Rules

Add or change a token only when at least one is true:

- The value appears in two or more places.
- The value expresses a canonical product state such as Live, Canary, Pending review, Approved, Mocked, Stale, Needs your eyes, Read-only, Risk, or Evidence.
- The value supports a named motion or polish primitive such as FocusPulse, MetricCountUp, StageStepper, EvidenceCallout, ConfidenceMeter, DiffRibbon, LiveBadge, CompletionMark, or RiskHalo.
- The value is required for accessibility, reduced motion, high contrast, density, or color-blind safety.
- Product Design explicitly promotes the value from local styling to the system.

Do not add a token for a one-off flourish.

## Steps

1. **Classify the token.**
   - color
   - typography
   - spacing
   - radius
   - elevation/shadow
   - motion duration
   - motion curve
   - opacity
   - density
   - status treatment
   - chart/trace shape or pattern

2. **Name it semantically.**
   Use product meaning, not raw appearance:
   - Good: `color.status.canary.bg`
   - Good: `motion.duration.expressive`
   - Good: `radius.control`
   - Avoid: `color.orange500`
   - Avoid: `duration.400`

3. **Check the canonical visual constraints.**
   - Avoid one-note palettes.
   - Status cannot rely on color alone.
   - Cards stay restrained; do not create new decorative card styles casually.
   - Motion must clarify cause/effect.
   - Reduced motion is first-class.
   - No confetti, particle effects, bokeh/orb backgrounds, or childish bounce.

4. **Define implementation values in the app design system.**
   - CSS variables for runtime theming.
   - Tailwind theme extension if Tailwind consumes it.
   - TypeScript token map only if components need typed access.
   - Light and dark values where relevant.
   - High-contrast/reduced-motion alternatives where relevant.

5. **Prove contrast and accessibility.**
   - Text contrast meets WCAG 2.2 AA.
   - Focus treatment is visible in dark and light themes.
   - Color-blind simulations remain distinguishable when the token represents state.
   - Motion token has reduced-motion fallback.

6. **Replace repeated raw values.**
   Convert the target call sites in the same change if safe. Do not leave a token unused unless it is part of a larger staged migration and the PR explains why.

7. **Document at the right level.**
   - Implementation details belong in app design-system docs or Storybook.
   - `ux/00_CANONICAL_TARGET_UX_STANDARD.md` changes only when the target visual language itself changes.
   - Section 42 says exact token tables can move out of the canonical target as the design system matures.

8. **Verify visually.**
   - Run relevant unit/story tests if available.
   - Inspect dark, light, reduced-motion, and high-contrast states.
   - Check at least one dense table/list and one spacious surface if the token affects layout.

## Definition Of Done

- [ ] Token is justified by reuse, product state, accessibility, or explicit design-system need.
- [ ] Name is semantic and stable.
- [ ] Dark/light values exist where relevant.
- [ ] Reduced-motion/high-contrast alternatives exist where relevant.
- [ ] Status treatment has non-color support where relevant.
- [ ] Existing raw values were replaced where safe.
- [ ] Visual checks or screenshots cover the token's real use.
- [ ] Canonical target doc updated only if the target visual language changed.

## Anti-Patterns

- Literal token names such as `blue500` for product semantics.
- Single-use tokens created to justify a one-off visual.
- New accent colors that weaken the trust palette.
- Color-only status tokens.
- Motion tokens that enable decorative animation without state meaning.
- Tokens added to the canonical target doc when they belong in implementation docs.
- Raw hex added to components after a semantic token exists.

## Related Skills

- `ux/add-studio-component.md` when a token supports a reusable component.
- `ux/design-studio-surface.md` when token changes affect a whole surface.
- `ux/review-studio-ux.md` for visual and accessibility review.

## References

- `ux/00_CANONICAL_TARGET_UX_STANDARD.md`
- `engineering/HANDBOOK.md`
