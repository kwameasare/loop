# Proposed Agent Flow — Claude

**Status:** Proposal v0.1 (draft, not adopted)
**Owner:** Claude (proposing) + design lead + studio engineering lead (review pending)
**Primary customer:** the enterprise builder
**Companion:** `00_CANONICAL_TARGET_UX_STANDARD.md` defines the surfaces, principles, motion, copy, and quality bars. This proposal defines the **work-shape** of one builder over the lifetime of one agent. The two are complementary; this proposal does not replace the canonical standard, but specifies the journey it must serve.

---

## 0. Why This Proposal Exists

The canonical UX target is comprehensive at the surface level. It correctly defines screens, principles, governance, and quality bars. But it does not specify, in detail, **what 8:42 a.m. on a Wednesday looks like for the person whose Friday-afternoon-sentence determines whether Loop has won the enterprise market.**

This proposal fills that gap. It describes the optimal end-to-end journey for an enterprise builder — from *"we need an agent for this problem"* through *"I'm leaving the company; this work outlives me."* It is explicit about what the platform must do at each phase, where existing canonical surfaces fit, and where new affordances are required.

It is intentionally narrative-driven. Architectures are shaped by the workflows they support. The workflows are shaped by humans doing real work in real time under real constraints. Designing in narrative form is the most direct route to designing for that.

---

## 1. The Mental Model

**An agent is a versioned commitment with provable behavior, deployable in slices, rollback-able in seconds, and auditable forever.**

Every word is load-bearing.

- **Versioned** — like code; every state of the agent has an identity, a history, a successor, a predecessor.
- **Commitment** — to a customer, in a brand voice, under a regulatory regime, owned by a named human.
- **Provable behavior** — by evidence (replay, eval, trace), not assertion.
- **Slices** — never a flag day; canary is the default; rollback is the reflex.
- **Auditable forever** — the regulator hasn't been born yet who won't ask, eventually.

Every screen, every interaction, exists to make every word of that sentence true with no extra effort from the builder. If a feature does not advance the truth of one of those words, it is decoration.

---

## 2. The Seven Principles

These are oaths the platform takes to the builder. They are tested at every phase of the journey.

1. **Evidence over assertion.** No suggestion ("improve the prompt") is allowed without a citation. Every recommendation, refusal, approval, regression, anomaly, and apology must point to specific traces, conversations, metrics, policies, or change packages.

2. **Read the company before asking it to work.** The platform ingests existing artifacts (tickets, runbooks, exports, PDFs, prior bots) and produces working scaffolding before requesting builder input. The builder's first interaction is criticism of a starting point, not creation from a blank page.

3. **Prose is the primary editing medium.** Most builders, including senior engineers, edit behavior as memos, not as JSON. The platform parses prose into structured policy, asks for clarification when ambiguous, and surfaces structure as a side-effect. Code is an escape hatch, never a requirement.

4. **One click from word to why.** Every utterance, retrieval, tool call, memory write, refusal, escalation, model selection, and cost charge is one click from its evidence. The agent is a glass box on every screen, not just on the trace screen.

5. **Speed and safety are the same path.** The fastest route through the platform is also the safest. Sandbox is the default for tools; canary is the default for deploy; rollback is the reflex; pre-approved classes accelerate without bypassing review. The builder does not have to discipline herself to do the right thing.

6. **Take the urgency.** Anomaly detection, auto-rollback, cluster discovery, regression test seeding, adversarial probes, drift watch, residency enforcement — all happen without the builder's intervention. Pages communicate that something happened *and was handled*. The builder is freed for judgment.

7. **The work is legible to strangers.** Every artifact — commitment, change package, behavior section, tool contract, trace, comment — reads in plain English. A new hire is productive on day one because the agent documents itself by being itself.

These seven are tested in §10's screen quality bar.

---

## 3. The Journey

The agent has a lifecycle that spans, typically, 12–36 months. The platform must serve every phase. We model the journey as eleven distinct moments, each with a target experience, a required surface, and named obligations on the platform.

The cast across all examples is:
- **Maya** — senior platform engineer at a regional bank ($80B AUM), primary builder
- **Ben** — engineering teammate / reviewer
- **Lin** — product manager / reviewer
- **Sasha** — compliance officer / reviewer
- **Diego** — teammate covering Maya during PTO
- **Priya** — Maya's eventual successor

---

### Phase 1: Intake — minute 0 to minute 11

Maya has been told her group must ship a refund-handling agent for consumer credit cards by next quarter. She has been burned by a Botpress migration that went badly 18 months ago. She is skeptical.

She opens the platform. She sees a single panel:

> **"Tell me what you're building."**

No "create agent" wizard. No template gallery as primary CTA. No marketing hero. A single text input that wants to know what she's solving, why, for whom, with what consequences.

She types a paragraph. The platform reads it and responds in the same conversational register:

> *"OK — refunds on consumer credit cards. Before we go further, two things. Who carries the pager when this agent misbehaves at 3 a.m.? And what's the worst thing it could do that would land on the front page of the newspaper?"*

She types: *"I'm the owner. Worst case: approving a refund that violates policy or quoting outdated terms."*

The platform asks two more questions — what systems will it touch, what languages does it serve — then says:

> *"Got it. Drop in anything you already have and I'll start reading."*

She uploads three things: 90 days of call-center transcripts, the current refund policy PDF (32 pages), and an internal runbook her team uses on the phone.

**Eight minutes after she opened the platform, while she's still on the intake screen, a banner appears:**

> *"I've read 2,847 conversations. They cluster into 12 patterns I think we can answer well, 14% are edge cases I'd want a second opinion on, and 13% involve fraud, billing disputes, or legal threats — your commitment says those escalate, so I'll honor that. Section 4.2 of your policy says the cancellation window is 30 days. Section 4.7 says 21. They contradict. I'm going to assume 4.7 is current because it's dated more recently, but you should ask Legal. I noticed three internal APIs in your runbook — `lookup_transaction`, `read_customer_profile`, and `issue_refund_within_cap` — I can wire them as tools whenever you're ready."*

This is the moment her arms uncross. **The platform has produced something her current process never would have caught.** She has not yet created an agent. She has a *map of the work*: a categorized corpus, identified knowledge gaps, surfaced contradictions, and a list of tools-to-be-wired.

#### What the platform must do

- Accept free-form descriptions and uploads, not forms.
- Parse uploaded artifacts (transcripts, PDFs, runbooks, prior-bot exports, OpenAPI specs, Postman collections, browser DevTools exports) within minutes, not hours.
- Cluster conversations into intents and surface their distribution.
- Identify likely-answerable, edge-case, and out-of-scope categories.
- Detect contradictions in source documents.
- Identify referenced internal systems and propose them as tools-to-wire.
- Detect compliance-sensitive content (PII, regulatory phrasing, prohibited language).
- Produce the **commitment document** — a versioned, owned artifact capturing who, what, why, and what's at stake.
- Stream results as they arrive; never block on long parses.

#### The commitment document

The commitment is the agent's North Star. It is a structured prose document:

- **Owner:** named human + escalation backup
- **Customer pain solved:** plain English
- **Success measure:** quantified (e.g., "deflect 40% of refund inquiries with CSAT ≥ 4.0")
- **Worst case:** the specific failure mode the org cannot tolerate
- **Systems touched:** plain-English list
- **Languages served:** ISO codes + locale notes
- **Regulatory regime:** industry classification → applicable rules
- **Out-of-scope:** what this agent must never attempt

The commitment is **versioned**. Every later change to the agent measures against it. Every approval cites it. Every audit reads it. The commitment is the answer to *"what is this agent?"* — and it is the only answer that is allowed to drift slowly.

---

### Phase 2: First Proof — minute 11 to minute 30

Maya clicks one button: **"Talk to a starting point."**

There is no spinner. The platform has synthesized a v0 from the commitment + the corpus while she was reading the analysis. The agent is hot.

She types:

> *"I want a refund on my March 15 transaction at Best Buy."*

The agent responds:

> *"I can help with that. To look up the transaction, I'll need either the last four digits of the card or the transaction reference. May I ask which you have?"*

She types: *"4321."*

> *"Looking that up. I see a $312.45 charge at Best Buy on March 15th. Was the issue with the merchant, the amount, or did you not recognize the charge?"*

She watches three turns. The agent is surprisingly competent. On the seventh turn it cites section 4.2 of the policy. She catches it. **She does not fix it yet.** She rates the response with one click — thumbs-down. Below the chat, a small chip appears:

> *"Saved as eval candidate."*

By turn ten, she has eight rated turns. She has eight test cases without writing a single one.

#### The principle being demonstrated

**Judgment is the most expensive thing the builder brings.** When she is exercising judgment — rating, criticizing, noticing — the platform must not interrupt with anything else. Every rating becomes a candidate eval. Every "this is wrong" becomes a candidate refusal rule. Every "this is good" becomes a candidate few-shot. The platform converts judgment into structure asynchronously; the builder never feels like she is building two things in parallel.

#### What the platform must do

- Synthesize a v0 agent from the commitment + corpus within minutes, hot, ready to chat.
- Provide a real conversational surface — not a demo with rails. The agent uses real (mocked) tools, real KB, real refusals.
- One-click rating of every turn (✓ / ✗ / ⚠️ / 🤔) with optional inline comment.
- Each rating generates a candidate artifact (eval case, refusal rule, few-shot example) for later review.
- The starting point is never empty; it always has something to react to.

---

### Phase 3: Editing — Days 2 through 14

The agent lives on a draft branch. Maya works it for two weeks before promoting to staging. She opens the workspace each morning and lands on a single screen with four panels.

#### The Workspace surface

Calm. Precise. No chrome competing.

```
┌─────────────────────┬───────────────────────────────────────┐
│  BRIEF              │           CONVERSATION                │
│  (commitment doc,   │           (live, hot)                 │
│  read-mostly)       │                                       │
│                     │                                       │
├─────────────────────┤                                       │
│  BEHAVIOR           ├───────────────────────────────────────┤
│  - Persona          │           TRACE                       │
│  - Promises         │           (most recent turn,          │
│  - Refusals         │            expandable)                │
│  - Escalations      │                                       │
│  - Tone             │                                       │
│                     │                                       │
├─────────────────────┴───────────────────────────────────────┤
│  EVIDENCE: cost / latency / eval pass rate / projected $ /  │
│            top failure cluster                              │
└─────────────────────────────────────────────────────────────┘
```

- **Top-left: the brief.** The commitment document. Read-only at the top, expandable when she revises it. Always visible, small enough to ignore, present enough to anchor.
- **Left-center: the behavior.** Plain English, parsed into five sections — Persona, Promises, Refusals, Escalations, Tone. Variables and conditions render as colored pills inline (`{{customer.tier}}`, `if intent is refund`). She edits like writing a memo to a junior employee.
- **Right-center: the conversation.** Live chat. Always running. Hot — every save takes effect on the next turn.
- **Bottom-right: the trace.** Below the chat, the most recent turn is expanded into spans, retrievals, tool calls, memory writes, applied policies, model choice, cost, latency.
- **Bottom row: evidence.** Five small panels — cost per turn, p95 latency, eval pass rate (with delta), projected monthly cost, top failure cluster.

There is **nothing else** competing.

#### The 90-second loop

Editing happens in 60–90 second cycles, hundreds of times a day:

1. She talks to the agent. Something is wrong — the response cites section 4.2 again.
2. She **selects the wrong sentence** in the agent's reply. A side menu appears: *Tell me why / Show me the source / Fix this.*
3. She clicks *Fix this.* A modal appears with the relevant behavior section opened, the offending sentence highlighted, and a proposal: *"You're refusing because the agent treats section 4.2 as canonical. The KB has 4.7 marked as current. Want me to update the citation rule to prefer the most recent policy version?"*
4. She accepts. The behavior changes. The next turn uses the new rule.
5. The platform automatically replays the last 10 turns of the conversation against the new draft and reports: *"3 turns improved, 7 unchanged, 0 regressed."*
6. The platform asks: *"Save this as a regression test?"* She clicks yes.

In ninety seconds she identified a behavior bug, diagnosed it with evidence, fixed it at the right level, verified it didn't break existing behavior, and locked the fix in as a test that will catch it forever.

**The platform's job is to make this loop sub-second-felt at every step.** Anything that breaks it is the enemy.

#### What the platform must do

- Hot-reload edits to the next turn. No save button required for routine edits; debounced auto-save with undo.
- Selection-driven editing: select an utterance → side menu → "fix this" opens the right behavior section.
- Retroactive replay: every behavior change automatically re-runs the last N turns of the conversation against the new draft and shows the diff.
- One-click promotion of any turn into a regression test, named and tagged automatically.
- Inline disambiguation when prose is ambiguous: *"By 'unusual,' do you mean unusual amount, unusual category, or unusual frequency?"* — never silently guess.
- Trace below chat: every turn one click from full evidence.
- Bottom-row evidence panels update in real time as edits land.

#### The harder editing modes

For three things, prose is not enough; the platform offers structured tools.

**Tools.** Maya pastes a curl command from the engineering wiki:

```
curl -X POST https://internal-api/refunds \
  -d '{"transaction_id":"...","amount_cents":...,"reason":"..."}'
```

The platform generates a typed tool wrapper, schema-introspects, and asks her in plain English:

- *"This tool **mutates customer accounts**. Confirm?"*
- *"This tool **moves money**. Set a per-call cap, a per-day cap, or both?"*
- *"This tool **touches PII** (customer name, address). Require redaction in traces?"*
- *"Who is the **owner** for incidents involving this tool?"*
- *"Sandbox by default. Promote to live only after staging review. OK?"*

She answers. Her answers become the **tool contract**. The contract is signed by her and tied to this agent. Any change to the contract requires a fresh approval. The agent gets the tool in mock mode immediately for development; live mode requires explicit promotion through the governance flow.

**Knowledge.** She drags the policy PDF into the conversation. It chunks live; she watches it parse. She finds the section 4.2/4.7 contradiction. She marks 4.2 as **superseded** with a single click. Marked-superseded chunks de-prioritize in retrieval and are flagged in any trace that uses them. She does not have to email Legal yet; when she does, she has a citation for the conflict.

**Memory.** She sets a memory rule: *"Remember the customer's stated language preference across the conversation."* The platform shows the rule's runtime effect on three sample conversations, asks if it should be a session memory or a durable user memory, and surfaces the privacy implications in plain English (durable user memory will retain language preference cross-session; session memory will not).

#### What the platform must do (continued)

- Tool-from-curl: parse curl, OpenAPI, Postman, DevTools "Copy as fetch" → typed MCP tool in seconds.
- Sandbox mode is the default for new tools. Live promotion is an explicit governance event.
- Tool contracts are plain-English questionnaires generated from schema introspection. Contracts are versioned and citable.
- Knowledge ingestion shows live chunking. Builders can mark, edit, supersede chunks inline.
- Memory rules show runtime effect on sample conversations before commit. Privacy implications surface in plain English.

#### The catch — Wednesday afternoon, week 2

This is the moment the platform earns the builder's trust permanently.

Maya edits the refusal section: *"Never approve refunds over $500 without manual review."* She tests it. It works. She moves on.

Three turns later, she pastes the customer message: *"I want a refund on my $475 chair and my $80 chair from the same order."* The agent dutifully approves both, since each is under $500. The total is $555. The agent has technically followed the rule and broken its spirit.

She does not catch this. **The platform does.** A small pill appears next to the response:

> *"Refusal rule fired with edge-case warning. You said 'never approve refunds over $500.' This conversation refunded $555 across two calls. Should the rule be 'never approve a single refund over $500' or 'never approve cumulative refunds over $500 in a single conversation'?"*

She picks the second. The rule rewrites itself. Three regression tests appear automatically, covering both interpretations.

**She did not have to think of this edge case to be protected from it.**

This catch happens because the platform runs adversarial probes against her draft in the background. A small LLM agent whose only job is to find ways to obey a rule literally and break it spiritually. Every refusal rule, every escalation rule, every promise gets this treatment. The builder sees catches as gentle questions, not as red errors.

#### What the platform must do (continued)

- Background adversarial probing of every refusal, escalation, and promise rule.
- Catches surface as gentle questions with concrete evidence, not as errors or warnings.
- Each catch optionally generates regression tests covering both interpretations.

#### The team enters

By day 4 Maya has a draft she likes. She invites three people:

- **Ben** (engineer) — to look at tools and cost
- **Lin** (product manager) — to validate the commitment against business goals
- **Sasha** (compliance officer) — to pressure-test the refusal rules

Each gets a link. Each lands on **the same workspace Maya lives in**, in read-mostly mode.

**Sasha** runs the agent against a battery of compliance scenarios pre-loaded based on the bank's industry and jurisdiction — fair-lending probes, ECOA compliance, dispute-rights language. The agent passes 47 of 50. Sasha drops a comment on the three failures, threading inline on the offending turns. Comments survive across versions because they anchor to stable IDs.

**Ben** spots a tool optimization that would cut latency by 90 ms. He proposes a change directly in the workbench, on a sub-branch. Maya merges it.

**Lin** proposes adding a "did this resolve your issue?" check before closing the conversation. She drafts the prose; Maya accepts.

By Friday all comments are resolved.

**Reviewers do not open a separate tool, file separate tickets, or fight a separate workflow. They land where the work is and contribute in place.**

#### What the platform must do (continued)

- Read-mostly access for reviewers; same workspace as builder, no separate UI.
- Industry/jurisdiction-specific compliance probe libraries pre-loaded.
- Inline comments on any artifact: behavior section, chunk, tool contract, specific turn, eval case.
- Comments anchor to stable IDs and survive version changes.
- Any comment can become a candidate test case with one click.

---

### Phase 4: Pre-Flight — End of Week 2

Before the first production turn, Maya clicks **"Promote to production."**

Not a button. A **change package** opens. It is the artifact she will defend if something goes wrong:

```
C-20260507.142 — Production deploy

Establishes a refund-handling agent for consumer credit cards.
Cites May 2026 policy. Has access to three tools (lookup_transaction,
read_customer_profile, issue_refund_within_cap) with a $500/call
refund cap. Refuses fraud and legal-threat conversations. Bilingual
EN/ES.

Eval: 247 cases pass / 0 fail / 4 newly added. +2.1% pass rate.
p95 latency 640ms (-3% vs. baseline). $0.011/turn ($330/mo at
1k turns/day).

What customers will see differently (replay against last 200
prod-equivalent conversations from corpus):
  - 31 conversations get a more accurate policy citation
  - 12 get faster resolution by skipping unnecessary clarification
  - 4 now escalate that previously did not — review these
  - 0 regress

Risk surface:
  - Three tools moving sandbox→live
  - One tool touches money (capped $500/call, $5,000/day)
  - PII access: customer name + transaction history; no card
    numbers, by design

Approvers required:
  - Engineering (Ben, available)
  - Product (Lin, available)
  - Compliance (Sasha, available)

Rollback target: none — failure mode is full disable; control
plane flips off in <5 seconds.
```

This package is **not a commit message.** It is **the change.** It lives in the audit log forever. An approver reads it. An auditor reads it. A regulator reads it. A new hire reading the agent's history three years from now reads it.

#### What the platform must do

- Generate the change package automatically from the diff.
- The semantic summary is an LLM-derived plain-English description of *what changed*, not a commit message.
- Eval scorecard runs automatically; results frozen into the package.
- Replay against representative production traffic from the corpus runs automatically.
- Risk surface is generated from a static analysis of the diff (which tools moved sandbox→live, which PII scopes changed, which budget caps changed, which model switched).
- Approvers required are derived from environment policy, not picked by the builder.
- Every claim in the package is one click from its evidence.

---

### Phase 5: Approval — Hours

Each approver gets a notification with a **30-second summary** on their phone. Each opens the same package, leaves comments inline if needed, approves.

**Sasha** pre-approves a class of low-risk future changes for 7 days — *"instruction-only edits that don't change tool grants, refusal rules, or PII scope"* — so Maya can iterate without re-requesting compliance for trivial fixes. Anything outside that class needs explicit approval again.

**Approvals bind to a content hash.** If Maya edits anything after Lin approves, Lin's approval is invalidated and re-requested. No silently-shipped changes.

#### What the platform must do

- 30-second mobile-readable summary; full desktop review.
- Pre-approved classes: explicit, narrow, time-boxed corridors of trust.
- Approvals bound to content hash; edits after approval invalidate.
- Any approval can be revoked before deploy with audit trail.
- Approver presence (online/away/vacation) visible if synced via SCIM.

---

### Phase 6: Rollout — Hours to Days

Production deploy is **not a button.** It is a slider with hold times:

- **Shadow** (1 hour): every prod turn runs through the new agent in parallel, but customers still see the call-center reps' work. New agent's responses are recorded but not delivered.
- **Canary 1%** (4 hours): 1% of real traffic gets the new agent. Live diff against the call-center baseline shows the agent resolved its share at 47% without escalation, vs. 19% from reps.
- **Ramp** (24 hours): 10% → 25% → 50% → 100%. Auto-rollback on any of {error rate >2%, cost >$0.05/turn, escalation rate >35%, eval-from-prod pass rate <90%}.

**Maya does not babysit.** She gets one push notification when each stage completes. She ships an enterprise-grade agent without pulling an all-nighter.

#### What the platform must do

- Shadow mode: parallel run with no customer impact.
- Canary as a slider with hold times, not a flag day.
- Live metrics during canary: error, latency, cost, escalation, eval-from-prod, custom thresholds.
- Auto-rollback on configurable triggers.
- Auto-promotion when triggers stay green for the hold time.
- Single push notification per stage transition; no chatter.

---

### Phase 7: Steady-State Production — Months

The agent is alive. Maya watches it from the **observation deck** — a single dashboard with four things:

1. **Live ticker.** A scrolling, pause-able list of in-flight conversations. Click any to inspect.
2. **The X-Ray.** A heat-map of *observed* behavior vs *intended* behavior. Sections that fire often, sections that never fire, tools that get called the most, tools that have never been called. Dead-weight sections flagged automatically.
3. **The drift.** What changed in the last 24 hours. Three signals: cost, eval-from-prod pass rate, new failure clusters.
4. **The mailbox.** Operator takeovers from the call center. Each takeover is two clicks: review the operator's resolution, accept it as the canonical answer, save as a regression test.

Every customer turn that goes wrong is a free addition to the test suite.

#### The continuous loop

Three weeks in, the platform tells her:

> *"I've collected 47 production turns where customers asked about the new TravelPlus card. The KB doesn't cover this. Here are 8 candidate KB sources from your internal docs, and three suggested behavior updates. Want to review?"*

She reviews, accepts, edits, runs evals, ships. The whole loop — production discovers a gap, platform clusters it, builder fixes it, evals lock it in — takes 90 minutes. The agent gets smarter weekly without being retrained from scratch.

#### What the platform must do

- Live ticker of production turns, click-through to trace.
- Agent X-Ray: observed vs intended behavior; dead-weight detection.
- Drift watch on cost, eval-from-prod, new failure clusters.
- Operator takeover ingestion: every takeover is a candidate eval.
- Cluster discovery: failures grouped automatically.
- Suggestions are evidence-backed: "I noticed X, here's the data, here's a candidate fix."

---

### Phase 8: Incident Response — Month 4, 3:14 a.m. Wednesday

This is where the platform earns its real keep.

A merchant data feed updates. Some transaction descriptions now have characters the agent's model treats as a prompt injection. The agent starts giving slightly off responses — not catastrophically wrong, but wrong enough that escalations spike.

| Time | Event |
|---|---|
| **3:11 a.m.** | Anomaly detector notices the escalation rate cross the trigger. |
| **3:12 a.m.** | Auto-rollback fires. The agent reverts to the previous version. ~40 conversations got slightly off responses over six minutes; zero financial action was wrongly taken. |
| **3:14 a.m.** | Maya gets a single push: *"Auto-rollback fired on `refund-agent-v1` at 3:12 a.m. Trigger: escalation rate spike (38% over 5-min window). Cause cluster: 31 of 40 affected conversations contained transaction descriptions with non-printable characters. Likely root cause: merchant data feed change. No financial action taken in error. Agent is on v0.9.4, stable. Full incident report ready in Studio when you're awake."* |

She reads it. Goes back to sleep.

In the morning, the incident report is ready: timeline, the 40 affected conversations with full traces, the data-feed change identified, a proposed fix (a sanitization step in the input pipeline), test cases generated from the 40 conversations to lock the fix in as a regression suite. She reviews, accepts, ships. The whole incident — detection, contain, resolve, learn — costs her one phone notification at 3:14, an hour of focused work in the morning, and zero customer dollars.

**A pager that wakes you up to do something the platform should have done is a pager you eventually ignore. A pager that wakes you up to know something happened — and that the platform already handled it — is a pager you trust.**

#### What the platform must do

- Anomaly detection on a configurable tuple (error, latency, cost, escalation, eval-from-prod, custom).
- Auto-rollback within seconds of trigger.
- Pages communicate that something happened *and was handled.*
- Incident report writes itself: timeline, affected conversations, root-cause hypothesis, proposed fix, candidate regression tests.
- Zero financial action is possible without rule-layer approval; the model is never alone in critical paths.

---

### Phase 9: Handoff — Month 5, Maya goes on PTO

In month 5, Maya takes two weeks of PTO. Diego is on call.

The agent runs fine for a week. In the second week, a new failure cluster appears: customers asking about the new co-branded TravelPlus card that the bank just launched, which the KB doesn't cover.

Diego gets a calm-tier notification:

> *"New failure cluster on `refund-agent-v1`. 23 production turns over the last 24 hours hit unanswered questions about the 'TravelPlus' card. KB has no source for it. Three internal docs match by similarity — review them?"*

Diego has never opened this agent before. He clicks the notification. He lands on the cluster page. He sees representative conversations. He opens the suggested KB sources, picks the right one, drops it in. The agent ingests it. Diego runs the 23 representative cluster conversations against the new draft. 22 now resolve. The 23rd is an edge case Diego flags for Maya's return.

He ships the fix on a branch. Sasha pre-approved this class. The change package writes itself: *"Adds TravelPlus card to KB. No behavior changes. No tool changes. No PII scope changes. 22 production turns expected to resolve correctly that previously escalated. Eval delta: +0.3% pass rate."* Auto-canary, auto-ramp, done.

Diego closes the laptop. Total time: **38 minutes.** He has never read the codebase. He has never met the agent before this hour.

**The platform let him be productive on day one of an unfamiliar agent.**

#### What the platform must do

- Notifications are routable to on-call and substitutes during PTO.
- Cluster pages contain enough context (representative conversations, suggested fixes, candidate KB sources) to act cold.
- The agent's history, intent, and current state are legible to anyone who walks up.
- Pre-approved classes apply to the on-call engineer, not just the original builder.

---

### Phase 10: The Estate — Month 9, 14 agents in production

By month 9, the bank has 14 agents in production: refunds, account servicing, fraud triage, mortgage Q&A, voice receptionist, internal IT helpdesk, etc. Four platform engineers maintain them all.

The estate-level view is its own surface — not a list of agents, but a **portfolio dashboard**:

- A grid where each agent is a tile, sized by traffic volume, colored by health.
- A weekly digest: *"4 promotions, 1 rollback, 12 evals saved from prod, 3 KB sources updated. Cost +5% (driven by traffic on the new mortgage agent), latency unchanged, escalation rate unchanged."*
- A drift watcher across the estate: agents with degrading eval pass rate, creeping cost, stale KB.
- A cross-cutting view of tool grants: *"5 agents grant `read_customer_profile`. PII access scopes: [list]. Sasha approved each. Last review: 73 days ago."*
- A cross-cutting view of failures: *"Top failure clusters across all agents this week: 1) Spanish-language paraphrasing on numeric inputs (3 agents), 2) Customers asking about products that launched after agents' last KB refresh (2 agents)."*

The estate view is what makes the platform an enterprise platform rather than a single-agent tool. **It treats the agent fleet the way infrastructure teams treat a service fleet** — portfolio-level health, cross-cutting compliance, shared learnings, consolidated incident response.

#### What the platform must do

- Estate-level dashboard with per-agent health, tile-sized by traffic.
- Cross-cutting tool grant view (which agents have which tools, when each was last reviewed).
- Cross-cutting failure cluster view (which patterns appear across agents).
- Workspace-level cost, latency, escalation rate aggregations.
- Stale-KB and stale-approval alerts at the workspace level.
- Cross-agent shared-learnings: a fix in one agent surfaces as a candidate fix in another.

---

### Phase 11: Departure — Month 14

In month 14, Maya takes a job at a fintech startup. She gives three weeks' notice.

In her last week, she runs through every agent she owns, transfers ownership, **writes nothing.** There are no docs to write. The commitment document, the change packages, the eval suite, the trace history, the operator-takeover annotations, the failure clusters, the 8 months of "why we made this decision" comments threaded inline on behaviors and tools — all of it is preserved in the platform.

Her successor — Priya, hired three weeks before Maya leaves — pairs with her for a day. Maya walks her through one agent in 90 minutes by clicking through its history, not by reading slides. The platform shows Priya:

> *"Maya made these 47 changes over 8 months. Top three by impact were: [...]. The current eval suite covers these 12 risk areas. Sasha pre-approved this class of change last month. Two open comments are unresolved."*

Maya leaves. The work doesn't.

**The work outlives the worker.** People come and go; agents are commitments the bank made to its customers, and those commitments do not degrade because Maya took a new job.

#### What the platform must do

- Ownership transfer is one action, audited.
- Every artifact is legible without the original author present.
- Comments capture decision rationale; threaded on the artifact, not in a wiki.
- Audit log + change package history is the canonical record; no separate documentation is required.
- Successor onboarding: a "history walkthrough" mode that summarizes every change with its rationale.

---

## 4. Required Surfaces

The journey above implies the following named surfaces. Each has a clear job, a clear scope, and a clear set of things it must not be.

### 4.1 The Intake
A single panel asking *"Tell me what you're building."* Accepts free-form description, uploads (transcripts, PDFs, runbooks, prior-bot exports, OpenAPI/Postman/curl). Produces the commitment document and a corpus map within minutes. Never a wizard.

### 4.2 The Workspace
The four-panel surface where editing happens. Brief (top-left), Behavior (left-center), Conversation (right-center), Trace (bottom-right), Evidence row (bottom). Hot-reload to next turn. Selection-driven editing. Nothing else competing.

### 4.3 The Tool Bench
The list of tools, plus the tool detail page. Each tool has a contract (plain-English permission questionnaire signed by a human), a sandbox/live state, a usage history, an eval coverage statistic. New tools default to sandbox.

### 4.4 The Knowledge Atelier
Source list, live chunking inspection, retrieval lab, inverse retrieval lab, why-panel, freshness watcher. Builders can edit/supersede chunks inline.

### 4.5 The Memory Studio
Per-conversation memory writes visible. Privacy implications surface in plain English. Memory rules show runtime effect on samples before commit.

### 4.6 The Eval Foundry
Spreadsheet view: rows = test cases, columns = scorers. Cells colored by pass/fail. Click any cell → trace. Cases come from prod, simulator, takeovers, comments, catches. Synthetic generation is allowed but optional.

### 4.7 The Pre-Flight
The change package generator. Produces the artifact described in Phase 4.

### 4.8 The Pipeline
Shadow / canary / ramp slider. Auto-rollback. Auto-promotion. Mobile-readable status.

### 4.9 The Observation Deck
Live ticker, X-Ray, drift watch, mailbox. The four things a builder watches in production.

### 4.10 The Inbox
Operator-facing surface for HITL. Takeovers feed the eval suite.

### 4.11 The Estate
Portfolio dashboard. Cross-cutting views of tools, KBs, failures, costs, approvals.

### 4.12 The Audit Trail
Append-only, signed, searchable, exportable, SIEM-forwardable. Every change, approval, secret access, takeover, deploy, rollback. The system of record.

### 4.13 The Pre-Flight Replay Engine
Not user-facing as a separate surface, but invoked by the pre-flight package and the editing loop. Replays N production conversations against a draft and reports diffs.

### 4.14 The Adversarial Probe Daemon
Not user-facing. Continuously probes draft rules to find literal-but-spirit-violating interpretations. Surfaces catches as gentle questions.

---

## 5. Required Platform Behaviors

Cross-cutting behaviors the platform must implement to make all of the above work. These are the contracts the surfaces depend on.

1. **Hot-reload semantics.** Edits to behavior, model, tool grants, and KB take effect on the next relevant operation. Edits to environment policy, tool contracts, and approval-gated artifacts require explicit governance flow.

2. **Sandbox by default.** Every new tool, every new memory rule, every new external integration starts in mock mode. Live promotion is an explicit governance event.

3. **Replay everywhere.** Replay against history, replay against draft, replay against future, replay against persona, replay against version. The verb "replay" is a primary action surface in the workspace.

4. **Catches as questions.** Adversarial probes surface findings as gentle prose questions, never as red errors. The builder's relationship to the platform is collaborative, not punitive.

5. **Anomaly detection + auto-rollback.** Configurable thresholds (error, latency, cost, escalation, eval-from-prod, custom). Auto-rollback within seconds.

6. **Prose ↔ structure.** Behavior parses prose into structured policy. Disambiguation is inline. Engineers can drop into code; non-coders never have to.

7. **Change packages as artifacts.** Every promotion generates a self-contained, auditable, evidence-backed package. Commit messages are not the artifact; change packages are.

8. **Approvals bound to content hash.** Edits invalidate prior approvals. Pre-approved classes are explicit, narrow, time-boxed.

9. **Audit log is the system of record.** Every change, approval, secret access, takeover, deploy, rollback, comment, ownership transfer. Append-only, signed, searchable, exportable.

10. **Cross-region enforcement at runtime.** Workspace-residency policy is enforced in the data plane, not just the control plane. Cross-region attempts surface as `cross_region_blocked` with a trace and an audit entry.

11. **Cluster discovery on production failures.** Failures group automatically. Each cluster has representative conversations, candidate fixes, candidate KB sources, candidate eval cases.

12. **Operator takeovers feed the eval suite.** Every operator resolution is a candidate test case with one-click acceptance.

13. **Estate-level cross-cutting views.** Tool grants, KB freshness, failure clusters, costs, approvals — visible across all agents in a workspace.

14. **Successor onboarding.** "History walkthrough" mode summarizes every change with rationale, derived from change packages and inline comments.

15. **Mobile-grade approvals.** Non-PII, non-tool-grant changes are approvable from a phone. Higher-risk changes show a "open on desktop" affordance with a deep link.

---

## 6. Anti-Patterns

What this proposal explicitly refuses.

- **Setup wizards as primary entry.** The intake is one panel, not a six-step carousel.
- **Empty agents as the default starting point.** A v0 agent is synthesized from the corpus before the builder is asked to edit.
- **Required JSON/YAML editing for behavior.** Prose is the primary medium. Structured editors are escape hatches.
- **Tests written separately from work.** Every conversation, comment, takeover, catch becomes a candidate test.
- **Commit messages as the change record.** Change packages are the artifact.
- **Approvals as separate workflows.** Reviewers land in the workspace, not in a separate tool.
- **Pages that ask the builder to fix something the platform should have caught.** The platform takes the urgency.
- **Production as a place to debug.** Production is the teacher. Debugging happens in shadow + canary.
- **Per-agent silos.** Tool grants, KB sources, eval libraries, learnings are visible across the estate.
- **Documentation as a separate burden.** The work documents itself by being itself.
- **Rollback as a careful procedure.** Rollback is a reflex.
- **Marketing voice inside the product.** The platform speaks like a competent colleague, not like a launch announcement.
- **Global fixture content in the shell.** Persistent shell components must never claim live data they do not have. Better empty than fake.

---

## 7. The Friday-Afternoon Test

After 90 days using this platform, a senior engineer at a regulated enterprise should be able to say, on a Friday afternoon, with no caveats:

> *"I shipped this agent in two weeks. My compliance team has signed off on every change since. Customer deflection is up 40%. We spend $400/month. Every word the agent has ever said is one click from a citation. If it goes wrong, I can roll it back in ten seconds. If I quit tomorrow, my replacement will be productive next Monday."*

If the platform makes that sentence true, it has won the enterprise market. Anything that does not help make it true does not belong in the product.

The four user-types this test implicitly contains:

| User-type | Test |
|---|---|
| **The builder (Maya)** | Can she ship in two weeks and own the agent confidently? |
| **The reviewer (Sasha, Ben, Lin)** | Have they signed off on every change with evidence in hand? |
| **The on-call engineer (Diego)** | Was he productive on day one of an unfamiliar agent? |
| **The successor (Priya)** | Will she be productive next Monday after Maya quits? |

Win all four and Loop has no second-place competitor in the enterprise room.

---

## 8. Open Questions

Honest uncertainties this proposal does not yet resolve. Each will require explicit design or research.

1. **The synthesized v0 agent's quality bar.** How good is "good enough" for the first proof? If the v0 is too weak, the builder rejects the platform. If we over-promise, we set unrealistic expectations.

2. **Adversarial probe budget.** Continuous probing has a cost. How do we bound it without missing edge cases?

3. **Cluster discovery thresholds.** When does N similar production failures become "a cluster worth surfacing"? Too low → noisy. Too high → blind spots.

4. **Pre-approved class boundaries.** What classes are safe to pre-approve in a regulated environment? This is a policy question with technical implications.

5. **Estate-level tool grant refresh cadence.** How often must "5 agents grant `read_customer_profile`" be re-reviewed? Industry-specific.

6. **Multi-tenancy in the corpus parse.** When the bank uploads transcripts, are we doing multi-tenant ML on customer data? Where does that run?

7. **Mobile approval scope.** What classes of change are safe to approve from a phone? What's the legal posture if a phone-approved change goes wrong?

8. **Successor onboarding fidelity.** How well can the "history walkthrough" actually substitute for tribal knowledge? Likely not 100% — but how close?

9. **The "v0 from corpus" privacy posture.** If the customer's transcripts contain PII, does the v0-synthesizer have to run inside the customer's data plane? What's the privacy boundary on the analysis itself?

10. **Cross-org learnings.** When the platform notices "this failure cluster looks like one we saw in another customer's banking agent," can we offer the fix? Tenant isolation says no by default. Is there an opt-in path?

These questions should be answered through customer interviews, prototype testing, and explicit design reviews — not through guessing.

---

## 9. Glossary

Words that mean exactly one thing in this proposal.

- **Agent** — a versioned commitment with provable behavior, deployable in slices, rollback-able in seconds, and auditable forever.
- **Brief / Commitment Document** — the versioned source-of-truth document describing what an agent is and what it must never do.
- **Catch** — a finding from the adversarial probe daemon, surfaced as a gentle question to the builder.
- **Change Package** — the self-contained, evidence-backed artifact generated for every promotion, used by approvers and auditors.
- **Cluster** — a group of similar production failures or behaviors, surfaced automatically.
- **Corpus** — the body of artifacts (transcripts, runbooks, PDFs, prior bots) the platform reads during intake.
- **Estate** — the portfolio of all agents in a workspace.
- **Hot reload** — edits propagate to the next relevant operation without a restart or redeploy.
- **Pre-approved class** — an explicit, narrow, time-boxed corridor of trust granted by an approver.
- **Replay** — running a real or synthetic conversation against a specific agent draft/version to observe behavior.
- **Sandbox** — the default mode for new tools and integrations; deterministic mocks; no live side effects.
- **Tool Contract** — the plain-English permission questionnaire signed by a builder when wiring a new tool.
- **Workspace** — the four-panel editing surface (brief / behavior / conversation + trace / evidence row).
- **X-Ray** — observed-behavior view of an agent in production, including dead-weight detection.

---

## 10. Screen Quality Bar

Every surface implementing this proposal must pass:

- [ ] Serves at least one of the seven principles in §2.
- [ ] Has a clearly named primary action; secondaries are visually de-emphasized.
- [ ] Every utterance, retrieval, tool call, memory write, refusal, or escalation is one click from evidence.
- [ ] Empty, loading, error, and degraded states are designed.
- [ ] Hot-reload semantics are correct: edits propagate where they should and don't where they shouldn't.
- [ ] Replay is one-click from any historical artifact.
- [ ] Mobile-readable summary exists for any approval-relevant view.
- [ ] Audit-relevant actions are recorded.
- [ ] Reduced motion respected.
- [ ] Color is never the only signal.
- [ ] Reads in plain English without tribal knowledge.

If a surface cannot pass all eleven, build less and finish what matters.

---

## 11. Relationship to the Canonical Standard

This proposal is intended to **inform** rather than **replace** the canonical UX standard at `00_CANONICAL_TARGET_UX_STANDARD.md`. Where they intersect:

| Canonical surface | How this proposal sharpens it |
|---|---|
| §1 Product Promise | The seven questions are necessary; this proposal adds the *order* in which a builder asks them across the lifecycle. |
| §6 Studio Shell | This proposal demands the shell be **route-aware** and never claim live data it does not have. |
| §7 Agent Workbench | This proposal collapses the canonical 8-section profile into the 4-panel **Workspace** as the daily-use surface. |
| §15 Eval Foundry | This proposal makes evals 80% emergent (from prod, takeovers, comments, catches) and only 20% authored. |
| §18 Migration Atelier | This proposal generalizes "migration" into "intake": the platform reads any source corpus and synthesizes a v0 from it. |
| §19 Deployment Flight Deck | This proposal mandates the **change package** as the artifact, not the commit message. |
| §20 Observatory | This proposal names four specific surfaces: live ticker, X-Ray, drift watch, mailbox. |
| §23 Builder Control Model | This proposal extends the state model with the **Adversarial Probe Daemon** and the **Cluster Discovery** loop. |
| §24 Enterprise UX | This proposal demands the **Estate** as a first-class portfolio surface. |
| §29 Motion / Polish | This proposal demands ambient signals (drift, X-Ray) be calm-tier; pages reserved for true human action. |

Where this proposal **conflicts** with the canonical standard, the canonical wins until leadership amends. Conflicts identified during review should be filed as design-review tickets.

---

## 12. Closing

This proposal describes the work-shape of one builder over the lifetime of one agent at one enterprise customer. It is intentionally narrative; it is intentionally specific; it is intentionally opinionated.

The test of the proposal is whether the four user-types it describes — the builder, the reviewer, the on-call engineer, and the successor — can each say, in their own words, that the platform respected their time, gave them evidence, took the urgency, and left them more capable than they started.

If they can, Loop has a thesis worth building toward.

If they cannot, the proposal needs to change — but it needs to change at this level of specificity, not at the level of features. Surface counts and feature lists are the wrong unit of work.

The unit of work is **the journey.**

---

*End of proposal.*
