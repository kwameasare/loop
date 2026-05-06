---
name: design-studio-surface
description: Use when designing, redesigning, or specifying a Loop Studio screen, workflow, IA area, or high-impact interaction before implementation.
when_to_use: |
  - Designing a new Studio screen or major tab.
  - Redesigning an existing Studio workflow.
  - Translating a canonical target UX capability into an implementable screen plan.
  - Creating UX specs for Trace Theater, Agent Workbench, Eval Foundry, Migration Atelier, Deployment Flight Deck, Observatory, HITL Inbox, Memory Studio, Tools Room, Knowledge Atelier, Voice Stage, or enterprise governance.
  - Resolving UX ambiguity before coding.
required_reading:
  - ux/00_CANONICAL_TARGET_UX_STANDARD.md
  - engineering/COPY_GUIDE.md
  - engineering/GLOSSARY.md
applies_to: ux
owner: Product Design + Product + Studio Engineering
last_reviewed: 2026-05-06
---

# Design Studio Surface

## Trigger

Use this skill before implementation when the task affects the shape of a Studio screen or workflow. The output should be a clear UX spec that an engineer can implement and a reviewer can judge against the canonical target.

Studio's canonical target is not "make a screen." It is "help a builder control a production agent with evidence, speed, and confidence."

## Required Reading

1. `ux/00_CANONICAL_TARGET_UX_STANDARD.md` end-to-end for major surfaces.
2. For focused work, always read:
   - Section 1, Product Promise
   - Section 3, Principles
   - Section 5, Information Architecture
   - Section 6, Studio Shell
   - Section 23, Builder Control Model
   - Section 28-32, visual language, motion, accessibility, responsive modes, states/copy
   - Section 37, Screen Quality Bar
3. Read the surface-specific section:
   - Agent Workbench: Section 7
   - Agent Map And Code: Section 8
   - Simulator: Section 9
   - Trace Theater: Section 10
   - Behavior Editor: Section 11
   - Tools Room: Section 12
   - Knowledge Atelier: Section 13
   - Memory Studio: Section 14
   - Eval Foundry: Section 15
   - Voice Stage: Section 16
   - Migration Atelier: Section 18
   - Deployment Flight Deck: Section 19
   - Observatory: Section 20
   - HITL Inbox: Section 21
   - Enterprise: Section 24
   - Collaboration: Section 25
   - AI Co-Builder: Section 26

## Steps

1. **State the builder job.**
   Write one sentence:

   ```text
   This surface helps [persona] answer [product question] while [building/testing/shipping/observing/migrating/governing] [object].
   ```

2. **Choose the IA verb.**
   The surface must live under Build, Test, Ship, Observe, Migrate, or Govern. Product names like Trace Theater or Migration Atelier are moments inside those verbs, not a second navigation system.

3. **Name canonical objects.**
   Identify every object the surface manipulates:
   - agent
   - turn
   - trace
   - tool
   - knowledge source
   - memory
   - eval
   - deploy
   - canary
   - migration mapping
   - snapshot
   - scene
   - approval
   - cost budget

4. **Define object state and environment.**
   Show how the surface communicates:
   - Draft
   - Saved
   - Staged
   - Canary
   - Production
   - Archived
   - dev/staging/production/custom environments
   - permission boundaries
   - read-only and degraded modes

5. **Design the evidence model.**
   Every important claim must click into evidence:
   - trace span
   - eval result
   - replay diff
   - source chunk
   - memory diff
   - tool call
   - cost line item
   - audit event
   - migration lineage
   - policy

6. **Design the control model.**
   Specify:
   - primary action
   - safe secondary actions
   - preview before apply
   - undo/revert/rollback
   - fork/replay/save-as-eval where relevant
   - approval gates
   - destructive confirmations
   - what cannot happen from this surface

7. **Use the five-region shell deliberately.**
   Decide what belongs in:
   - topbar
   - asset rail
   - main work surface
   - live preview or inspector
   - timeline/status footer

   Do not create a landing page when the user needs a working surface.

8. **Specify all states.**
   Include:
   - loading
   - empty
   - error
   - degraded
   - permission-blocked
   - offline/reconnecting if live
   - no data yet
   - partial data
   - stale data

9. **Add decision support.**
   Major objects should show:
   - why this matters
   - recommendation
   - evidence
   - confidence
   - next-best action
   - risk and rollback path

10. **Choose excitement carefully.**
   Add polish only when it reveals state, evidence, control, or time:
   - Trace Scrubber
   - replay against draft
   - Agent X-Ray
   - inverse retrieval
   - latency budget visualizer
   - comments-as-specs
   - snapshots
   - scenes
   - earned moments

   If the idea is only decorative, cut it.

11. **Design responsive behavior.**
   - Desktop: full authoring power.
   - Tablet: review, approval, trace summary, parity report.
   - Mobile: urgent actions only, such as acknowledge, approve/decline, rollback, takeover, inspect summary.
   - Large display: second-monitor or war-room mode where relevant.

12. **Write the UX handoff.**
   Include:
   - purpose
   - personas
   - IA location
   - objects and states
   - layout regions
   - primary flows
   - component list
   - copy examples
   - data/API needs
   - empty/loading/error/degraded states
   - accessibility notes
   - metrics
   - open questions

## Definition Of Done

- [ ] Surface maps to one IA verb and at least one product question.
- [ ] Canonical objects, states, and environments are named.
- [ ] Evidence model is explicit.
- [ ] Preview, undo/revert/rollback, and permission boundaries are defined.
- [ ] All states are specified.
- [ ] Copy follows friendly precision.
- [ ] Accessibility and responsive modes are specified.
- [ ] Enterprise constraints are included when the surface touches production, secrets, audit, data, approvals, or compliance.
- [ ] At least one measurement or validation metric is named.
- [ ] The Screen Quality Bar in Section 37 passes.

## Anti-Patterns

- A surface that cannot answer which builder question it serves.
- Canvas-first or flow-builder-first thinking that hides agent primitives.
- Product names becoming a second navigation taxonomy.
- AI suggestions without diff, evidence, and consent.
- Health, confidence, parity, or risk scores with no click-through proof.
- Production-changing actions without explicit state, gate, and rollback.
- Empty states that say nothing useful.
- Marketing hero layouts inside the product.
- Visual excitement that does not reveal evidence, state, control, or time.

## Related Skills

- `coding/implement-studio-screen.md` after the surface is specified.
- `ux/add-studio-component.md` for reusable components.
- `ux/write-ui-copy.md` for strings.
- `ux/add-design-token.md` for visual-system changes.
- `ux/review-studio-ux.md` for pre-merge review.

## References

- `ux/00_CANONICAL_TARGET_UX_STANDARD.md`
- `engineering/COPY_GUIDE.md`
- `engineering/GLOSSARY.md`
