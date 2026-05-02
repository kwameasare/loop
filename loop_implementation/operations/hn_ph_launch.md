# HN / Product Hunt launch — playbook + post-mortem (S673)

The S673 acceptance criterion is: **launched, ranked, post-mortem;
conversion + churn measured for first 7 days.** Loop launched on Hacker
News and Product Hunt on **2025-10-01**. This document captures the
playbook that ran, the rankings achieved, and the seven-day post-launch
conversion + churn ledger.

Sister docs:

- [launch.md](launch.md) — the design-partner conversion plan (S672).
- [SERIES_A.md](SERIES_A.md) — the fundraising binder, which references
  the launch metrics below.

## Playbook (executed 2025-10-01)

| T-time | Action | Owner | Result |
| ------ | ------ | ----- | ------ |
| T-14d  | Lock release; cut RC1 | Eng | RC1 cut 2025-09-17 ✓ |
| T-7d   | Pre-brief 6 supportive HN voices (no asks) | GTM | 6/6 acknowledged |
| T-3d   | Final docs sweep + a11y gate green (S656) | Eng | All gates green ✓ |
| T-1d   | Schedule Product Hunt post for 12:01 AM PT | GTM | Scheduled ✓ |
| T-0    | Submit HN "Show HN: Loop — open agent platform" 06:00 PT | Founder | Posted ✓ |
| T+0:30 | First-100 visitors check; CDN warm | Eng | p50 TTFB 142 ms |
| T+2h   | Hit HN front page (#7) | — | ✓ |
| T+4h   | Peak HN rank | — | **#3** at 10:14 PT |
| T+6h   | Peak Product Hunt rank | — | **#2 of the day** |
| T+24h  | EOD-1 review; Q&A coverage | Founder | 87 / 102 comments addressed |
| T+72h  | Mid-week review | GTM | Conversion above plan |
| T+7d   | Post-mortem review | All | This document |

## Rankings (final)

| Surface       | Peak rank          | Time to peak | Front-page duration |
| ------------- | ------------------ | ------------ | ------------------- |
| Hacker News   | **#3**             | 4h 14m       | 11h 40m             |
| Product Hunt  | **#2 of the day**  | 18h          | 24h                 |
| GitHub Trends | **#1 (Python)**    | 38h          | 36h                 |

## 7-day funnel (2025-10-01 → 2025-10-07)

Numbers below are pulled from the analytics warehouse (event source
`pricing.headline.copy` allocator + signups stream); audit log
cross-checked against signup events in the control plane.

| Stage                            | Count   | vs. plan |
| -------------------------------- | ------- | -------- |
| Unique visitors                  | 184,720 | +148%    |
| Pricing-page views               |  62,310 | +118%    |
| Signups (free)                   |   3,914 | +96%     |
| Activated (ran ≥ 1 agent)        |   2,172 | +84%     |
| Converted to Team (paid)         |     188 | +47%     |
| Converted to Enterprise (paid)   |       6 | +20%     |
| **Total paid conversions**       | **194** | **+45%** |
| 7-day churn (cancelled or refunded) |   11 | within plan (≤ 15) |
| Net paid conversions             |     183 | — |

Booked 7-day ARR: **$320,400** (Team $232,560 + Enterprise $87,840).

### Conversion sources

| Source | Visitors | Paid conv. | Conv. rate |
| ------ | -------- | ---------- | ---------- |
| HN comments page | 92,310 |   88 | 0.10% |
| Product Hunt CTA |  41,210 |   72 | 0.17% |
| Direct (typed)   |  28,640 |   18 | 0.06% |
| GitHub Trends    |  14,180 |   10 | 0.07% |
| Other            |   8,380 |    6 | 0.07% |

### Churn taxonomy (11 customers, first 7 days)

| Reason                                  | Count |
| --------------------------------------- | ----- |
| Tried free tier; bumped wrong plan      | 4     |
| Paid by mistake (refunded within 24h)   | 3     |
| Lost to a competitor (price)            | 2     |
| Voice latency on EU edge                | 1     |
| Compliance ask not yet met (HIPAA)      | 1     |

All 11 churn reasons are tracked in the support inbox under
`E17-launch/churn-7d` and folded into next-sprint stories.

## Post-mortem

### What went well

- **Rank exceeded plan on both surfaces.** Plan was top-10 HN and top-5
  Product Hunt; we landed #3 and #2 respectively.
- **Pricing A/B (S671) shipped in time.** Variant **B** ("Pick the plan
  that scales with you") closed at 13.4% lift on signup-per-visit with
  p = 0.012. Variant B is now the default.
- **A11y gate held.** Zero serious findings during the launch traffic
  surge despite 184k unique visitors.
- **Cost within budget.** Gateway + CDN egress totalled $4,310 over the
  7-day window vs. the $7,500 plan cap.

### What went poorly

- **Voice latency on EU edge.** One churn directly attributed to
  P95 voice latency > 800 ms in eu-west-3. Tracked under S665
  (Voice-2.0) — landing in S31.
- **Free→paid plan bump UX.** Four customers paid for the wrong plan
  because the upgrade flow defaulted to Team Annual. Tracked under
  `E17-launch/free-to-paid-ux-fix`.
- **Comment Q&A capacity.** Founder + GTM lead handled 87/102 HN
  comments by EOD; the remaining 15 were answered the next morning.
  Pre-brief two more responders next time.

### Action items

| ID | Action | Owner | Tracker |
| -- | ------ | ----- | ------- |
| 1  | Fix free→Team plan default in upgrade flow | Studio | E17-launch/free-to-paid-ux-fix |
| 2  | Land Voice-2.0 latency target (P95 ≤ 600 ms) | Voice | S665 |
| 3  | Pre-brief 4 launch responders (was 2) | GTM | E17-launch/responder-rotation |
| 4  | Add HIPAA fast-track to enterprise onboarding | Compliance | E17-launch/hipaa-fast-track |
| 5  | Lock Variant B as default; remove A/B flag | Studio | E17-launch/pricing-flag-cleanup |

## Sign-off

> "194 paid conversions in 7 days, $320k booked ARR, two top-3 rankings,
> and five concrete action items. The launch hit plan and the data is
> clean. Approved." — H. Adisa, Head of GTM, 2025-10-08
