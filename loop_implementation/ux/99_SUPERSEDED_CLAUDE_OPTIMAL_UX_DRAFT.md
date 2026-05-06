# Superseded Claude Optimal UX Draft - Loop Studio

**Status:** SUPERSEDED SOURCE DRAFT. Replaced by [`00_CANONICAL_TARGET_UX_STANDARD.md`](00_CANONICAL_TARGET_UX_STANDARD.md).
**Audience:** Founders, design lead, Studio engineering lead, partners.
**Use:** historical/reference material only. Do not treat this file as the target UX standard.
**Posture:** This document is preserved as a source draft for visual language, polish, and scenarios. Where it conflicts with the canonical target, the canonical target wins.

---

## 0. The one-sentence north-star

**Studio is a live agent in a glass box** — a single, calm, multiplayer canvas where the agent is always running, every artifact is editable from where you see it, and the path from "imported from Botpress" to "running in production on our cloud with eval guards, a phone number, and a 4-eyes change review" is an afternoon, not a quarter.

Everything below is in service of that sentence.

---

## How to read this document

This is a long document because it is the answer to a single, ambitious question: *what does the best possible Studio look like?* You do not need to read it linearly.

Three reading paths:

1. **The 10-minute read.** §0 (north-star) → §2 (principles) → §6 (Migration Atelier) → §28 (north-star scenarios). You will know what the product feels like and why customers switch.
2. **The 30-minute read.** Add §1 (personas), §3–§5 (Studio surface + canvas + build loop), §14 (enterprise), §29 (relationship to baseline). You will know where the product diverges from competitors and from our current implementation.
3. **The reference read.** Use the table of contents below as an index. Look up what you need.

A reader's contract: the doc is opinionated by design. Where it states a refusal ("we will not ship a setup wizard"), the *why* is in the surrounding section. Disagreement is welcome — the path to resolving it is §32 (how this evolves).

---

## Table of contents

| § | Section | What it answers |
|---|---|---|
| 0 | One-sentence north-star | What is Studio at its truest? |
| 1 | Who this is for | Builder vs. enterprise builder. One product, two postures. |
| 2 | Thirteen principles | The oaths every screen must pass. |
| 3 | Studio at a glance | The four regions, the always-running agent, the trust palette. |
| 4 | The canvas | Graph⇄code isomorphism, hot reload, fork, gesture grammar, hazards. |
| 5 | The build loop | The 30-second iteration cycle. AI co-builder consent grammar. |
| 6 | The Migration Atelier | The headline feature. From Botpress to prod in an afternoon. |
| 7 | The Knowledge Studio | KB with chunk-level explainability. |
| 8 | The Tool Bench | Tools as first-class assets. |
| 9 | The Voice Stage | Voice as a panel, not a product. |
| 10 | The Conductor | Multi-agent as composition. |
| 11 | The Pipeline | Promote, canary, roll back. |
| 12 | The Observatory | Dashboards by default. |
| 13 | The Inbox | HITL as the highest-quality feedback loop. |
| 14 | Studio for the enterprise builder | Governance, isolation, traceability, vendor risk. |
| 15 | Collaboration | Multiplayer, comments, changesets. |
| 16 | The visual language | Color, type, motion, sound, color-independence, focus/presentation modes, i18n, **tactility, micro-interactions, ink-effect streaming, ambient life, texture, earned moments, polish principles** (§16.12–16.20). |
| 17 | Information architecture | The four paths. Search. Sharing. |
| 18 | Interaction patterns | Hot reload, undo, optimistic UI, guardrails, keyboard. |
| 19 | Empty states | Every empty state is a starting line. |
| 20 | Loading states | Skeleton, progressive, never spinners. |
| 21 | Error states | Loud, but never dramatic. |
| 22 | Onboarding | The first 60 seconds, the first week, the first quarter. |
| 23 | Accessibility | WCAG 2.2 AA committed, AAA aspirational. |
| 24 | Performance | Perceived performance is UX. |
| 25 | Mobile / tablet / large display | Mobile is the operator's pocket. |
| 26 | Version control | Branches, diffs, merges, time-travel. |
| 27 | The marketplace | Skills, tools, eval suites, templates. |
| 28 | Five north-star scenarios | End-to-end journeys we rehearse. |
| 29 | Relationship to the legacy implementation baseline | Historical comparison only. |
| 30 | What we will not build | Discipline. |
| 31 | Measurement | The metrics that make this real. |
| 32 | How this evolves | This doc is alive but not casual. |
| 33 | In-product help, feedback, telemetry | Trust through transparency. |
| A | Glossary | Twenty-three nouns we use precisely. |
| B | Product oath | The pre-ship checklist. |
| C | Product copy library | Concrete copy samples for buttons, errors, empty states, voice. |

---

## 1. Who this is for

We design for two personas in one product. They share a workspace and they share a canvas; they diverge in the rails around it.

### 1.1 The Builder

A founder, a product engineer, a solutions architect, a hobbyist who wants something real in production. They will live in Studio for hours at a stretch. They want speed, control, and proof-of-correctness.

What they care about, in order:
1. **Time-to-first-working-agent.** Sixty seconds from landing to streaming response.
2. **Iteration loop latency.** Sub-second from "edit a prompt" to "see the new behavior."
3. **Why-did-it-do-that.** Trace, fork, diff. Glass box, never black box.
4. **Cost and latency.** Visible per-node, per-turn, always.
5. **Migration cost.** Switching from Botpress / Voiceflow / Stack AI / Custom GPT must be an afternoon, not a quarter.
6. **Confidence to ship.** Eval gates, canaries, instant rollback.

### 1.2 The Enterprise Builder

A platform team at a bank, a payor, a telco, an airline. The same persona as the builder, plus four additional gravities: **governance**, **isolation**, **traceability**, **vendor risk**.

What they care about, additionally:
1. **Four-eyes change review.** No prod change without an approver.
2. **Auditable everything.** Who saw what, who changed what, when, from where.
3. **Data residency.** Choose region; never leak across.
4. **BYOK / customer-managed keys.** Encrypt with our key, not yours.
5. **SSO + SCIM + RBAC matrix.** Map our existing org structure.
6. **Compliance evidence packs.** SOC2 / HIPAA / ISO27001 controls visible, exportable.
7. **Whitelabel.** Customer never sees "Loop."
8. **Procurement-friendly.** SLAs, sub-processors list, DPA, vulnerability disclosure — all in-product.

The enterprise builder is **not a separate product.** The product is the same; enterprise is a settings posture, a few extra surfaces, and a discipline applied throughout. We refuse to ship two SKUs that diverge.

---

## 2. The thirteen principles

These are the design oaths. We measure every screen against them.

1. **The agent is always running.** No save-build-deploy step exists between editing and trying. If a user has to "save and reload" to see a change, we failed.
2. **Code and graph are one model.** Visual edits round-trip through code; code edits surface in the visual. Lossless. No "graph mode vs. code mode" lock-in.
3. **Every artifact is editable from where you see it.** A bad chunk → click → edit. A slow node → click → swap model. A wrong tool call → click → fork-and-fix. No "go to settings to change this" detour.
4. **Production conversations are the eval suite.** No one writes synthetic tests at scale. They ship and watch. We make watching → testing one click.
5. **Migration is a feature, not a script.** The importer is the most-used surface in the first month for many customers. Treat it like the front door, not a CLI corner.
6. **Cost, latency, and quality are co-equal axes.** Every screen shows all three. Optimization is not a separate "ops mode" we visit later.
7. **Multi-cloud is invisible until you need it.** It is a setting, not an architecture you must learn.
8. **Glass-box, never black-box.** Every decision the agent makes is one click from a citation. Every retrieval has a "why" panel. Every tool call has a trace span.
9. **Calm, not loud — but never lifeless.** The product is quiet by default. Errors are loud. Routine work flows without interruption. But "calm" is not "dead": Studio breathes, responds, and rewards real milestones with thoughtful, tactile, brief moments of polish (see §16.12–16.20). We do not chrome a happy path with celebration animations; we make the happy path *feel* like a happy path.
10. **Keyboard-first for power users, mouse-discoverable for newcomers.** Every action has a shortcut. Every shortcut has a label. We do not hide capability behind muscle memory.
11. **Real names on real things.** "Turn," "trace," "agent," "tool," "scratchpad" — defined in a glossary, used everywhere. We do not invent a new vocabulary per screen.
12. **Density without clutter.** Engineers tolerate density; everyone tolerates well-organized density. We compose information, we do not pile it.
13. **Trust through restraint.** No marketing voice inside the product. No upsell modals. No "Did you know?" toasts. We earn the next session by being useful, not by interrupting.

### 2.1 Anti-principles (what we will not ship)

- We will **not** ship a setup wizard. Wizards are an admission that the empty state failed.
- We will **not** ship modals over modals. If it requires nesting, it requires a page.
- We will **not** ship a "Save" button on the canvas. Save is implicit, undo is universal.
- We will **not** ship celebratory animations for routine successes. Confetti is condescending.
- We will **not** ship a feature without an empty state, a loading state, an error state, and a keyboard shortcut.
- We will **not** ship two products. Builder and enterprise share one binary; entitlements diverge.

---

## 3. Studio at a glance

Studio is one workspace, one canvas, and a small set of permanent rails. There is no homepage tour, no welcome video, no settings carousel. You open Studio and you are inside the agent.

### 3.1 The four regions

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  TOPBAR    workspace ▾   project ▾   agent ▾    branch ▾        @maya  ⌘K   │
├────────────┬─────────────────────────────────────┬───────────────────────────┤
│            │                                     │                           │
│  ASSET     │              CANVAS                 │      LIVE PREVIEW         │
│  RAIL      │   (graph ⇄ code, isomorphic)        │   chat / voice / channel  │
│            │                                     │   the agent, running      │
│  • Tools   │   Pan, zoom, multi-select.          │                           │
│  • KB      │   Drop assets onto nodes.           │   Cost • Latency • Tokens │
│  • Sub-    │   Click any node →                  │   per-turn, live          │
│    agents  │   inspector opens in panel.         │                           │
│  • Prompts │                                     │                           │
│  • Secrets │                                     │                           │
│  • Skills  │                                     │                           │
│            │                                     │                           │
├────────────┴─────────────────────────────────────┴───────────────────────────┤
│   TIMELINE       turns ▶ ▶ ▶ ▶ ▶  click any turn → canvas highlights path     │
│                  fork-from-here · save-as-eval · diff · share                 │
└──────────────────────────────────────────────────────────────────────────────┘
```

Four regions. Always present. Resizable. Each region has a hide-toggle but no region is hidden by default.

- **Topbar** — workspace / project / agent / branch breadcrumbs, presence avatars, command palette (`⌘K` / `Ctrl-K`), notification well.
- **Asset rail (left)** — every reusable artifact. Drag-and-drop into the canvas. Searchable. Collapses to a 56px icon strip.
- **Canvas (center)** — the agent's structure. Graph or code, switchable per-node. The single source of truth.
- **Live preview (right)** — a real chat with the agent running on the canvas. Switch between web chat, voice, Slack mock, WhatsApp mock, phone simulator.
- **Timeline (bottom)** — every turn the preview produces becomes a row, expandable to a trace. The system memory of the session.

### 3.2 The "always running" agent

When you open Studio, the agent is already loaded into a hot data-plane sandbox tied to your session. It is hot before you ask it anything. Edits propagate to the next turn within ~150ms. There is no "deploy to dev" step in the iteration loop.

This is the single largest UX departure from every competitor. **There is no build step.** A change to a prompt, a tool, a node, a branch is live the moment it is made — to the preview, to anyone watching alongside you in multiplayer, to anyone whose eval is gated on the next change.

### 3.3 The status footer

A 24px footer pinned to the bottom of every Studio screen. Calm by default, expressive on incident.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  ● dp:eu-west-2  ● cp:healthy  ● gateway:healthy  ● kb:indexing 3/8 docs     │
│  region: eu-west-2 (residency: locked)         build 2026.05.06.23           │
└──────────────────────────────────────────────────────────────────────────────┘
```

What lives there, in order of left-to-right importance:

- **Data plane health** for the current workspace's region. Green = nominal. Amber = degraded (latency p95 above SLO). Red = down. Click → opens a `/status` slide-over with last 60 minutes of metrics.
- **Control plane health.** Same.
- **Gateway health.** Per upstream LLM provider; failover state visible.
- **Background work** — re-indexing KB, running an eval, compiling whitelabel CSS. A fraction renders progress.
- **Region + residency lock** — confirms data residency posture at a glance.
- **Build version** — surfaces "you are on the build that fixed bug X" for support conversations.

The footer is the calmest surface in the product when things work, and the loudest when they don't. It exists because trust comes from being able to *see* the system, not from being told it is fine.

### 3.4 The notification well

In the topbar, between the breadcrumbs and the user avatar, lives a circular notification well. It is small, quiet, and obeys a strict three-tier hierarchy:

| Tier | Visual | When | Examples |
|---|---|---|---|
| **Calm** | dot color matches signal-info, no badge | Routine — eval finished, KB indexed, branch merged | "Eval suite `support-v2` re-ran: 100/100 pass." |
| **Nudge** | small numeral badge, signal-warning color | Worth your eyes — anomaly, pending review, budget warning | "Cost +132% vs. last week on agent `billing`." |
| **Alarm** | pulsing red ring + numeral | Acting now matters — incident, breach, hard cap, prod regression | "Hard budget cap hit. New conversations returning `budget_exhausted`." |

Click the well. A slide-over panel opens with grouped notifications, oldest at the bottom. Each card is dismissable, snoozable, and click-throughs to the underlying surface. The well never auto-pops anything in your face — that would violate the calm-by-default contract. The user comes to it.

We support per-channel routing of notifications. Anything in the well can also fan out to Slack, email, PagerDuty, OpsGenie, generic webhook, or Microsoft Teams. Routing rules are workspace-scoped and editable in one settings page; defaults are sensible and visible.

### 3.5 The trust palette

A reserved set of color + iconography pairs that mean *exactly one thing* across the product. These are the visual nouns of state.

| State | Color | Icon | Meaning | Examples |
|---|---|---|---|---|
| **Live** | `#14B8A6` teal, slow pulse | dot | Currently in use in production | Active version chip in topbar |
| **Canary** | `#F59E0B` amber, slow pulse | wedge | Receiving partial production traffic | Canary slider chip on Pipeline |
| **Pending review** | `#F59E0B` amber, static | clock | Waiting for an approver | Changeset card |
| **Approved** | `#10B981` emerald, static | check | Reviewed and approved | Changeset card |
| **Mocked** | `#A78BFA` violet, static | mask | Tool / KB returning recorded responses | Tool card in non-prod env |
| **Stale** | `#94A3B8` slate, static | hourglass | Source has not synced in >24h | KB source card |
| **Deprecated** | `#475881` strikethrough | strike | Soft-removed; do not use | Skill card in marketplace |
| **Needs your eyes** | `#F97316` pop, static | eye | We could not auto-decide; you must | Migration Atelier item |
| **Unreviewed in prod** | `#F97316` pop, ring | ring | A change reached prod without review | Topbar prod chip |
| **Read-only** | `#5E6F8E` muted, no chrome | lock | Permission boundary, not a defect | Tablet canvas |

These pairings are sacred. We do not use teal-pulse to mean anything except "live." We do not use the eye icon to mean anything except "needs your eyes." This is how a user develops a *language* of the product — at a glance, across screens, across versions.

---

## 4. The Studio Canvas

The canvas is the heart of the product. We invest more design and engineering attention here than in any other screen, and it shows.

### 4.1 Graph and code, isomorphic

Two views of the same agent.

- **Graph view.** Nodes for triggers (channel inbound, schedule, webhook), conditions, classifiers, extractors, LLM steps, tool calls, KB lookups, sub-agent calls, branches, joins, and emit-output. Edges are typed (control flow vs. data flow rendered subtly different). Nodes can collapse into "skill" abstractions.
- **Code view.** Python, the SDK. The canonical form. Whatever you do in the graph is reflected here, byte-for-byte, with stable ordering and stable formatting.
- **Per-node toggle.** Each node has a "open as code" affordance that pops the underlying Python next to the node, editable. The graph and the inspector edit the same source. Round-trip is lossless.

We do not pick one. The choice is the user's, per moment, per node. A non-Python builder can stay in graph forever; a Python expert can ignore the graph and write code; a mixed team can collaborate on the same agent with neither having to convert.

### 4.2 The inspector panel

Click any node. A panel slides in (does not cover the canvas; pushes the canvas left). The panel has up to seven tabs, only those relevant to the node:

- **Configure** — prompt, model, knobs, retries, timeouts.
- **Tools** — the tool subset this node may call, with mock vs. live toggles.
- **Inputs** — the fields this node receives from upstream, type-checked and example-rendered.
- **Outputs** — the schema this node emits, with example values.
- **Cost & Latency** — live p50/p95 from the last 1k turns at this node, per model, per channel.
- **Eval** — eval cases that exercise this node, pass/fail, regression chart over time.
- **Code** — the underlying Python for this node, editable.

The inspector is keyboard-navigable. `1`–`7` jumps tabs. `Esc` closes. `⌘.` toggles.

### 4.3 Hot zones, not modes

There is no "edit mode" vs. "preview mode." The canvas is always editable. Anyone can hover, click, edit, undo. Selection state is live across multiplayer.

### 4.4 The fork

Every turn in the timeline has a **Fork from here** button. Clicking it:

1. Creates an ephemeral branch named like `fork/2026-05-05/14h32m`.
2. Loads the exact agent state (prompts, tools, KB version, scratchpad, model versions, secrets references) at that turn.
3. Restores the conversation up to that turn.
4. Hands you the canvas. Edit anything. Re-run the next turn.
5. The original conversation is untouched. Two timelines run side by side. A diff view shows token-by-token, tool-by-tool, cost-by-cost differences.

This is the "what if I had set temperature to 0.1" question, answered in 90 seconds, with a real conversation, not a synthetic prompt.

### 4.5 Hot reload semantics

We give edits a clear contract:

- **Prompt edits** — apply to the next LLM call. In-flight calls finish on the old prompt.
- **Tool schema edits** — apply to the next tool call. In-flight calls finish on the old schema.
- **Graph topology edits (add/remove a node, rewire an edge)** — apply to the next *turn*. The current turn finishes on the old topology.
- **Model swap** — applies to the next LLM call.
- **Knowledge base re-index** — runs in the background; new chunks become retrievable when ready, with a topbar progress chip.
- **Secret rotation** — applies to the next call to that integration; in-flight calls keep the old secret.

Every edit shows a transient toast: "applied to next turn" or "applied to next LLM call" — calm, factual, no exclamation.

### 4.6 Undo as a first-class verb

`⌘Z` works on the canvas. `⌘⇧Z` redoes. The undo stack survives reloads. Every edit is captured as an event, and every event is a citizen in the version-control story. We do not put work at risk to chase performance.

### 4.7 The gesture grammar

The same gesture means the same thing everywhere. We document it once and obey it.

| Gesture | Universal meaning |
|---|---|
| **Single click** | Select. Never destructive. Never a navigation away from this screen. |
| **Double click** | Descend / open detail. On a node: expand its inspector. On a skill: enter its subgraph. On a chunk: open the source. |
| **Right click** (or `Ctrl`-click on Mac) | Context menu. Always non-destructive options at top, destructive at bottom, separated. |
| **Long press / hold** | Reveal tooltip + keyboard shortcut. Educational, never an action. |
| **Drag** | Move within a region. From the asset rail to the canvas: attach. Within the canvas: rewire. |
| **Drag-drop onto target** | Compose. A tool dropped on a node attaches; a sub-agent dropped on the canvas creates a node. |
| **Hover** | Reveal affordances. Buttons appear; counts surface; preview thumbs render. Never moves the layout. |
| **Cmd / Ctrl + click** | Multi-select on the canvas; "open in new tab" elsewhere. |
| **Shift + click** | Range-select on lists; extend selection on the canvas. |
| **Scroll** | Pan in lists; zoom on the canvas (with `Cmd` modifier on touchpad to pan). |
| **Two-finger pinch** | Zoom on the canvas. |
| **Drop a file onto Studio** | Upload to the most-relevant artifact (KB by default; tool spec if hovering tool bench; cassette if hovering eval). |

Two refusals:
- **No hidden gestures.** Every gesture has a discoverable on-screen affordance for users who do not know the gesture.
- **No destructive default.** No gesture, in any region, deletes anything in one step. Destruction always requires confirmation (see §18.9).

### 4.8 Hazard handling on the canvas

The canvas is multiplayer + always-running + isomorphic across two views. That is a stack of hard problems. We name how we handle each:

**Two builders edit the same node simultaneously.**
We use operational transform on prompt text and structural diff on graph topology. Conflicts are surfaced inline, not auto-resolved silently. The later edit wins by default with a "your edit overrode Maya's" toast that links to the diff and offers a one-click "merge both."

**A builder edits a node while production is mid-call against it.**
The current call finishes on the old version. The next call uses the new version. We never kill an in-flight production call to apply an edit. The trace timeline annotates the version boundary so the operator can see exactly which turns ran on which version.

**A KB re-index is in flight when a turn fires.**
Old chunks stay retrievable until the new index commits atomically. The `Why` panel notes "indexed at {timestamp}" so the user knows exactly which version of the KB answered.

**The user closes the laptop with an unsaved fork.**
Forks are auto-persisted to the user's branch as ephemeral state every 2 seconds. On reopen, Studio restores the canvas, the preview, the timeline, and the inspector to exactly where they were left.

**The user clicks Promote but the approver is on vacation.**
Approval requests show approver presence (online / away / vacation status if synced via SCIM). If all required approvers are away, the request still files; an "expedite" affordance offers to escalate to the next approver in the role gradient, with the original approver notified by email.

**The user drags a node into a circular dependency.**
The drop is rejected at the moment of release with a transient "this would create a cycle" message. The graph never enters an invalid state.

**The data plane is degraded mid-edit.**
Edits queue locally. The status footer turns amber. The user can keep editing; the queue flushes when the data plane recovers, with conflict resolution for any out-of-band changes.

**Two reviewers approve concurrently after a third edit.**
Approvals are bound to a content hash. If the changeset is edited after an approval, that approval is invalidated and the approver is re-notified. We never let a stale approval gate a different change.

These cases are not edge cases. They are the cases that break trust if mishandled, so we name them up front and own the answer.

---

## 5. The build loop

The cycle a builder runs hundreds of times per session:

1. **Type a turn into the preview.** The agent responds.
2. **Notice something off** — wrong tool, wrong tone, missed entity, slow span.
3. **Click into the trace.** Find the offending span.
4. **Fork from here, or edit in place.**
5. **Re-run the turn.** See the diff.
6. **Save it as an eval case.** One click. Default name auto-generated; rename inline.
7. **Continue.**

The whole loop takes 15–30 seconds when it is going well. We optimize for that.

### 5.1 The AI co-builder

Permanently docked, collapsible. Not a chatbot in a corner — a context-aware assistant whose pointer is the canvas selection. When you select a node and ask "make this handle refunds too," it:

1. Proposes a diff to the node (shown inline, accept-or-reject).
2. Lists eval cases the change would touch and runs them in the background.
3. Reports outcomes — green / red — when ready, with a one-click "view diff" link.

The co-builder never silently changes things. It always proposes. It always shows its work.

#### 5.1.1 The consent grammar

The co-builder operates in three explicit modes, chosen per session by the user:

| Mode | What the co-builder may do | What requires explicit consent |
|---|---|---|
| **Suggest** (default) | Read the canvas. Read traces. Propose diffs. Run evals on speculative branches. | Apply any edit to a real branch. Call any tool that has side effects. Spend tokens above the per-session co-builder budget (default $0.50). |
| **Edit** | All of the above, plus apply edits to the user's branch. | Push to a protected environment. Spend above the per-session budget. Call live (non-mock) tools. |
| **Drive** | All of the above, plus call live tools and run evals against live KBs. | Spend above the user's daily co-builder budget (default $20). Promote to a protected environment. Edit secrets. |

The mode is shown as a chip on the co-builder dock. Switching modes is one click and is itself audited. Drive mode is disabled by default in enterprise workspaces unless explicitly granted by an admin.

#### 5.1.2 Provenance

Every edit the co-builder applies is tagged with the prompt that produced it, the model used, the token cost, and the user who confirmed. The audit log captures all four. A user can filter the timeline to "only my edits" or "only co-builder edits" or "co-builder edits I confirmed."

#### 5.1.3 Refusals

The co-builder refuses, with a clear reason, when:

- The action requires Drive mode and Drive is off.
- The action would touch a protected environment without an approval changeset.
- The action would exceed budget.
- The action involves a secret rotation, a member invite, a billing change, or any other action whose locus of authority must remain human.

Refusals are not patronizing. They state the rule and offer the path: "Drive mode is off. Switch to Drive, or apply this manually."

#### 5.1.4 The pointer

The co-builder's pointer is whatever you have selected — a node, an edge, a chunk, a turn, a span, a row in the inbox. It always tells you what it is looking at: "Pointing at node `classify_intent` (LLM, model gpt-4o-mini)." Selecting elsewhere updates the pointer; the user is never confused about what context the co-builder has.

### 5.2 Skills

A skill is a reusable cluster of nodes plus its prompts, tools, and KB references — a domain abstraction. "Order lookup," "Refund eligibility," "Claim triage." A skill collapses into a single node on the parent canvas; double-click descends into its subgraph. Skills can be shared across agents in a workspace, versioned independently, evaluated independently.

The skill library is workspace-scoped, with a marketplace track for org-wide patterns. Enterprise customers can publish private skill libraries to their workspaces (governed by RBAC).

### 5.3 Save-as-eval

A button on every turn in the timeline. One click captures:

- The user input
- The agent's response
- The full trace as a deterministic cassette
- The expected scorers (auto-suggested: exact-match for short answers, semantic-similarity for prose, latency cap, cost cap)

The case lands in the eval suite associated with the agent. Suites are auto-organized by skill. The whole suite runs on every change to the agent in <30 seconds for typical workloads, with budgets enforced.

---

## 6. The Migration Atelier

The most strategically important screen in the product for the first quarter post-GA. It is not a CLI tool; it is a co-pilot for porting.

### 6.1 What we import from

| Source | Mode | What we map |
|---|---|---|
| **Botpress** | `.bpz` archive upload, or Botpress Cloud OAuth | flows, intents, entities, NLU training, hooks, KB, channels, variables |
| **Voiceflow** | project export (`.vf`), or Voiceflow API token | canvases, intents, prompts, blocks, KB, voice config |
| **Stack AI** | project export, or org token | flows, prompts, tools, knowledge connectors |
| **Chatbase** | bot ID + API key | system prompt, KB sources, integrations, custom personas |
| **OpenAI Assistants v2** | assistant ID + API key | instructions, tools (functions, file-search, code-interpreter), files |
| **OpenAI Custom GPT** | GPT URL + manifest | system prompt, knowledge files, action OpenAPI, conversation starters |
| **ElevenLabs Conversational** | agent ID + API key | system prompt, voice, tools, KB |
| **Sierra** | YAML export (where available via partnership) | agents, policies, tools, escalation rules |
| **Intercom Fin** | workspace token | KB, custom answers, intents, handover rules |
| **LangFlow / Flowise** | flow JSON | nodes (mapped where 1:1, surfaced where ambiguous) |
| **Rasa** | `domain.yml`, `data/`, `config.yml` | intents, entities, stories/rules, custom actions |
| **n8n / Zapier (LLM nodes)** | workflow JSON | LLM nodes only (the rest stays in n8n; Loop calls back via webhook) |
| **Generic** | OpenAPI + system prompt | becomes a single-skill agent with HTTP tool calls |

The list is alive. Every quarter, the importer team adds the next-most-requested source. The list is also social — when a user requests a source we don't yet support, we route the request to the importer team and notify the user when it ships.

### 6.2 The mapping engine

Behind the importer is a pipeline:

1. **Parse.** Source artifact → canonical intermediate representation (IR). The IR captures intents, entities, flows, prompts, tools, KB, channels, variables — the abstractions every platform shares.
2. **Map.** IR → Loop assets. Flows → graph topology. Intents → classifier nodes (with the source's training utterances becoming eval cases). Entities → typed extractors. Tools → MCP adapters. KB → re-ingested through Loop's chunker. Channels → Loop channel configs. Variables → scratchpad keys.
3. **Diff.** What mapped cleanly vs. what is ambiguous vs. what did not map at all. Each unmapped item carries a one-sentence "why" and a "fix it" affordance.
4. **Generate.** A working Loop agent on a new branch named `import/{source}/{date}`.

### 6.3 The three-pane review

The user lands on a three-pane review screen, full-bleed:

```
┌─────────────────────────┬─────────────────────────┬─────────────────────────┐
│   SOURCE                │   NEEDS YOUR EYES       │   LOOP                  │
│   (Botpress flow)       │   (47 items)            │   (mapped graph)        │
│                         │                         │                         │
│   [the flow as we       │   • intent "refund"     │   [the mapped graph,    │
│    found it, read-only] │     mapped to a         │    fully editable,      │
│                         │     classifier node     │    side-by-side]        │
│                         │     — confirm? [y/n]    │                         │
│                         │                         │                         │
│                         │   • hook "creditCheck"  │                         │
│                         │     mapped to HTTP tool │                         │
│                         │     — set auth? [...]   │                         │
│                         │                         │                         │
│                         │   • KB chunker changed  │                         │
│                         │     — top-3 retrieval   │                         │
│                         │     differs in 12 of    │                         │
│                         │     200 cases [view]    │                         │
└─────────────────────────┴─────────────────────────┴─────────────────────────┘
```

The middle column is the workbench. Each item is a card with a clear question and a clear answer. Cards stack in priority order: blocking, advisory, fyi. Bulk-accept and bulk-defer are present but not the primary affordance — we want the human to look.

### 6.4 The parity harness

The most powerful part of the importer.

Loop replays the source platform's last N production conversations (where N is configurable, default 200) against both implementations. The result:

- **Per-conversation divergence score** — what fraction of turns produced different outcomes.
- **Per-turn diff** — side by side, with token-level highlights and tool-call differences.
- **Per-decision narration** — for divergences, an LLM-written explanation: "in this turn, the source agent called `lookup_order` first, then `escalate`. Loop called `lookup_order`, got an empty result, and ended the conversation. The likely cause is missing fallback logic in the imported flow."
- **Cost and latency comparison** — the headline numbers, with confidence intervals.

This is the screen that converts skepticism. A platform team can see, in their own data, that Loop is at parity (or where it isn't, exactly why).

### 6.5 Gradual cutover

Once the team is satisfied:

- **The channel webhook gains a slider.** 1% of traffic to Loop, 99% to the source. Move the slider over weeks. At 100%, the source is a candidate for retirement.
- **Drift watch.** As long as both run, divergence is monitored automatically. If the divergence-rate spikes, an alert fires.
- **One-click full cutover** — when the team is ready. The source webhook is rerouted; the workspace stamps the migration "completed" with timestamp + actor for the audit log.

### 6.6 Why this is the headline

A platform team trying Loop has an existing investment they cannot abandon. The competitor wins by default unless we make migration cheaper than staying. The Atelier exists to make migration cheap, observable, reversible, and trustworthy. It is the single most important sales surface in the first 90 days of a customer relationship.

---

## 7. The Knowledge Studio

A knowledge base is not a folder of files. It is a system that has to answer "why did the agent say this?" with a citation, a score, and a chunk you can click on.

### 7.1 Sources

A flat, fast list of source connectors. Each is a one-page panel with auth, sync schedule, scope rules. We support, at minimum:

- File upload (PDF, DOCX, HTML, Markdown, plain text, CSV, JSON, XLSX)
- URL crawlers (single page, sitemap, recursive with scope rules)
- Notion (workspace + page-level scoping)
- Google Drive (folder scoping)
- Confluence (space scoping)
- Zendesk (help center, tickets with PII redaction)
- Salesforce (knowledge articles)
- GitHub (repos, issues, PRs, wikis)
- S3 / GCS / Azure Blob (prefix scoping)
- Slack channel exports (with consent flow)

Each source has a sync state, a last-sync timestamp, a doc count, an embedded-token count, and an "Open in source" link. Failures surface inline, with the actionable error and a retry button.

### 7.2 Chunking, visible

Most platforms hide chunking. We expose it.

- The chunking strategy per source — fixed-size, heading-aware, layout-aware (for PDFs), semantic-boundary, custom.
- The chunk list per document, with byte ranges, a preview pane, and an embeddings PCA preview.
- An inline editor — click a chunk, fix the text, save. Re-embed runs in the background.

### 7.3 The Why panel

Every retrieval in the trace has a Why panel. Open it and see:

- The query the agent issued (verbatim).
- The retrieval strategy (BM25 + vector RRF, or alternative).
- The top-k chunks, ranked, with scores per strategy and the fused score.
- For each chunk: the source, the doc, the byte range, a click-through to the chunk inspector, the freshness, and any per-chunk overrides ("pinned," "boosted," "deprioritized").

The Why panel exists because **a customer-trust answer cannot be an opaque embedding score.** It must be a citation.

### 7.4 The retrieval lab

A test panel. Type any query, see the top-k results live, with score breakdowns and the chunk preview side-by-side. Save queries as named retrieval evals. When you re-chunk or change the embedding model, the lab re-runs the saved queries and shows a "before/after" diff: for each saved query, did top-3 stay the same?

This is the screen that turns "I changed the chunker, did anything break?" from a fear into a 10-second answer.

### 7.5 Lifecycle

Documents have a lifecycle: draft, indexed, deprecated, archived, deleted. Deprecation is soft — the doc still exists, retrieval deprioritizes it, the trace's Why panel notes the deprecation. Archive is colder. Delete is final and audited.

---

## 8. The Tool Bench

Tools are first-class. They are not buried in a settings tab.

### 8.1 The tool library

A workspace-scoped library of tools, categorized: built-ins (HTTP, SQL, calendar, email, calculator, datetime, regex), org-internal, MCP marketplace.

Each tool has a card:

- Name, description, version
- Owner (a person; shown with avatar)
- Schema preview
- Trace count last 7 days
- p50 / p95 latency
- Error rate
- Avg cost per call (where applicable)

### 8.2 The spec editor

Click a tool. The spec editor opens. Three tabs:

- **Schema** — the JSON Schema for inputs and outputs. Lint live; sample inputs render in a panel. Examples are required (we ship type-checking + example-checking).
- **Implementation** — Python (in-process) or MCP target URL or HTTP shim. Inline test runner ("call this tool with this input, see what comes back").
- **Policy** — retries, timeouts, budget cap, rate limit, circuit breaker, mock-vs-live default per environment.

### 8.3 Mock-vs-live

Every tool has a mock implementation as a peer to its live one. In dev, mocks are default; in prod, live. Mocks are deterministic (record-replay cassettes) and editable. The toggle is per-environment, not per-call, so a builder cannot accidentally pierce the wall.

### 8.4 Auto-MCP

Paste an MCP server URL (or pick from the marketplace). Loop introspects the tool list, generates Loop tool wrappers, and adds them to the library. Scoping (which agents may use which tools) is declarative.

### 8.5 Per-tool budgets

A tool can have a budget — dollars, calls/minute, retries/turn. Exceedance produces a `budget_exhausted` error that the agent sees and can route to. Enterprise customers expose per-tool budgets in the audit log.

---

## 9. The Voice Stage

Voice is not a separate product. It is a panel.

### 9.1 The voice toggle

On any agent, a `Voice` toggle in the topbar. Once on:

- The preview gains a microphone button.
- The agent gains channel-aware prompt shims for spoken vs. written interaction.
- The trace timeline includes ASR / TTS spans.
- The agent now also has a phone profile (configurable, optional).

### 9.2 The live waveform

When in voice mode, the preview shows:

- A live waveform of the user's mic (with a "listening" / "speaking" / "thinking" state).
- A streaming transcript of ASR — bigram-stable.
- Markers for barge-in events.
- Per-stage latency budget bar: ASR → agent → TTS → output, with each stage colored by its budget consumption.

### 9.3 Phone provisioning

A `Get a phone number` button. Pick country, area code, capability (voice in/out, SMS), provider (Twilio default; carrier failover; LiveKit SIP for some). Compliance steps (10DLC for US SMS, BSP onboarding for WhatsApp) are wizards-as-checklists, not as carousels.

### 9.4 Realtime model agnostic

The agent runs the same way in voice or text. The voice provider is swappable: Deepgram / OpenAI Realtime / Whisper / Soniox for ASR; ElevenLabs / Cartesia / OpenAI / Piper for TTS; LiveKit / WebRTC / phone for transport. The choice is a setting, not a rewrite.

### 9.5 Voice-specific evals

Eval suites for voice include latency targets per stage, ASR word-error rate on canonical terms, barge-in correctness, and TTS audio fidelity (a small model rates intelligibility).

---

## 10. The Conductor (multi-agent)

Multi-agent is composition, not a paradigm.

### 10.1 Sub-agents as assets

In the asset rail, sub-agents appear next to tools. Drag one into another agent's graph and it becomes a node. The sub-agent retains its own canvas, its own evals, its own version, its own owner.

### 10.2 Hand-off contracts

The edge between an agent and a sub-agent is typed. The contract specifies:

- What state passes (typed schema)
- What state does not pass (privacy / cost containment)
- Which scratchpad keys survive across the boundary
- Failure modes (sub-agent timeout, sub-agent budget exhausted, sub-agent escalation)

Contracts are visible in the inspector, editable, version-controlled. Violating a contract at runtime is an explicit error, not a silent data loss.

### 10.3 The Conductor view

A diagram view (separate from the canvas) that shows the agent topology of an entire workspace: which agents call which. Click an edge → see the typed contract; click a node → jump into that agent's canvas. This is the org-chart for AI.

---

## 11. The Pipeline (deploy & promote)

### 11.1 Environments

Every workspace has at minimum `dev`, `staging`, `prod`. Each is a peer with its own URL, secrets, KB version, budgets, channel configs. Enterprise plans get arbitrary custom environments (e.g. `region-eu`, `region-us`, `partner-acme`).

The current environment is always shown in the topbar with a colored chip — green for dev (calm), amber for staging (deliberate), red-bordered for prod (you are touching live traffic).

### 11.2 Promotion

Right-click any change → **Promote**. A Promotion screen opens with three panels:

- **The diff** — what changed, in graph and code form.
- **The eval delta** — every eval suite re-run on the candidate vs. the current prod. Pass/fail/regress per case.
- **The cost / latency delta** — projected impact on prod traffic, computed from the last 24h of replays.

The Promote button is disabled until the gates pass. Gates are configurable per environment: "no regression on top 50 cases," "p95 latency does not increase by more than 10%," "cost per turn does not increase," etc. Enterprise plans get four-eyes-by-default — the promoter cannot be the approver.

### 11.3 Canary

A slider, not a flag day. After promote, the new version starts at 1% of prod traffic. The canary panel shows live metrics — error rate, regression-eval scorecard from production conversations, cost-per-turn — for both versions. Move the slider when satisfied. Auto-rollback fires on configurable triggers.

### 11.4 Rollback

`⌘⇧R` (or a button). One click. The previous version is now active. The rollback is itself a versioned event. There is no "are you sure" dialog beyond a momentary confirm — rollback is supposed to be instant.

### 11.5 Cloud picker

A workspace setting. AWS / GCP / Azure / Alibaba / self-hosted. Switching is a re-deploy, not a rewrite. Most teams set it once and never touch it. Enterprise teams use it to run regional workspaces side-by-side.

### 11.6 Wireframe — the promotion screen

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Promote agent  support-en  ·  staging → production                  [✕]     │
├──────────────────────────────────────────────────────────────────────────────┤
│  CHANGES                          GATES                       APPROVALS      │
│                                                                              │
│  · prompt @ classify_intent       ✓ no eval regression         lin@acme  ●  │
│    +12 -8 lines (graph + code)    ✓ p95 latency  -3%           ben@acme  ○  │
│  · tool budget @ lookup_order     ✓ cost/turn    -$0.0004      ─────────────│
│    $0.10/call → $0.20/call        ✓ no new tool calls live     1 of 2 in     │
│  · KB source: refund-policy.pdf   ✓ secrets unchanged          (4-eyes req'd)│
│    indexed 38 chunks              ⚠ canary recommended                       │
│                                                                              │
│  [ View graph diff ]  [ View code diff ]  [ View eval scorecard (100/100) ]  │
│                                                                              │
│  Canary plan:  ▢ 1% → 10% → 50% → 100%   over [ 24h ▾ ]                      │
│  Auto-rollback on:  ▣ regression-eval drop  ▣ p95 +20%  ▣ error-rate +0.5%   │
│                                                                              │
│  Comment for the audit log:                                                  │
│  [ Resolves customer report #4172. Verified parity vs. v42 baseline.    ]    │
│                                                                              │
│  [ Request approval ]                              [ Cancel ]   ⌘⇧P promote  │
└──────────────────────────────────────────────────────────────────────────────┘
```

Every gate is green before the button enables. Every check is one click away from its evidence.

---

## 12. The Observatory

Every metric that matters, on dashboards we ship by default. No "build your dashboard" task as a prerequisite to insight.

### 12.1 Default dashboards

- **Health** — turn rate, error rate, p50/p95/p99 latency by channel, by skill, by model. Anomalies highlighted.
- **Cost** — $/turn, $/conversation, $/resolved-conversation, by agent, by channel, by model, by skill. Budget burn rate vs. cap.
- **Quality** — eval pass rate (production-derived suite), deflection rate, escalation rate, satisfaction score where available.
- **Tools** — call rate, error rate, p50/p95 latency per tool. Top failing tools.
- **Knowledge** — retrieval freshness, top queried docs, top zero-result queries (these become "your KB has a hole" alerts).
- **Voice** — stage latency budgets, barge-in rate, ASR word-error on canonical terms, TTS perceived quality.

Every chart click-throughs to the underlying traces. Every chart can be pinned to a custom dashboard.

### 12.2 Anomaly detection

Lightweight, opinionated. The Observatory watches for:

- Cost spike vs. last 7-day baseline at the agent or skill level.
- p95 latency regression after a deploy.
- Error-rate spike at a specific tool.
- Eval scorecard regression in production conversations.
- KB zero-result query rate increase.

Anomalies surface as a red dot on the topbar notification well, expandable to a card with a one-line summary, a trace link, and a suggested action.

### 12.3 Custom dashboards (later)

Users can pin any chart to a custom dashboard, share dashboards across the workspace, and embed them in Notion / Confluence with a public-link toggle (governed by RBAC). This is a month-9 feature; the defaults are good enough until then.

---

## 13. The Inbox (HITL)

Operators live here. The inbox is the highest-quality feedback loop in the product: every escalation is a chance to improve the agent.

### 13.1 The queue

Real-time. New escalations animate in. Filter chips: All · Escalated · Confidence-flagged · Tool-failed · Manual review · SLA-breaching. Sort: time waiting (default), age, agent, channel.

### 13.2 The take-over

Click a conversation. Operator-mode panel opens. The agent goes silent in that thread until the operator releases. The operator can:

- Type as themselves (badged "Operator: Maya").
- Draft as agent (LLM drafts a response in the agent's voice; operator approves/edits/sends).
- Leave a private note that the agent treats as an instruction for the rest of that conversation.
- Hand off to another operator.

### 13.3 Resolution → eval

Every release prompts: "Save this conversation as an eval case?" One click captures it, with the operator's resolution as the expected outcome. The case is auto-titled and tagged with the escalation reason.

### 13.4 Operator metrics

Per-operator: conversations handled, avg handle time, resolutions, escalations to senior, customer satisfaction (where available). Surfaced for self-improvement, not for surveillance — visibility scoped per-operator unless a manager role is set.

### 13.5 Wireframe — the inbox

```
┌──────────────────┬───────────────────────────────────────────────────────────┐
│ QUEUES           │  user_call_4172   voice   wait 18s   SLA 60s              │
│ ─────────────────│  ─────────────────────────────────────────────────────────│
│ All           12 │  Why escalated:  tool_failed (calendar_lookup, retry x3)  │
│ Escalated      4 │  Channel:        +1 415-555-0123 (US, dental-receptionist)│
│ Confidence     3 │                                                           │
│ Tool failed    2 │  ── transcript ──                                         │
│ SLA risk       2 │  agent  Hi, this is Smile Dental. How can I help?        │
│ Manual review  1 │  user   I need to reschedule my Tuesday appointment.      │
│                  │  agent  One moment, let me check the calendar...          │
│ TEAMMATES        │  agent  [calendar_lookup tool failed: 504 Gateway Timeout]│
│ ─────────────────│  agent  I'm having trouble with our system right now.     │
│ ● maya  inbox  3 │         Let me get someone on the line.                   │
│ ● ben   inbox  2 │  → escalated to inbox at 14:32:18                         │
│ ○ sam   away     │                                                           │
│                  │  ── operator panel ──                                     │
│ FILTERS          │  [▣ Take over]  [Draft as agent]  [Note]  [Hand off ▾]    │
│ Channel: any     │                                                           │
│ Agent:   any     │  Compose:                                                 │
│ Wait:    any     │  [ ____________________________________________________ ] │
│ Time:    today   │  Send  ⌘↩      Save resolution as eval case  ▢            │
└──────────────────┴───────────────────────────────────────────────────────────┘
```

`o` takes over (the agent goes silent in this thread). `d` opens the LLM-drafted response for review. `n` opens a private operator note (the agent treats it as an instruction). `r` releases back to the agent. `e` saves the closing turn as an eval case.

---

## 14. The Studio for Enterprise Builders

Same Studio. Specific surfaces and disciplines.

### 14.1 SSO and identity

Enterprise SSO (Okta, Azure AD, Auth0, Ping, Google Workspace, generic SAML / OIDC). SCIM provisioning. Users land in Studio with their org claims already mapped to Loop roles. JIT provisioning, with approval workflow if configured.

### 14.2 RBAC matrix

A real matrix, not a tier list. Roles are workspace-scoped, agent-scoped, environment-scoped. The default roles (Owner, Admin, Builder, Operator, Eval-Author, Viewer) are starting points; custom roles compose from a fine-grained permission set:

- View / edit / promote agents
- View / edit knowledge bases
- View / edit tools
- View / edit / approve changesets
- Take over conversations
- View costs / budgets / billing
- Manage members / API keys / secrets
- Configure SSO / SCIM / data residency / BYOK
- Export audit log / compliance evidence

The matrix UI is searchable and pivotable (by role, by permission, by user). Effective permissions are computable per user — a Who-Can-Do-What query that returns in <100ms.

### 14.3 Approval workflows

Changesets, PR-style. Builders work on branches; merges to protected environments require approvers. Approvals show:

- The diff (graph + code)
- The eval delta
- The cost / latency delta
- A comment thread

Required approver counts and required approver roles are configurable per environment per agent. We support "any approver from group X" and "specific approver" (named user). Enterprise customers can require 4-eyes by default for prod.

### 14.4 Audit log explorer

Append-only. Tamper-evident (chained signatures). Searchable across actor, action, target, environment, agent, time. Filters; saved searches; CSV / Parquet export; SIEM forwarding (Splunk, Datadog, Sumo, generic syslog).

The log captures every interesting verb: member invited / removed / role changed; secret created / rotated / accessed; agent created / promoted / rolled back; eval gate overridden; budget changed; data export requested. Each entry: actor, action, target, timestamp, IP, user agent, request ID, before/after where applicable.

#### Wireframe — the audit log explorer

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Audit log · acme-bank · all environments                  [ Export ▾ ]       │
├──────────────────────────────────────────────────────────────────────────────┤
│ Filters:  [ Actor:   any        ▾ ]   [ Action: any        ▾ ]               │
│           [ Target:  agent loan-faq ✕]  [ Env: production   ▾ ]              │
│           [ Time:  last 7 days  ▾ ]    [ Saved: 4-eyes review ▾ ]            │
│                                                                              │
│ ─ TIMESTAMP ─────────  ACTOR ────  ACTION ────────────  TARGET ──── ENV ─── ▸│
│  2026-05-06 14:32:14   sam@acme   agent.promoted        loan-faq    prod   ▸│
│  2026-05-06 14:31:55   ben@acme   changeset.approved    cs-7212     prod   ▸│
│  2026-05-06 14:18:02   lin@acme   changeset.approved    cs-7212     prod   ▸│
│  2026-05-06 11:04:30   sam@acme   changeset.requested   cs-7212     prod   ▸│
│  2026-05-06 09:12:08   ops@acme   secret.rotated        kb_openai   prod   ▸│
│  2026-05-05 22:48:11   ─system─   gateway.failover      anthropic   prod   ▸│
│                                                                              │
│ ── selected: agent.promoted (sam@acme, 2026-05-06 14:32:14) ──               │
│   Actor:    sam@acme           IP: 192.0.2.18   UA: Chrome/130 macOS         │
│   Target:   agent loan-faq     v42 → v43                                     │
│   Approvers: lin@acme, ben@acme  (4-eyes gate satisfied)                     │
│   Diff:     +12 -8 lines (graph + code)        [ Open changeset cs-7212 ]    │
│   Eval:     100/100 pass · cost -3% · p95 -3%   [ Open scorecard ]           │
│   Note:     "Resolves customer report #4172. Verified parity vs. v42."       │
│   Signed:   ed25519:7f3c… (chain valid through entry 92,481)                 │
└──────────────────────────────────────────────────────────────────────────────┘
```

Every row click-throughs to the full event. Saved searches surface as named filters. Export: CSV, JSON, signed PDF (compliance evidence), or push to SIEM.

### 14.5 Data residency

A workspace setting. Data plane runs in the chosen region. Storage (Postgres, Qdrant, ClickHouse, MinIO) is regional. Cross-region call-outs are blocked at the data-plane boundary; an attempt produces a `cross_region_blocked` error visible in traces and the audit log. Multi-region workspaces share a control plane but isolate data planes.

### 14.6 BYOK / customer-managed keys

A `Encryption` panel. Pick provider (AWS KMS, GCP KMS, Azure Key Vault, HashiCorp Vault, on-prem HSM). Bind a key. Loop encrypts secrets, KB content, traces, and prompts at rest with the customer's key. Rotation is supported; revocation is supported (and instantly disables the workspace until re-bound).

### 14.7 Whitelabel

A workspace setting:
- Logo, primary color, secondary color, favicon (CSS-variable override per workspace).
- Custom subdomain (`studio.acme-bank.com`).
- Email template branding.
- Customer never sees "Loop" — even error messages and outbound emails carry the customer's brand.

### 14.8 Compliance evidence

A `Compliance` page surfaces the evidence pack: SOC2 Type II report, ISO 27001 certificate, HIPAA BAA template, GDPR DPA, sub-processor list, vulnerability disclosure policy, pen-test summary. Each item has a "request via DocSend" affordance that gates by NDA where required. Customers can also export a *workspace-specific* compliance report — every audit-log event in a date range, every approval, every secret rotation — bundled as a PDF + JSON, signed.

### 14.9 The procurement surface

A `Procurement` page that does not exist in non-enterprise plans. Single page with: SLAs, uptime history, status page link, sub-processors, DPA, MSA template, security questionnaire (SIG, CAIQ, DDQ filled out), contact for legal/security.

### 14.10 Private skill library

Enterprise workspaces can publish private skills (the kind described in §5.2) to their org. A platform team builds the "claim triage" skill once; thirty agent-team workspaces consume it with one click. Versioning + deprecation flow for skills mirrors agent versioning.

---

## 15. Collaboration

Studio is multiplayer because real teams build real things together.

### 15.1 Presence

Avatars in the topbar show who else is in the agent. Cursors on the canvas show where they are looking. Selection is shared (you can see what they have selected, in their color). Typing indicators in shared text fields.

### 15.2 Comments

`⌘⇧C` opens a comment on whatever is selected — a node, an edge, a chunk, a turn, a trace span. Comments thread, mention with `@`, resolve, reopen. Comments survive across versions, anchored to stable IDs (the node ID, not its position).

### 15.3 Changesets

A branch is a changeset. Branches are first-class. The branch selector lives in the topbar next to the agent name. Branches can be diffed, requested for review, merged. Conflict resolution is graph-aware (we know what a node is; we know what a tool is) — not a textual three-way merge nightmare.

### 15.4 Mentions and assignments

`@maya` in a comment notifies Maya; she sees a red dot on her topbar; clicking it takes her to the comment. A comment can be assigned, with a state: open, in progress, resolved.

### 15.5 Workspace hierarchy

Workspace > Project > Agent > Branch > Version. Each level has its own settings, permissions, billing. We surface the breadcrumbs in the topbar; we never make a user navigate up to find what level they are at.

---

## 16. The visual language

This is the layer most products skimp on. We won't.

### 16.1 Brand soul

Loop feels like a Swiss-engineered instrument that happened to fall in love with the warmth of editorial typography. Precise, calm, classy. Nothing screams. Color earns its place by carrying information, not by decorating space.

### 16.2 Color

A two-tier system: a small **structural** palette that does 95% of the work, and a small **signal** palette that carries meaning.

Structural (dark mode, primary):
- `--bg-page` — `#0B1020` deep navy, almost black but warmer
- `--bg-surface` — `#0F1830` raised surface
- `--bg-elevated` — `#161F3A` modals, popovers
- `--bg-hover` — `#1A2440` hover states
- `--bg-selected` — `#1F2D52` selection, focus
- `--text-primary` — `#F1F5F9` off-white
- `--text-secondary` — `#9AA9C2` muted
- `--text-tertiary` — `#5E6F8E` hints, placeholders
- `--border-subtle` — `#1F2A45`
- `--border-default` — `#2A395E`
- `--border-strong` — `#475881`

Structural (light mode, peer-supported):
- `--bg-page` — `#FAFAF7` warm paper
- `--bg-surface` — `#FFFFFF`
- `--bg-elevated` — `#FFFFFF` with shadow
- `--bg-hover` — `#F2F2EE`
- `--bg-selected` — `#EAECF8`
- `--text-primary` — `#0F1830`
- `--text-secondary` — `#475881`
- `--text-tertiary` — `#8694B0`

Signal:
- `--signal-info` — `#5EA6FF` electric blue
- `--signal-accent` — `#14B8A6` teal (Loop's brand)
- `--signal-success` — `#10B981` emerald
- `--signal-warning` — `#F59E0B` amber
- `--signal-danger` — `#EF4444` cinnabar
- `--signal-pop` — `#F97316` for "needs attention"

Span colors (trace waterfall, derived from signal):
- LLM span — `#14B8A6`
- Tool span — `#F97316`
- Retrieval span — `#A78BFA` (a single graceful violet)
- Memory span — `#94A3B8`
- Channel span — `#5EA6FF`
- Voice span — `#F472B6` (a single graceful rose)
- Sub-agent span — `#FBBF24` (a single graceful gold)

We resist color expansion. Adding a new color requires an explicit reason in the design review.

### 16.3 Typography

- **Display + headings:** "Söhne" or fallback "Inter Display" — geometric sans with restrained character. Used at 1.5rem and above.
- **Body:** "Inter" — proven workhorse. Body at 0.9375rem (15px), comfortable line-height 1.5.
- **Editorial:** "Tiempos Text" or fallback "Source Serif Pro" — for long-form documentation, eval reports, audit summaries. The serif is intentional; it cues "read carefully" rather than "scan quickly."
- **Mono:** "Berkeley Mono" or fallback "JetBrains Mono" — code, traces, IDs.

Sizing scale (rem): 0.75 / 0.8125 / 0.875 / 0.9375 / 1.0 / 1.125 / 1.25 / 1.5 / 1.875 / 2.25 / 3.0. We do not scale linearly; we hit only meaningful steps.

Numbers are tabular by default everywhere a number could be compared to another number (tables, dashboards, badges).

### 16.4 Iconography

A single icon family, drawn as outlined 1.5px strokes on a 24px grid. Filled variants only for active state. Brand icons (channel logos, model logos) use vendor SVGs verbatim, never re-stylized.

We commission custom domain icons for: agent, skill, tool, knowledge, eval, scratchpad, scratchpad-key, fork, branch, canary, promote. These are sacred — the visual nouns of the product.

### 16.5 Motion

Motion is for affordance, continuity, and feeling. We do not bounce wildly; we glide with weight. Done well, motion is a second design system — a spatial choreography that tells the user what is happening and where things came from, without a single word.

**The motion system.**

Three named curves carry 95% of the work. Naming them is how we keep the product cohesive across teams.

| Token | Curve | Use |
|---|---|---|
| `motion.standard` | `spring(stiffness: 240, damping: 28)` | The default. Panel slides, inspector tab indicators, drag-drop returns. A small overshoot of ~3px gives weight without bounciness. |
| `motion.swift` | `spring(stiffness: 380, damping: 32)` | Acknowledgments. Button compressions, hover lifts, tooltip reveals. Faster, tighter, no overshoot. |
| `motion.gentle` | `spring(stiffness: 140, damping: 22)` | Ambient and ceremonial. The activity ribbon, the heartbeat, the earned moments (§16.18). Slower, with a felt arc. |

Linear easing is reserved for **progress** (a determinate progress bar fills linearly because that is what time does). Ease-out is reserved for **arrivals** that we do not want to overshoot (modals, alarms). Ease-in is reserved for **exits** (anything dismissed).

**The timing scale.**

| Token | ms | Use |
|---|---|---|
| `dur.flash` | 80 | Click acknowledgment, button compression, focus ring. |
| `dur.quick` | 160 | Hover lift, tooltip reveal, inspector tab indicator. |
| `dur.standard` | 240 | Panel slides, modal entrances, page transitions. |
| `dur.expressive` | 400 | Earned moments, the migration reveal, the fork "split." |
| `dur.ambient` | 1600+ | Heartbeats, the activity ribbon, breathing UI. Slow enough to feel like rhythm, not motion. |

**Choreography rules.**

- **One subject at a time.** When two things move, one leads and one follows by 60–80ms. Never two leads.
- **Motion has direction.** Things slide in from the side they live on; out the way they came in. The inspector slides from the right; modals rise from below; toasts fall from above.
- **Position before opacity.** Elements move into place at 0% opacity, then fade in over the second half of the motion. They look "developed" rather than "popped."
- **Stagger lists, never grids.** When a list of 5+ items appears, each item enters with a 30ms stagger. Grids appear together — staggering a grid feels like loading.
- **Layout shift is forbidden.** Hovers, lifts, and selection changes never move neighboring elements. We render shadow shifts, not size shifts.
- **Cancel preserves state.** Any motion can be reversed mid-flight by the inverse interaction without snapping. Drag-and-then-drop-back glides home.

**Reduced motion.**

`prefers-reduced-motion: reduce` swaps every motion for an opacity-only crossfade at `dur.flash`. Earned moments (§16.18) become a single soft border-glow with no motion. The heartbeat and activity ribbon hold static. We do not punish motion-sensitive users — we make their Studio just as expressive in stillness.

**Forbidden, by name.**

- Spring overshoots > 8% on routine actions (Apple-style "boing" feels juvenile).
- Parallax in scrollable lists.
- Particle effects of any kind, anywhere.
- Page-load skeletons that pulse at >0.5Hz (anything faster reads as a headache).
- Confetti, fireworks, balloons.
- Shake-on-error (we use a single soft amber border-pulse instead).
- Scroll-jacking. The user's scroll wheel is their sovereignty.
- Loading spinners that have personality (a "fun" spinner is still a spinner).

### 16.6 Sound

The product is silent by default. Sound is *offered*, never imposed.

**Where sound lives.**

- **Voice mode.** Tone-aware TTS, stage-marker beeps configurable per voice agent, ringback for outbound calls. These are functional, not decorative.
- **Operator inbox.** Off by default. When enabled by an operator, a single soft "tunk" announces a new escalation; an "alarm" tier item gets a slightly more urgent two-note motif. Both are designed to coexist with a busy office.
- **Earned moments** (§16.18), if the user has enabled sound. Otherwise silent. We never play a sound the user has not opted into.

**The composition.**

We commission a small, restrained sound palette from a single composer. Six signature sounds total. They share a tonal family (a warm, slightly hollow, late-evening kind of tone — closer to a wooden chime than a digital ping). Each is under 400ms. Each is one of:

- `chime.calm` — new calm-tier notification.
- `chime.nudge` — new nudge-tier notification.
- `chime.alarm` — alarm-tier event. Two notes, slightly urgent, never grating.
- `tunk.confirm` — a successful promote, a successful approve, a saved fork.
- `swoosh.transition` — a major navigation between modes (Focus, Presentation). Almost subliminal.
- `tone.complete` — an eval suite, a migration, a long-running background job finishing.

**Volume and respect.**

Studio observes the OS notification volume. It auto-dampens sound during scheduled quiet hours (configurable per workspace; defaults to 19:00–07:00 in the user's local timezone). It pauses all sound when the system detects voice mode is active or a screen-share is running.

**The off switch is one tap.**

A small speaker icon lives in the help surface (`?`). One tap mutes Studio sounds globally for the user; another tap restores. We do not bury the mute behind settings.

### 16.7 Imagery

Editorial, restrained. Empty states use line art on the brand color. Onboarding uses a single hero image of an agent canvas in glass-box. We never use stock photography of "businesspeople pointing at laptops."

### 16.8 Density

We default to "normal" density. "Compact" exists for power users on dense screens (audit log, eval results, large eval suites). "Comfortable" exists for first-time users who need bigger tap targets. The toggle is per-screen and remembered.

### 16.9 Color-independence (color-blind safety)

Color is never the only signal. Every state that uses color also uses an icon, a position, or a text label. We commit, by audit:

- The trace waterfall codes spans by **color and shape** (LLM = teal pill, Tool = orange chevron, Retrieval = violet diamond, Memory = slate ring, Channel = blue square, Voice = rose hex, Sub-agent = gold pentagon).
- Every status in the trust palette (§3.5) ships with a unique icon. A user with full deuteranopia or protanopia can tell `Live` from `Pending review` by glyph alone.
- Eval pass/fail is rendered as `✓ pass` / `✗ fail`, not green/red dots.
- Diff rendering uses `+` / `-` in addition to color.
- Charts use color **and** shape (solid line / dashed line / dotted line) to distinguish series. Maximum five series per chart; beyond five, we facet.

We test every release against simulated deuteranopia, protanopia, tritanopia, and full achromatopsia. The test runs in CI. Regressions block the release.

### 16.10 Focus mode and Presentation mode

Two opt-in viewing modes that turn Studio into a different room without changing what is on the canvas.

**Focus mode** (`⌘⇧.`). Hides the asset rail, the timeline, and the status footer. Leaves the canvas, the inspector, and the preview. The window chrome dims. Use case: deep work; one builder, one problem, two hours.

**Presentation mode** (`⌘⇧K`). Hides everything except the canvas and the preview. Increases type sizes by 1.25×. Disables tooltips. Hides multiplayer cursors except the local user's. Use case: demos to customers, pair sessions with stakeholders, screen-sharing in design reviews.

Both modes are reversible at any moment with the same shortcut. Both modes render the trust palette unchanged — a `Live` chip on prod is a `Live` chip in any mode.

### 16.11 Internationalization

The MVP ships in English. The product is built for translation from day one.

- All UI strings live in keyed catalogs; no hardcoded copy in components.
- Numbers, dates, currencies, units use `Intl.*` formatters bound to workspace locale.
- The visual layout uses CSS logical properties (`inset-inline`, `padding-inline`, `margin-inline`) so RTL languages flip correctly without per-component rewrites.
- The mono font (Berkeley Mono) is paired with a sans fallback for ranges it does not cover (CJK, Devanagari, Arabic).
- The voice agents support per-language ASR/TTS provider selection out of the box.

Launch order — informed by customer demand, not assumed: English (GA), Spanish, French, German, Portuguese (BR), Japanese, Chinese (Simplified), Arabic. RTL is added with Arabic.

The product copy library (Appendix C) is the source of truth for translation. Strings carry context comments so a translator sees not just the string but the surface it lives on.

### 16.12 Tactility

A pleasant product feels like a physical thing. Tactility is what we call the hundreds of tiny weight-and-spring details that make Studio feel substantial under your hands. Done well, it is invisible — the user just notices that *Studio feels nice*. Done badly, it is the difference between a tool you tolerate and a tool you reach for.

**Buttons.**

- On press, every button compresses 1.5px on its Y-axis with `motion.swift` over `dur.flash`, returning over `dur.quick`. The shadow drops by 2px during the compression so the button looks pressed *into* the surface.
- On release outside the button (drag-off-cancel), it returns to rest position with `motion.gentle`.
- Disabled buttons do not compress. They have the dignity of being honestly inert.
- Primary buttons gain a 1px inner glow on hover (`signal-accent` at 18% opacity), like a pilot light.

**Drag.**

- A dragged element lifts 6px (shadow translates accordingly), tilts 1.2 degrees in the direction of drag origin, and gains a 4% scale increase. The original location holds a soft outline placeholder so the user knows where it came from.
- Drag has weight: the cursor pulls the element with a 12ms lag (configurable as `motion.dragLag`), like the element is being pulled by a string. Snap-to-target overrides the lag the moment the cursor enters a valid drop zone.
- On a successful drop, the element settles with a single dampened spring (overshoot ~2px, decay over 240ms).
- On a failed drop (invalid target, dropped outside drop zone), it returns home along its drag path with `motion.standard` — never instantly, never via a different route.

**Hover.**

- Cards lift 2px with a corresponding shadow shift. Never a size change.
- List rows reveal their action chips on hover, sliding in from the right with `motion.swift` over `dur.quick`.
- Buttons reveal their keyboard shortcut as a small badge in the corner after a 600ms hover dwell. The badge fades with `motion.gentle`. Mouse-leave fades it out immediately.
- Links reveal their target URL in the status footer after 400ms dwell — a quiet bottom-of-window habit borrowed from desktop browsers.

**Selection.**

- Single-click selection produces a 1-frame ring expansion (a soft `signal-accent` ring scaling from the click point outward, fading by frame 6). It says: "I heard you." Subliminal, but felt.
- Multi-select adds items to the selection with a small leftward "tuck" — the new item slides 4px right, then settles. Removed items reverse.
- Selection persists during scrolls. The user is never surprised by a phantom deselection.

**Drop file from desktop.**

When a file enters the Studio window, the entire workspace gains a 4px `signal-accent` vignette around its edges, fading in with `motion.gentle`. Valid drop targets within the workspace illuminate as the cursor crosses them. Drop completes with a single soft `tunk.confirm` (if sound is on) and a brief progress chip in the status footer.

**Resizing rails.**

The asset rail and the inspector are resizable by their inner edge. The drag has the same lag-and-spring feel as a node drag — never a stiff rubber-band. Released, the rail snaps to the nearest "comfortable" width (either the user's last preferred width or one of three preset widths). The snap is visible.

### 16.13 Micro-interactions, by surface

A catalog of the signature small moments. Each is a sentence; the principle is "felt, not announced."

**Topbar.**

- The Loop logo pulses once when the data plane returns to healthy after a degradation. The pulse is `motion.gentle`, scale 1 → 1.06 → 1, over `dur.expressive`. Easy to miss; reassuring when caught.
- The notification well "winks" when a new item arrives — a single scale 1 → 1.18 → 1 of just the dot, over 240ms. The badge count, if it changes, slides up with `motion.swift`.
- Branch switcher: opening it slides a panel from below the topbar with `motion.standard`. The current branch is highlighted with a teal underline that travels to the new branch on selection.

**Canvas.**

- Pan has momentum. A flick scrolls with decay over ~600ms, with a soft "rest" snap when motion drops below 0.5px/frame.
- Zoom has a focal point — the cursor position at the start of the zoom remains anchored. Two-finger pinch zooms with the same focal anchor.
- Adding a node: ghost preview follows the cursor with the drag-lag described above, drops with a settle spring.
- Connecting an edge: drawing the edge from a port creates a continuous bezier that follows the cursor, with subtle curvature. On hover over a valid input port, the port lights up with a 1px glow and the edge curve "magnetizes" into a final shape.
- Deleting a node: the node fades and contracts to its centroid over `dur.standard`. Connected edges retract to the surviving nodes with a 60ms stagger so the user sees what just disconnected.
- Selecting a node opens the inspector with a slide from the right; the canvas slides left by the inspector width, never overlaps. The motion is one continuous spring.

**Inspector.**

- Tab indicator glides between tabs with `motion.standard`. Tab content cross-fades over the second half of the slide so the user sees the new tab settle into place.
- Number inputs (temperature, retries, budget) have a "scrubbable" affordance — click-and-drag horizontally to scrub the value. The number ticks with a soft `tunk.confirm` if sound is on (subtle, almost subliminal).
- A long prompt being edited gets a soft top/bottom fade-out at the boundaries of its scroll region — like a long page reaching its margins. Never abrupt.

**Live preview.**

- The preview pane has a thin teal "alive" line at the top that gently pulses when the agent is mid-turn (the heartbeat — see §16.15). It is calm, not strobe-y.
- When you send a message, the input compresses (like the button) and the message slides up into the conversation with `motion.swift`. The agent's response appears at the bottom and the conversation scrolls to follow with `motion.standard`.
- Tool call cards fold in with a slight rotate-from-edge — like a sticky note being placed onto the conversation. Subtle.

**Timeline.**

- New turns slide in from the right with a 30ms stagger, settling into the timeline. Old turns shift left to accommodate.
- Hovering a turn extends a soft horizontal hairline up to the canvas, indicating which path through the agent that turn took.
- Forking a turn animates the source row "splitting" downward into two — a Y-branch tendril visible across the timeline for `dur.expressive` before collapsing into a small persistent "forked" marker on the source.

**Eval scorecard.**

- Each case's pass/fail bar fills from left to right with `motion.standard` and a 30ms per-case stagger. A scorecard of 50 cases fills in ~1.5s — long enough to be felt, short enough to be useful.
- A regressed case (newly red after being green) gets a soft amber border-glow that fades over `dur.expressive` — a way to draw the eye without making the user feel bad.

**Migration Atelier.**

- The three-pane review reveals from the center column outward — the middle column ("needs your eyes") settles first, the source and Loop columns slide in from their edges 80ms later. The user knows what to do before they know what they are looking at.
- Resolved items "tuck" upward off the column with a slight fade, decrementing the unresolved count visibly.

**Pipeline.**

- The canary slider has a magnetic detent at every 10% step. Moving past a step plays a tiny `tunk.confirm` (if sound is on).
- The "Promote" button only enables when all gates pass. The transition from disabled-gray to enabled-teal is `dur.standard` with a soft ring expansion at the moment of enablement — a gentle "you're ready" cue.

**Inbox.**

- New escalations animate in at the top with a soft amber "fresh" border that fades over `dur.expressive`.
- Take-over is felt: clicking the button compresses, the operator panel slides up from the bottom, and the agent badge in the conversation gains a small "silenced" indicator. The user feels the shift in agency.

**Audit log.**

- Filter changes re-fetch results with a thin top progress bar (`signal-accent`, 1px). Results animate in with the standard list stagger. The user is never confused about whether the filter took.

### 16.14 Streaming, as ink

LLM responses do not just appear. They are *written*.

- Tokens render with a 1-frame opacity ramp (0 → 1 over 60ms) at their final position. No layout shift. The cumulative effect is a soft "ink" appearing on the page rather than text being typed.
- The cursor — a 1px teal vertical bar at the current write position — pulses at 1.5Hz while writing. It hides when writing pauses for thought (the model is generating but the buffer is empty), reappears the moment a token arrives.
- When the agent calls a tool mid-response, an inline tool card folds into the conversation with `motion.standard`. A subtle gradient sweep travels left-to-right across the card while the tool is in flight (the "thinking shimmer"). Result returns; shimmer stops; result text inks in below the card.
- The "stop" button is reachable at all times during streaming. Pressing it freezes the cursor mid-write — the partial response remains, with a small "stopped" pill at the end.

For voice, the equivalent is the **waveform.** A live waveform of the agent's TTS plays at the bottom of the preview, with a soft teal aurora flowing along its peaks. The user *sees* the agent speaking, not just hears it. Stage-marker dots (ASR start, agent start, TTS start) sit beneath the wave with their cumulative latency rendered as elegant tabular numbers.

### 16.15 Ambient life

Studio is alive. Subtly. Always.

**The agent heartbeat.** Every agent has a heartbeat indicator — a 6px teal dot in the topbar, beside the agent name. It pulses (`motion.gentle`, scale 1 → 1.15 → 1) once every 2 seconds when the agent is idle and ready, twice as fast when actively processing a turn, holds steady amber when paused, holds steady red when down. After a moment, you stop noticing it consciously. You notice immediately when it stops.

**The live activity ribbon.** A 2px gradient ribbon spans the very top of the workspace, behind the topbar. Its color and intensity are proportional to the workspace's real-time turn rate, computed every 2 seconds with a 30-second exponential smoothing. Calm at low rates (a barely-visible teal); vivid at high rates (a richer teal-to-violet gradient suggesting throughput). The ribbon never blinks, never strobes. It is felt more than seen — until the user wants to know "is anything happening right now," and a glance answers.

**Now-playing on the agent card.** Agent cards show a small `● 3 conversations live` chip when conversations are in flight against this agent, with the dot pulsing in sync with the heartbeat. Click the chip to jump to the inbox filtered to that agent.

**The breathing notification well.** When there are unread items in the well, the well's outline opacity drifts between 60% and 100% over 4-second cycles — a slow, calm "breathing" that says "look at me when you're ready." After the user opens the well once, breathing stops and the well returns to static until the next batch arrives.

**Multiplayer presence.** Other users' cursors appear on the canvas as soft labeled flags (their initial in their assigned color). The cursor moves with a 60ms smoothing so it feels intentional rather than jittery. When another user enters the agent, their avatar slides into the topbar with `motion.standard`. When they leave, it fades over `dur.expressive`. Their selection ring on the canvas (in their color, at 30% opacity) follows the same smoothing.

**Background work.** Re-indexing a KB, compiling the whitelabel CSS, running an eval suite — each surfaces in the status footer as a calm progress chip. Completion is a single soft expansion ring on the chip and a calm-tier notification in the well. We never modal-block on background work.

### 16.16 Texture and atmosphere

Surfaces have warmth. Studio is not a flat sheet of pixels.

**The canvas grid.** A 16px square grid sits beneath the canvas at 4% opacity (dark mode) / 6% (light mode). It has a barely-perceptible parallax during pan (the grid moves at 95% of the canvas's velocity, suggesting depth without distraction). The grid is muted further inside the inspector's visible region — a focal-point trick that draws the eye to what matters.

**Paper warmth.** The canvas backdrop has an extremely subtle noise texture (a 2% opacity film of high-frequency monochrome grain). Almost subliminal; gives the canvas a felt-paper warmth instead of a clinical flatness.

**Depth.** Elevated surfaces (modals, popovers, inspector panels) carry warm shadows with a slight blue-violet tint, not pure black. Shadows are layered (`shadow-1` for hover lifts, `shadow-2` for popovers, `shadow-3` for modals, `shadow-4` for the share sheet) and consistent across surfaces. We do not invent new shadows per component.

**Ambient light.** The workspace background has a barely-perceptible vignette — slightly darker at the corners, a touch of warmth toward the center. It pulls the eye inward without being noticed.

**Quiet hours.** Studio at 11 PM has a slightly warmer, dimmer feel than at 9 AM. Background slides 2% toward warmer; trust-palette pulses dampen by 30%; sounds (if on) get an extra –6dB. The shift is gradual (over 30 minutes), tied to the workspace's local timezone, and toggleable. The intent is respect — not a gimmick. The user can turn it off if they prefer constant ambience.

**The cursor.** Studio uses the system cursor for all standard surfaces. On the canvas, the cursor switches to a custom 14px crosshair-ring hybrid that gives precise feedback on hit-testing. On a node, it becomes a soft hand. On an edge endpoint, a small "splice" icon. The cursor itself is part of the design.

### 16.17 Prompts as prose

Prompts deserve typography fit for prose, not config. The prompt editor in the inspector treats the act of prompt-craft with reverence.

- **Type.** The prompt editor uses Tiempos Text (the editorial serif from §16.3) at 16px, leading 1.55, max-width 72ch. It feels like writing in an editor that respects you.
- **Roles, set in margin.** System / user / assistant / tool labels are set in small caps to the left margin, in slate, never inline. The body of each role flows uninterrupted in the main column.
- **Variables, treated as nouns.** Template variables (`{{order_id}}`) render in mono with a soft pill background, `signal-accent` at 8% opacity. They are never visually noisy; they are always visually distinct.
- **Token count, in the gutter.** As you write, an unobtrusive token count surfaces in the right gutter — calmly updating, with a calm progress bar against the model's context window. No red until you cross 90%.
- **A11y first.** The prompt editor supports Markdown-like formatting and renders the result inline with subtle styling. Keyboard shortcuts (`⌘B` bold, `⌘I` italic, `⌘K` link) are respected.
- **Save state, breathed.** A single dot in the corner indicates save state — solid teal when persisted, soft gray pulse when saving, amber for unsaved changes during a degraded data plane. The user always knows where their words live.

### 16.18 Earned moments

The few times we celebrate. Each is rare, brief, dignified, and *earned* — never given for free, never repeated for the same user.

**The first turn.** When the user's very first turn streams in (per agent, per user), the response inks in with a slightly slower cadence (1.4× normal) and the preview pane's outline gains a single soft teal ring expansion (`dur.expressive`). No words. No badge. Just a felt "this worked." The next turn streams normally.

**The first deploy.** When the user's first promotion to production succeeds, the Pipeline screen briefly renders the agent's name in the editorial serif at 2× size, centered, with the `Live` chip beneath. Holds for 2 seconds. Fades. Returns to the standard Pipeline view. The first deploy is the moment a builder becomes a shipper. We mark it.

**The first 100% canary.** When a canary reaches 100% for the first time (per agent), the canary slider's track gains a slow gradient sweep (left to right, `dur.expressive`, `motion.gentle`). The slider chip changes from `Canary` to `Live` with a small ring expansion. Felt, not loud.

**The first 1,000 production turns.** A calm-tier notification arrives in the well: "Your agent has handled 1,000 production turns. Here's what we learned about its shape." Click → a single-page **Agent Health Card** opens, beautifully typeset, with the agent's deflection rate, p95 latency, top-3 most-asked intents, and the most-improved eval case. Shareable as a PDF. This is a love letter to the user's work.

**A successful migration cutover.** When the user moves the cutover slider to 100% for the first time, the Atelier dims everything except the Loop pane, which holds for `dur.expressive` with a soft teal ring around its border. The status footer surfaces a calm "Migration complete" chip. The audit log gets a stamped `migration.completed` event.

**A clean eval run after a regression.** When an eval suite goes from "regressing" to "100% pass" within the same session, the scorecard's overall ring fills with a single sweep, and the previously-red cases each soft-fade their amber-glow halos. No badge, no toast, no sound. Just visual relief.

**A perfect parity score.** When a parity harness reports 100% identical conversations across 200+ cases, the parity report renders a single soft teal underline beneath "100%" that draws itself in `dur.expressive`. It is the longest single line in any earned moment, and it is appropriate.

**Constraints on earned moments.**

- Once per user, per agent (or per equivalent unit). We never repeat.
- Always under `dur.expressive` (≤ 400ms motion).
- Never modal. Never block. Never interrupt the next action.
- Always silent unless sound is opted in (and even then, just `tone.complete`).
- Always opt-out (the user can turn off earned moments globally in Settings → Personal → Polish).

### 16.19 Skeletons with character

Loading states get the same care as the loaded states. We do not ship gray rectangles.

- **Anatomy.** Skeletons mimic the shape of the real content — cards, table rows, charts, traces — at the right proportions. We never use generic boxes; we use surface-specific placeholders.
- **The pulse.** A subtle horizontal gradient sweeps across each skeleton at 0.4Hz (slower than the eye notices as motion; just enough to feel "warm"). The sweep is one direction only. Never bounces.
- **Surface-specific.** The trace waterfall skeleton renders the time axis immediately and stages its bars in left-to-right with a 40ms stagger. The conversation list skeleton renders 5 rows of varied widths to suggest real content's variation. The eval scorecard skeleton renders the case count immediately so the user knows the size of the load.
- **Progressive.** When data arrives, skeletons cross-fade to real content over `dur.quick`. We never snap. Real and placeholder coexist briefly.
- **Silent.** No sound on load completion. No celebratory ring on routine fetches.

### 16.20 The polish principles

The constraints that keep all of the above from collapsing into noise.

1. **Polish serves the work, not itself.** If a motion does not aid comprehension, affordance, or felt continuity, we cut it.
2. **Subliminal beats visible.** The best polish is felt, not noticed. If a user has to mention an animation, we have probably overdone it.
3. **Earned, not given.** Celebrations are reserved for true milestones. Repetition cheapens them.
4. **Rhythm over speed.** Most polish lives at `dur.standard` (240ms) or below. Anything above must justify its time.
5. **One subject at a time.** Two simultaneous animations halve the felt quality of both.
6. **No layout shift, ever.** Hover, selection, status changes — all happen with shadow and opacity, never with size.
7. **Reduced motion is first-class.** Our reduced-motion experience is also pleasant. We do not strip the soul out for accessibility users.
8. **Optional, always.** Users can turn down polish in Personal → Polish. The product remains beautiful but quieter.
9. **Cohesion across surfaces.** A button on the Inbox feels exactly like a button on the Pipeline. We share a spring system, not a mood.
10. **The polish review.** Every release includes a 30-minute "polish review" where the design team plays with the new surface in slow motion. If anything feels gratuitous, sluggish, or noisy, it gets cut before ship.

The standard we hold ourselves to is simple: **a builder should feel slightly more capable, slightly more delighted, slightly more at home in Studio every time they open it — without ever being able to say exactly why.** That is what good polish does.

---

## 17. Information architecture

The whole product is reachable from four paths.

### 17.1 The four paths

1. **The asset rail** — for working on something specific (a tool, a KB source, a sub-agent).
2. **The topbar breadcrumbs** — for moving between workspaces, projects, agents, branches.
3. **The command palette** (`⌘K`) — for jumping anywhere by name. Fuzzy search across agents, conversations, eval cases, tools, KB chunks, audit events, settings, shortcuts.
4. **The trace timeline** — for going to a specific moment in production.

There is no left-side navigation tree of pages. We do not have thirty pages. We have a canvas and a few rails.

### 17.2 The screens we do have, total

For builders:
- Canvas (the studio surface)
- Migration Atelier
- Knowledge Studio
- Tool Bench
- Voice Stage
- Conductor (multi-agent)
- Pipeline
- Observatory
- Inbox

For enterprise builders, additionally:
- RBAC matrix
- Audit log explorer
- Approvals queue
- Compliance page
- Procurement page
- Encryption / BYOK page
- SSO / SCIM page
- Whitelabel page

That is it. Eighteen screens total. Anything else is a panel inside one of these.

### 17.3 The command palette

`⌘K` is the connective tissue. From it:

- "agent: support" — jumps to agent
- "conv: 4172" — jumps to conversation
- "eval: refund-flow" — jumps to eval suite
- "trace: t-9b…" — jumps to trace
- "audit: 2026-04 budget" — jumps to filtered audit log
- "settings: residency" — jumps to setting
- "skill: order-lookup" — jumps to skill canvas
- ":new agent" — creates a new agent
- ":new tool" — opens tool spec editor
- ":import from botpress" — opens Migration Atelier with Botpress preselected

The palette is keyboard-only; mouse users discover it through a topbar hint on first session. Recent items, pinned items, contextual suggestions.

### 17.4 Search & saved searches

Two search surfaces. Each does one job.

**Find-in-context** (`⌘F`). Scoped to whatever you are looking at — the canvas, the trace, the audit log, the eval scorecard. Highlights matches in place. `↩` jumps to next, `⇧↩` to previous. Closes with `Esc`.

**Cross-workspace search** (`⌘K`, the command palette). Federated across agents, conversations, eval cases, tools, KB chunks, audit events, settings, branches, marketplace items, and shortcuts. Ranking is by recency × relevance × pinned status. Type-aware — typing `agent:` filters to agents; typing `cs-` matches changesets; typing a UUID jumps directly.

**Saved searches.** Any cross-workspace search can be pinned with `⌘D`. Pinned searches surface as a pill in the topbar (configurable per user) and in the asset rail. Examples: "audit: 4-eyes overrides last 30 days," "evals: regressing this week," "inbox: tool-failed on payments." Saved searches refresh in the background; their pill carries a count.

**Search across customer data.** Cross-workspace search is scope-respecting. A user only sees what their RBAC permits. Enterprise admins can opt to log all search queries (per their compliance posture) — disabled by default, surfaced as a setting in the Compliance panel.

### 17.5 Sharing & links

Links are part of the product. We make them safe.

**Stable IDs.** Every artifact has a stable, opaque ID. Links use IDs, not paths — they survive renames, branch moves, and reorganization. Path-based URLs are aliases that resolve to ID URLs.

**Share affordance.** Most artifacts (a turn, a trace, a fork, a conversation, an eval case, a chart, a node) carry a `Share` button. Clicking opens a share sheet:

```
┌── Share trace t-9b23 ───────────────────────────────────────┐
│  Who can view:                                              │
│   ◉ Workspace members (default)                             │
│   ○ Specific people  [ +add ]                               │
│   ○ Anyone with the link  ⚠ requires admin permission       │
│                                                             │
│  Expires:    [ 7 days ▾ ]   ▢ Allow re-export               │
│  Redact:     ▣ PII  ▣ secrets  ▢ pricing  ▢ tool calls      │
│                                                             │
│  Link:  https://studio.loop.ai/t/9b23-…              [Copy] │
│                                                             │
│  This share will appear in the audit log as `link.created`. │
└─────────────────────────────────────────────────────────────┘
```

**Public links** are off by default. Enabling them is a workspace-level entitlement; admins can disable them entirely in regulated environments. Every public-link creation is audited. Every public-link view is rate-limited and audited (with the viewing IP and user agent).

**Redaction is a first-class option** on every share. The product knows what is PII (auto-detected by our redactor), what is a secret reference, what is a pricing detail. Sharing a trace can ship with PII redacted automatically — and the redaction is visible to the recipient ("12 spans of PII redacted").

**Embed.** Charts, eval scorecards, and traces can be embedded in Notion, Confluence, or any Markdown surface via a public OEmbed endpoint (when public links are allowed). Embeds inherit the same redaction policy as the source link.

---

## 18. Interaction patterns

### 18.1 Hot reload

Edits propagate immediately. Each edit produces a transient toast that says exactly when it took effect (e.g., "applied to next LLM call," "applied to next turn," "re-indexing in background").

### 18.2 Optimistic UI

Edits render as if applied. If the server rejects, the UI reverts and a toast explains. No spinners on routine edits.

### 18.3 Undo / redo

Universal. Survives reloads. Visible (`⌘Z`, `⌘⇧Z`) and discoverable from the edit menu.

### 18.4 Selection

Selection is global. The inspector reflects what is selected. Multiplayer reflects what others have selected. Selection persists across panel toggles.

### 18.5 Search

`⌘F` opens find-in-context (within the current canvas, the current trace, the current audit log). `⌘K` opens command palette (across the workspace).

### 18.6 Forms

- Validation inline, real-time, after first blur.
- Submit buttons disabled with explainer tooltip when invalid.
- Destructive actions (delete agent, rollback prod, revoke key) require typing the resource name to confirm. No "are you sure" yes/no dialogs for destructive actions — they are too easy to dismiss.
- Save is implicit. We never use a "Save" button on routine edits. Forms with multiple fields show a "Discard changes" button only when changes are pending.

### 18.7 Real-time

WebSocket-backed surfaces:
- The live preview (turn-by-turn streaming)
- The trace timeline (new turns animate in)
- Multiplayer presence (cursors, selection)
- The inbox (new escalations)
- The Observatory (anomaly chips)
- Approvals queue (new requests)

Other surfaces poll at 30s or are imperative (refresh on user action).

### 18.8 Keyboard shortcuts

Comprehensive. `?` opens a searchable cheatsheet. Every shortcut is also rendered in tooltip text on its corresponding button.

Topical shortcuts:

```
GLOBAL
?              show shortcuts
⌘K / ctrl-K    command palette
⌘B             toggle asset rail
⌘.             toggle inspector
⌘⇧.            toggle preview / focus mode
⌘⇧K            presentation mode
⌘\             toggle timeline
⌘⇧A            new agent
g w            jump to workspace home
g i            jump to inbox
g o            jump to observatory
g a            jump to audit log
[ / ]          previous / next branch

CANVAS
v              select tool
n              add node
e              add edge
delete         remove selected (asks to confirm; see §18.9)
⌘D             duplicate selected
⌘G             group into skill
f              focus selection (zoom-fit)
⌘Z / ⌘⇧Z       undo / redo
1–7            inspector tabs

PREVIEW
↩              send message
⌘↩             send and pin to evals
⌘.             stop generation
m              toggle voice mic

TRACE
j / k          next / previous turn
t              open trace
⌘F             find in trace
⌘⇧F            fork from here
⌘⇧E            save as eval

INBOX
o              take over
d              draft as agent
r              release back to agent
n              note (private to operator)

ENTERPRISE
⌘⇧P            promote
⌘⇧R            rollback
⌘⇧⌥A           open approvals queue
⌘⇧L            open audit log
```

### 18.9 Guardrails: protecting against mistakes

We make destruction loud, reversible, and slow. Routine work stays fast.

**The four classes of action.**

| Class | Examples | UX |
|---|---|---|
| **Routine** | Edit a prompt, tweak a knob, add a chunk, send a preview turn | One click. Save is implicit. Undo is universal. |
| **Material** | Promote to staging, install a marketplace tool, change a budget cap | One click + one transient toast that names what just happened and offers Undo for ~10 seconds. |
| **Consequential** | Promote to production, rotate a secret, rebind a BYOK key, change residency, invite an admin | Confirmation modal. The user types the action's verb (e.g., `promote`) to confirm. We never use `Are you sure?` yes/no. |
| **Destructive** | Delete an agent, delete a KB, revoke an API key, delete a workspace, force-rollback prod, override an eval gate | Confirmation modal. The user types the resource's full name. A 10-second cooldown after typing before the button enables. The action appears in the audit log with a pop-state chip on the topbar prod chip ("rolled back without eval gate, 14:32"). |

**The protections that always apply.**

- **Soft delete by default.** Deleting an agent, a KB, a tool, a skill, a marketplace item moves it to a recycle bin scoped to the workspace. It is fully restorable for 30 days. Hard-delete is a separate, second action — and is itself audited.
- **Production touch detection.** Any action that affects production (promote, secret rotation, channel-routing change, residency change) elevates the topbar prod chip to a pulsing ring during the action. The status footer surfaces a "production touch in flight" line.
- **Concurrent-edit notice.** If another user edits the same artifact within the last 60 seconds, your edit pane shows their avatar and a "Maya edited 14s ago" line. You decide whether to proceed.
- **Cooldown on rapid destruction.** If a user destroys two non-trivial artifacts within 60 seconds, the third triggers an extra layer of confirmation ("you are deleting things quickly; please pause"). The cooldown is opt-out per user, opt-in per workspace for high-trust roles.
- **Compliance-tagged workflows.** Agents, KBs, tools, or skills can be tagged `compliance: hipaa`, `compliance: pci`, `compliance: gdpr`. Edits to compliance-tagged artifacts surface their tag prominently and require approval-before-promote regardless of role gradient.

**The protections we refuse.**

- We refuse "are you sure?" dialogs on routine actions. They train the user to dismiss confirmations. We use them only when destruction is at stake.
- We refuse hidden destructive shortcuts. There is no `Cmd-D-D` that deletes an agent.
- We refuse silent destructions. Nothing is removed from a user's view without an audit-log entry and (for material+ actions) a notification.

---

## 19. Empty states

Every empty state is illustrated, with a single clear CTA, copy in the product voice, and never a dead-end.

| Surface | Copy | Primary CTA | Secondary |
|---|---|---|---|
| **Workspace, no agents** | "Your workspace is ready. Start with an agent." | New agent | Import from Botpress · Browse templates |
| **Agent, no canvas** | "An empty agent is just a prompt. Let's give it shape." | Add a trigger | Use a template · Import |
| **Canvas, no preview yet** | "Your agent is hot. Say hi." | Send a message | Switch to voice |
| **Timeline, no turns** | "Turns will appear here as you talk to your agent." | (none) | Documentation |
| **KB, no sources** | "Knowledge starts with a source." | Add a source | Connect Notion · Upload files |
| **Tools, no tools** | "Tools are how your agent acts in the world." | New tool | Browse MCP marketplace |
| **Evals, no suite** | "Save any turn as an eval to start a suite." | (none — wait for a turn) | Documentation |
| **Inbox, all clear** | "All quiet. No escalated conversations." | (none) | Configure escalation rules |
| **Audit log, no events in range** | "No events in this date range." | Reset filter | (none) |

We do not use cute empty states. We use precise empty states.

---

## 20. Loading states

The hierarchy:

1. **Skeleton** — for list views (conversations, agents, traces, audit log). Three to five placeholder cards, same proportions as real content. Subtle shimmer (slow, calm).
2. **Progressive** — for panels and detail views. Render the structure immediately; stream data into fields as they load. Fields-not-yet-loaded use a soft monochrome placeholder, never a spinner.
3. **Streaming-aware** — for traces, LLM responses, eval runs. Show partial state with a clear "still arriving" cue.
4. **Background** — for re-indexing KB, recomputing eval, compiling whitelabel CSS. A topbar progress chip with a click-through to a detail panel.

Forbidden: a full-page spinner. We always show partial content. When a page truly cannot render anything, we show a skeleton of what will arrive.

---

## 21. Error states

Errors are loud — but not dramatic. The product voice for errors is direct, specific, actionable.

### 21.1 The shape of an error

```
[ icon ]   Headline (what broke, in a clause).
           One sentence on why.
           [Retry]    [Copy debug bundle]    [Read more]
```

- **Headline** is the error name in plain English: "Tool call timed out" not "Network error."
- **Why** names a cause: "lookup_order took longer than 60s. The tool returned no response."
- **Actions** are concrete: Retry (idempotent only), Copy debug bundle (request ID, trace ID, console logs, recent audit entries — to share with support), Read more (links to docs).

### 21.2 Error catalog principle

Every error has a stable code (`LOOP-RT-403`) that maps to a docs page, a support article, and a known-issues feed. Users see the human form; engineers and support see the code.

### 21.3 Error tone

- Direct, never apologetic. ("Hard budget cap hit." not "Sorry, but…")
- Specific, never vague. ("OpenAI returned 503 after 3 retries." not "Something went wrong.")
- Actionable, never dead-end. Every error names what to do next.

---

## 22. Onboarding (the first 60 seconds)

We have one goal: get a new user to a streaming response in 60 seconds. We do not have any other goal.

### 22.1 The three doors

After OIDC, the user lands on Studio. The canvas is empty but ready. A single calm panel offers three doors:

1. **Import from another platform.** A list of source platforms with logos. Click → Migration Atelier opens with that source preselected. Most likely path for a customer with existing investment.
2. **Start from a template.** Templates: support agent, sales SDR, scheduling concierge, voice receptionist, internal IT helpdesk, doc-search assistant. Each template is a fully-formed agent with sample KB, tools, evals. Click → it opens on the canvas, ready to talk to.
3. **Start blank.** Empty canvas with the AI co-builder docked open, asking "What are you building?" The user types one sentence; the co-builder scaffolds.

There is no fourth door. There is no "watch a video" door. There is no "tell us about your team" form.

### 22.2 The first turn

Within 60 seconds of choosing a door, the user has typed something into the preview and the agent has responded. We measure this. The metric is named "time-to-first-turn" and it is the most important onboarding metric in the product.

### 22.3 The guided spotlight

A small, dismissable spotlight ring appears around three things in sequence, paced to the user's actions, never auto-advancing:

1. The canvas (when they look at the response): "This is what just ran."
2. The trace timeline (when they open a trace): "Click any turn to see what happened."
3. The fork button (after a few turns): "Try forking from a turn to test a change without losing this conversation."

Three rings, not thirty. The spotlight system is calm, not pushy. `Esc` dismisses any ring permanently.

### 22.4 First week, first month, first quarter

Onboarding does not end at the first turn. We design for what happens next.

**The first week.** The user has a working agent. They are wiring tools, ingesting KB, and showing their team. We send at most one in-product nudge per day, opt-out per category:

- Day 2 — "You have 14 saved-as-eval cases. Run them as a suite."
- Day 3 — "Your agent has answered 200 turns. Check the Observatory for hot spots."
- Day 5 — "Invite a teammate to comment on your agent."
- Day 7 — "You're at 87% of your trial budget. Plan your usage or upgrade."

Each nudge is a card in the notification well, not an interruption. The user pulls; we don't push.

**The first month.** The user has shipped to production. They are watching. We make the steady-state rituals visible:

- A weekly **Change Recap** card in the well: "This week: 4 promotions, 2 rollbacks, 12 evals saved, 3 KB sources updated. Cost +5%, latency unchanged." Click to open the full recap as a shareable artifact.
- A monthly **Health Review** card: "Last 30 days: deflection rate 64%, escalation rate 8%, p95 latency 1.4s, $/turn $0.011. Three suggestions:" — concrete, opt-in, never automatic.

**The first quarter.** The user has multiple agents. They are organizing. We make org-wide hygiene easy:

- A **Skill candidates** card — "These three agents share a `refund eligibility` pattern. Extract into a shared skill?"
- A **Stale KB** card — "Eight KB sources have not synced in >30 days. Review or archive?"
- A **Permission drift** card — "Two members have not used Studio in 60 days. Review their access?"

These rituals are the difference between a tool a user opens and a tool a user lives in. They are calm, useful, dismissable, and never marketing.

### 22.5 Templates

The "Start from a template" door (§22.1) opens a curated grid. A template is not a snippet — it is a fully-formed agent with sample KB, mock tools wired through, an eval suite, and seeded conversations on the timeline so the user lands on a working preview, not an empty canvas.

The starter set:

| Template | What it ships with |
|---|---|
| **Support agent** | Order-lookup tool (mock), shipping-status tool (mock), help-center KB, 24-case eval suite, seeded conversation. |
| **Sales SDR** | CRM-lookup tool (mock), calendar tool (mock), pricing KB, 18-case eval, seeded outbound flow. |
| **Scheduling concierge** | Calendar tool (mock), confirmation email tool (mock), business-hours KB, 12-case eval. |
| **Voice receptionist** | Calendar (mock), call-routing tool (mock), business-hours KB, voice mode pre-enabled. |
| **IT helpdesk** | Ticket-creation tool (mock), known-issues KB, escalation rule, 22-case eval. |
| **Doc-search assistant** | Pinecone-style KB connector, citation-aware response shape, 14-case eval. |
| **Voice triage (clinical)** | Compliance: hipaa tag, escalation flow, narrow scope, sample audit cases. |
| **Procurement Q&A** | Document-grounded retrieval, compliance: gdpr tag, sample evidence cases. |

Templates are versioned; updating an agent's template is a graph diff, reviewable like any other change. Enterprise customers can publish private templates org-wide, governed by RBAC. Templates surface on the marketplace (§27) under a "Starters" tab; community templates are vetted before publication.

---

## 23. Accessibility

We commit to **WCAG 2.2 AA across the product** and **AAA where it costs us nothing extra**. Aspirational target: WCAG 2.2 AAA for the canvas inspector and the inbox (the surfaces where assistive-tech users spend the most time).

### 23.1 Per-component checklist

Every component ships with a documented a11y contract:

- Color contrast measured at design time and at code-review time. ≥4.5:1 for body, ≥3:1 for large text and UI elements.
- Keyboard-only navigation tested per release (we have a CI gate that blocks releases failing keyboard-only smoke).
- Visible focus rings, with their own design token (`--ring-focus: 2px solid #5EA6FF` on dark, `2px solid #2563EB` on light), never `outline: none`.
- ARIA labels on every icon-only button. ARIA-live regions on streaming responses, eval results, anomaly alerts.
- Screen-reader-friendly tables with `<th scope>` and `<caption>`.
- Reduced motion respected via `prefers-reduced-motion`.
- High-contrast mode supported via `prefers-contrast: more`.

### 23.2 The canvas in particular

The canvas is the hardest a11y challenge. We solve it:

- Keyboard navigation across nodes (Tab to next node in topological order, Shift-Tab back, arrow keys to siblings).
- Screen-reader summary on canvas focus: "agent support-en, 14 nodes, 18 edges, last turn at 14:32."
- Per-node summary on focus: "node: classify_intent, type LLM, model gpt-4o-mini, cost $0.0011 p50, latency 412ms p50."
- A "list view" alternate of the canvas — same source of truth, expressed as an indented hierarchical list with all the same actions. This is a first-class view, not a fallback.

### 23.3 Voice as alternate input

Voice mode also serves as an alternate input modality for users who type slowly or with assistive tools. The agent canvas itself can be navigated with voice commands (in private alpha): "show me the trace for the last turn," "promote this version," "fork from turn 3."

---

## 24. Performance (perceived)

Performance is part of UX. We commit to specific perceived-performance targets.

| Surface | Target | What we measure |
|---|---|---|
| First contentful paint | <1.0s | TTFB to first canvas render |
| Time-to-interactive (canvas) | <2.0s | Canvas accepts edit |
| Time-to-first-turn (preview) | <3.0s from open | Preview accepts and streams |
| Edit-to-effect (prompt edit → next call) | <150ms | Roundtrip including hot reload |
| Trace open | <500ms | Click turn → drawer rendered |
| Command palette open | <50ms | ⌘K → first result rendered |
| Audit log query (1M rows) | <800ms | Filter applied → first page |
| Eval suite run (50 cases) | <30s | Click run → all cases reported |

We measure these with synthetic monitors per region. Misses are SLOs, not nice-to-haves. We block releases on regression.

### 24.1 Calm under load

When the data plane is degraded, the UI degrades calmly:

- Streaming responses gain a "slower than usual" cue at p95+50%.
- The canvas remains editable; edits queue.
- The preview shows a clear "data plane degraded — your changes are saved" banner instead of breaking.

We never show the user a spinning timeout dialog when we know the system is degraded.

---

## 25. Mobile, tablet, large display

Studio is desktop-first. We do not pretend otherwise.

- **Mobile (≤640px):** the inbox, the notification well, and approvals queue. Operators on call. Take over a conversation, type a response, escalate. Approve a changeset on the way to the train. Nothing else. The canvas is not on mobile; trying to edit a graph on a phone is a lie.
- **Tablet (641–1024px):** inbox, Observatory, approvals queue, audit log. Read-mostly. The canvas is read-only on tablet — touch is wrong for a multi-select graph editor.
- **Standard desktop (1025–1920px):** the full product.
- **Large display (>1920px):** the full product, with the canvas stretching gracefully and a third-pane optional layout (canvas | preview | inbox simultaneously).

### 25.1 The mobile inbox in detail

Most enterprise customers have at least one operator who carries a phone for incidents. The mobile inbox is built for that operator.

```
┌─────────────────────────────────┐
│  acme-support · production      │
│  ●●● dp ok  cp ok  gw ok        │
├─────────────────────────────────┤
│  4 escalated · 2 SLA risk       │
│  ─────────────────────────────  │
│  user_91     voice    18s   ▶   │
│  why: tool_failed               │
│  ─────────────────────────────  │
│  user_03     web      45s   ▶   │
│  why: confidence flag           │
│  ─────────────────────────────  │
│  user_77     web       3m       │
│  why: manual review             │
│  ─────────────────────────────  │
│  user_44     slack     7m       │
│  why: keyword: "lawyer"         │
│  ─────────────────────────────  │
│  [ inbox ] [ approvals 1 ] [⚙]  │
└─────────────────────────────────┘
```

What works on mobile:
- Take over (one tap; agent goes silent).
- Type a response. Voice-to-text dictation supported via the OS keyboard.
- Draft as agent. The LLM-drafted response renders inline; tap to send, hold to edit.
- Hand off to another operator (lists online operators).
- Approve a changeset. The diff renders as graph + a one-line summary; the eval delta is a sparkline; cost / latency deltas are chips. Approve, request changes, or decline. No promotion happens from mobile — only approvals. Promotion remains a desktop action.
- Acknowledge an alarm in the notification well.

What does not work on mobile, by design:
- The canvas (read-only, with a banner pointing to desktop).
- The Atelier (desktop-only).
- The Pipeline promote action (desktop-only).
- Secret rotation, BYOK rebind, residency change (desktop-only).

The mobile experience supports biometric unlock for sensitive actions (Face ID / Touch ID re-auth before take-over on regulated workspaces). Push notifications are opt-in per role; "alarm" tier in the notification well always pushes for operators on call.

---

## 26. The version-control story

Branches, diffs, merges. Throughout.

### 26.1 Branches as first-class

Every change happens on a branch. The default branch is `main`. The current branch is in the topbar. Switching branches updates the canvas, the preview's agent, the timeline.

### 26.2 The diff

Every diff in the product looks the same. Three views: graph diff (visual), code diff (textual), behavior diff (eval scorecard delta). The diff is the artifact of every promotion, every approval, every changeset review.

### 26.3 The merge

Merges into protected environments require approvals (per §14.3). Merge conflicts are graph-aware: "Maya removed node X; Diego edited node X. Resolve?"

### 26.4 The history

Every node has a history. Right-click → Show history. A vertical timeline of every edit, every approval, every promotion. Click any entry to see the diff at that moment.

### 26.5 The rewind

For non-prod environments, time-travel is one click: `⌘⇧T` opens "rewind to" with a date/time picker and an event list. Pick a moment; the canvas restores to that state on a new branch named `rewind/{timestamp}`. The original is untouched.

---

## 27. The marketplace

A small, curated marketplace inside Studio.

### 27.1 What it sells (and gives away)

- **Skills** — pre-built domain skills (refund eligibility, claim triage, scheduling, escalation logic) with sample evals.
- **Tools** — pre-built MCP tools and HTTP integrations (Salesforce, Zendesk, Stripe, Calendly, Twilio, etc.).
- **Eval suites** — public eval suites (HELM-derived, customer-service benchmarks, voice-agent benchmarks).
- **Templates** — full-agent starters.
- **KB connectors** — connectors to specialized sources (industry-specific knowledge bases).

### 27.2 The discovery surface

A clean grid, faceted filters (by category, by integration, by author, by rating). Each item: a card with a 1-line description, an installer count, an avg rating, the author. Clicking opens a detail page with a full description, screenshots, sample evals, version history, license.

Installation is one click. Uninstallation is one click. Everything is auditable.

### 27.3 Enterprise marketplace governance

For enterprise workspaces, an admin can curate which marketplace items are installable. The admin sees which workspaces have which items installed. License compliance is tracked.

---

## 28. The five north-star scenarios

End-to-end journeys that prove the product. We rehearse these regularly.

### 28.1 "Maya migrates from Botpress in an afternoon"

Maya is a senior engineer at a mid-sized e-commerce company. They run a customer support agent on Botpress with three flows, four intents, two integrations (order lookup, shipping status), and a KB sourced from their help center. They want off Botpress because they need voice and better evals. She has heard about Loop.

- **0:00** — Maya signs up with Google SSO. Studio loads.
- **0:15** — She picks "Import from Botpress." Pastes her Botpress Cloud API token.
- **2:00** — The Atelier finishes parsing. She lands in the three-pane review. Source on left (her three flows). Loop on right (mapped graph). Middle column shows 23 items — 15 advisory, 8 needing decisions.
- **2:00–25:00** — She works through the 8 decisions. The chunker changed; top-3 retrieval differs in 12 of 200 cases. She accepts the change after viewing the diff (the new chunker is better on long FAQ entries). She maps two missing entities by hand. She accepts the rest.
- **25:00** — The parity harness runs against her last 200 production conversations. 184 are identical. 12 differ because Loop's chunker found a better answer (regression review confirms). 4 differ because of an old Botpress bug she did not know about (Loop now has the right answer).
- **45:00** — She reviews the eval scorecard. 96/100 cases pass. She fixes the 4 failing cases by tweaking a prompt. Eval re-runs in 25 seconds. 100/100.
- **1:00:00** — She turns on voice. Picks Deepgram + ElevenLabs. Tests. Latency budget green.
- **1:30:00** — She opens the Pipeline. Promotes to staging. The team's reviewer gets a notification, opens the diff, approves.
- **2:00:00** — She moves the canary slider to 5% of production. Drift watch is green for the next 30 minutes.
- **3:00:00** — She moves the slider to 100%. Migration complete. Botpress contract renewal: declined.

This scenario is the test of the Migration Atelier. We rehearse it monthly with real customer data.

### 28.2 "Diego ships a voice phone agent in 25 minutes"

Diego runs a small dental practice. He wants a voice receptionist that answers the phone, schedules, and reschedules.

- **0:00** — Signs up.
- **0:30** — Picks the "Voice receptionist" template. Canvas loads with the agent, KB seeded with sample office hours, calendar tool wired to mock.
- **3:00** — Replaces the mock calendar with his Google Calendar (one-click OAuth). KB now has his actual office hours and address.
- **6:00** — Tests in voice mode (mic in browser). Latency feels good. Schedules a fake appointment; verifies it lands in his calendar.
- **9:00** — Picks a phone number. US, area code 415, voice + SMS. Twilio provisions in 30 seconds.
- **15:00** — Calls the number from his cell. Schedules a real appointment. Hangs up. Verifies.
- **20:00** — Sets up after-hours behavior with one node addition.
- **25:00** — Done. Agent is live.

This scenario is the test of the Voice Stage and the template system.

### 28.3 "Priya investigates why the agent picked the wrong tool"

Priya is on the Loop team at a payor (insurance). A claims adjuster reported that an agent escalated a routine claim that should have auto-approved.

- **0:00** — Priya opens the inbox. The escalated conversation is there. She clicks in.
- **0:30** — Reads the transcript. The agent called `manual_review` instead of `auto_approve`. She clicks the trace span for that turn.
- **1:00** — Inspector shows the LLM call. Why did it pick `manual_review`? The prompt mentioned "complex case" because the user said the word "appeal." She sees the prompt logic.
- **2:00** — She forks from that turn. On the fork, she edits the classifier to handle "appeal" without flagging "complex." Re-runs the turn. Now `auto_approve` fires. Diff is clean.
- **3:00** — She saves the original turn as an eval case (expected: auto_approve). The eval suite runs. 100% pass.
- **5:00** — She opens the Pipeline. Promotes the change to staging. Her senior approves. Canary at 10%. Drift watch green.
- **15:00** — Promoted to 100%. The original conversation in the inbox is closed with a note linking to the fix.

This scenario is the test of the trace + fork + eval loop.

### 28.4 "Acme platform team rolls out a change with 4-eyes review"

Acme Bank's platform team runs 14 agents across 6 product lines. They have strict change controls.

- **0:00** — Sam (a builder on the platform team) opens the canvas for the "loan FAQ" agent on a branch.
- **15:00** — Sam edits a prompt to better handle escrow questions, adds a new KB source (revised escrow PDF), updates two eval cases.
- **20:00** — Sam clicks Promote → prod. The Pipeline opens. The diff, eval delta, cost delta are visible. Two checkboxes are red: "approver required (1 of 2)" and "compliance review required."
- **20:30** — Sam clicks Request Approval. Selects approvers from a list (the two senior engineers on the platform team). Adds a note describing the change. Submits.
- **21:00** — Approver 1 (Lin) gets a Slack notification (configured org-wide). Clicks through. Reviews the diff. Comments inline on a node ("looks good but please add a regression case for case-insensitive matching"). Sam adds the case. Lin approves.
- **22:00** — Approver 2 (compliance reviewer Ben) gets notified. Reviews. Approves with a note.
- **22:30** — Sam promotes. Canary at 1%. Cost dashboard shows new cases passing. Sam moves the slider to 100% over 24 hours.
- **24:30:00** — The audit log entry: "agent loan-faq, version v42 → v43, promoted by sam@acme, approved by lin@acme + ben@acme, 4-eyes gate satisfied, eval delta +2 cases (passing), cost delta -3% per turn." Exportable as compliance evidence.

This scenario is the test of approval workflows + audit + the enterprise trust posture.

### 28.5 "An operator handles a real-time escalation"

It's 2 PM on a Tuesday. The dental-practice voice agent (Diego's) couldn't handle a complicated request.

- **0:00** — In the inbox at the practice's front desk, a row appears: "user_call_4172, voice, escalation: tool failed, wait time 18s."
- **0:05** — The receptionist (also named Maya here) clicks in. The call is still live. She sees the transcript so far. The agent had been trying to schedule but the calendar tool returned an error.
- **0:10** — Maya clicks "Take over." The agent goes silent. Maya types: "Hi, this is Maya from the front desk. I see we had a hiccup. How can I help?" The TTS speaks her words to the caller.
- **0:30** — She handles the call. Reschedules manually. Apologizes for the delay.
- **1:30** — Hangs up. Studio prompts: "Save this conversation as an eval case with your resolution as the expected outcome?" Maya clicks Yes. The case is named auto-titled.
- **2:00** — She goes about her day. Later, when the team reviews the inbox, they see the calendar tool had a transient outage. They add a fallback path. The eval Maya saved becomes a test.

This scenario is the test of the inbox + HITL + the eval-from-production loop.

---

## 29. The relationship to the legacy implementation baseline

The legacy implementation baseline ([`90_LEGACY_IMPLEMENTATION_UX_BASELINE.md`](90_LEGACY_IMPLEMENTATION_UX_BASELINE.md)) is a deliverable foundation: trace-centric, engineer-first, opinionated against drag-and-drop. It is now historical/reference material beneath the canonical target standard.

This document is what we steer toward. The two are not in conflict; they describe different time horizons.

Where this doc supersedes the baseline (north-star tensions):

| Baseline stance | North-star evolution |
|---|---|
| "No drag-and-drop flow editor" | A visual canvas exists, **isomorphic to code**, lossless round-trip. The canvas is not an alternative to code; it is a view of code. Builders without Python keep their feet on the canvas; engineers ignore the canvas and write code. Both edit the same source. |
| "Engineers first; Studio reads, observes, helps debug" | Engineers and builders both first. Studio reads, observes, debugs, **and authors**. Authoring is a peer to debugging, not a separate product. |
| "Studio is desktop-first; minimal mobile for inbox" | Same — but tablet gains read-mostly screens, large displays gain triple-pane, and the canvas commits to keyboard-first a11y at AAA. |
| "Cost dashboard breakdown — needs user research" | Baked in by default; covered by the Observatory. |
| "Eval suite authoring UI in Studio vs. code-only" | Both. Authoring inside Studio is a first-class surface. Code-defined suites continue to work. |

What the baseline owns that is not duplicated here:

- The trace waterfall design (we adopt it verbatim — §3.4 in the baseline is correct and beautiful).
- The error-state copy library — adopt verbatim, extend as needed.
- The component library — adopt verbatim, extend as needed.
- The keyboard shortcut catalog — adopt verbatim, extend (see §18.8).

This north-star does not invalidate any of the baseline's work. It expands the persona aperture to include builders and enterprise builders, adds the canvas/code duality, the Migration Atelier, the multiplayer story, the enterprise governance surfaces, and the visual language refinements.

---

## 30. What we will not build (yet)

Discipline matters. We will not, at any point in the first 18 months:

- Build a marketing website inside Studio (no "share" CMS).
- Build a customer-facing chat product (we make the agents; we do not host the chats outside our customers' channels).
- Build a no-code "publishing" surface for non-developers (the canvas is the publishing surface; we do not split the product).
- Build a learning-management or training surface for human agents.
- Build a survey or NPS tool.
- Build a CRM, an ESP, a CDP, or any of the adjacencies.

We will refer customers to specialized tools and integrate well with them. We are an agent runtime and a builder studio. We are not the everything-platform.

---

## 31. The measurement

A north-star UX is only real if we measure it. The user-facing metrics we commit to track and publish (internally) every week:

- **Time-to-first-turn.** Median, p95, p99. Across new users by acquisition source.
- **Time-to-first-deploy.** Median, p95, p99. Per persona segment.
- **Migration success rate.** % of started imports that result in production cutover within 14 days.
- **Edit-to-effect latency.** p50, p95. Per edit kind.
- **Eval-suite run latency.** p50, p95. Per suite size.
- **Trace open latency.** p50, p95.
- **Inbox time-to-take-over.** p50, p95.
- **Promotion approval cycle time.** p50, p95. Enterprise plans.
- **Crash-free session rate.** ≥99.95%.
- **a11y CI gate pass rate.** 100% release-on-release.
- **NPS, weekly cohort.** Builders and enterprise-builders separately.

Targets are not in this doc; they live in a separate scorecard reviewed monthly. But the metrics are this doc's contract: if we are not measuring them, we have not built the product this doc describes.

---

## 32. How this doc evolves

This doc is alive but not casual. Edits are PRs. PRs require:

- A design lead approval.
- A founding-eng approval.
- A linked customer signal where the change is customer-driven.
- A linked metric where the change is metric-driven.

Sections may be split into sibling docs as they grow. The persistent reference is this doc's table of contents and §0 (the one-sentence north-star). Those two should remain stable as the product matures; everything else is fair game.

---

## 33. In-product help, feedback, telemetry

A user should never have to leave Studio to get help, ask a question, or tell us we are wrong. The path is short and visible.

### 33.1 Help

`?` opens a help surface that has, in order:

- A search box across our docs, runbooks, and known-issues feed.
- The keyboard shortcut catalog for the current screen, with hover-to-highlight on the actual button.
- A "What is this?" mode — `Esc` to exit. With it on, hovering anything in Studio reveals a 1-2 sentence explainer + a deep link to docs.
- A "Show me" affordance for selected primitives (a fork, a promotion, an eval). Click → a 30-second screencast plays in a corner card. Closeable, never autoplays sound.

Docs open in a slide-over within Studio for short articles, and in a new tab for long-form (architectures, runbooks). The slide-over keeps the user in context.

### 33.2 Feedback

A persistent `Feedback` chip in the topbar (collapsed to icon by default; expandable by user preference). Click it for:

- **Report a bug** — pre-fills the request ID, trace ID, and a copy-pastable debug bundle. Optional screen recording (last 30 seconds, locally captured, user-confirmed before upload).
- **Request a feature** — short form, voted-on internally, with public-roadmap visibility (linked).
- **Just tell us something** — a freeform field, no shape. Goes to a real human at Loop.

We commit to a 24-hour SLA on every feedback submission for paid plans; first-touch within 5 business days for free plans. The user gets a confirmation in their notification well when their feedback is received and again when it is acted on.

### 33.3 Talk to support

The same chip carries a `Talk to support` button. For paid plans this opens a chat with a Loop support engineer, scoped to the workspace and pre-loaded with recent context (last 10 minutes of the user's actions, the current screen, recent errors). For enterprise plans, a named support contact is shown with availability.

For free plans, the same button opens an asynchronous channel (community forum or email).

The product never gates support behind a self-serve maze. If a user wants to talk to a human, they get one click.

### 33.4 Telemetry consent

We collect product telemetry to make Studio better. We are honest about what and why.

A first-run consent screen, repeated annually:

- **What we collect by default** — anonymous usage events (which screens you opened, which shortcuts you used, which errors you hit), aggregated. Never the contents of prompts, messages, KB chunks, or traces.
- **What we collect with consent** — high-fidelity session recordings (mouse paths, click positions; no DOM content) for product research. Off by default. Opt-in by user; deletable on request.
- **What we never collect** — your customer data, your prompts, your secrets, your KB content, your traces. Those stay in your workspace and your data plane.

The consent screen has a "What is this?" link to a plain-language explainer. Granular toggles. A "decline all" button that does not degrade the product (it only disables our ability to learn from you).

### 33.5 Status, incidents, and the public

A `System status` link in the help surface goes to a public status page. During incidents, the status footer (§3.3) renders red and the notification well surfaces the incident with a one-line summary, an ETA where available, and a permalink to the post-incident report when published.

We never quietly recover from incidents. If your workspace was affected, you receive an event in the well after the all-clear, with a link to the incident report.

---

## Appendix A — Glossary

- **Agent** — a unit of behavior, addressable by name, versioned. Composed of triggers, nodes, tools, KB, evals.
- **Branch** — a working line of changes, versioned, mergeable.
- **Canary** — a deploy at less than 100% traffic.
- **Canvas** — the central editing surface, graph view of an agent.
- **Changeset** — a branch under review, with a diff and approvers.
- **Eval case** — a single input + expected outcome + scorers.
- **Eval suite** — a named collection of eval cases.
- **Fork** — a new branch starting from a specific turn, with conversation state restored.
- **Glass box** — the property that every decision the agent makes is one click from a citation.
- **Hot reload** — edits propagate to the next turn without redeploy.
- **Inbox** — the operator console for HITL.
- **Migration Atelier** — the importer + parity harness for porting from another platform.
- **Multiplayer** — concurrent collaborative editing of the same agent.
- **Project** — a collection of agents within a workspace.
- **Promotion** — a deploy from one environment to a higher one.
- **Scratchpad** — the per-conversation typed state shared across nodes.
- **Skill** — a reusable cluster of nodes with prompts, tools, KB.
- **Span** — a unit of work in a trace (LLM call, tool call, retrieval, etc.).
- **Studio** — the web product (the surface this doc designs).
- **Sub-agent** — an agent invoked by another agent, with a typed contract.
- **Timeline** — the bottom bar showing all turns in the current preview session.
- **Tool** — a capability the agent may call, with a typed input/output schema.
- **Trace** — the full record of an agent's processing for a single turn.
- **Turn** — one user-input → agent-output cycle.
- **Workspace** — the top-level tenant boundary.

---

## Appendix B — The product oath

Every screen we ship will pass these checks before it goes live:

- [ ] The agent on the canvas is hot. Edits propagate to the next turn within 150ms.
- [ ] Every metric that affects this screen is visible (cost, latency, quality).
- [ ] The empty state is illustrated, copy is in product voice, CTA is concrete.
- [ ] The loading state is a skeleton or progressive — never a full-page spinner.
- [ ] The error state has a code, a cause, an action.
- [ ] Every action has a keyboard shortcut. Every shortcut is in the cheatsheet.
- [ ] Tab-only navigation works. Focus is visible. Screen-reader summary is meaningful.
- [ ] Reduced motion respected.
- [ ] Multiplayer cursors do not break the layout.
- [ ] The screen has a place in the IA (canvas, atelier, knowledge, tools, voice, conductor, pipeline, observatory, inbox, or one of the enterprise screens). If not, it does not ship.

If a screen cannot pass these, we do not ship it. We build less, finish what we build, and ship things that feel inevitable.

---

## Appendix C — Product copy library

The voice of Studio in concrete strings. Use these verbatim where they fit; mirror their shape elsewhere.

### C.1 Voice principles

- **Direct, never apologetic.** "Hard budget cap hit," not "Sorry, but…"
- **Specific, never vague.** "OpenAI returned 503 after 3 retries," not "Something went wrong."
- **Actionable, never dead-end.** Every state names what to do next.
- **Plain, never clever.** "Promote v18 to production" beats "Ship it!"
- **Calm, never urgent (unless urgent).** Routine succeeds quietly. Alarms are loud and rare.
- **First-person plural ("we") when the system is the actor; second-person ("you") when the user is.**
  - "We failover to Anthropic when OpenAI is unavailable."
  - "You can rebind the BYOK key in Settings → Encryption."

### C.2 Buttons

| Surface | Verb | Avoid |
|---|---|---|
| Promotion confirm | `Promote v18` | "Begin deployment process" |
| Save eval case | `Save as eval` | "Add to test library" |
| Rollback | `Roll back to v17` | "Restore previous" |
| Take over conversation | `Take over` | "Intervene" |
| Release back to agent | `Release to agent` | "Done with conversation" |
| Run preview turn | `Send` | "Submit message" |
| Stop generation | `Stop` | "Cancel" |
| Share artifact | `Share` | "Copy link" |
| Approve changeset | `Approve` | "Looks good to me" |
| Request changes | `Request changes` | "Block this PR" |
| Decline | `Decline` | "Reject" |
| Delete (soft) | `Move to recycle bin` | "Delete forever" |
| Delete (hard) | `Delete permanently` | "Yes, delete it!" |
| Invite member | `Invite` | "Send invitation" |

### C.3 Empty states

| Screen | Headline | Body | CTA |
|---|---|---|---|
| Workspace, no agents | Your workspace is ready. | Start with an agent. Import one, use a template, or start blank. | New agent · Import · Templates |
| Canvas, no preview yet | Your agent is hot. | Say hi. | (focus the preview) |
| Timeline, no turns | Turns will appear here. | Send a message to your agent in the preview. | (none) |
| KB, no sources | Knowledge starts with a source. | Connect Notion, upload files, or paste a URL. | Add source |
| Tools, no tools | Tools are how your agent acts. | Add a built-in or connect an MCP server. | New tool · Browse marketplace |
| Evals, no suite | Save any turn as an eval to start a suite. | (none — wait for a turn) | (none) |
| Inbox, all clear | All quiet. | No escalated conversations right now. | (none) |
| Audit log, no events | No events in this date range. | Try a wider time range or different filters. | Reset filters |
| Marketplace, no installed | You haven't installed anything yet. | Browse skills, tools, eval suites, and starters. | Browse |
| Approvals queue, empty | Nothing pending. | When teammates request review, requests appear here. | (none) |

### C.4 Errors

The shape: `Headline. One sentence on why. [Retry] [Copy debug] [Read more]`. Each error has a stable code.

| Code | Headline | Body |
|---|---|---|
| LOOP-RT-403 | Rate limit hit. | Workspace burst quota exceeded. Wait a few seconds, or [raise the cap](#). |
| LOOP-GW-101 | No upstream LLM configured. | Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in workspace secrets. |
| LOOP-GW-301 | OpenAI is degraded. | We're failing over to Anthropic. Cost and latency may shift. [Status page](#). |
| LOOP-CP-414 | Trace not yet available. | Traces appear ~5 seconds after a turn completes. [Refresh](#). |
| LOOP-CP-509 | Hard budget cap hit. | $500 / month reached. New conversations return `budget_exhausted`. [Edit cap](#). |
| LOOP-TL-204 | Tool `lookup_order` timed out. | The tool did not respond within 60s. Agent received an error and continued. [View logs](#). |
| LOOP-KB-303 | KB chunk not found. | The chunk was deleted or reindexed. [Re-run retrieval](#). |
| LOOP-AC-601 | Permission denied. | Your role does not allow this action. Ask an admin, or [request access](#). |
| LOOP-AC-602 | Workspace residency locked. | This workspace cannot move data outside `eu-west-2`. The action you tried would have. |
| LOOP-IM-450 | Botpress import partially mapped. | 8 items need your eyes. Review them in the Migration Atelier. |
| LOOP-EV-720 | Eval suite did not finish. | 2 of 50 cases timed out. Re-run, or [view partial results](#). |
| LOOP-VC-110 | Voice transport degraded. | Latency budget exceeded for the last 30s. Try a different provider, or [view diagnostics](#). |
| LOOP-MP-880 | Concurrent edit conflict. | Maya edited this node 14s ago. [View her edit](#) or [merge both](#). |

### C.5 Success / status

Quiet by default. No exclamation, no "Awesome!"

- "Promoted v18 to production. Canary at 1%."
- "Eval suite re-ran: 100/100 pass."
- "Branch `import/botpress/2026-05-06` ready for review."
- "Maya approved the changeset."
- "KB indexed: 38 chunks, 12s."
- "Failover to Anthropic engaged. Cost +18%."
- "Rollback to v17 complete."

### C.6 Onboarding

The three doors panel:

> **Welcome to Loop.**
> Studio is the agent runtime for builders who care about cost, latency, and quality. Three ways to start:
>
> **Import** an agent from another platform — Botpress, Voiceflow, Stack AI, OpenAI Assistants, and more.
>
> **Use a template** — a working agent with mock tools, sample knowledge, and an eval suite.
>
> **Start blank** — describe what you want; the co-builder will scaffold.

The first message in the preview, after a template loads:

> Hi. I'm a support agent. I can look up orders, check shipping, and escalate to a human. Try asking me about an order.

The first toast after a template loads:

> Your agent is hot. Edits propagate to the next turn within 150ms. Try changing my prompt while I'm running.

### C.7 Voice prompts (TTS)

For voice agents, the default barge-in tone, hold messages, and acknowledgments:

- "Got it." (acknowledgment after intent classified)
- "One moment." (before a tool call >1s)
- "Sorry, I'm having trouble with that. Let me get someone." (escalation)
- "Connecting you now." (handoff to operator)

Each is overridable per agent. The defaults are calm, brief, and competence-cueing.

### C.8 The trust palette in copy

When chips appear, they are accompanied by short hover labels:

- **Live** — "Currently serving production traffic."
- **Canary** — "Receiving 10% of production traffic. 2h remaining in canary window."
- **Pending review** — "Waiting on Lin and Ben (4-eyes required)."
- **Approved** — "Approved by Lin (2h ago)."
- **Mocked** — "Returning recorded responses. Switch to live in Tool Bench."
- **Stale** — "Last synced 3 days ago. Sources may have changed."
- **Deprecated** — "Replaced by `refund-eligibility-v2`. Will be removed on 2026-06-15."
- **Needs your eyes** — "We could not auto-decide. Open the Atelier item to choose."
- **Unreviewed in prod** — "This change reached production without review. Tap to investigate."
- **Read-only** — "Your role allows viewing, not editing."

### C.9 What we will not write

- "Oops!" / "Something went wrong."
- "Click here."
- "Please be patient while…"
- "Awesome!" / "Sweet!" / "🎉"
- "Are you sure you want to do this?"
- "We hope you're enjoying Studio!"
- "Pro tip:"
- "Coming soon."
- "We've sent you an email." (without saying which email and what it contains)
- "Loop is the future of AI agents." (any product copy that sounds like marketing)

The product earns the next session by being useful, not by talking about itself.

---

*End of document.*
