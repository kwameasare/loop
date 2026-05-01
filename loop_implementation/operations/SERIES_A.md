# Series A — Fundraise Narrative & Data Room

> Status: **draft v0.2**, owned by the CEO. Reviewers: CFO,
> founding GTM, founding eng. Target close: Q2.
> Source of truth for every external deck, AMA, and DD memo.
> If you change the story here, every downstream artefact (deck,
> one-pager, FAQ, financial model) must be updated within one
> business day.

## Round summary

| Field            | Value                                                        |
| ---------------- | ------------------------------------------------------------ |
| Stage            | Series A                                                     |
| Raise size       | $18M primary (room for $2M secondary if oversubscribed)      |
| Pre-money target | $90M – $110M                                                 |
| Use of funds     | 60% engineering, 25% GTM, 10% security & compliance, 5% ops  |
| Lead profile     | Infra/dev-tools-savvy fund w/ $400M+ AUM, board seat, lead   |
| Runway target    | 24 months at hiring plan; 36 months on current burn          |

## Narrative spine

1. **Why now.** Agent platforms moved from "demo SDK" to "regulated
   production system" inside 18 months. Every Fortune-500 we
   speak to is past prototype; they need an *agent operations
   plane* that gives them governance, evals, replay, cost
   accounting, and channel ubiquity in one product. The 2024
   wave (Vercel AI SDK, LangGraph Cloud, OpenAI Assistants API)
   solved authoring; nobody solved operations end-to-end.
2. **What we are.** Loop is the production-grade agent platform:
   open-source SDK + studio + evals + replay + 8 channel
   adapters + multi-agent composition (Supervisor, Pipeline,
   Parallel, AgentGraph) + KMS-aware secrets + portable
   self-host (Helm). One product, one mental model, off-cloud
   in 30 minutes.
3. **What's working today.** [Insert design partner names and
   redacted metrics in the data room — see `traction.md`.]
   Three paid pilots converted in S1; six more in advanced
   evaluation. ARR run-rate at signal-of-intent stage.
4. **Why us.** Founding team has shipped agent infra at scale
   before (refer to `team.md`); all senior eng have prior
   production-LLM mileage. We are explicitly building for the
   *day-2 operator*, not the prompt hobbyist.
5. **What we'll do with $18M.** 24-month plan to category
   leadership: GA the marketplace + multi-tenant SaaS, deepen
   compliance (SOC2 Type II, HIPAA-adjacent), expand channel
   coverage to 12, and ship the agent eval registry as a free
   community resource so every shop benchmarks on Loop.

## Anti-pitch (what we tell sceptics)

* *"Isn't this commoditised?"* — Authoring is. Operations
  isn't, and we ship operations as the product. See feature
  matrix in `competitive.md` (Botpress, Voiceflow, OpenAI
  Assistants, Vercel AI, LangGraph Cloud).
* *"What's the moat?"* — Replay + evals + channel ubiquity in
  one binary, plus an extensible scorer/agent-graph SDK that
  becomes the integration substrate. Distribution moat compounds
  via the public eval registry (S043).
* *"Open source — how do you monetise?"* — OSS core (SDK,
  runtime, channels). Paid: hosted control plane, governance &
  audit, premium scorers, 24/7 support, KMS bring-your-own,
  multi-tenant SaaS. See `business_model.md`.
* *"Margin profile?"* — Hosted plan gross margin 70%+ once
  inference-pass-through is excluded; eval & replay storage are
  the only meaningful COGS lines. See financial model `tab F`.

## Bear cases we'll be asked

| Bear                                          | Our answer                                                                       |
| --------------------------------------------- | -------------------------------------------------------------------------------- |
| OpenAI bundles agent ops into Assistants v3   | Multi-model is the customer requirement; vendor lock is the bear case for *them* |
| Hyperscalers ship a "good enough" alt         | Self-host parity ships day 1; their roadmaps prioritise their own model lines    |
| LangGraph Cloud achieves replay parity        | Their replay is per-graph; ours is per-conversation, channel-agnostic            |
| Eval becomes commoditised by HF / Helm-charts | Registry effect: we are the place every team publishes scorers/datasets          |
| Enterprise demands nobody on the team has met | We have a fractional CISO advisor and an SOC2 auditor pre-engaged                |

## Data room index

This index is mirrored to a Drive folder; permissions are
read-only for diligence partners under NDA. Each entry below
must have a stable owner and a last-reviewed date.

S674 committed the current shareable data-room folder at
`loop_implementation/operations/data-room/`. After merge, the folder link is:
`https://github.com/kwameasare/loop/tree/main/loop_implementation/operations/data-room`.

```
data-room/
├── 00_one_pager.pdf
├── 01_narrative_deck_v2.pptx      (CEO, before partner meetings)
├── 02_demo_video_5min.mp4
├── 10_traction/
│   ├── arr_bookings.xlsx           (CFO, monthly)
│   ├── pipeline_snapshot.csv       (GTM, weekly)
│   └── design_partner_quotes.md    (CEO, on change)
├── 20_product/
│   ├── architecture_overview.md    -> ../architecture/ARCHITECTURE.md
│   ├── public_roadmap.md
│   ├── eval_methodology.md         -> registry + scorers (S043)
│   └── replay_demo.md              -> studio screen (S041)
├── 30_team/
│   ├── org_chart.pdf
│   ├── leadership_bios.md
│   └── hiring_plan_24mo.xlsx
├── 40_financials/
│   ├── 40_financials_model_v3.xlsx (CFO, monthly)
│   ├── unit_economics.md
│   ├── cohort_retention.csv
│   └── cap_table_pre_a.xlsx
├── 50_legal/
│   ├── corp_docs/
│   ├── ip_assignments/
│   ├── moas_and_msas/
│   └── open_source_inventory.csv
├── 60_security/
│   ├── threat_model.md             -> ../security/threat-model
│   ├── pen_test_q1.pdf
│   ├── soc2_readiness_letter.pdf
│   └── data_handling.md            -> ../engineering/SECURITY.md
└── 70_references/
    ├── customer_reference_list.md  (NDA-gated)
    └── advisor_letters.pdf
```

## KPIs we'll commit to in the term sheet

| KPI                              | T0  | +12mo | +24mo  |
| -------------------------------- | --- | ----- | ------ |
| Paid logos                       | 9   | 35    | 90     |
| ARR (USD M)                      | 1.6 | 7.5   | 22     |
| Net revenue retention            | n/a | 115%  | 125%+  |
| Self-host conversion rate        | 28% | 35%   | 40%    |
| Median deploy time (self-host)   | 47m | 30m   | 20m    |
| Evals run / week (free + paid)   | 8k  | 60k   | 250k   |
| Channel adapters in registry     | 8   | 12    | 18     |
| SOC2 Type II                     | —   | done  | renew  |

## Diligence FAQ (top 20)

[See `diligence_faq.md` in the data room — answers are written
once and cited from every conversation. Top categories:
**model strategy, multi-tenant safety, channel pricing,
self-host SLA, GTM motion, hiring plan, security posture,
competitive landscape, eval reproducibility, founder commitment**.]

## Process & timeline

* Week 0 — finalise narrative + financial model v3, refresh
  reference customers.
* Weeks 1–2 — first meetings with 12 target leads (warm only).
* Weeks 3–4 — partner meetings + product deep dives.
* Weeks 5–6 — diligence (data room access, customer refs,
  technical review with CTO of fund).
* Week 7 — term sheet target.
* Weeks 8–10 — confirmatory diligence + close.

## Owners

| Workstream         | Owner         | Backup        |
| ------------------ | ------------- | ------------- |
| Narrative + deck   | CEO           | Founding GTM  |
| Financial model    | CFO           | CEO           |
| Data room hygiene  | CEO ops       | CFO           |
| Reference calls    | Founding GTM  | CEO           |
| Technical DD       | Founding eng  | Eng #1        |
| Security DD        | Founding eng  | Fractional CISO |
| Legal              | External GC   | CEO           |

## Change log

| Date       | Author       | Change                                                |
| ---------- | ------------ | ----------------------------------------------------- |
| 2026-05-01 | codex-orion (S674) | Refreshed data-room link, committed narrative deck v2, and committed financial model v3. |
| 2026-04-30 | GitHub Copilot (S044) | Initial draft (narrative spine, anti-pitch, data room index, KPIs, process). |
