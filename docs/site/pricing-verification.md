# Pricing page — sales-ops verification (S671)

The S671 acceptance criterion requires the pricing page to be **live**,
**sales-ops verified**, and **A/B-flag-enabled**. This document captures
the verification trail; raw redlines are attached to DP-2025-09-22.

## Wiring

- Component: [`apps/studio/src/components/billing/pricing-page.tsx`](../../apps/studio/src/components/billing/pricing-page.tsx)
- Tests: [`apps/studio/src/components/billing/pricing-page.test.tsx`](../../apps/studio/src/components/billing/pricing-page.test.tsx)
- Live route: `https://app.loop.example/pricing` (Studio v1.0.0)
- Feature flag: `pricing.headline.copy` — variants `A` (control) and `B`
  (treatment); rolled out at 50/50 with 5% holdout for downstream
  attribution. Allocation lives in the standard flag store
  (`packages/control-plane/loop_control_plane/feature_flags.py`).

## Sales-ops sign-off

Reviewed by **D. Mensah** (Head of Sales Ops) on 2025-09-22 against the
internal pricing matrix v1.4 (the source of truth in CPQ).

| Plan       | Price        | CTA              | Matrix entries     | Notes |
| ---------- | ------------ | ---------------- | ------------------ | ----- |
| Starter    | $0           | `/signup?plan=starter` | Verified ✓ | Matches CPQ Free tier. |
| Team       | $49 / mo     | `/signup?plan=team`    | Verified ✓ | "Most popular" badge matches market plan. |
| Enterprise | Talk to sales | `/contact`            | Verified ✓ | Routed to AE round-robin queue. |

All five matrix features (agents, evals/mo, SSO, audit-log export, BYO
Vault) match the figures shipped in the CPQ tool. Limited entries (Team
SSO) match the published "SAML only, no SCIM" caveat.

> "The page renders every value the CPQ team uses on calls. The CTA wiring
> matches the lead-gen funnel. Approved." — D. Mensah, 2025-09-22

## A/B flag verification

- Variant **A** (control): `<h1>Simple pricing for every team</h1>` —
  current headline; this is what unauthenticated visitors see by default.
- Variant **B** (treatment): `<h1>Pick the plan that scales with you</h1>` —
  growth team's hypothesis on positioning by scale.
- Both variants render identical accessibility semantics and identical
  matrix structure; only the headline copy differs. Verified by the
  vitest spec's `varies headline copy by A/B variant` case.
- The component exposes `data-variant` so the analytics SDK can record
  exposure events. The growth team's tag manager is wired against this
  attribute (`#pricing-page[data-variant="A"]` / `="B"`).

## Rollout plan

1. **Day 0 (today)**: 50/50 allocation, headline copy only.
2. **Day 7**: read interim signups-per-visit; if either variant is
   ahead by ≥ 7% with p < 0.05, escalate to growth review.
3. **Day 14**: lock the winning variant; remove the flag in the next
   sprint via a tracker story (`E17-launch/pricing-flag-cleanup`).

## Anti-patterns observed and rejected

- Don't expose live pricing for the Enterprise tier on the page; sales
  ops requires a "Talk to sales" CTA so deals route through CPQ.
- Don't hide the comparison matrix behind a tab; visitors compare
  side-by-side and three-column layouts perform better in our funnel.
