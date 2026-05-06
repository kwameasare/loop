---
name: add-studio-component
description: Use when adding or changing a reusable Loop Studio UI component, design-system primitive, or domain component.
when_to_use: |
  - Adding a shared React component in apps/studio.
  - Changing a component used by more than one Studio surface.
  - Implementing a target-standard primitive such as Trace Scrubber, EvidenceCallout, ConfidenceMeter, DiffRibbon, RiskHalo, LiveBadge, StageStepper, MetricCountUp, or SnapshotCard.
  - Encoding a reusable pattern for traces, evals, migration, deploys, memory, tools, knowledge, costs, or collaboration.
required_reading:
  - ux/00_CANONICAL_TARGET_UX_STANDARD.md
  - engineering/COPY_GUIDE.md
  - engineering/HANDBOOK.md
applies_to: ux
owner: Product Design + Founding Eng #5
last_reviewed: 2026-05-06
---

# Add Studio Component

## Trigger

Use this skill when the work creates or changes a reusable Studio component. If the work is a whole screen or workflow, start with `ux/design-studio-surface.md`, then use this skill for the shared pieces.

Components in Studio are not decorative building blocks. They are control, evidence, state, and decision-support primitives for builders.

## Required Reading

1. `ux/00_CANONICAL_TARGET_UX_STANDARD.md`, especially:
   - Section 3, Principles
   - Section 5, Information Architecture
   - Section 23, Builder Control Model
   - Section 28, Visual Language
   - Section 29, Motion, Tactility, And Sound
   - Section 30, Accessibility And Inclusion
   - Section 32, States And Copy
   - Section 37, Screen Quality Bar
2. `engineering/COPY_GUIDE.md` for any user-facing text.
3. `engineering/HANDBOOK.md` for TypeScript, React, and code conventions.

## Steps

1. **Name the product job.**
   - Which builder question does this component answer?
   - Which canonical object does it represent: agent, trace, turn, tool, knowledge source, memory, eval, deploy, migration, cost, approval, snapshot, scene, or comment?
   - Which IA verb owns it: Build, Test, Ship, Observe, Migrate, or Govern?

2. **Classify the component.**
   - **Primitive:** generic design-system unit such as button, badge, meter, stepper, callout, timeline, command item.
   - **Domain component:** reusable Loop object view such as TraceSpan, EvalResultCard, MigrationGapCard, ToolGrantPanel.
   - **Surface composition:** multi-part component that belongs to a screen. If it is too screen-specific, keep it local.

3. **Design the state matrix before coding.**
   Cover at minimum:
   - default
   - hover/focus/active
   - selected
   - loading
   - empty
   - error
   - degraded/stale
   - read-only
   - permission-blocked
   - reduced-motion
   - compact and comfortable density when relevant

4. **Expose evidence and control.**
   A target-standard component should usually answer:
   - What is this object?
   - What state is it in?
   - What evidence supports the claim?
   - What can the builder safely do next?
   - What happens if the builder clicks through?

5. **Use canonical visual behavior.**
   - Follow Section 28 for palette, typography, iconography, status treatment, and non-color status indicators.
   - Follow Section 29 for motion. Motion must explain cause/effect, not decorate.
   - Do not introduce one-off colors, oversized radius, nested cards, bokeh/orb decoration, or marketing-style panels.

6. **Keep layout stable.**
   - Define stable dimensions for counters, icon buttons, timeline items, meters, trace spans, and repeated rows.
   - Hover and loading states must not resize the layout.
   - Long labels must wrap or truncate intentionally with accessible full text.

7. **Implement with local conventions.**
   - Prefer existing primitives before inventing a new one.
   - Use function components with named exports.
   - Use Tailwind utilities and project tokens.
   - Accept `className` for composition where appropriate.
   - Forward refs for interactive wrappers.
   - Keep domain logic out of presentational primitives.

8. **Make accessibility a component contract.**
   - Keyboard access for every interaction.
   - Visible focus rings.
   - ARIA labels for icon-only actions.
   - Shape, icon, text, or pattern in addition to color.
   - Reduced-motion equivalent for every animated state.
   - Screen-reader text for meters, charts, status arcs, and progress indicators.

9. **Write stories and tests.**
   - Storybook story or equivalent component showcase if Storybook exists.
   - Cover default, loading, error, empty, selected, permission-blocked, reduced-motion, and dense states.
   - Vitest/Testing Library for behavior and accessibility-sensitive logic.
   - Visual regression when the component is a core primitive.

10. **Update docs only when the pattern changes.**
   - Update `ux/00_CANONICAL_TARGET_UX_STANDARD.md` only if the component creates or changes a target-standard pattern.
   - For implementation-only component inventory, prefer the app design-system docs or Storybook.

## Definition Of Done

- [ ] Component maps to a canonical object, IA verb, and builder question.
- [ ] State matrix is implemented or intentionally scoped.
- [ ] Evidence/control behavior is visible where relevant.
- [ ] Uses existing tokens/primitives unless a new one is justified.
- [ ] No raw color values where tokens exist.
- [ ] Layout is stable across hover, loading, and dynamic content.
- [ ] Keyboard, focus, screen-reader, contrast, and reduced-motion paths are covered.
- [ ] User-facing text follows `engineering/COPY_GUIDE.md` and `ux/write-ui-copy.md`.
- [ ] Tests/stories cover meaningful states.
- [ ] Canonical UX doc updated only if the target pattern changed.

## Anti-Patterns

- A beautiful component that hides state, evidence, permission, or consequence.
- Components that make Studio feel like a marketing page instead of a builder cockpit.
- Nested cards, floating page-section cards, or decorative wrappers around everything.
- Color-only status.
- Magic health scores with no click-through evidence.
- Generic empty states when workspace evidence can propose a next action.
- Components that silently mutate production or imply production mutation.
- Component APIs that bake in one screen's assumptions and block reuse.

## Related Skills

- `ux/design-studio-surface.md` for whole screens and workflows.
- `ux/add-design-token.md` when a missing token blocks a reusable pattern.
- `ux/write-ui-copy.md` for copy, errors, empty states, and labels.
- `ux/review-studio-ux.md` before merging high-impact UX changes.
- `coding/implement-studio-screen.md` when the component is part of a screen implementation.

## References

- `ux/00_CANONICAL_TARGET_UX_STANDARD.md`
- `engineering/COPY_GUIDE.md`
- `engineering/HANDBOOK.md`
