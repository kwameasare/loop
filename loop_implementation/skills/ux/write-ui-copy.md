---
name: write-ui-copy
description: Use when authoring or reviewing user-facing copy for Studio, including labels, errors, empty states, recommendations, toasts, dialogs, approvals, audit text, and docs intros.
when_to_use: |
  - Adding or changing button labels, form labels, helper text, empty states, loading states, errors, toasts, banners, recommendations, confirmation dialogs, approval copy, audit text, or onboarding copy.
  - Explaining traces, evals, migration gaps, deployment gates, cost changes, memory writes, tool permissions, or AI-generated recommendations.
  - Writing copy for enterprise, security, compliance, procurement, or operator workflows.
required_reading:
  - engineering/COPY_GUIDE.md
  - ux/00_CANONICAL_TARGET_UX_STANDARD.md
applies_to: ux
owner: Product Design + author of the change
last_reviewed: 2026-05-06
---

# Write UI Copy

## Trigger

Use this skill for any text a user can see. In Loop Studio, copy is part of the control surface: it tells builders what happened, why it matters, what evidence exists, and what they can safely do next.

## Required Reading

1. `engineering/COPY_GUIDE.md` end-to-end.
2. `ux/00_CANONICAL_TARGET_UX_STANDARD.md`, especially:
   - Section 3, Principles
   - Section 10.4, Explain Without Inventing
   - Section 23, Builder Control Model
   - Section 26, AI Co-Builder
   - Section 30, Accessibility And Inclusion
   - Section 32, States And Copy
   - Section 37, Screen Quality Bar
   - Appendix C, Copy Library

## Copy Principles

1. **Friendly precision.**
   Be warm enough to reduce anxiety and precise enough to support production decisions.

2. **Evidence over vibes.**
   Trace, eval, cost, migration, and deploy explanations must cite concrete evidence. If evidence is missing, say so.

3. **Control before comfort.**
   The builder should know the next safe action. Comforting copy that hides consequence is bad UX.

4. **No invented causality.**
   Do not say "the model likely reasoned" or imply knowledge the system does not have.

5. **No marketing voice inside production surfaces.**
   Studio is a builder cockpit, not a landing page.

## Steps

1. **Identify the object and state.**
   Name the object in the copy:
   - agent
   - trace
   - turn
   - tool
   - memory
   - eval
   - deploy
   - canary
   - migration
   - snapshot
   - scene
   - approval

   Name the state when relevant:
   - Draft
   - Saved
   - Staged
   - Canary
   - Production
   - Archived
   - Read-only
   - Degraded
   - Blocked

2. **Write the useful sentence first.**
   Good:

   ```text
   Promotion blocked. `refund_window_basic` regressed from 0.91 to 0.72.
   ```

   Weak:

   ```text
   Deployment failed.
   ```

3. **Include recovery or next action.**
   Every error, warning, empty state, and blocked action should offer a useful next step:
   - open diff
   - rerun eval
   - grant tool
   - reconnect secret
   - review mapping
   - keep current production version
   - roll back
   - save as eval
   - open trace

4. **Ground explanations.**
   For trace/eval/retrieval/memory/AI explanations, include at least one evidence source:
   - trace span
   - source chunk
   - eval case
   - config diff
   - policy
   - cost line item
   - source platform lineage
   - audit event

   If no evidence exists:

   ```text
   No evidence yet. Run replay or save production turns as evals to measure this.
   ```

5. **Use decision-support shape for recommendations.**
   Preferred format:

   ```text
   Add an escalation rule for refund disputes.
   Evidence: 7 of 12 failed refund turns ended with unresolved policy conflict.
   Expected effect: reduce failed refund evals.
   Risk: may increase human handoff rate.
   ```

6. **Use confidence carefully.**
   Use the canonical taxonomy:
   - High: direct evidence from traces/evals/config.
   - Medium: partial evidence or representative samples.
   - Low: weak sample or speculative recommendation.
   - Unsupported: no evidence; do not present as a recommendation.

7. **Respect enterprise seriousness.**
   Compliance, security, audit, data residency, BYOK, approvals, and production deploys require exact copy:
   - who is affected
   - what environment is affected
   - what permission or policy applies
   - what will be audited
   - how to reverse or escalate

8. **Make empty states productive.**
   Generic:

   ```text
   No evals yet.
   ```

   Target:

   ```text
   No evals yet. Save any simulator run or production turn as an eval case.
   ```

   Best when workspace data exists:

   ```text
   Save these 12 turns from yesterday as a starter eval suite.
   ```

9. **Localize and keep UI strings out of components.**
   Use the app localization system. Avoid hard-coded literals in React components.

10. **Read it under pressure.**
   Ask: would this copy help a tired builder at 2 a.m. decide what to do safely?

## Definition Of Done

- [ ] Copy uses canonical nouns.
- [ ] State and environment are named when relevant.
- [ ] Errors include what failed, why if known, affected object, and next action.
- [ ] Recommendations include evidence and expected effect.
- [ ] AI-generated explanations do not invent causality or telemetry.
- [ ] Empty/loading/degraded states are useful, not generic.
- [ ] Enterprise/security/compliance copy names policy, permission, and audit consequence when relevant.
- [ ] Copy is sentence case except product names and code identifiers.
- [ ] Strings are localized.
- [ ] No marketing voice inside production surfaces.

## Anti-Patterns

- "Something went wrong" with no recovery path.
- "The model likely reasoned differently."
- "Improve your prompt."
- "Awesome", "Whoops", "frictionless", "magic", "just works", or hype copy in production surfaces.
- Button labels like "Continue" when the action has risk.
- Hiding cost, latency, policy, or production consequence behind soft language.
- Anthropomorphizing the system to avoid accountability.

## Related Skills

- `ux/design-studio-surface.md` when copy belongs to a new workflow.
- `ux/add-studio-component.md` when copy lives inside a reusable component.
- `coding/implement-studio-screen.md` when implementing strings in Studio.

## References

- `engineering/COPY_GUIDE.md`
- `ux/00_CANONICAL_TARGET_UX_STANDARD.md`
