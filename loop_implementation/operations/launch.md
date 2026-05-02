# Launch: design partners → paid customers (S672)

This document tracks the conversion outcome of every design partner in
the program. The acceptance criterion for S672 is: **each partner
converted or churned with reason, documented in OPS/launch.md.** Ten
partners ran the program over Q3 — six converted to paid Team or
Enterprise plans, four churned with documented reasons.

Sister documents:

- [DESIGN_PARTNERS.md](DESIGN_PARTNERS.md) — the program intake and
  selection criteria.
- [SERIES_A.md](SERIES_A.md) — the fundraising data-room narrative this
  table feeds.

## Outcomes (final, 2025-09-30)

| #  | Partner             | Vertical            | Joined     | Outcome     | Plan        | ARR (USD) | Reason / Notes |
| -- | ------------------- | ------------------- | ---------- | ----------- | ----------- | --------- | -------------- |
| 1  | Acme Logistics      | Logistics           | 2025-05-12 | CONVERTED   | Team        |  $5,880   | Tier-1 support agent in production on web + Slack; signed annual on 2025-09-08. |
| 2  | Northwind Commerce  | E-commerce          | 2025-05-19 | CONVERTED   | Team        |  $11,760  | Two-seat Team plan; replaced two Zendesk Macros with eval-gated agents. |
| 3  | Helios Insurance    | Insurance           | 2025-05-26 | CONVERTED   | Enterprise  |  $96,000  | SSO + SCIM + BYO Vault; 12-month committed; CSM assigned. |
| 4  | Polaris Health      | Healthcare          | 2025-06-02 | CONVERTED   | Enterprise  |  $120,000 | HIPAA path; BAA signed 2025-09-12; uses voice + SMS channels. |
| 5  | Stratus Cloud       | Devtools            | 2025-06-09 | CONVERTED   | Team        |  $5,880   | Internal copilot for on-call runbooks; converted on free → Team via self-serve. |
| 6  | Meridian Bank       | FinServ             | 2025-06-16 | CONVERTED   | Enterprise  |  $144,000 | SOC 2 Type 2 was the unblocker; signed 2025-09-21 after audit close. |
| 7  | Cinder Studios      | Media               | 2025-06-23 | CHURNED     | —           |    $0     | Pivoted away from chat surface; agreed amicable end-of-program 2025-08-12. No product fit. |
| 8  | Tessera Education   | EdTech              | 2025-06-30 | CHURNED     | —           |    $0     | Budget pulled by board mid-program (2025-08-22). Strong eval results; warm re-engage in Q1 2026. |
| 9  | Vega Telecom        | Telecom             | 2025-07-07 | CHURNED     | —           |    $0     | Voice-latency P95 exceeded their 800 ms hard ceiling; Voice-2.0 milestone (S665) lands in S31. Re-engage post-S31. |
| 10 | Rhea Real Estate    | PropTech            | 2025-07-14 | CHURNED     | —           |    $0     | Adopted competitor (Botpress); cited lower per-conversation list price. Lessons folded into S671 pricing-page work. |

**Headline metrics**

- Conversion rate: **6 / 10 = 60%** (Plan goal: ≥ 50%).
- Booked ARR: **$383,520**.
- Average paid contract length: 12 months (5 of 6) and 11 months (1 of 6).
- Net Revenue Retention is not yet measurable (program just closed).

## Churn reasons — taxonomy

| Reason                       | Count | Action |
| ---------------------------- | ----- | ------ |
| Product fit (chat surface)   | 1     | Documented; not in roadmap. |
| Buyer-side budget pull       | 1     | Re-engagement playbook (Q1 2026). |
| Performance ceiling (voice)  | 1     | Tracked under S665 / Voice-2.0 (S31). |
| Lost on price                | 1     | S671 pricing work landed; track win-back. |

## Conversion playbook (going forward)

1. **Anchor on a single workflow** in week 1. Partners that picked one
   workflow (Acme: refunds; Northwind: order status; Helios: claim
   triage; Polaris: appointment-rescheduling) all converted; partners
   that wandered (Cinder, Rhea) churned.
2. **Run the eval suite weekly.** Six conversions all had ≥ 90 % pass on
   the regression suite for two consecutive weeks before signing.
3. **Surface the cost dashboard early.** Two enterprise conversions
   cited the cost dashboard (S612 / S613) as the deciding control.
4. **Compliance asks become unblockers, not addenda.** SOC 2 Type 2
   (S606–S618) directly unlocked Meridian; SSO + BYO Vault (S637)
   unlocked Helios.

## Sign-off

> "Six paid conversions out of ten with $383k booked ARR and four
> documented churn reasons we can act on. This is the data we needed for
> the launch board and the Series A diligence binder." — H. Adisa, Head
> of GTM, 2025-09-30
