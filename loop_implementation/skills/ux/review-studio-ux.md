---
name: review-studio-ux
description: Use when reviewing a Studio UX spec, screenshot, implementation, component, or workflow against the canonical target UX standard.
when_to_use: |
  - Reviewing a PR that changes Studio UI/UX.
  - Auditing an existing screen against the canonical target.
  - Comparing a proposed design to 00_CANONICAL_TARGET_UX_STANDARD.md.
  - Checking whether a component, copy set, or workflow is target-standard quality.
  - Producing findings without making changes.
required_reading:
  - ux/00_CANONICAL_TARGET_UX_STANDARD.md
  - engineering/COPY_GUIDE.md
applies_to: ux
owner: Product Design + Studio Engineering
last_reviewed: 2026-05-06
---

# Review Studio UX

## Trigger

Use this skill when asked to review UX/UI. Default to a findings-first review stance. Do not rewrite files unless the user explicitly asks for changes.

The review standard is `ux/00_CANONICAL_TARGET_UX_STANDARD.md`. Superseded drafts and legacy baselines are historical reference only.

## Required Reading

1. `ux/00_CANONICAL_TARGET_UX_STANDARD.md`, especially:
   - Section 1, Product Promise
   - Section 3, Principles
   - Section 5, Information Architecture
   - Section 23, Builder Control Model
   - Section 28-32, visual/copy/accessibility/state standards
   - Section 37, Screen Quality Bar
   - Section 41, Anti-Patterns
2. `engineering/COPY_GUIDE.md` for copy review.
3. The changed files, design spec, screenshots, or local UI under review.

## Review Severity

- **P0:** Can cause unsafe production changes, data exposure, broken auditability, severe accessibility failure, or misleading evidence.
- **P1:** Violates the target UX in a way that would materially reduce builder control, confidence, migration trust, deploy safety, or enterprise readiness.
- **P2:** Creates confusion, unnecessary friction, weak copy, missing state, incomplete evidence, or noticeable craft gap.
- **P3:** Polish, consistency, naming, or documentation improvement.

## Review Checklist

1. **Canonical authority.**
   - Does the work follow `00_CANONICAL_TARGET_UX_STANDARD.md`?
   - Does it accidentally revive the legacy baseline, superseded drafts, or canvas-first assumptions?

2. **Builder question.**
   - Which of the seven product questions does the screen answer?
   - Is that answer visible without hunting?

3. **IA and mental model.**
   - Does the surface fit Build, Test, Ship, Observe, Migrate, or Govern?
   - Are product names treated as modes, not competing nav?
   - Is it agent-native, not flow-builder-native?

4. **State and control.**
   - Are Draft/Saved/Staged/Canary/Production/Archived states clear where relevant?
   - Are environment, permissions, approvals, and rollback visible?
   - Is preview-before-apply respected?

5. **Evidence and explanation.**
   - Can every major claim click into trace, eval, source chunk, cost line, policy, audit event, migration lineage, or config diff?
   - Does any copy invent causality?

6. **Decision support.**
   - Are recommendations specific, evidence-backed, and reversible?
   - Is confidence labeled correctly?
   - Is next-best action visible?

7. **States and resilience.**
   - Loading, empty, error, degraded, stale, permission-blocked, and offline states are handled.
   - Empty states are productive and workspace-aware where possible.

8. **Accessibility and inclusion.**
   - Keyboard path exists.
   - Focus is visible.
   - Color is not the only signal.
   - Reduced motion works.
   - Text fits and does not overlap.
   - Dense data remains navigable.

9. **Visual craft and polish.**
   - Calm, classy, instrument-panel feel.
   - No nested cards or decorative page cards.
   - No one-note palette.
   - Motion clarifies cause/effect.
   - Delight is earned by proof, not noise.

10. **Enterprise readiness.**
   - Audit, RBAC, secrets, approvals, data residency, BYOK, procurement, or compliance implications are visible where relevant.

11. **Migration quality.**
   - If import/porting is involved, parity, lineage, source support labels, gap resolution, cutover, and rollback are visible.

## Output Format

Lead with findings ordered by severity. Use file/line references when reviewing files. For design-only reviews, reference screen regions or interaction names.

Suggested structure:

```markdown
Findings

- [P1] Title
  Evidence: file/path.md:123 or screen region.
  Why it matters: ...
  Recommendation: ...

Open Questions

- ...

Quality Bar

- Clarity: pass/fail
- Control: pass/fail
- Precision: pass/fail
- Friendliness: pass/fail
- Enterprise readiness: pass/fail
- Craft: pass/fail
- Delight: pass/fail
```

If there are no findings, say that clearly and name any residual risk or test gap.

## Definition Of Done

- [ ] Review uses the canonical target standard, not superseded drafts.
- [ ] Findings are severity-ranked.
- [ ] Each finding explains user impact.
- [ ] Recommendations are concrete.
- [ ] Screen Quality Bar is assessed.
- [ ] Accessibility, copy, enterprise, and evidence/control implications are considered.
- [ ] No file changes unless explicitly requested.

## Anti-Patterns

- Reviewing only visual taste and missing production safety.
- Praising "delight" that hides state or evidence.
- Accepting canvas-first flow mental models as the product center.
- Accepting AI explanations that invent telemetry.
- Treating legacy docs as authoritative.
- Producing a redesign instead of findings when asked for a review.

## Related Skills

- `ux/design-studio-surface.md` when the review reveals a need for a new spec.
- `ux/write-ui-copy.md` for copy fixes.
- `ux/add-studio-component.md` for component-level fixes.
- `coding/implement-studio-screen.md` for implementation after review.

## References

- `ux/00_CANONICAL_TARGET_UX_STANDARD.md`
- `engineering/COPY_GUIDE.md`
