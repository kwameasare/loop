# Loop Studio - Canonical Target UX Standard

**Status:** CANONICAL TARGET STANDARD v1.1  
**Owner:** Product + Design + Studio Engineering  
**Primary customer:** builder and enterprise builder  
**Authority:** this is the true target UX/UI standard for Loop Studio. If another UX document conflicts with this one, this document wins unless leadership explicitly amends it.

**Demoted source files:** `90_LEGACY_IMPLEMENTATION_UX_BASELINE.md`, `99_SUPERSEDED_CODEX_OPTIMAL_UX_DRAFT.md`, and `99_SUPERSEDED_CLAUDE_OPTIMAL_UX_DRAFT.md` are historical/reference material only.

Loop Studio is the production-grade place to build, migrate, test, ship, observe, and govern AI agents. It should feel like a live agent in a glass box: always inspectable, always explainable, and always under the builder's control.

The builder is the customer. Operators, admins, security teams, and end users matter because they shape production trust, but the product wins or loses on whether a serious builder can create useful agent behavior, understand why it happened, prove it works, control its risk, and move from older platforms without a rewrite.

This is not a chatbot builder. It is an agent engineering cockpit with the tactility of a premium creative tool and the discipline of enterprise infrastructure.

---

## How To Read This

This document is intentionally long. It answers one question: what is the best possible Loop Studio?

Use these paths:

1. **10-minute read:** Product Promise, Principles, Information Architecture, Migration Atelier, Minimum Lovable Slice.
2. **30-minute read:** Add Personas, Workbench, Trace Theater, Builder Control Model, Enterprise UX, Visual Language.
3. **Reference read:** Use the table of contents below and jump by section.

This document is aspirational, but it is not loose. A target standard is useful only when it can guide tradeoffs.

---

## Table Of Contents

| Section | Name | What it answers |
|---:|---|---|
| 1 | Product Promise | What must Studio help builders know? |
| 2 | North-Star Statement | What should Studio feel like? |
| 3 | Principles | What rules govern every screen? |
| 4 | Personas And Journeys | Who is this for, and what must happen early? |
| 5 | Information Architecture | How is the product organized? |
| 6 | Studio Shell | What is always present? |
| 7 | Agent Workbench | What is the primary builder surface? |
| 8 | Agent Map And Code | How do visual and code editing coexist safely? |
| 9 | Simulator And Conversation Lab | How do builders test quickly? |
| 10 | Trace Theater | How do builders understand behavior? |
| 11 | Behavior Editor | How are instructions, policies, and code shaped? |
| 12 | Tools Room | How do tools become safe agent capabilities? |
| 13 | Knowledge Atelier | How does KB become inspectable and measurable? |
| 14 | Memory Studio | How do builders control what agents remember? |
| 15 | Eval Foundry | How does production become test coverage? |
| 16 | Voice Stage | How does voice become a first-class channel? |
| 17 | Multi-Agent Conductor | How do agents compose safely? |
| 18 | Migration Atelier | How do builders port from Botpress and others? |
| 19 | Deployment Flight Deck | How do builders ship safely? |
| 20 | Observatory | How do builders operate production? |
| 21 | Inbox And HITL | How do humans intervene and teach the system? |
| 22 | Cost And Capacity | How do builders stay financially safe? |
| 23 | Builder Control Model | How does state, undo, preview, and evidence work? |
| 24 | Enterprise Builder UX | How does Studio satisfy governance? |
| 25 | Collaboration | How do teams build together? |
| 26 | AI Co-Builder | How does AI assistance stay consentful? |
| 27 | Command, Search, And Sharing | How do experts move quickly? |
| 28 | Visual Language | What should the product look and feel like? |
| 29 | Motion, Tactility, And Sound | How does Studio feel alive? |
| 30 | Accessibility And Inclusion | How does every builder use it well? |
| 31 | Responsive Modes | What works on desktop, tablet, and mobile? |
| 32 | States And Copy | How do loading, errors, empty states, and degraded states work? |
| 33 | Onboarding | What happens in the first minute, week, month, and quarter? |
| 34 | Marketplace | How do skills, tools, templates, and evals grow? |
| 35 | Help, Feedback, And Telemetry | How does Studio earn trust after launch? |
| 36 | North-Star Scenarios | What end-to-end moments prove the product? |
| 37 | Screen Quality Bar | What must every screen pass? |
| 38 | Minimum Lovable Slice | What should we build first if scope is tight? |
| 39 | Measurement | How do we know the UX is real? |
| 40 | External Format Notes | What import assumptions must be verified? |
| 41 | Anti-Patterns | What will we not build? |
| 42 | Evolution | How does this doc change? |
| Appendix A | Glossary | What words mean one thing only? |
| Appendix B | Product Oath | What must ship-quality screens satisfy? |
| Appendix C | Copy Library | What does Studio sound like? |

---

## 1. Product Promise

Loop Studio helps a builder answer seven questions faster than any competing platform:

1. What does this agent do?
2. What can it access?
3. Why did it behave that way?
4. Is the answer grounded, safe, and useful?
5. What will this cost at scale?
6. Can I deploy without breaking production?
7. Can I leave my old platform without losing behavior?

Every screen, action, and empty state must help answer one of those questions. If a screen cannot do that, it should not exist.

---

## 2. North-Star Statement

Studio is a live agent in a glass box.

That means:

- the agent can be tried immediately in a safe preview environment
- every prompt, tool call, retrieval, memory write, eval, cost, and deploy gate is visible
- every artifact can be inspected and edited from where it appears
- every high-impact edit has preview, diff, validation, evidence, approval when required, and rollback
- migration from Botpress and similar platforms is measurable, reversible, and provable
- production is never touched casually

"Live" does not mean uncontrolled production mutation. "Live" means the builder's development loop is hot and responsive. Protected environments still require explicit state changes, evidence, eval gates, approvals, and rollback.

---

## 3. Principles

### 3.1 Builder First

The primary user is building a production agent, not admiring a canvas. Studio must serve engineering judgment: inspectability, control, repeatability, debugging, fast iteration, and clean handoff to code.

### 3.2 Agent-Native, Not Flow-Native

Studio may include visual maps, graphs, and canvas-like views, but the destination model is not a legacy flowchart. The first-class primitives are agents, behavior, tools, knowledge, memory, evals, channels, budgets, traces, and deploys.

Visual editing is a view over agent primitives, not the product's center of gravity.

### 3.3 Glass Box, Never Black Box

No hidden prompts. No mystery tool calls. No vague "AI reasoning" panel. Every important agent decision is one click from evidence: trace spans, retrieved chunks, memory diffs, tool arguments, model inputs, policy checks, cost math, and eval results.

### 3.4 Control Is The Luxury

The best builder UX is not the fewest clicks. It is knowing what will happen before a change touches production. Every high-impact action must show scope, effect, risk, and recovery.

### 3.5 The Safe Path Is The Fast Path

The easiest route through Studio should naturally create evals, inspect traces, reconnect secrets correctly, run preflight, canary deploy, and preserve rollback.

Builders should not need discipline to do the right thing. The product should carry them there.

### 3.6 Cost, Latency, And Quality Are Co-Equal

Optimization is not an ops mode. Every major surface should show quality, cost, and latency together when they affect a decision.

### 3.7 Migration Is A Product, Not A Script

For many customers, import is the front door. Migration must be visual, guided, auditable, parity-tested, and reversible. The goal is not to reproduce the old diagram. The goal is to preserve business behavior in a better agent-native system.

### 3.8 Friendly Means Guided, Not Vague

Friendly UX reduces cognitive load without hiding the machinery. Use good defaults, examples, progressive disclosure, next-best actions, precise labels, and concrete errors.

### 3.9 Calm Power

Studio should be quiet by default, exact under pressure, and delightful when the builder gains confidence. It should feel alive, not noisy.

### 3.10 Code And Visual Views Are Isomorphic Where They Exist

When Studio offers a visual editor, it must round-trip with code and config. No lock-in to graph mode. No divergence between visual truth and code truth.

### 3.11 Production Conversations Become Evals

No team writes enough synthetic tests by hand. Production turns, simulator runs, operator resolutions, migration transcripts, and failures should become eval cases in one click.

### 3.12 Real Names On Real Things

Use canonical product nouns consistently: agent, turn, trace, tool, memory, eval, deploy, workspace, channel, canary. Do not invent new vocabulary per screen.

### 3.13 Discipline Before Drama

No marketing voice inside production surfaces. No upsell interruptions. No celebration for unproven progress. Celebrate proof, not hope.

### 3.14 Excitement Comes From Seeing More

The most exciting Studio moments should be inversions, measurements, or time travel:

- **Inversions:** answer the question builders did not know they could ask, such as "which production queries should have retrieved this chunk?"
- **Measurements:** replace intuition with evidence, such as sentence-level prompt telemetry and observed behavior maps.
- **Time travel:** let builders replay, scrub, fork, bisect, and compare agent behavior across versions, memories, tools, and future drafts.

Creative polish must increase builder confidence. If an idea only decorates state without revealing control, evidence, or consequence, it does not belong in the north star.

---

## 4. Personas And Journeys

### 4.1 Solo Technical Builder

Wants to import or scaffold an agent, wire tools, test quickly, and deploy without infrastructure drama. Values speed, clear errors, and code escape hatches.

### 4.2 Startup Product Engineer

Owns customer-facing agent behavior and production incidents. Needs traces, evals, cost controls, channel testing, deploy safety, and rollback.

### 4.3 Enterprise Builder

Builds agents inside governance constraints. Needs SSO, SCIM, RBAC, audit logs, environment promotion, secret handling, approval workflows, data residency, BYOK, migration evidence, and compliance artifacts.

### 4.4 Platform Team

Maintains many agents, tools, channels, and shared knowledge sources across teams. Needs reusable templates, private skills, policy controls, cost attribution, versioning, and workspace-wide observability.

### 4.5 Migration Lead

Owns the move from an incumbent platform. Needs import diagnostics, mapping confidence, parity testing, transcript replay, stakeholder reports, staged cutover, and rollback.

### 4.6 Operator

Monitors and takes over live conversations. Needs queue clarity, conversation context, trace access, agent silence controls, resolution capture, and eval-from-resolution.

### 4.7 Security And Compliance Reviewer

Approves sensitive changes. Needs readable diffs, evidence packs, audit trails, policy names, data residency proof, secret access logs, and exportable artifacts.

### 4.8 The First 60 Seconds

The first session offers three doors:

1. Import from another platform.
2. Start from a template.
3. Start blank with the AI co-builder.

Within 60 seconds of choosing a door, the builder should send a turn and see a streaming response in the preview.

### 4.9 The First 30 Minutes

The ideal first 30 minutes:

1. Create or import an agent.
2. See a complete agent profile with missing pieces highlighted.
3. Run one realistic simulated conversation.
4. Open the generated trace.
5. Turn that run into an eval case.
6. Connect or test one real tool.
7. Deploy to staging.
8. Understand what blocks production.

Docs deepen mastery. They should not rescue a confusing product.

### 4.10 The Enterprise First Day

The ideal enterprise first day:

1. Import an existing Botpress or comparable project.
2. Review inventory and source mapping.
3. Reconnect secrets through an approved vault flow.
4. Resolve the top migration gaps.
5. Run parity tests on historical transcripts.
6. Share a migration report with product, support, and security.
7. Stage the imported agent behind a canary.
8. Export the evidence package for review.

---

## 5. Information Architecture

Studio is organized around the builder's lifecycle:

```text
Studio
|
|-- Build
|   |-- Agents
|   |-- Behavior
|   |-- Tools
|   |-- Knowledge
|   |-- Memory
|   |-- Channels
|   |-- Templates
|
|-- Test
|   |-- Simulator
|   |-- Evals
|   |-- Replay
|   |-- Red team
|   |-- Fixtures
|
|-- Ship
|   |-- Versions
|   |-- Deployments
|   |-- Environments
|   |-- Canaries
|   |-- Rollback
|
|-- Observe
|   |-- Conversations
|   |-- Traces
|   |-- Tool calls
|   |-- Retrieval
|   |-- Memory writes
|   |-- Quality
|   |-- Cost
|
|-- Migrate
|   |-- Imports
|   |-- Mapping
|   |-- Parity
|   |-- Cutover
|   |-- Lineage
|
|-- Govern
    |-- Members
    |-- Roles
    |-- Secrets
    |-- Policies
    |-- Audit
    |-- Billing
    |-- Compliance
```

The stable navigation should expose the lifecycle verbs. Surface names like "Migration Atelier" and "Trace Theater" may appear as product moments, but the main IA should remain builder-legible: Build, Test, Ship, Observe, Migrate, Govern.

Named surfaces are modes inside the six verbs, not a second competing navigation taxonomy. The product can be poetic in the work area; the spine must stay boringly findable.

---

## 6. Studio Shell

The shell has five permanent regions on desktop:

```text
+------------------------------------------------------------------------------+
| Topbar: workspace / project / agent / environment / branch / command / user   |
+--------------+---------------------------------------+-----------------------+
| Asset rail   | Main work surface                     | Live preview          |
|              | Agent workbench, trace, migration,    | Web, Slack, phone,    |
| Tools        | evals, deploy, dashboards             | WhatsApp, email       |
| Knowledge    |                                       | Cost, latency, trace  |
| Memory       |                                       | for current turn      |
| Evals        |                                       |                       |
+--------------+---------------------------------------+-----------------------+
| Timeline: turns, forks, eval captures, deploy events, migration checkpoints    |
+------------------------------------------------------------------------------+
| Status footer: data plane, control plane, gateway, background jobs, residency  |
+------------------------------------------------------------------------------+
```

### 6.1 Topbar

Shows:

- workspace
- project
- agent
- environment
- version or branch
- unsaved state
- presence
- command palette
- notification well
- user menu

The current environment and version must always be visible when an action could affect behavior.

### 6.2 Asset Rail

Contains reusable artifacts:

- tools
- knowledge sources
- memory policies
- eval suites
- channel fixtures
- prompts and behavior sections
- sub-agents
- skills
- secrets references
- templates

Drag-and-drop is useful, but every drag action must have a click or keyboard alternative.

### 6.3 Main Work Surface

The surface changes by task: workbench, trace, eval, migration, deploy, observatory, inbox, governance. It should support resizable panes and persistent inspectors.

### 6.4 Live Preview

The preview is a real simulator for the current safe environment. It switches channel constraints:

- web streaming
- Slack threading
- WhatsApp templates
- SMS character pressure
- email subject/body/attachments
- voice latency and barge-in
- custom webhook payloads

The preview is always clear about which environment, version, memory snapshot, knowledge snapshot, tools, and channel fixture it uses.

### 6.5 Timeline

Every meaningful event lands in the timeline:

- simulated turns
- production turns opened for replay
- forks
- eval captures
- tool tests
- knowledge ingestion
- migration mapping decisions
- deploy gates
- approvals
- rollback

The timeline is the user's session memory and the bridge from "what happened" to "make this a test."

### 6.6 Status Footer

The footer is a quiet trust surface:

- data plane health
- control plane health
- gateway health
- provider failover
- KB indexing progress
- eval run progress
- region and residency
- build version

The footer should be calm when healthy and unmistakable when degraded.

### 6.7 Notification Well

Notifications use three tiers:

| Tier | Meaning | Behavior |
|---|---|---|
| Calm | routine completion | quiet dot, grouped in well |
| Nudge | worth attention | count badge, no interruption |
| Alarm | action matters now | visible alarm treatment, routes to on-call if configured |

The well never auto-pops routine cards. The builder comes to it.

---

## 7. Agent Workbench

The Agent Workbench is the primary builder surface. It is not a flow editor. It is a structured cockpit for the agent's behavior, dependencies, evidence, and deploy state.

### 7.1 Workbench Anatomy

```text
+----------------------------------------------------------------------------+
| support-concierge   Draft v24   Staging   Unsaved changes    Run   Deploy  |
+-----------------+-------------------------------------+--------------------+
| Agent outline   | Main editor / simulator / diff      | Inspector          |
|                 |                                     |                    |
| Purpose         |                                     | Selection details  |
| Behavior        |                                     | Evidence           |
| Tools           |                                     | Risks              |
| Knowledge       |                                     | Actions            |
| Memory          |                                     | History            |
| Channels        |                                     |                    |
| Evals           |                                     |                    |
| Deploy          |                                     |                    |
+-----------------+-------------------------------------+--------------------+
```

### 7.2 Agent Profile

Every agent exposes:

- name and slug
- owner team
- purpose statement
- supported channels
- model aliases
- tool permissions
- knowledge sources
- memory policy
- budget caps
- escalation rules
- eval gates
- environments
- deploy state
- last production version
- draft changes

Each section shows:

- current config
- last changed by
- diff from production
- validation status
- quick test action
- linked trace/eval evidence

### 7.3 Agent Outline

The outline is a navigation and dependency map, not the primary logic model:

```text
User channels -> Agent behavior -> Tools
                             | -> Knowledge
                             | -> Memory
                             | -> Evals
                             | -> Deploy policy
```

For advanced users, the outline can expand into a graph/code composition view. The graph is agent-native and code-isomorphic; it must not become a Botpress-style flow-builder clone.

---

## 8. Agent Map And Code

Studio may include a visual map, but it must obey agent-native constraints.

### 8.1 Isomorphic Views

Two views of the same agent:

- **Profile view:** structured sections for purpose, behavior, tools, knowledge, memory, channels, evals, deploy.
- **Map view:** visual composition of triggers, routines, tools, KB lookups, sub-agents, policies, branches, and outputs.
- **Code/config view:** canonical source representation for advanced users.

Edits in one view must round-trip to the others without semantic loss.

The map is comprehension-first and instrumentation-first. It may support safe structured edits, but core behavior must remain legible through agent primitives, structured policies, evals, traces, and code/config. A builder who never opens the map should still be able to build, test, ship, and govern a serious agent.

### 8.2 Visual Map Rules

The map is allowed when it clarifies:

- dependencies
- data flow
- tool grants
- memory writes
- channel-specific behavior
- eval coverage
- deploy impact

The map is not allowed to become:

- a drag-and-drop flowchart as the main mental model
- a hidden DSL that diverges from code
- a place where business logic is locked away from version control

### 8.3 Inspector Panel

Selecting anything opens an inspector. The inspector never throws the user into a dead end.

Possible tabs:

- configure
- tools
- inputs
- outputs
- cost and latency
- eval coverage
- trace evidence
- code/config
- policy
- history

### 8.4 Hot Loop Semantics

Safe preview/dev-loop edits can apply immediately to the next relevant operation:

- prompt edits apply to the next preview LLM call
- tool schema edits apply to the next preview tool call
- map topology edits apply to the next preview turn
- model swaps apply to the next preview LLM call
- KB re-indexing appears when committed
- secret rotation applies to the next call using that secret

Protected environments do not inherit this freedom. Staging and production changes move through explicit object states, checks, approvals, and deploy events.

### 8.5 Fork From Here

Every turn can be forked:

1. Create an ephemeral branch.
2. Load exact agent state at that turn.
3. Restore conversation up to that point.
4. Let the builder edit behavior, tools, KB snapshot, model, or memory.
5. Re-run the next turn.
6. Show token, tool, retrieval, memory, cost, latency, and eval diffs.

This is how builders answer "what if?" without contaminating production.

### 8.6 Gesture Grammar

The same gesture means the same thing everywhere:

| Gesture | Meaning |
|---|---|
| Single click | select |
| Double click | open detail or descend |
| Right click | context menu |
| Long press | reveal tooltip and shortcut |
| Drag | move or attach |
| Drag to target | compose or attach |
| Hover | reveal affordances without layout shift |
| Cmd/Ctrl + click | multi-select or open in new tab |
| Shift + click | range select |
| Esc | close current transient surface |

No hidden gesture may be the only way to perform an action. No gesture deletes in one step.

### 8.7 Hazard Handling

Studio must name and handle hard cases:

| Hazard | Required behavior |
|---|---|
| two builders edit same object | conflict surfaced inline, diff and merge offered |
| prod call in flight while edit happens | in-flight call finishes on old version; next eligible call uses new deployed version |
| KB re-index in flight | old index remains until new index commits atomically |
| data plane degraded mid-edit | edits queue locally with clear degraded status |
| approver unavailable | request remains filed; escalation path shown |
| circular dependency | invalid drop rejected before graph enters bad state |
| stale approval after edit | approval invalidated and re-requested |
| lost session | draft, fork, inspector, and timeline restore |

---

## 9. Simulator And Conversation Lab

The simulator is the fastest path to confidence.

### 9.1 Multi-Channel Simulation

Support:

- web
- Slack
- WhatsApp
- SMS
- email
- voice
- custom webhook

Each channel simulation preserves channel constraints.

### 9.2 Test Controls

Every run can control:

- environment
- agent version
- model alias
- temperature
- tool allow/deny set
- mock vs live tool mode
- knowledge snapshot
- memory snapshot
- user fixture
- channel fixture
- budget cap simulation
- latency injection
- tool failure injection
- provider outage injection

### 9.3 Result View

Each run shows:

- response
- exact model input/output
- tool calls
- retrieved chunks
- memory reads/writes
- cost
- latency
- policy flags
- eval scorer results
- trace waterfall

One click creates:

- eval case
- regression fixture
- replay baseline
- bug report
- migration parity sample

---

## 10. Trace Theater

Trace Theater is the signature Loop experience. It should be visually distinctive, technically deep, and immediately useful.

### 10.1 Trace Summary

At the top:

- outcome
- total latency
- total cost
- provider and model
- tool count
- retrieval count
- memory writes
- eval score if attached
- deploy version
- channel
- environment

### 10.2 Waterfall

The waterfall shows:

- LLM spans
- tool spans
- retrieval spans
- memory spans
- channel spans
- voice spans
- sub-agent spans
- retries
- provider failover
- budget checks
- policy checks

Every span has label, duration, status, and keyboard access. Color is never the only signal.

### 10.3 Span Inspector

Selecting a span shows:

- inputs
- outputs
- raw payload
- normalized payload
- redaction view
- cost math
- retry history
- linked logs
- linked eval cases
- linked migration source
- linked deploy version

### 10.4 Explain Without Inventing

Trace explanations must cite concrete evidence:

Good:

```text
The answer changed because `refund_policy_2026.pdf` ranked above the older policy.
```

Good:

```text
Cost increased because the tool timeout caused two extra model iterations.
```

Bad:

```text
The model likely reasoned differently.
```

Generated explanations must quote trace facts, source chunks, eval scores, or config diffs. If the system does not know, it says so.

### 10.5 Replay And Diff

From any trace:

- replay with another model
- replay with locked historical memory
- replay with latest memory
- disable a tool
- swap knowledge snapshot
- vary temperature
- run attached evals
- replay against the current draft
- fork from any span or turn

Diffs show:

- answer
- token usage
- tool calls
- retrieval ranking
- memory writes
- cost
- latency
- eval score

### 10.6 Trace Scrubber

Trace Theater should have a scrubbable timeline, not only a static span list.

The builder can drag a playhead across a turn and see the right pane update frame by frame:

- active model context at that moment
- next tool call under consideration
- retrieval query and candidate chunks
- memory write before commit
- policy or budget gate being evaluated
- streaming response state
- current cost and latency accumulation

Playback modes:

- space toggles play/pause
- 1x, 2x, and 4x playback
- arrow keys step span by span
- `f` forks from the current frame
- `s` saves the frame as a scene or eval seed

The scrubber makes debugging feel like reviewing decision footage. It must still obey the glass-box rule: every frame is derived from recorded trace state, never invented animation.

### 10.7 Agent X-Ray

Agent X-Ray shows what the agent actually does in production, derived from traces.

Examples:

```text
Behavior section "Refund policy" is cited in 12% of turns.
Tool `lookup_order` is called from 6 routines; `escalate` calls it but never reads its result.
Sections 5-9 of the prompt have not influenced a visible output in 412 sampled turns.
The `appeal` branch fires in 0.3% of turns and contributes 18% of cost.
```

Every claim opens representative traces. No X-Ray claim may exist without a sample, query, metric, or config reference. This is dead-code detection for prompts, tools, retrieval, routines, and policies.

### 10.8 Honest Trace Identity

Every production turn should carry a durable trace identity:

```text
loop-trace-id: t-9b23
loop-version: v23.1.4
loop-snapshot: snap-7f3c
```

Operators can copy it. Regulated customers can request it where policy allows. Postmortems, support tickets, and audit reviews can point to a signed, replayable artifact instead of a memory of what the agent might have said.

---

## 11. Behavior Editor

The behavior editor gives builders three levels of control:

1. **Plain language:** fast purpose, role, tone, and constraints.
2. **Structured policy:** goals, refusal rules, escalation rules, compliance boundaries, tool permissions, memory rules, channel variants.
3. **Code/config:** exact source representation.

### 11.1 Inline Risk Flags

Flag:

- ambiguous instruction
- conflicting policy
- tool not granted
- tool too powerful
- missing eval coverage
- cost risk
- latency risk
- memory overreach
- PII risk
- unsupported channel behavior
- migration mapping uncertainty

### 11.2 Behavior Sections

Behavior should be organized into:

- purpose
- user promises
- answer style
- refusal policy
- escalation policy
- tool-use policy
- knowledge-use policy
- memory policy
- channel variants
- compliance boundaries

Each section shows diff from production and test coverage.

### 11.3 Prompt As Prose

Prompts deserve typography fit for careful writing:

- readable prose column
- role labels in the margin
- variables styled as distinct nouns
- token count in the gutter
- context-window meter
- change indicators
- linked eval coverage

The prompt editor should feel like a serious writing surface, not a raw textarea.

### 11.4 Sentence-Level Telemetry

Hover any sentence in a behavior section or system prompt and show observed production telemetry:

```text
Cited in 47 outputs over 7 days
Contradicted by model behavior in 3 sampled traces
Never visibly invoked in 412 sampled turns
Covered by 9 eval cases
```

Click opens representative traces and evals. If telemetry is unavailable, the tooltip says "No evidence yet" and offers to run replay, create evals, or sample production safely.

### 11.5 Semantic Behavior Diff

When a builder changes behavior, Studio explains the semantic diff in plain language before showing raw text diff:

```text
You removed the constraint that refund answers stay under 100 words.
You added a refusal boundary for medical advice.
You expanded `lookup_order` access from staging-only to staging and production.
```

The explanation must be grounded in the actual diff. No vague "the prompt changed" copy.

### 11.6 Style Transfer With Evidence

Builders can preview the same instruction style in controlled variants:

- formal
- concise
- empathetic
- expert
- channel-native

Each style variant shows eval delta, token delta, and representative output diff. Studio never implies that "nicer writing" is safer unless evals and traces support it.

---

## 12. Tools Room

Tools are how agents affect the world. They must feel powerful and safe.

### 12.1 Tool Catalog

Builders can add:

- MCP servers
- OpenAPI-backed APIs
- Python functions
- TypeScript functions
- webhooks
- database queries
- internal services
- marketplace tools

### 12.2 Tool Detail

Every tool exposes:

- schema
- permissions
- auth
- secrets
- sample calls
- test console
- mock and live implementation
- timeout
- retry policy
- rate limit
- side-effect classification
- audit classification
- owner
- usage history
- failure rate
- cost impact
- eval coverage

### 12.3 Tool Safety Contract

Before a production agent can call a tool, Studio answers:

- Can this mutate data?
- Can this spend money?
- Can this expose personal data?
- Which agents can call it?
- Which arguments are sensitive?
- What happens when it fails?
- How is it tested?
- How is it audited?

### 12.4 Mock vs Live

Mocks are first-class:

- dev defaults to mock
- staging can choose mock or live per environment
- prod defaults to live only when approved
- mocks can be recorded from real calls and edited
- evals should prefer deterministic mocks where possible

### 12.5 Instant Tool From Real Requests

A builder can paste:

- curl command
- browser DevTools network request
- OpenAPI fragment
- Postman collection
- webhook sample
- internal service example

Studio drafts a typed tool with schema, auth needs, side-effect classification, sample fixture, mock response, and eval stub. The generated tool is a draft until the builder reviews permissions, secrets, rate limits, and production grant.

---

## 13. Knowledge Atelier

Knowledge is not a file drawer. It is a retrieval system that must explain itself.

### 13.1 Sources

Support:

- files
- URLs
- crawled sites
- docs sites
- Notion
- Google Drive
- SharePoint
- Zendesk
- Intercom
- Slack
- databases
- custom sync jobs

Each source shows:

- freshness
- owner
- access rules
- sync status
- errors
- chunk count
- eval coverage
- sensitivity classification

### 13.2 Chunking, Visible

Builders can inspect:

- original document
- chunks
- overlap
- metadata
- embeddings
- source permissions
- version history
- cited usage

### 13.3 Retrieval Lab

Type a query, see:

- top-k chunks
- hybrid score breakdown
- semantic score
- keyword score
- metadata filters
- freshness
- citation preview
- missed candidates
- answer preview

Saved retrieval queries become retrieval evals.

### 13.4 Why Panel

Every retrieval in a trace has a Why panel:

- why this chunk ranked
- which query was sent
- which filters applied
- which candidates lost
- which document version answered
- whether the source is stale or deprecated

### 13.5 Readiness Report

After ingestion:

- likely answerable questions
- likely unanswerable questions
- duplicate sources
- stale sources
- missing metadata
- generated eval cases
- citation quality estimate
- sensitive data warnings

### 13.6 Inverse Retrieval Lab

Retrieval Lab must answer both directions:

- "What chunks would this query retrieve?"
- "What production queries should have retrieved this chunk but did not?"

For any chunk, the inverse view shows:

- nearby production queries
- missed matches ranked by closeness
- why the chunk lost
- whether metadata blocked it
- whether chunk boundaries hurt relevance
- whether reranking suppressed it
- whether prompt instructions discouraged citation

One-click repairs:

- re-chunk
- adjust metadata
- add source title or summary
- tune reranker
- add retrieval eval
- add instruction nudge

This converts "we have a KB gap" into a sortable, fixable list.

### 13.7 Embeddings Explorer

Offer an optional 2D projection of knowledge chunks for curation:

- clusters by topic
- outliers
- near-duplicates
- stale regions
- sensitive regions
- high-citation regions
- high-miss regions

Clicking a region opens chunks, source files, representative queries, citations, misses, and eval coverage. The explorer is a diagnostic view, not the only way to manage knowledge; all findings must be available as table/list views for accessibility.

---

## 14. Memory Studio

Builders should never wonder what the agent remembers.

### 14.1 Memory Explorer

Show:

- session memory
- user memory
- episodic memory
- scratch state
- retention policy
- last write
- writer version
- source trace
- confidence
- deletion controls

### 14.2 Memory Diff

Every turn can show memory changes:

```text
Before: preferred_language = unknown
After:  preferred_language = "English"
Source: user said "English is fine"
Policy: durable user memory
Trace:  turn_9b23
```

### 14.3 Memory Safety

Flag:

- secret-like values
- PII writes
- conflicting facts
- stale facts
- memory without source trace
- channel-specific facts stored globally
- durable memory created from weak evidence

### 14.4 Memory Controls

Builders can:

- approve memory classes
- block memory classes
- set retention
- delete user memory
- replay without memory
- replay with historical memory
- inspect memory impact on answers

---

## 15. Eval Foundry

Evals are a first-class build primitive, not a QA afterthought.

### 15.1 Eval Creation

Create evals from:

- manual cases
- simulator runs
- production conversations
- failed turns
- operator resolutions
- migration transcripts
- knowledge sources
- policy docs
- generated adversarial cases
- support macros

### 15.2 Suite Builder

Each suite has:

- intent
- owner
- required deploy gate
- scorers
- datasets
- fixtures
- cassettes
- thresholds
- historical trend
- flaky-case detection
- cost and latency budget

### 15.3 Result View

Show:

- what regressed
- what improved
- exact before/after output
- trace diff
- tool diff
- retrieval diff
- memory diff
- cost delta
- latency delta
- recommended fix

The builder should be able to fix a regression from the result screen.

### 15.4 Production Replay Against The Future

Any production conversation can be replayed against an uncommitted draft.

The view shows:

- production behavior
- draft behavior
- token-aligned answer diff
- tool-call diff
- retrieval diff
- memory diff
- cost and latency diff
- changed risk flags

Builders can select the 100 worst conversations from last week and run them against tomorrow's agent before promoting. Production traffic becomes the living regression suite without mutating production state.

### 15.5 First User Persona Simulator

Studio can generate a small, explainable persona run:

- journalist
- English-as-second-language user
- angry repeat customer
- accessibility-tool user
- adversarial user

Each persona runs realistic scenarios against the draft and groups failures by who was underserved, not just by technical category. Generated cases include provenance, prompt, model, and conversion path into evals. Enterprise workspaces can disable synthetic persona generation or restrict it to approved rubrics.

### 15.6 Conversation Property Tester

From any turn, builders can run "simulate 100 like this with variation."

Variation axes:

- typos
- tone changes
- paraphrases
- language switches
- missing context
- extra context
- adversarial phrasing
- channel constraints

Results cluster by failure mode and produce candidate eval cases. The starting production turn remains the anchor so synthetic coverage does not drift into abstract test theater.

### 15.7 LLM-Judge Tuning

Editing an LLM-judge rubric shows live previews on representative sample turns:

- judge score
- judge reasoning
- expected human rating when known
- disagreements
- examples that changed score

Builders tune the rubric until it matches their eyeball, then lock it behind versioning and audit. Judge changes have the same seriousness as behavior changes.

### 15.8 Scenes

Scenes are canonical production conversations turned into teaching and regression artifacts.

Examples:

- refund flow
- escalation
- legal threat
- hostile user
- accessibility request
- multilingual handoff
- multi-turn negotiation

Each scene includes representative turns, linked traces, expected behavior, known risks, and one-click replay against the current draft. New builders learn the agent through scenes; experienced builders cite scenes in reviews.

---

## 16. Voice Stage

Voice is a channel, not a separate product. Same agent, tools, memory, evals, budgets, and traces.

### 16.1 Voice Preview

The preview can switch to voice mode:

- push-to-talk
- live waveform
- transcript
- ASR spans
- TTS spans
- barge-in markers
- latency markers
- stage dots for ASR, agent start, TTS start

### 16.2 Voice Configuration

Builders can configure:

- voice provider
- ASR provider
- TTS provider
- language
- phone number
- transfer target
- hot keyword for human takeover
- recording policy
- latency budget

### 16.3 Voice Evals

Voice evals include:

- transcript accuracy
- latency
- interruption handling
- transfer behavior
- tone
- compliance phrases
- failed-call replay

### 16.4 Queued Speech Preview

During voice debugging, show the agent's queued speech before TTS begins when technically possible:

- faint transcript of the next utterance
- cancellable before audio starts
- linked to the LLM span that produced it
- visible latency from text-ready to speech-start

This is a debugging affordance, not an end-user production promise. It helps builders catch wrong speech before it leaves the speaker in dev and staging.

### 16.5 Voice Demo Share Link

Builders can generate a short-lived voice-only demo link:

- no login for invited stakeholder when policy allows
- browser mic test
- five-minute default cap
- per-link rate limit
- expiration
- optional whitelabel shell
- redaction and trace capture policy visible

Enterprise workspaces can require RBAC, SSO, watermarking, or approval before external demo links are created.

---

## 17. Multi-Agent Conductor

Multi-agent orchestration should be composable but inspectable.

### 17.1 Sub-Agents As Assets

Sub-agents appear alongside tools. Drag or add one into an agent and it becomes a node or routine with:

- contract
- inputs
- outputs
- owner
- version
- evals
- cost and latency
- trace spans

### 17.2 Hand-Off Contracts

Each hand-off defines:

- input schema
- output schema
- timeout
- fallback
- memory access
- tool grants
- budget

Violating a contract is explicit and traced.

### 17.3 Conductor View

Show:

- sub-agent topology
- active hand-offs
- cost by agent
- latency by agent
- failure points
- eval coverage
- shared memory use

---

## 18. Migration Atelier

Migration is the headline conversion surface. It should make switching cheaper, safer, and more measurable than staying.

### 18.1 Entry Point

First-run paths:

- Import from existing platform
- Start from template
- Connect Git repository
- Start blank

Import should never feel secondary.

### 18.2 Supported Sources

Source support has three labels:

| Label | Meaning |
|---|---|
| Verified | official export/API path confirmed and implemented |
| Planned | official or feasible path identified, not yet implemented |
| Aspirational | partnership, reverse mapping, or customer-supplied format required |

Initial target list:

| Source | Typical input | Status label | Loop goal |
|---|---|---|---|
| Botpress | `.bpz` export or connected workspace | verified/planned by importer stage | flows, KBs, actions, integrations, tables, variables, transcripts |
| Voiceflow | `.vf`, `.vfr`, project API | verified/planned by importer stage | intents, paths, variables, API blocks, knowledge, transcripts |
| Dialogflow CX/ES | agent export archive or cloud export | verified/planned by importer stage | intents, flows, routes, fulfillments, training phrases |
| Rasa | Git repo or project zip | verified/planned by importer stage | domain, stories/rules, NLU data, actions, endpoints |
| Dify | YAML DSL export | verified/planned by importer stage | app config, workflow, tools, knowledge, variables |
| Microsoft Copilot Studio | solution export | planned | topics, actions, entities, channels |
| Langflow / Flowise | JSON graph export | planned | graph nodes, tools, routines, eval fixtures |
| n8n / Zapier-style automations | workflow JSON | aspirational/planned | LLM nodes, automations, event handlers |
| OpenAI Assistants / Custom GPTs | assistant config, manifest, files | planned | instructions, files, actions, tools |
| Chatbase / Intercom Fin / Sierra / ElevenLabs | token, export, or partnership path | aspirational | prompts, KB, tools, escalation, voice |
| Custom framework | Git repo, OpenAPI, transcripts | planned | behavior draft, tools, evals, migration gaps |

Do not promise a source path in product marketing unless it is labeled correctly.

### 18.3 Import Wizard

The guided import flow is not a generic setup wizard. It is a safety workflow.

Steps:

1. Choose source.
2. Upload export or connect account.
3. Analyze project.
4. Review inventory.
5. Map to Loop.
6. Resolve gaps.
7. Generate agent.
8. Prove parity.
9. Stage cutover.

### 18.4 Three-Pane Review

```text
+-------------------------+-------------------------+-------------------------+
| Source                  | Needs your eyes         | Loop                    |
| Original structure      | Blocking/advisory/fyi   | Generated agent view    |
| read-only               | decisions               | editable                |
+-------------------------+-------------------------+-------------------------+
```

The middle pane is the migration workbench. Every card asks a clear question and offers a concrete action.

### 18.5 Mapping Model

Porting preserves behavior, not diagrams.

| Legacy concept | Loop destination |
|---|---|
| Bot/workspace assistant | Agent |
| Flow/topic/story | Behavior routine or eval-backed instruction section |
| Node/block/card | Routine step, tool call, channel response, or policy |
| Action/hook/function | Tool or lifecycle handler |
| Knowledge base | Knowledge source |
| Table/entity | Structured data source or managed tool |
| Variable | Memory, config, or channel state |
| Integration | Tool, channel, or MCP server |
| Transcript | Eval case and replay fixture |
| Human handoff | Escalation policy and inbox route |
| Analytics event | Trace, cost, or quality metric |

### 18.6 Migration Confidence

Readiness is explainable:

```text
Migration readiness: 82%

Cleanly imported:      147 items
Needs review:           23 items
Secrets to reconnect:    8 items
Unsupported:             4 items
Parity tests passing:   91 / 100
```

Clicking the score opens the blockers.

### 18.7 Botpress-Specific Experience

Botpress import should be exceptionally polished:

- accept `.bpz` archives and connected workspace paths where available
- parse workflows, nodes, cards, KBs, tables, actions, hooks, variables, integrations, transcripts
- identify autonomous nodes and convert them into behavior sections with tool grants
- convert KBs into knowledge sources
- convert actions/hooks into tools or lifecycle handlers
- convert tables into structured data tools
- convert variables into memory/config recommendations
- map integrations into channel/tool setup tasks
- generate eval cases from transcripts and examples
- preserve source IDs for traceability

Source lineage panel:

```text
Loop behavior: Refund policy routine
Imported from: Botpress workflow "refunds"
Original nodes: refund_start, lookup_order, refund_decision, escalation
Confidence: medium
Review reason: custom JavaScript action uses external secret
```

### 18.8 Parity Harness

Replay historical conversations against source and Loop:

- per-conversation divergence
- per-turn diff
- tool-call parity
- escalation parity
- answer quality delta
- cost delta
- latency delta
- policy violations
- unresolved behavior gaps
- LLM-written narration grounded in trace facts

This screen converts skepticism.

### 18.9 Migration Diff Modes

| Mode | Shows |
|---|---|
| Structure diff | old flows/topics/actions against Loop agent/tools/knowledge |
| Behavior diff | transcript outcome, answer, escalation, and tool differences |
| Cost diff | projected Loop cost against historical platform cost where data exists |
| Risk diff | unsupported source features, missing secrets, policy conflicts |

### 18.10 Assisted Repair

Studio suggests repairs:

- replace integration with MCP server
- convert JavaScript action into typed tool
- convert route condition into eval-backed policy
- map variable into session memory
- map persistent customer data into user memory
- split overloaded workflow into routines or tools
- create channel-specific variant
- mark intentionally unsupported

Every suggestion shows confidence, evidence, diff, and revert path.

### 18.11 Migration Workspace

After cutover, keep:

- original source archive
- parsed inventory
- generated Loop objects
- mapping decisions
- unresolved gaps
- accepted risks
- parity runs
- cutover events
- rollback plan

Lineage must remain available months later.

### 18.12 Gradual Cutover

Cutover supports:

- production channel connection
- shadow traffic
- divergence watch
- percentage or segment canary
- freeze legacy changes
- promote Loop to primary
- rollback route
- archive source mapping

Never imply "import complete" means "safe for production." Safe means parity measured, deploy gated, and rollback ready.

### 18.13 Migration Parity As A Conversion Moment

The parity harness is the sales and trust screen for builders leaving Botpress, Voiceflow, Rasa, Dialogflow, or custom stacks.

It should narrate the migration with proof:

- preserved behavior
- changed behavior
- intentionally improved behavior
- unsupported behavior
- cost and latency difference
- source lineage
- rollback route

When parity crosses a meaningful threshold, Studio may use an earned moment, but the celebration must stay tied to evidence and unresolved gaps must remain visible.

---

## 19. Deployment Flight Deck

Deploying should feel like shipping software.

### 19.1 Environments

Minimum:

- dev
- staging
- production

Enterprise can add custom environments:

- region-eu
- region-us
- partner-acme
- sandbox-customer

Each environment has its own secrets, KB version, budgets, channel configs, and approval policy.

### 19.2 Preflight

Before deploy:

- behavior diff
- graph/map diff if relevant
- code/config diff
- tool diff
- knowledge diff
- memory policy diff
- channel diff
- budget diff
- eval result
- expected cost change
- latency projection
- risk flags
- approval requirements
- rollback target

### 19.3 Promotion

Promote opens a three-panel view:

- changes
- gates
- approvals

Every check links to evidence. The production button does not enable until gates pass or an authorized override is approved.

### 19.4 Canary

Canary is a slider, not a flag day:

- 1%
- 10%
- 50%
- 100%

Show live comparison against current production:

- error rate
- p95 latency
- cost per turn
- eval-derived score
- escalation rate
- tool failure rate

Auto-rollback triggers are explicit.

### 19.5 Rollback

Rollback must be fast and clear. It is a production action, but it is designed for emergencies:

- previous known-good version visible
- impact shown
- confirm required
- action audited
- rollback itself becomes a versioned event

### 19.6 Deploy Timeline

```text
Build artifact       passed    18s
Security scan        passed     7s
Evals                passed    124/124
Staging smoke        passed     2m 04s
Canary 10%           active     42 turns
Canary 50%           waiting    needs 100 clean turns
Production 100%      locked     pending promotion
```

### 19.7 What Could Break

Before promotion, Studio should surface the top production conversations most likely to behave differently under the new version.

Rank by behavioral distance across:

- answer semantics
- tool selection
- retrieval ranking
- memory writes
- refusal/escalation changes
- cost and latency movement
- policy risk

Each item opens old-version vs new-version replay with trace diff. This is the bridge between "evals are green" and "I am safe to ship."

### 19.8 Regression Bisect

When an eval suite goes red between two known points, Studio can run a behavior bisect:

```text
Regression introduced by changeset f3a8c21
Time: Wed 14:22
Object: behavior section `classify_intent`
Author: sam@acme
Failed cases: refund/ambiguous-cancel, refund/spanish-cancel
```

The bisect uses versions, changesets, snapshots, fixtures, and deterministic mocks where available. It should never hide nondeterminism; if the result is probabilistic, confidence and rerun options are visible.

### 19.9 Snapshots As First-Class Artifacts

A snapshot freezes:

- prompts and structured policies
- tools and grants
- KB versions
- memory rules
- eval suite versions
- model and provider settings
- environment config
- deploy state

Snapshots are shareable, replayable, branchable, signed where appropriate, and attachable to incidents, demos, audit requests, and training libraries. A snapshot answers "what exactly was this agent at that moment?"

---

## 20. Observatory

Observability is the builder's production sensemaking layer.

### 20.1 Default Dashboards

Default dashboards:

- health
- quality
- latency
- cost
- knowledge
- tools
- channels
- deploys
- eval trends

Every chart click-throughs to traces.

### 20.2 Anomaly Detection

Detect:

- cost spike
- latency regression
- tool failure spike
- retrieval zero-result spike
- eval regression after deploy
- provider failover
- channel delivery failure
- memory write anomaly

Anomaly cards include summary, evidence, affected object, and next-best action.

### 20.3 Custom Dashboards

Builders can pin:

- charts
- saved searches
- trace filters
- cost breakdowns
- eval trends
- migration parity trends
- audit filters
- KB sources
- inbox queues
- deploy gates

Anything pinned can appear on the personal homepage. The homepage should become the builder's command surface, not a generic product billboard.

### 20.4 Production Tail

Observatory should include a pause-able live trace stream:

- production turns flow in as a readable timeline
- pause freezes the stream without losing events
- scrub backward through recent turns
- filter by agent, channel, version, customer segment, cost, latency, tool, retrieval, memory, or anomaly
- open any event into Trace Theater
- fork or save as eval from the stream

It should feel like tailing production with product-grade controls.

### 20.5 Ambient Agent Health

The asset rail can show a tiny health arc around each production agent avatar.

The arc is derived from:

- eval pass rate
- cost against baseline
- p95 latency
- escalation rate
- tool failure rate
- incident state

States are calm and non-color-only:

- healthy: steady shape, green-compatible color
- drifting: static amber-compatible treatment
- degrading: slow pulse with shape change
- incident: red-compatible treatment plus icon and label

This gives builders peripheral production awareness without forcing dashboard visits. It must never replace detailed Observatory evidence.

---

## 21. Inbox And HITL

Human intervention is not a failure. It is one of the best sources of evals and product learning.

### 21.1 Queue

Queues:

- all
- escalated
- confidence-flagged
- tool-failed
- budget-hit
- manual review
- voice transfer

Rows show user, agent, channel, reason, wait time, SLA, owner.

### 21.2 Takeover

Operator sees:

- conversation
- trace
- memory
- tools used
- retrieved chunks
- escalation reason
- suggested draft
- private notes
- release back to agent

Taking over silences the agent in that thread.

### 21.3 Resolution To Eval

At resolution:

- save as eval case
- expected outcome from operator resolution
- linked trace
- linked failure reason
- attached tool/retrieval evidence

---

## 22. Cost And Capacity

Cost UI should make the builder financially safe.

### 22.1 Cost Surfaces

Show:

- per turn
- per trace
- per agent
- per channel
- per model
- per tool
- per knowledge query
- per environment
- per customer segment
- projected month-end

### 22.2 Cost Decisions

Builders can:

- set soft caps
- set hard caps
- define degrade rules
- compare model cost and quality
- simulate traffic increases
- detect tool loops
- estimate campaign cost
- attribute spend to teams

### 22.3 Cost Copy

Use concrete math:

```text
This turn cost USD $0.0184.
Model:    $0.0151
Tools:    $0.0019
Retrieval:$0.0007
Runtime:  $0.0007
```

Never hide line items that affect production decisions.

### 22.4 Latency Budget Visualizer

Latency is a budget builders can shape.

Show a horizontal stacked bar for a turn or scenario:

- channel ingress
- ASR
- model
- retrieval
- tool calls
- memory
- orchestration
- TTS
- channel delivery

The builder can drag a target marker, such as 800ms or 2.5s. Studio highlights which spans must shrink and offers concrete draft changes:

```text
Cache `pricing_policy` retrieval: expected -90ms
Use smaller model for classification: expected -280ms
Remove second model iteration in routine `triage`: expected -410ms
```

Each suggestion links to eval, quality, and cost impact before it can be applied.

---

## 23. Builder Control Model

The builder must always know whether they are exploring, editing, testing, or changing production.

### 23.1 Object State

| State | Meaning | UX treatment |
|---|---|---|
| Draft | editable, not deployed | unsaved badge, diff to last saved |
| Saved | persisted, not staged | simulator and evals available |
| Staged | deployed to staging | staging badge, smoke status |
| Canary | partial production traffic | traffic percent, live health, promote/rollback |
| Production | active live version | protected edits, rollback target |
| Archived | inactive | read-only, lineage preserved |

State appears in header, version history, command palette, object inspector, and audit log.

### 23.2 Undo And Recovery

Required:

- autosave draft history
- manual checkpoints
- version restore
- config diff revert
- tool permission revert
- knowledge source rollback
- memory policy rollback
- deploy rollback
- migration mapping rollback
- deleted object recovery window for non-secret objects

### 23.3 Preview Before Apply

Preview required for:

- production deploy
- mutating tool grant
- memory retention change
- external channel addition
- budget cap increase
- eval gate override
- AI-generated behavior rewrite
- migration mapping acceptance
- source-platform cutover

Preview includes diff, affected environments, policy checks, cost, risk, and rollback.

### 23.4 Permission Clarity

Disabled controls explain why:

```text
Deploy to production is locked.
Reason: production deploy requires approval from Workspace admin.
Next: request approval for v24.
```

Do not hide unavailable actions when the builder needs to understand the workflow.

### 23.5 Evidence Trail

Every meaningful change captures:

- actor
- object
- previous value
- new value
- linked diff
- reason if supplied
- approval if required
- trace/eval/deploy reference
- timestamp
- request ID

Evidence serves the builder first and compliance second.

---

## 24. Enterprise Builder UX

Enterprise is not a separate product. It is the same Studio with stronger rails.

### 24.1 Identity

Support:

- Okta
- Azure AD / Entra ID
- Auth0
- Ping
- Google Workspace
- generic SAML
- generic OIDC
- SCIM
- JIT provisioning

### 24.2 RBAC Matrix

Roles are composable by scope:

- workspace
- agent
- environment
- tool
- knowledge source
- channel

Default roles:

- owner
- admin
- builder
- operator
- eval author
- security reviewer
- viewer

The RBAC matrix is searchable and can answer "who can do what?" in under 100ms for normal workspaces.

### 24.3 Approval Workflows

High-risk changes require approval:

- production deploy
- mutating tool grant
- external channel
- memory retention increase
- budget increase
- secret access change
- eval gate override
- migration cutover

Approvals bind to a content hash. Editing after approval invalidates approval.

### 24.4 Audit Log Explorer

Audit log is:

- append-only
- tamper-evident
- searchable
- exportable
- filterable by actor, action, target, environment, agent, time
- forwardable to SIEM

Each row links to the affected object and evidence.

### 24.5 Data Residency

Workspace data plane, storage, traces, KB, and memory are region-pinned. Cross-region callouts are blocked where policy disallows them and surfaced in trace/audit.

### 24.6 BYOK

Enterprise encryption panel:

- AWS KMS
- GCP KMS
- Azure Key Vault
- HashiCorp Vault
- on-prem HSM

Rotation and revocation are supported and audited.

### 24.7 Whitelabel

Enterprise can configure:

- logo
- primary color
- favicon
- custom domain
- email templates
- branded operator surfaces

Whitelabel must not hide audit evidence or operational truth.

### 24.8 Compliance And Procurement

A procurement/compliance page includes:

- SLA
- uptime history
- status page
- sub-processors
- DPA
- MSA template
- security questionnaires
- SOC2/ISO/HIPAA evidence where available
- vulnerability disclosure
- named support contact

Workspace-specific evidence can be exported.

### 24.9 Private Skill Library

Enterprise teams can publish internal skills with versioning, deprecation, approvals, usage analytics, and eval suites.

---

## 25. Collaboration

Studio is multiplayer without becoming chaotic.

### 25.1 Presence

Show:

- avatars
- cursors
- selected objects
- current branch
- active screen

Presence smooths cursor motion and never breaks layout.

### 25.2 Comments

Comments attach to:

- behavior sections
- tool configs
- knowledge chunks
- memory writes
- traces
- eval cases
- deploys
- migration gaps
- cost anomalies

Comments survive version changes by anchoring to stable object IDs.

### 25.3 Changesets

Branches are changesets:

- graph/map diff
- code/config diff
- behavior diff
- eval delta
- cost delta
- latency delta
- approvals
- comments

Conflict resolution understands object structure, not just text.

### 25.4 Handoff

Anyone can share:

- review this eval regression
- approve this tool
- inspect this trace
- validate this migration gap
- approve production cutover

Recipients land on the exact object with context.

### 25.5 Comments As Specifications

When a reviewer resolves a comment with "this should have done X instead," Studio offers to turn that comment into an eval case:

- linked conversation or trace
- expected behavior
- failure reason
- reviewer
- source object
- owner
- deploy gate suggestion

Critique becomes regression coverage. The product should make this feel like the natural end of review, not a separate QA chore.

### 25.6 Real-Time Pair Debugging

For high-pressure debugging, Studio can offer a lightweight collaboration channel inside the workspace:

- screen-surface aware presence
- optional voice room
- shared trace playhead
- shared replay controls
- handoff of keyboard focus
- audit-safe transcript policy

This must be optional and enterprise-governed. Pair debugging should not require leaving the surface where the evidence lives.

---

## 26. AI Co-Builder

AI assistance should make builders faster without blurring accountability.

### 26.1 Pointer

The co-builder's context is the current selection: behavior section, tool, chunk, trace span, eval case, deploy, migration gap. It always shows what it is looking at.

### 26.2 Consent Grammar

| Mode | May do | Requires explicit consent |
|---|---|---|
| Suggest | read context, propose diffs, run speculative evals | edit real branch, call side-effect tools, exceed session budget |
| Edit | apply edits to user's branch, run evals, update drafts | protected environment changes, live side-effect tools, secrets |
| Drive | call live tools where permitted, run live KB evals, execute multi-step fixes | promote, edit secrets, spend above daily budget, override gates |

Drive mode is disabled by default for enterprise workspaces unless granted.

### 26.3 Provenance

Every AI-applied change records:

- user who confirmed
- prompt
- model
- token cost
- diff
- evidence

### 26.4 Guardrails

AI suggestions must:

- cite source evidence
- show exact diff
- be reversible
- never silently mutate production
- never invent unavailable telemetry
- respect budgets
- respect permissions

### 26.5 Rubber Duck Panel

The Rubber Duck is diagnostic. The builder describes a problem in plain English:

```text
The agent keeps citing the wrong policy when users say "cancel."
```

The panel has read-only context over the selected agent, behavior, tools, KB, evals, recent traces, and policies. It proposes two or three specific fixes, each with:

- diff
- evidence trail
- expected eval impact
- risk flags
- one-click preview

It is different from Drive mode: the Rubber Duck diagnoses and proposes; it does not execute without builder action.

### 26.6 Second Pair Of Eyes

Before promotion, import cutover, tool grant, or risky behavior edit, a builder can request adversarial review.

The review is five bullets or fewer. Each bullet cites an eval, trace, policy, cost calculation, or missing coverage:

```text
This prompt change may fail on Spanish refund queries; the eval suite has no Spanish refund coverage.
The new tool grant can spend USD $0.27 per turn in the worst case; the cap is USD $0.10.
```

If evidence is missing, the reviewer says what it cannot know and suggests how to gather proof.

---

## 27. Command, Search, And Sharing

### 27.1 Command Palette

Command palette supports:

- jump to agent
- jump to trace
- jump to conversation
- run eval
- replay turn
- deploy version
- rollback
- import project
- create tool
- open knowledge source
- switch environment
- compare versions
- copy IDs
- open docs

It understands typed prefixes:

```text
agent: support
trace: t-9b23
eval: refund
import: botpress
cost: whatsapp yesterday
```

### 27.2 Find In Context

Find within:

- current workbench
- current trace
- current audit log
- current eval result
- current migration inventory

### 27.3 Saved Searches

Saved searches can pin:

- regressing evals
- failed tools
- expensive turns
- pending approvals
- migration gaps
- audit overrides

### 27.4 Sharing

Shareable artifacts:

- trace
- conversation
- eval result
- deploy diff
- parity report
- cost chart
- audit evidence

Every share has:

- permission scope
- expiration
- redaction preview
- access log
- revoke action

### 27.5 Redaction

Sharing can redact:

- PII
- secrets
- customer messages
- prompts
- pricing
- internal notes

The recipient sees what was redacted.

### 27.6 Inline ChatOps In Preview

The live preview can accept slash commands for expert debugging:

```text
/swap model=fast-draft
/disable tool=lookup_order
/inject ctx="user is on premium tier"
/as-user persona=angry-customer
/replay turn=3 with-memory=cleared
/diff against=v23
```

Commands are discoverable through autocomplete, permission-aware, and logged in the local test timeline. They never mutate production unless routed through the normal deploy and approval model.

### 27.7 Quick Branch Links

A branch link shared in Slack, Linear, email, or chat should open the smallest useful review surface:

- change summary
- semantic behavior diff
- eval status
- preflight blockers
- canary slider if deployable
- approve/comment/request-change actions

Reviewers should not wait for full Studio context when the task is one focused decision.

---

## 28. Visual Language

Studio should feel like a Swiss-engineered instrument with editorial warmth: precise, calm, classy, and quietly alive.

### 28.1 Palette

Use a structural palette for 95% of surfaces and a signal palette for state.

Structural dark:

- `--bg-page`: `#0B1020`
- `--bg-surface`: `#0F1830`
- `--bg-elevated`: `#161F3A`
- `--bg-hover`: `#1A2440`
- `--bg-selected`: `#1F2D52`
- `--text-primary`: `#F1F5F9`
- `--text-secondary`: `#9AA9C2`
- `--text-tertiary`: `#5E6F8E`
- `--border-subtle`: `#1F2A45`
- `--border-default`: `#2A395E`

Structural light:

- `--bg-page`: `#FAFAF7`
- `--bg-surface`: `#FFFFFF`
- `--bg-hover`: `#F2F2EE`
- `--bg-selected`: `#EAECF8`
- `--text-primary`: `#0F1830`
- `--text-secondary`: `#475881`
- `--text-tertiary`: `#8694B0`

Signal:

- `--signal-info`: `#5EA6FF`
- `--signal-accent`: `#14B8A6`
- `--signal-success`: `#10B981`
- `--signal-warning`: `#F59E0B`
- `--signal-danger`: `#EF4444`
- `--signal-pop`: `#F97316`
- `--signal-violet`: `#A78BFA`

Adding a new color requires a reason in design review.

### 28.2 Trace Span Shapes

Trace spans use color and shape:

| Span | Color | Shape |
|---|---|---|
| LLM | teal | pill |
| Tool | orange | chevron |
| Retrieval | violet | diamond |
| Memory | slate | ring |
| Channel | blue | square |
| Voice | rose | hex |
| Sub-agent | gold | pentagon |

### 28.3 Typography

Recommended:

- display/headings: Inter Display or similar
- body: Inter or similar
- editorial/reporting: Source Serif Pro or similar
- mono: Berkeley Mono or JetBrains Mono

Numbers use tabular figures anywhere comparison matters.

### 28.4 Iconography

Single icon family:

- 24px grid
- 1.5px outline
- filled variants only for active state
- vendor icons rendered faithfully
- custom domain icons for agent, tool, knowledge, memory, eval, trace, canary, branch, fork, promote

### 28.5 Trust Palette

State/color/icon pairings are sacred:

| State | Signal | Meaning |
|---|---|---|
| Live | teal dot | active in production |
| Canary | amber wedge | partial production traffic |
| Pending review | amber clock | waiting for approval |
| Approved | emerald check | reviewed and approved |
| Mocked | violet mask | deterministic mock responses |
| Stale | slate hourglass | source is old |
| Needs your eyes | orange eye | human decision required |
| Read-only | muted lock | permission or policy boundary |

---

## 29. Motion, Tactility, And Sound

Motion is a second design system. It explains cause and effect, gives the product weight, and makes progress feel real.

### 29.1 Motion Tokens

Curves:

| Token | Use |
|---|---|
| `motion.standard` | panel slides, inspector transitions, drag-drop returns |
| `motion.swift` | button press, hover lift, tooltip reveal |
| `motion.gentle` | earned moments, ambient life, completion rings |

Durations:

| Token | Duration | Use |
|---|---:|---|
| `dur.flash` | 80ms | click acknowledgement, focus ring |
| `dur.quick` | 160ms | hover, tooltip, tab indicator |
| `dur.standard` | 240ms | panel, modal, page transition |
| `dur.expressive` | 400ms | earned moments, migration reveal, fork split |
| `dur.ambient` | 1600ms+ | heartbeat, activity ribbon |

### 29.2 Choreography Rules

- one subject leads at a time
- direction matches origin
- progress uses linear motion
- arrivals use ease-out
- exits use ease-in
- list items may stagger; grids should not
- no layout shift on hover or selection
- reduced motion is first-class

### 29.3 Forbidden Motion

- confetti
- fireworks
- particle effects
- scroll-jacking
- shake-on-error
- childish bounce
- fast skeleton pulsing
- personality spinners

### 29.4 Tactility

Buttons compress slightly on press. Cards lift without changing size. Dragged objects lift, show origin, and settle into valid targets. Invalid drops return home along their path. Rail resizing has weight and snap points.

These details should be felt more than noticed.

### 29.5 Streaming As Ink

LLM text appears as ink:

- tokens fade in at final position
- no layout jumps
- cursor pulses while writing
- tool cards fold in mid-response
- stop button is always reachable

Voice equivalent:

- live waveform
- stage dots
- cumulative latency
- ASR/TTS spans

### 29.6 Ambient Life

Use only when tied to real state:

- agent heartbeat
- live activity ribbon
- now-playing chip on agent card
- breathing notification well for unread items
- background progress chips
- multiplayer presence

The UI must never fake liveness.

### 29.7 Earned Moments

Rare, brief, opt-out:

- first turn
- first staging deploy
- first production promotion
- canary reaches 100%
- first 1,000 production turns
- migration cutover complete
- clean eval after regression
- perfect parity score across a meaningful sample
- first migration parity at or above the workspace threshold
- first fork that beats its source branch on the same eval suite
- first scene canonicalized
- 30 consecutive days above the eval pass-rate floor
- first downstream use of a private workspace skill

Constraints:

- once per user per relevant object
- never modal
- never blocks next action
- silent unless sound is enabled
- reduced-motion alternative
- global personal setting to reduce polish

### 29.8 Sound

Silent by default. Optional and respectful.

Where sound can exist:

- voice mode functional tones
- operator inbox if enabled
- earned moments if enabled

Sound rules:

- under 400ms
- OS volume-aware
- quiet-hours aware
- pauses during voice mode or screen sharing
- one-tap mute

### 29.9 Skeletons With Character

Skeletons mimic actual content:

- trace skeleton has time axis
- conversation skeleton has varied rows
- eval skeleton shows case count
- charts show axes
- progressive replacement cross-fades to real content

No generic gray boxes.

### 29.10 Polish Primitives

Design system primitives:

| Primitive | Purpose |
|---|---|
| `FocusPulse` | highlight a newly created or changed object |
| `MetricCountUp` | animate meaningful numeric changes |
| `StageStepper` | progress through import, eval, deploy, ingest |
| `EvidenceCallout` | connect recommendation to proof |
| `ConfidenceMeter` | show explainable confidence |
| `DiffRibbon` | mark changed lines or config blocks |
| `LiveBadge` | streaming, cached, stale, estimated |
| `CompletionMark` | restrained proof moment |
| `RiskHalo` | subtle treatment around blocked or risky controls |

---

## 30. Accessibility And Inclusion

WCAG 2.2 AA is required. AAA is aspirational where feasible.

### 30.1 Global Requirements

- full keyboard navigation
- visible focus states
- screen-reader summaries
- reduced-motion mode
- high-contrast mode
- no color-only meaning
- resize-friendly text
- comfortable touch targets
- accessible tables
- ARIA-live for streaming and alerts

### 30.2 Canvas Accessibility

The map/canvas must have a first-class list view:

- same source of truth
- same actions
- hierarchical structure
- keyboard reorder
- screen-reader labels
- no visual-only dependency

### 30.3 Trace Accessibility

Trace waterfall must have:

- sortable span table alternative
- kind, duration, status, cost, parent span
- keyboard navigation
- screen-reader summary

### 30.4 Color-Blind Safety

Test:

- deuteranopia
- protanopia
- tritanopia
- achromatopsia

Trace spans use shape as well as color. Charts use line style as well as color. Diff uses `+` and `-` as well as color.

### 30.5 Voice As Alternate Input

Private alpha may support voice commands:

- show last trace
- fork this turn
- run eval
- open deploy diff
- approve changeset

High-impact commands require explicit confirmation.

---

## 31. Responsive Modes

### 31.1 Desktop

Full power:

- five-region shell
- resizable panes
- trace theater
- side-by-side diffs
- command palette
- dense tables
- multiplayer

### 31.2 Tablet

Review and approval:

- two-pane layout
- trace summaries
- cost dashboards
- approvals
- conversation review
- parity reports

### 31.3 Mobile

Urgent actions only:

- acknowledge incident
- inspect summary
- view deploy status
- approve/decline changeset
- rollback
- take over inbox item
- view cost alert

Do not force full agent editing onto mobile.

### 31.4 Large Display

For war rooms and design reviews:

- observatory dashboards
- deploy watch
- migration parity board
- live trace stream
- inbox queue

Second monitor mode is low-chrome and persistent: timeline, production tail, inbox, and current deploy health stay visible beside the main editor without stealing focus.

---

## 32. States And Copy

### 32.1 Loading

No full-page spinners. Use:

- skeletons
- progressive loading
- streaming partials
- named stages
- background progress chips
- cancel for long jobs

### 32.2 Empty States

Every empty state is a starting line:

- import
- create
- connect
- run
- deploy
- invite
- save as eval

Empty states should be personalized when workspace evidence exists:

```text
Save these 12 turns from yesterday as a starter eval suite.
```

```text
Three KB chunks were cited often but failed two evals. Review them now.
```

Never show generic placeholder copy when traces, imports, or workspace history can produce a useful next action.

### 32.3 Errors

Every error includes:

- what failed
- why, if known
- affected object
- next action
- retry when safe
- request/trace ID
- docs or runbook link where useful

### 32.4 Degraded States

When degraded:

- cached data remains visible
- read-only mode is clear
- queued actions are visible
- retry state is visible
- status link is present

### 32.5 Friendly Precision Copy

| Moment | Weak copy | North-star copy |
|---|---|---|
| Eval failed | Deployment failed | Promotion blocked. `refund_window_basic` regressed from 0.91 to 0.72. Open the diff or keep v23 live. |
| Tool missing | Unauthorized | This agent cannot call `refund_order`. Grant the tool or remove it from the behavior policy. |
| Import gap | Unsupported node | This Botpress node uses custom JavaScript with a secret. Convert it into a typed Loop tool and reconnect the secret. |
| Cost risk | High cost | Projected month-end cost is USD $1,240, 2.4x above cap. Degrade to `fast` after USD $500 or raise the cap. |
| Trace missing | No data | Trace is still ingesting. Last event arrived 3s ago. Refresh automatically for 30s. |

---

## 33. Onboarding

### 33.1 Three Doors

After login:

1. Import from another platform.
2. Start from template.
3. Start blank.

No fourth door. No required video. No team survey before value.

### 33.2 Templates

Templates are working agents:

- support agent
- sales SDR
- scheduling concierge
- voice receptionist
- internal IT helpdesk
- document search assistant
- procurement Q&A

Each includes:

- sample KB
- mock tools
- eval suite
- seeded conversations
- trace examples
- cost estimate

### 33.3 Guided Spotlight

Only three first-run hints:

1. This is what just ran.
2. Click any turn to see what happened.
3. Fork from a turn to test a change.

Dismissable forever.

### 33.4 First Week

Nudges are limited and useful:

- run eval suite
- connect tool
- add KB
- inspect cost
- invite reviewer

At most one nudge per day, opt-out by category.

### 33.5 First Month

Show weekly recap:

```text
This week: 4 promotions, 2 rollbacks, 12 evals saved, 3 KB sources updated.
Cost +5%, latency unchanged.
```

### 33.6 First Quarter

Help teams organize:

- workspace hygiene
- stale tools
- untested agents
- expensive agents
- missing owners
- old knowledge sources
- eval gaps

### 33.7 Concierge From Real Data

On day one, Studio can ask:

```text
Want me to learn from your last 20 conversations?
```

If accepted, Studio imports or samples recent conversations, suggests starter evals, flags likely KB holes, drafts scenes, identifies risky tools, and recommends one safe first improvement. This must be permissioned, reversible, and explicit about what data was read.

---

## 34. Marketplace

Marketplace includes:

- skills
- tools
- eval suites
- templates
- channel adapters
- migration importers

Each item includes:

- description
- author
- license
- version history
- install count
- rating
- security posture
- sample evals
- screenshots
- required permissions

Enterprise admins can curate allowed items and see workspace usage.

---

## 35. Help, Feedback, And Telemetry

### 35.1 Help

Help is contextual:

- selected object docs
- "show me" 30-second clips
- examples
- runbooks
- support contact

No autoplay sound.

### 35.2 Feedback

Feedback options:

- report bug
- send product feedback
- request importer
- request support

Bug reports pre-fill:

- request ID
- trace ID
- current screen
- recent client errors
- optional user-approved screen recording

### 35.3 Telemetry Consent

Consent screen explains:

- what is collected by default
- what is never collected
- how to opt out
- how enterprise admins control telemetry

Never collect prompts, messages, KB chunks, secrets, or traces for product analytics unless explicitly configured by the customer.

### 35.4 Status And Incidents

Status is visible in product:

- current incident
- affected region
- affected service
- workaround
- last update
- subscribe option

---

## 36. North-Star Scenarios

### 36.1 Maya Migrates From Botpress In An Afternoon

Maya imports a Botpress workspace, reviews mappings, reconnects secrets, runs parity against 200 conversations, fixes four divergences, stages Loop, shadows traffic, canaries to 10%, then promotes to 100% with rollback ready.

This tests migration, parity, source lineage, cutover, and deploy safety.

### 36.2 Diego Ships A Voice Phone Agent In 25 Minutes

Diego starts from a voice receptionist template, connects a phone number, tests voice preview, sees ASR/TTS spans, runs voice evals, deploys to staging, and canaries calls.

This tests voice as a channel, not a separate product.

### 36.3 Priya Investigates The Wrong Tool

Priya opens a failed production turn, inspects the tool span, sees the policy mismatch, forks the turn, updates behavior, saves the original as an eval, and confirms regression suite passes.

This tests trace -> fork -> fix -> eval.

### 36.4 Acme Rolls Out With Four-Eyes Review

A bank platform team updates a loan FAQ agent. Preflight shows graph/code diff, eval delta, cost delta, latency delta, and required approvers. Two reviewers approve. Canary passes. Audit evidence exports.

This tests enterprise governance.

### 36.5 Operator Handles Real-Time Escalation

An operator takes over a voice escalation, sees the trace and memory, resolves the customer issue, saves the resolution as an eval, and releases the conversation.

This tests HITL as production learning.

### 36.6 Support Lead Finds KB Gap

A dashboard surfaces zero-result retrievals. The support lead opens the Knowledge Atelier, sees missed candidates, adds a source, runs retrieval evals, and watches grounded answer quality improve.

This tests knowledge as a measurable system.

### 36.7 Sam Replays Tomorrow Before Shipping

Sam edits a refund behavior section. Preflight surfaces five production conversations most likely to change. Sam replays them against the draft, sees one Spanish refund case regress, asks Second Pair Of Eyes to review, adds a missing eval, and promotes only after the replay diff clears.

This tests production replay, What Could Break, behavior review, and deploy confidence.

### 36.8 Nadia Uses X-Ray To Remove Dead Context

Nadia opens Agent X-Ray and sees that five prompt sections are never visibly invoked while one rare branch drives most cost. She opens representative traces, trims dead context, adds a targeted eval for the rare branch, and uses the latency budget visualizer to confirm the agent is faster without losing quality.

This tests observed behavior, sentence telemetry, cost control, and evidence-backed simplification.

---

## 37. Screen Quality Bar

Every Studio screen must pass.

### 37.1 Clarity

- one primary job
- object/workflow named clearly
- primary action obvious
- environment/version visible when relevant
- empty/loading/error/degraded states designed

### 37.2 Control

- preview for high-impact changes
- diff from production visible
- undo/recovery for non-production edits
- rollback path for production
- disabled actions explain why

### 37.3 Precision

- numbers include units
- status labels are specific
- health scores drill down to evidence
- AI summaries cite sources
- operational tables sort/filter/export

### 37.4 Friendliness

- next useful action present
- examples available
- errors say what failed and what to do
- forms have tested defaults
- long workflows show named stages

### 37.5 Enterprise Readiness

- audit-relevant actions recorded
- secret boundaries visible
- approvals visible before block
- policy violations name policy and owner
- evidence exportable

### 37.6 Craft

- stable layout under long values
- no critical truncation without access
- keyboard reachable
- density controls for tables
- visual emphasis maps to risk

### 37.7 Delight

- at least one pleasant responsiveness moment
- progress visible for operations over 1s
- success satisfying but not noisy
- motion clarifies cause/effect
- reduced-motion equally understandable

If a screen fails more than one category, it is not north-star quality.

---

## 38. Minimum Lovable Slice

If only a narrow version can be built first, build this:

1. Agent workbench with structured profile.
2. Multi-channel simulator for web and Slack.
3. Trace Theater with tool/retrieval/memory visibility.
4. Eval creation from conversation and simulator run.
5. Deploy preflight with eval gate and rollback.
6. Cost per turn and per agent.
7. Botpress import wizard with inventory, mapping, parity report, and lineage.

This slice expresses the product better than a broad shallow admin console.

Once the slice works, the first differentiating expansions should be:

1. Trace Scrubber plus replay against draft, because debugging becomes a creative act and production turns become future tests.
2. Agent X-Ray, because builders can see observed behavior instead of guessing from config.
3. Migration parity harness with diff narration, because it is the conversion proof for Botpress and adjacent platform customers.

---

## 39. Measurement

Track:

- time to first turn
- time to first eval
- time to first staging deploy
- time to first production deploy
- migration success rate
- parity threshold reached
- edit-to-effect latency
- trace open latency
- eval-suite run latency
- promotion approval cycle time
- cost anomalies resolved before cap
- deploy rollbacks avoided by preflight
- crash-free session rate
- a11y CI pass rate
- weekly active builders
- agents with eval gates
- agents with monitored costs
- imported projects cut over to production
- production turns converted to evals
- comments converted to eval specifications
- traces replayed against draft before promotion
- regressions caught by What Could Break
- bisections completed successfully
- X-Ray findings resolved
- inverse retrieval gaps fixed
- personalized empty states acted on

If we do not measure it, the north-star is theater.

---

## 40. External Format Notes

Importer assumptions must be verified against official platform docs before implementation. Current public entry points to account for:

- Botpress import/export archives, commonly `.bpz`: https://www.botpress.com/docs/learn/reference/import-export-bots
- Voiceflow project export/API, including `.vf` and `.vfr`: https://docs.voiceflow.com/reference/fetchproject
- Dify YAML DSL import/export: https://docs.dify.ai/en/guides/management/app-management
- Dialogflow CX binary or JSON export: https://cloud.google.com/dialogflow/cx/docs/reference/rest/v3/projects.locations.agents/export
- Dialogflow ES ZIP export: https://cloud.google.com/dialogflow/es/docs/reference/rest/v2/projects.agent/export
- Microsoft Copilot Studio export/import through solutions: https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-export-import-bots

These links are not UX dependencies. They prevent the migration UX from promising impossible source formats.

---

## 41. Anti-Patterns

Do not build:

- a giant flow editor as the primary interface
- canvas-first logic that hides agent primitives
- hidden prompts or hidden tool selection
- mystery health scores
- migration that lacks parity proof
- deploy without preflight and rollback
- cost UI without line items
- settings pages that bury behavior
- AI suggestions that mutate production without review
- joyless admin console
- fake progress
- celebration for risk
- modals over modals
- destructive gestures
- unsupported import promises
- telemetry that surprises customers
- decorative excitement that does not reveal state, evidence, or control
- a second navigation taxonomy competing with Build/Test/Ship/Observe/Migrate/Govern
- visual maps that become the only place logic can be understood
- synthetic eval generation without provenance
- health indicators that cannot be clicked into evidence
- semantic summaries that are not grounded in actual diffs

---

## 42. Evolution

This doc is alive but not casual.

Changes should require:

- product approval
- design approval
- engineering approval
- customer signal when customer-driven
- metric signal when metric-driven
- explicit note when a section is aspirational vs committed

The persistent references are:

- seven product questions
- agent-native constraint
- builder control model
- migration parity standard
- screen quality bar
- minimum lovable slice

As implementation matures, move exact color values, duration values, spacing, and component APIs into dedicated design-token and design-system references. This document should keep principles, quality bars, product moments, and evidence standards; token files should carry mechanical details.

---

## Appendix A - Glossary

**Agent:** unit of behavior, versioned, deployable, connected to tools, knowledge, memory, channels, evals, and budgets.

**Agent map:** visual view of agent dependencies and composition. It is not a legacy flowchart.

**Agent X-Ray:** observed-behavior analysis derived from traces that shows which prompts, tools, branches, KB chunks, and policies actually influence production behavior.

**Behavior:** instructions, policies, constraints, tool-use rules, refusal rules, escalation rules, tone, and compliance boundaries.

**Canary:** partial production traffic to a candidate version.

**Changeset:** reviewable branch with graph/config/code/behavior diffs and evidence.

**Eval:** automated case or suite measuring output, tool calls, quality, latency, cost, safety, or policy adherence.

**Fork:** replayable branch from a historical turn with exact state.

**Knowledge source:** document, URL, workspace, database, or system used for retrieval.

**Memory:** session, user, episodic, or scratch state that affects agent behavior.

**Migration Atelier:** import, mapping, parity, and cutover surface.

**Parity:** measured equivalence or intentional divergence between source platform and Loop behavior.

**Production:** live environment receiving customer traffic.

**Scene:** canonical conversation artifact used for onboarding, review, replay, and regression coverage.

**Snapshot:** frozen, replayable agent state at a moment in time, including behavior, tools, KB versions, memory rules, evals, model settings, and deploy state.

**Trace:** evidence record of one turn, including LLM, tool, retrieval, memory, channel, cost, and latency spans.

**Turn:** one inbound user event and the resulting agent reasoning loop.

---

## Appendix B - Product Oath

Every screen we ship must answer:

- [ ] Which of the seven product questions does this screen serve?
- [ ] Is the object state visible?
- [ ] Is the current environment visible when relevant?
- [ ] Are cost, latency, and quality visible where they affect decisions?
- [ ] Can the builder inspect why something happened?
- [ ] Can high-impact changes be previewed?
- [ ] Is rollback or recovery visible?
- [ ] Are empty, loading, error, and degraded states designed?
- [ ] Is every recommendation tied to evidence?
- [ ] Does keyboard navigation work?
- [ ] Is reduced motion respected?
- [ ] Is color never the only signal?
- [ ] Are audit-relevant actions recorded?
- [ ] Does the screen feel crafted, not merely functional?

If a screen cannot pass these, build less and finish what matters.

---

## Appendix C - Copy Library

### C.1 Voice Principles

- Direct, never apologetic.
- Specific, never vague.
- Actionable, never dead-end.
- Evidence-backed when explaining AI behavior.
- No marketing voice inside production surfaces.

### C.2 Buttons

| Moment | Use | Avoid |
|---|---|---|
| deploy | Deploy version | Publish bot |
| promote | Promote v24 | Go live now |
| rollback | Roll back to v23 | Undo production |
| eval | Run eval suite | Test it |
| trace | Open trace | View logs |
| migration | Review mapping | Continue |
| parity | Run parity suite | Check import |
| tool | Grant tool | Enable integration |

### C.3 Errors

```text
Promotion blocked. `refund_window_basic` regressed from 0.91 to 0.72.
Open the diff or keep v23 live.
```

```text
This agent cannot call `refund_order`.
Grant the tool or remove it from the behavior policy.
```

```text
Trace is still ingesting. Last event arrived 3s ago.
Refreshing automatically for 30s.
```

### C.4 Success

```text
Staging deploy passed. 124 eval cases passed, p95 latency changed -3%, cost per turn changed -2%.
```

```text
Parity suite complete. 196 of 200 conversations match; 4 need review.
```

### C.5 Empty States

```text
No evals yet. Save any simulator run or production turn as an eval case.
```

```text
No tools connected. Add a typed tool, import an OpenAPI spec, or install from the marketplace.
```

```text
No migration started. Import a Botpress archive, connect a source workspace, or start from transcripts.
```

### C.6 Recommendation

Bad:

```text
Improve your prompt.
```

Good:

```text
Add an escalation rule for refund disputes.
Evidence: 7 of 12 failed refund turns ended with unresolved policy conflict.
Expected effect: reduce failed refund evals.
```
