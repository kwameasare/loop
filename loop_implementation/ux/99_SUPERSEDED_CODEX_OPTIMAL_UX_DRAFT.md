# Superseded Codex Optimal UX Draft - Loop Studio

**Status:** SUPERSEDED SOURCE DRAFT. Replaced by [`00_CANONICAL_TARGET_UX_STANDARD.md`](00_CANONICAL_TARGET_UX_STANDARD.md).  
**Owner:** Product + Design + Studio Engineering  
**Primary customer:** Builder and enterprise builder  
**Use:** historical/reference material only. Do not treat this file as the target UX standard.

Loop Studio should feel like the best possible place to build, test, migrate, ship, and operate production agents. The builder is the customer. Operators, admins, and end users matter, but the product should be judged by whether a serious builder can trust it with agent behavior, production reliability, observability, cost, security, and migration from incumbent platforms.

This is not a chatbot builder. It is an agent engineering cockpit with the elegance of a high-end creative tool and the precision of production infrastructure.

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

Every screen, action, and empty state should help answer one of those questions. If a screen cannot do that, it should not exist.

---

## 2. Experience Principles

### 2.1 Builder first

The primary user is building a production agent, not admiring a canvas. The UI should serve engineering judgment: inspectability, control, repeatability, debugging, fast iteration, and clean handoff to code.

### 2.2 Agent-native, not flow-native

Loop should not rebuild a legacy flow editor with nicer styling. Flow imports are accepted, understood, and transformed, but the destination model is agent-native: instructions, tools, knowledge, memory, evals, channels, budgets, traces, and deploys.

### 2.3 Transparent by default

No hidden prompts. No mystery tool calls. No vague "AI reasoning" panel. The builder sees exact inputs, outputs, retrieved context, memory changes, tool arguments, cost math, latency, eval scores, and deploy blockers.

### 2.4 Calm power

The product should feel classy, not flashy. Dense data is welcome, but hierarchy must be disciplined. The UI should feel expensive because it is exact, composed, and fast, not because it is decorative.

### 2.5 Progressive mastery

A new builder can ship a useful imported or template agent in one session. An expert builder can drive the product by keyboard, code, config, API, and trace queries without waiting for guided flows.

### 2.6 Migration is a first-class product

Porting from Botpress, Voiceflow, Dialogflow, Rasa, Dify, Copilot Studio, Langflow, n8n, or a custom framework should be a premium onboarding experience. The product should preserve business behavior, not recreate old UI metaphors.

### 2.7 Trust beats magic

Loop can assist with AI-generated suggestions, eval creation, migration mapping, and tool schema repair, but every suggestion must be reviewable, diffable, and reversible.

### 2.8 Control is the luxury

The best builder UX is not the fewest clicks. It is knowing exactly what will happen before a change touches production. Every high-impact action should have preview, diff, validation, evidence, approval when required, and rollback.

### 2.9 Friendly means guided, not vague

Friendly UX should reduce cognitive load without hiding the machinery. Use plain labels, good defaults, progressive disclosure, examples, and next-best actions. Do not replace precise concepts with soft language.

### 2.10 Make the safe path the fastest path

The easiest route through Studio should naturally create evals, inspect traces, reconnect secrets correctly, run preflight, canary deploy, and preserve rollback. Builders should not need discipline to do the right thing; the product should carry them there.

---

## 3. Target Builder Personas

### 3.1 Solo technical builder

Wants to import or scaffold an agent, wire tools, test quickly, and deploy without wrestling with infrastructure. Values speed, clear errors, and code escape hatches.

### 3.2 Startup product engineer

Owns customer-facing agent behavior and production incidents. Needs traces, evals, cost controls, channel testing, and rollback.

### 3.3 Enterprise builder

Builds agents inside governance constraints. Needs role-based access, audit logs, environment promotion, secret handling, approval workflows, SSO, data residency, migration evidence, and security review artifacts.

### 3.4 Platform team

Maintains many agents, tools, channels, and shared knowledge sources across teams. Needs reusable templates, policy controls, cost attribution, versioning, and workspace-wide observability.

### 3.5 Migration lead

Owns the move from an incumbent platform. Needs import diagnostics, mapping confidence, parity testing, transcript replay, stakeholder reports, and staged cutover.

### 3.6 The first 30 minutes

The ideal first 30 minutes for a builder:

1. Create or import an agent.
2. See a complete agent profile with missing pieces highlighted.
3. Run one realistic simulated conversation.
4. Open the generated trace.
5. Turn that run into an eval case.
6. Connect or test one real tool.
7. Deploy to staging.
8. Understand what blocks production.

The builder should reach this point without reading docs. Docs should deepen mastery, not rescue a confusing product.

### 3.7 The enterprise first day

The ideal first day for an enterprise builder:

1. Import an existing Botpress or comparable project.
2. Review inventory and source mapping.
3. Reconnect secrets through approved vault flow.
4. Resolve the top migration gaps.
5. Run parity tests on historical transcripts.
6. Share a migration report with product, support, and security.
7. Stage the imported agent behind a canary.
8. Export the evidence package for review.

The experience should make migration feel like a controlled program, not a risky rewrite.

---

## 4. The Ideal Information Architecture

The product should organize around the builder's lifecycle, not internal services.

```text
Studio
|
|-- Build
|   |-- Agents
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
|   |-- Test data
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
|   |-- Cost
|   |-- Quality
|
|-- Migrate
|   |-- Imports
|   |-- Mapping
|   |-- Parity
|   |-- Cutover
|
|-- Govern
    |-- Members
    |-- Roles
    |-- Secrets
    |-- Audit
    |-- Policies
    |-- Billing
    |-- Compliance
```

The left nav should be stable and compact. The command palette should make navigation optional for expert users. The current agent, environment, version, and unsaved state should always be visible.

---

## 5. Visual Direction

### 5.1 Overall feel

Studio should feel like a premium builder console:

- quiet, precise, and composed
- visually rich only where richness clarifies behavior
- elegant without looking like a landing page
- dense but never cramped
- enterprise credible without becoming gray software
- friendly enough for first-time builders, exact enough for senior engineers

The aesthetic target is "luxury instrument panel": deep craft, clean materials, no visual gimmicks.

### 5.2 Palette

Avoid one-note brand wash. Use a layered neutral system with restrained signal colors.

| Role | Suggested color | Use |
|---|---:|---|
| Ink | `#111318` | Dark text, high-contrast chrome |
| Graphite | `#2A2F38` | Secondary text, dark panels |
| Porcelain | `#F7F6F2` | Light surface, not pure white glare |
| Mist | `#E8ECEF` | Dividers, quiet fills |
| Jade | `#0F9F8F` | Primary action, healthy state |
| Ultramarine | `#3157D5` | Links, active focus, selected nav |
| Ember | `#E65F3C` | Errors, destructive actions |
| Marigold | `#D99A22` | Warnings, attention states |
| Violet | `#7457C8` | Retrieval, semantic memory, eval intelligence |

Dark mode should be elegant, but light mode should feel equally first-class. Many enterprise builders work in bright environments and screen-share often.

### 5.3 Typography

Use a highly legible UI typeface with a refined monospace pairing. The product should distinguish prose, config, IDs, code, traces, and metrics at a glance.

| Text type | Treatment |
|---|---|
| Page title | 24-28 px, medium weight, tight but not compressed |
| Section title | 16-18 px, semibold |
| Body | 14-15 px, regular |
| Metadata | 12-13 px, muted |
| Code/config | Monospace, 13 px, line-height optimized for scanning |
| Metrics | Tabular numerals, consistent decimal precision |

Do not use oversized marketing headings inside operational screens. The product should reserve drama for trace comparisons, migration results, deploy blockers, and cost anomalies.

### 5.4 Layout

The core layout should use resizable panes:

```text
+------------+------------------------------+----------------------+
| Navigation | Main work surface            | Inspector            |
|            |                              |                      |
| Agents     | Agent workbench / traces /   | Selected node, span, |
| Tools      | evals / migration mapping    | tool, chunk, diff    |
| Knowledge  |                              |                      |
+------------+------------------------------+----------------------+
```

The inspector is sacred. Selection should never throw the user into a dead end. Selecting anything meaningful should reveal its details, history, dependencies, risks, and next actions.

### 5.5 Motion

Motion should communicate state changes:

- pane transitions under 180 ms
- trace bars animate into place as data arrives
- deploy stages progress with crisp state changes
- migration mapping lines draw only when they help explain conversion
- no idle decorative loops, floating shapes, or ornamental motion in production surfaces

Motion should make Studio feel alive, not busy. The builder should feel the system responding with craft: fast, grounded, and exact.

### 5.6 Delight system

Loop should have deliberate delight. The product can be exciting without becoming unserious.

Delight belongs in moments where the builder gains confidence:

- first trace generated
- first eval case created
- migration inventory completed
- parity threshold reached
- staging deploy passed
- canary promoted cleanly
- cost anomaly explained
- tool schema validated
- knowledge source becomes queryable

Delight should be restrained and tactile:

- crisp check transitions
- elegant progress strokes
- subtle glow on newly validated objects
- short-lived highlight on changed rows
- smooth count-up for meaningful metrics
- gentle panel settle after save
- live trace bars drawing into place
- diff lines sliding into alignment
- migration mappings connecting with a precise snap

Avoid empty celebration. Do not celebrate actions that merely move risk forward, such as production deploy started, eval override, budget increase, or cutover initiated. Celebrate proof, not hope.

### 5.7 Animation grammar

Use a small, consistent motion language.

| Motion | Duration | Use |
|---|---:|---|
| Snap | 80-120 ms | Toggle, checkbox, selected row, copied ID |
| Slide | 140-180 ms | Drawer open, inspector change, tab transition |
| Settle | 180-240 ms | Saved panel, reordered list, mapping accepted |
| Reveal | 200-320 ms | Trace bars, deploy timeline stages, import inventory |
| Count | 400-700 ms | Cost, latency, parity score, eval pass count |
| Focus pulse | 500-900 ms | Newly created eval, changed config, source lineage link |

Easing should feel precise:

- fast-out, soft-in for panels
- linear for trace timelines
- stepped progress for deploy stages
- no bouncy easing on production or error states
- reduced-motion mode replaces movement with opacity and state labels

### 5.8 Living surfaces

Studio should feel connected to real systems.

Use living surfaces where real-time data matters:

- trace waterfall streams spans as they arrive
- deploy timeline updates stage by stage
- eval run shows cases completing in batches
- migration import reveals inventory as it parses
- tool test console streams request, response, retries, and redactions
- cost dashboard updates projections after simulation inputs change
- knowledge ingestion shows source, chunk, embed, index, and ready stages

The UI should never fake liveness. If data is cached, say so. If progress is estimated, label it as estimated.

### 5.9 Pleasant texture

Polish should come from material quality and spatial rhythm:

- thin, quiet dividers instead of heavy boxes
- panels that feel layered, not stacked
- hover states that reveal affordance without jumping layout
- focus states that are beautiful and obvious
- selected states with a clear left rail or inner stroke
- soft surface contrast between editor, inspector, and chrome
- restrained gradients only when they encode status or depth
- chart colors that remain readable in light and dark mode
- skeletons shaped like the real content

Avoid generic SaaS decoration. No decorative blobs, background ornaments, fake 3D cards, or mascot-driven empty states. If a visual element does not clarify work, status, risk, or progress, remove it.

### 5.10 Excitement without noise

The product should create excitement through momentum:

- "You are one step from staging" progress cues
- "3 gaps left before parity" migration countdown
- "This replay is 42% cheaper with no eval regression" comparison callout
- "Canary has 100 clean turns" promotion moment
- "12 production failures converted into eval coverage" quality moment
- "Refund tool validated against 8 scenarios" tool readiness moment

These moments should feel satisfying, almost game-like, but never gamified in a way that trivializes production. The builder is not collecting badges; they are increasing confidence.

---

## 6. The Main Product Surface: Agent Workbench

The Agent Workbench is the default screen for a builder. It replaces the legacy idea of a chatbot canvas.

### 6.1 Workbench anatomy

```text
+------------------------------------------------------------------+
| support-concierge    Draft v24    Staging    Unsaved changes      |
+--------------+--------------------------------------+------------+
| Agent map    | Live simulator / config / diff       | Inspector  |
|              |                                      |            |
| Purpose      |                                      | Selection  |
| Behavior     |                                      | details    |
| Tools        |                                      |            |
| Knowledge    |                                      | Risks      |
| Memory       |                                      |            |
| Channels     |                                      | Actions    |
| Evals        |                                      |            |
| Deploy       |                                      |            |
+--------------+--------------------------------------+------------+
```

### 6.2 Agent profile

The builder should see the agent as a structured production object:

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
- environments and deploy state

Every profile section should have:

- current config
- last changed by
- diff from production
- validation status
- quick test action

### 6.3 Behavior editor

The behavior editor should support three levels:

1. Plain-language instructions for builders who want speed.
2. Structured policies for reliability: goals, constraints, refusal rules, escalation rules, tone, compliance boundaries.
3. Code/config view for advanced users.

The UI should show risk flags inline:

- ambiguous instruction
- tool not granted
- missing eval coverage
- cost risk
- memory overreach
- conflicting policy
- unsupported channel behavior

The builder can accept suggestions, but the product must show the exact diff before applying them.

### 6.4 Agent map

Instead of a flow canvas, show a compact dependency map:

```text
User channels -> Agent behavior -> Tools
                             | -> Knowledge
                             | -> Memory
                             | -> Evals
                             | -> Deploy policy
```

The map is not where builders draw logic. It is where they understand the agent's operational shape.

---

## 7. Simulator and Conversation Lab

The simulator should be the fastest way to develop confidence.

### 7.1 Multi-channel simulation

The builder can test the same agent through:

- web chat
- Slack
- WhatsApp
- SMS
- email
- voice
- custom webhook

The simulator should preserve channel constraints:

- SMS character pressure
- WhatsApp templates and opt-in constraints
- Slack threading
- email subject/body/attachments
- voice interruption and latency
- web streaming

### 7.2 Test controls

Every simulated run should allow:

- environment selection
- agent version selection
- model alias override
- temperature override
- tool allow/deny toggles
- knowledge snapshot selection
- memory snapshot selection
- user profile fixture
- channel fixture
- budget cap simulation
- latency injection
- tool failure injection

### 7.3 Result view

Each run shows:

- response
- tool calls
- retrieved chunks
- memory reads/writes
- model input/output
- cost
- latency
- policy flags
- eval scorer results
- trace waterfall

One click turns any simulator run into:

- an eval case
- a regression fixture
- a replay baseline
- a bug report
- a migration parity sample

---

## 8. Trace Theater

Trace view should be the signature Loop experience. It should be visually distinctive, technically deep, and instantly useful.

### 8.1 Trace summary

At the top:

- outcome
- total latency
- total cost
- provider/model
- tool count
- retrieval count
- memory writes
- eval score if attached
- deploy version
- channel

### 8.2 Waterfall

The waterfall should make the turn understandable in seconds:

- LLM spans
- tool spans
- retrieval spans
- memory spans
- channel spans
- retries
- provider failover
- budget checks
- policy checks

Color is useful but never the only indicator. Every span has label, duration, and status.

### 8.3 Span inspector

Selecting a span opens:

- inputs
- outputs
- redacted secrets view
- raw payload
- normalized payload
- cost math
- retry history
- linked logs
- linked eval cases
- linked migration source if imported

### 8.4 Explain without inventing

The trace can include generated summaries, but they must cite concrete trace facts:

- "The answer changed because the `refund_policy_2026.pdf` chunk ranked above the older policy."
- "The deploy failed because eval case `refund-window-basic` regressed from 0.91 to 0.72."
- "Cost increased because the tool error caused two extra model iterations."

No hand-wavy "the model likely reasoned" copy.

---

## 9. Tools Room

Tools should feel safe to expose to an agent.

### 9.1 Tool catalog

The builder can add:

- MCP servers
- OpenAPI-backed HTTP APIs
- Python functions
- TypeScript functions
- webhooks
- database queries
- internal services
- marketplace connectors

### 9.2 Tool detail

Every tool has:

- schema
- permissions
- auth
- secrets
- sample calls
- test console
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

### 9.3 Safe tool exposure

Before a tool is available in production, Studio should answer:

- Can this tool mutate data?
- Can this tool spend money?
- Can this tool expose personal data?
- Which agents can call it?
- Which arguments are secret or sensitive?
- What happens when it fails?
- How is it tested?
- How is it audited?

The best UI here is a permissions contract, not a form dump.

---

## 10. Knowledge Atelier

Knowledge should feel inspectable, curatable, and measurable.

### 10.1 Source management

The builder can add:

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

Each source shows sync status, freshness, owner, access rules, chunk count, last errors, and eval coverage.

### 10.2 Retrieval playground

The builder can ask a question and see:

- top retrieved chunks
- hybrid score breakdown
- semantic score
- keyword score
- metadata filters
- source freshness
- citation preview
- answer preview
- missed candidates

The UI should make retrieval mistakes obvious:

- "Correct document ranked 8th."
- "Two stale chunks outrank current policy."
- "No chunk contains the requested term."
- "This answer has no citation support."

### 10.3 Readiness report

After ingestion, Loop should generate:

- likely answerable questions
- likely unanswerable questions
- duplicate sources
- stale sources
- missing metadata
- generated eval cases
- citation quality estimate
- sensitive data warnings

This turns knowledge upload into an immediate quality loop.

---

## 11. Memory Studio

Memory should be visible and controlled. Builders should never wonder what the agent remembers.

### 11.1 Memory explorer

Show:

- session memory
- user memory
- episodic memory
- scratch state during a turn
- retention policy
- last write
- writer version
- source trace
- confidence
- deletion controls

### 11.2 Memory diff

Every turn should show memory changes:

```text
Before: preferred_language = unknown
After:  preferred_language = "English"
Source: user said "English is fine"
Policy: durable user memory
```

### 11.3 Memory safety

Flag:

- secret-like values
- PII writes
- conflicting facts
- stale facts
- memory without source trace
- channel-specific facts being stored globally

---

## 12. Eval Foundry

Evals should be core to building, not a separate QA chore.

### 12.1 Eval creation

The builder can create evals from:

- manual cases
- production conversations
- failed turns
- migration transcripts
- knowledge sources
- policy docs
- generated adversarial cases
- support macros
- customer issue categories

### 12.2 Eval suite builder

Each suite has:

- intent
- owner
- required deploy gate
- scorer mix
- datasets
- fixtures
- model/provider locks
- threshold
- historical trend
- flaky case detection

### 12.3 Eval result view

The result view should be brutally useful:

- what regressed
- what improved
- why it matters
- exact before/after outputs
- trace diff
- tool diff
- retrieval diff
- memory diff
- cost and latency delta
- recommended fix

The builder should be able to fix a regression directly from the result screen.

---

## 13. Deployment Flight Deck

Deploying an agent should feel like shipping production software.

### 13.1 Preflight

Before deploy, Studio shows:

- behavior diff
- tool diff
- knowledge diff
- memory policy diff
- channel diff
- budget diff
- eval result
- expected cost change
- risk flags
- approval requirements
- rollback target

### 13.2 Deploy path

Ideal flow:

1. Save draft.
2. Run simulator.
3. Run evals.
4. Review preflight.
5. Deploy to staging.
6. Canary to production.
7. Watch live traces.
8. Promote or rollback.

### 13.3 Deployment UI

The deployment view should show an active timeline:

```text
Build artifact    passed    18s
Security scan     passed    7s
Evals             passed    124/124
Staging smoke     passed    2m 04s
Canary 10%        active    42 turns
Canary 50%        waiting   needs 100 clean turns
Production 100%   locked    pending promotion
```

Every failure links to the exact trace, eval, log, or policy that caused it.

---

## 14. Cost and Capacity Control

Cost UI should make the builder feel financially safe.

### 14.1 Cost surfaces

Show cost:

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

### 14.2 Cost decisions

The builder can:

- set soft caps
- set hard caps
- define degrade rules
- compare model costs
- simulate traffic increases
- detect anomalous tool loops
- estimate campaign cost before launch
- attribute spend to teams or customers

### 14.3 Cost copy

Use concrete math:

```text
This turn cost USD $0.0184.
Model: $0.0151
Tools: $0.0019
Retrieval: $0.0007
Runtime: $0.0007
```

Never hide line items that affect production decisions.

---

## 15. Builder Control Model

The builder should always understand whether they are exploring, editing, testing, or changing production. Studio should make state boundaries impossible to miss.

### 15.1 Object state

Every major object has explicit state:

| State | Meaning | UX treatment |
|---|---|---|
| Draft | Editable, not deployed | Clear unsaved badge, diff to last saved version |
| Saved | Persisted but not staged | Can run simulator and evals |
| Staged | Deployed to staging environment | Visible staging badge, smoke-test status |
| Canary | Receiving limited production traffic | Traffic percentage, live health, promote/rollback |
| Production | Active production version | Strong badge, protected edits, rollback target |
| Archived | No longer active | Read-only, lineage preserved |

State should appear in the header, version history, command palette results, and object inspector.

### 15.2 Undo and recovery

Every non-production editing action should be undoable. Every production action should be reversible where technically possible.

Required recovery patterns:

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

Builders should be able to experiment aggressively because recovery is obvious.

### 15.3 Preview before apply

High-impact actions must show a preview:

- deploying version
- enabling mutating tool
- changing memory retention
- adding channel
- increasing budget cap
- overriding eval gate
- applying AI-generated behavior rewrite
- accepting migration mapping
- cutting over from source platform

Preview should include exact object diff, affected environments, policy checks, cost implications, and rollback path.

### 15.4 Permission clarity

Disabled controls should explain the permission or policy that blocks them:

```text
Deploy to production is locked.
Reason: production deploy requires approval from Workspace admin.
Next: request approval for v24.
```

Never hide unavailable actions from builders who need to understand the workflow. Hide only actions that are irrelevant to their role.

### 15.5 Evidence trail

Every meaningful change should automatically capture:

- actor
- object
- previous value
- new value
- linked diff
- reason if supplied
- approval if required
- trace/eval/deploy reference
- timestamp

The evidence trail should be useful to the builder first and compliance second.

---

## 16. Migration and Porting

The porting experience should be one of Loop's strongest differentiators. A builder should feel that leaving a legacy platform is structured, measurable, and low-risk.

### 16.1 Migration entry point

The first-run screen should offer:

- Create from template
- Import from existing platform
- Connect Git repository
- Start blank

Import should never feel secondary. For many builders, migration is the product.

### 16.2 Supported import targets

Initial importers should prioritize:

| Source | Typical input | Loop goal |
|---|---|---|
| Botpress | `.bpz` export or connected workspace | Convert flows, KBs, actions, integrations, tables, variables, transcripts |
| Voiceflow | `.vf`, `.vfr`, or project API export | Convert intents, paths, variables, API blocks, knowledge, transcripts |
| Dialogflow CX/ES | agent export archive or cloud export | Convert intents, flows, routes, fulfillments, training phrases |
| Rasa | Git repo or project zip | Convert domain, stories/rules, NLU data, actions, endpoints |
| Dify | YAML DSL export | Convert app config, workflow, tools, knowledge, variables |
| Microsoft Copilot Studio | solution export | Convert topics, actions, entities, channels where possible |
| Langflow / Flowise | JSON graph export | Convert graph nodes into tools, routines, and eval fixtures |
| n8n / Zapier-style automations | workflow JSON | Convert automations into tools and event handlers |
| Custom framework | Git repo, OpenAPI, transcripts | Generate tools, behavior draft, evals, and migration gaps |

### 16.3 Import wizard

The wizard should be beautiful, calm, and brutally clear.

```text
Step 1: Choose source
Step 2: Upload export or connect account
Step 3: Analyze project
Step 4: Review inventory
Step 5: Map to Loop
Step 6: Resolve gaps
Step 7: Generate agent
Step 8: Prove parity
Step 9: Stage cutover
```

### 16.4 Inventory report

After analysis, show:

- agents/bots
- flows/topics/stories
- nodes/blocks
- actions/functions
- tools/APIs
- knowledge bases
- tables/entities
- variables
- secrets
- channels
- transcripts
- analytics
- unsupported features

Each item receives:

- import status
- confidence score
- mapped Loop primitive
- required user action
- production risk

### 16.5 Mapping model

Porting should preserve behavior, not diagrams.

| Legacy concept | Loop destination |
|---|---|
| Bot/workspace assistant | Agent |
| Flow/topic/story | Behavior routine or eval-backed instruction section |
| Node/block/card | Routine step, tool call, channel response, or policy |
| Action/hook/function | Tool or lifecycle handler |
| Knowledge base | Knowledge source |
| Table/entity | Structured data source or tool-backed store |
| Variable | Memory, config, or channel state |
| Integration | Tool, channel, or MCP server |
| Transcript | Eval case and replay fixture |
| Human handoff | Escalation policy and operator inbox route |
| Analytics event | Trace/cost/quality metric |

### 16.6 Migration confidence

Show a migration score, but make it explainable:

```text
Migration readiness: 82%

Cleanly imported:      147 items
Needs review:           23 items
Secrets to reconnect:    8 items
Unsupported:             4 items
Parity tests passing:   91 / 100
```

The score should never be a vanity metric. Clicking it opens the blockers.

### 16.7 Gap resolution

The builder should resolve migration gaps in-place:

- reconnect secret
- choose memory scope
- map old integration to MCP server
- rewrite unsupported node as tool
- convert deterministic branch into eval/policy
- mark behavior as intentionally dropped
- create custom adapter
- request migration support package

### 16.8 Botpress-specific experience

Botpress import should feel especially polished.

The importer should:

- accept `.bpz` bot archives
- parse bot structure
- extract workflows, nodes, cards, KBs, tables, actions, hooks, variables, integrations, and transcripts when present
- identify autonomous nodes and convert them into Loop behavior sections with tool grants
- convert Botpress KBs into Loop knowledge sources
- convert actions and hooks into tools or lifecycle handlers
- convert tables into structured data tools or managed tables
- convert variables into memory/config recommendations
- map channel integrations into Loop channel setup tasks
- generate eval cases from transcripts and flow examples
- produce a parity report
- preserve original IDs for traceability

The imported agent should include a "Source lineage" panel:

```text
Loop behavior: Refund policy routine
Imported from: Botpress workflow "refunds"
Original nodes: refund_start, lookup_order, refund_decision, escalation
Confidence: 88%
Review reason: custom JavaScript action uses external secret
```

### 16.9 Parity proof

Parity is the killer migration feature.

The builder uploads or selects historical transcripts, then Loop runs them against the imported agent and reports:

- outcome match
- answer quality delta
- tool call parity
- escalation parity
- cost delta
- latency delta
- policy violations
- unresolved behavior gaps

Report sections:

- Executive summary
- Passing scenarios
- Regressions
- Improvements
- Unsupported behavior
- Cutover risks
- Recommended fixes

This report should be exportable as PDF and shareable with stakeholders.

### 16.10 Cutover

Migration should end with a staged cutover plan:

- connect production channel
- run shadow traffic
- compare outcomes
- canary by percentage or segment
- freeze legacy platform changes
- promote Loop to primary
- keep rollback route
- archive source mapping

The product should never imply "import complete" means "safe for production." Safe means parity measured, deploy gated, and rollback ready.

### 16.11 Migration workspace

The migration workspace should remain available after cutover. Builders need lineage when production behavior is questioned months later.

It should contain:

- original source archive
- parsed inventory
- generated Loop objects
- mapping decisions
- unresolved gaps
- accepted risks
- parity runs
- cutover events
- rollback plan

Every imported object in Loop should retain a source link:

```text
Imported from Botpress
Project: acme-support
Workflow: refunds
Node: refund_decision_4
Imported at: 2026-05-05 13:44 UTC
Mapping confidence: medium
```

### 16.12 Migration diff modes

Builders should be able to compare old and new behavior in four ways:

| Mode | Shows |
|---|---|
| Structure diff | old flows/topics/actions against Loop agent/tools/knowledge |
| Behavior diff | transcript outcome, escalation, and answer differences |
| Cost diff | projected Loop cost against historical platform cost where data exists |
| Risk diff | unsupported source features, missing secrets, policy conflicts |

The UI should make it clear when a difference is an improvement, an intentional change, or an unresolved regression.

### 16.13 Migration assisted repair

For each gap, Studio should suggest one or more repairs:

- replace legacy integration with MCP server
- convert JavaScript action into typed tool
- convert route condition into eval-backed behavior rule
- map variable into session memory
- map persistent customer data into user memory
- split overloaded workflow into multiple tools or routines
- create channel-specific response variant
- mark as intentionally unsupported

Suggestions should be ranked by confidence and always preview generated code/config.

---

## 17. Enterprise Builder UX

Enterprise builders need confidence that Studio fits their organization.

### 17.1 Environments

Support:

- development
- staging
- production
- region-specific environments
- customer-specific sandboxes
- approval-gated environments

Every config diff should be environment-aware.

### 17.2 Review and approval

High-risk changes require approval:

- production deploy
- new mutating tool
- new external channel
- budget increase
- secret access change
- memory retention change
- eval gate override
- migration cutover

Approval screens should show precise risk summaries, not generic confirmation dialogs.

### 17.3 Policy center

Admins define:

- allowed model providers
- allowed tools
- channel restrictions
- data residency
- PII handling
- retention defaults
- eval gate requirements
- deploy approval rules
- cost limits

Builders see policy constraints inline while building, not only after failure.

### 17.4 Audit evidence

Every enterprise action should produce evidence:

- who changed it
- what changed
- why it changed
- approval chain
- affected agents
- affected environments
- linked trace/eval/deploy
- exportable report

Compliance should feel like a byproduct of good UX.

---

## 18. Onboarding

### 18.1 First session

The first session should offer three confident paths:

1. Import existing platform.
2. Start from a template.
3. Build from scratch.

The product should ask what the builder is trying to ship:

- support agent
- sales assistant
- internal IT agent
- voice receptionist
- knowledge assistant
- workflow operator
- custom

Then it should scaffold the right workbench, sample evals, tools, and channel simulator.

### 18.2 Empty states

Empty states should be useful, not decorative:

- "Import your Botpress export."
- "Connect your first tool."
- "Upload a policy doc."
- "Run this transcript as an eval."
- "Deploy to staging."

Each empty state should lead to one concrete next action.

### 18.3 Learning by doing

Avoid long tours. Let builders learn by completing work:

- "Add a tool" creates a working tool test.
- "Upload docs" creates retrieval evals.
- "Import project" creates a parity report.
- "Run simulation" creates a trace.
- "Deploy staging" creates a rollback target.

---

## 19. Command Palette and Keyboard UX

The command palette should be a first-class control plane.

It should support:

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
- search settings
- copy IDs
- open docs
- switch environment
- compare versions

Search should understand IDs, names, routes, trace IDs, user IDs, and natural language:

```text
"last failed refund trace"
"deploy support agent to staging"
"show whatsapp costs yesterday"
"import botpress"
```

Commands that mutate production require confirmation and respect permissions.

---

## 20. AI Assistance Inside Studio

AI assistance should be powerful but subordinate to builder control.

### 20.1 Useful assistant jobs

The assistant can:

- explain a trace using cited spans
- suggest evals from production failures
- suggest tool schema fixes
- propose migration mappings
- summarize deploy risk
- find cost anomalies
- generate retrieval test questions
- draft a behavior policy
- identify missing docs
- compare versions

### 20.2 Guardrails

AI suggestions must:

- show source evidence
- be diffable
- be reversible
- never silently change production
- never hide generated assumptions
- never invent unavailable telemetry

The assistant should make the builder faster, not blur accountability.

---

## 21. Collaboration

Builders rarely work alone. Studio should support product, engineering, support, security, and compliance collaboration.

### 21.1 Comments

Allow comments on:

- traces
- eval cases
- tool configs
- knowledge chunks
- deploys
- migration gaps
- cost anomalies

Comments should support mentions, links, status, and resolution.

### 21.2 Change review

Every draft version should have a review page:

- summary
- diffs
- test results
- risk flags
- comments
- approvals
- deploy button

### 21.3 Handoff

A builder should be able to send:

- "review this eval regression"
- "approve this tool"
- "inspect this trace"
- "validate this migration gap"
- "approve production cutover"

The recipient lands on the exact object with context.

---

## 22. Responsive Behavior

Studio is primarily desktop software, but should degrade intelligently.

### 22.1 Desktop

Desktop is full power:

- three-pane layout
- resizable panels
- trace theater
- side-by-side diffs
- keyboard workflows
- dense tables

### 22.2 Tablet

Tablet supports review:

- two-pane layout
- readable trace summaries
- approval flows
- conversation review
- cost dashboards

### 22.3 Mobile

Mobile supports urgent actions:

- acknowledge incident
- view deploy status
- approve/deny request
- rollback
- inspect summary
- view cost alert

Do not force full agent editing onto mobile.

---

## 23. Performance Expectations

The UI should feel instant.

| Interaction | Target |
|---|---:|
| Navigate between main sections | under 200 ms after shell load |
| Open command palette | under 80 ms |
| Filter table client-side | under 100 ms for visible data |
| Open trace summary | under 500 ms |
| Render first trace waterfall frame | under 800 ms |
| Run simulator first token | visible as soon as stream begins |
| Save draft config | under 500 ms optimistic |
| Show deploy preflight | under 2 s for normal agents |
| Migration inventory for medium project | first results under 10 s |

Long operations should stream progress with named stages and partial results.

---

## 24. State Design

### 24.1 Loading

No full-page spinners. Show skeletons, partial content, stage labels, and cancel options for long jobs.

### 24.2 Errors

Every error shows:

- what failed
- why, if known
- affected object
- next action
- retry option where safe
- link to trace/log/policy when relevant

### 24.3 Empty

Every empty state creates momentum:

- import
- create
- connect
- run
- deploy
- invite

### 24.4 Degraded

If upstream systems are degraded, the UI should still be useful:

- cached data visible
- read-only mode clear
- retry queued actions
- status shown inline
- incident link present

### 24.5 Friendly precision copy

Use copy that reduces anxiety and increases control.

| Moment | Weak copy | North-star copy |
|---|---|---|
| Eval failed | Deployment failed | Promotion blocked. `refund_window_basic` regressed from 0.91 to 0.72. Open the diff or keep v23 live. |
| Tool permission missing | Unauthorized | This agent cannot call `refund_order`. Grant the tool in Tools or remove it from the behavior policy. |
| Import gap | Unsupported node | This Botpress node uses custom JavaScript with a secret. Convert it into a typed Loop tool and reconnect the secret. |
| Cost risk | High cost | Projected month-end cost is USD $1,240, 2.4x above cap. Degrade to `fast` after USD $500 or raise the cap. |
| Trace missing | No data | Trace is still ingesting. Last event arrived 3s ago. Refresh automatically for 30s. |

Friendly precision means naming the object, the reason, and the next action.

---

## 25. Accessibility and Inclusion

The experience must be polished for keyboard, screen reader, low vision, and high-contrast users.

Requirements:

- full keyboard navigation
- visible focus states
- accessible data tables
- non-color status indicators
- screen-reader summaries for trace waterfalls and charts
- reduced-motion support
- high-contrast theme
- resize-friendly text
- no tiny tap targets for critical actions
- copy that explains terms in context

The trace waterfall must have an accessible alternate view: a sortable table of spans with duration, kind, status, and links to details.

---

## 26. Design System Components

Core components:

- App shell
- Command palette
- Agent selector
- Environment switcher
- Version pill
- Status badge
- Risk badge
- Cost badge
- Latency badge
- Eval score cell
- Trace waterfall
- Span inspector
- Tool call card
- Retrieval card
- Memory diff card
- Conversation stream
- Simulator panel
- Diff viewer
- Migration mapper
- Mapping confidence badge
- Parity report
- Deployment timeline
- Approval panel
- Audit event row
- Policy banner
- Empty state action panel
- Live progress rail
- Stage timeline
- Confidence meter
- Readiness checklist
- Source lineage chip
- Diff highlight ribbon
- Run completion flourish
- Guided next-step panel
- Inline evidence callout

Components should be composable across build, test, ship, observe, and migrate surfaces.

### 26.1 Polish primitives

The design system should include small primitives for craft and delight:

| Primitive | Purpose |
|---|---|
| `FocusPulse` | Briefly highlights a newly created or changed object |
| `MetricCountUp` | Animates meaningful numeric changes with tabular numerals |
| `StageStepper` | Shows named progress through import, eval, deploy, ingest |
| `EvidenceCallout` | Connects a recommendation to traces, evals, or source docs |
| `ConfidenceMeter` | Shows high/medium/low confidence with explanation |
| `DiffRibbon` | Marks changed lines or config blocks without noisy color fills |
| `LiveBadge` | Indicates data is streaming, cached, stale, or estimated |
| `CompletionMark` | Restrained success transition for proof moments |
| `RiskHalo` | Subtle visual treatment around blocked or risky controls |

These primitives should be accessible, theme-aware, and disabled or simplified in reduced-motion mode.

---

## 27. Screen Blueprints

### 27.1 Home

Purpose: orient the builder in under 10 seconds.

Shows:

- agents needing attention
- failed evals
- active deploys
- cost anomalies
- migration progress
- recent production failures
- suggested next work

No marketing hero. The home screen is a work queue.

### 27.2 Agent overview

Purpose: understand one agent's production shape.

Shows:

- purpose
- owner
- production version
- draft changes
- channels
- tools
- knowledge
- memory
- eval gates
- budget
- health
- recent traces
- next recommended action

### 27.3 Build tab

Purpose: edit behavior and dependencies.

Includes:

- behavior sections
- tool grants
- knowledge grants
- memory policy
- escalation policy
- channel-specific variants
- code/config view

### 27.4 Test tab

Purpose: prove behavior before deploy.

Includes:

- simulator
- eval suites
- red-team cases
- replay from production
- scenario fixtures
- regression diffs

### 27.5 Ship tab

Purpose: deploy safely.

Includes:

- preflight
- versions
- deploy timeline
- canary controls
- approval
- rollback

### 27.6 Observe tab

Purpose: debug production.

Includes:

- conversations
- traces
- tool calls
- retrieval
- memory writes
- quality metrics
- cost

### 27.7 Migrate tab

Purpose: port from an existing platform.

Includes:

- import history
- source inventory
- mapping view
- gap resolution
- parity tests
- cutover plan
- exportable reports

---

## 28. Anti-Patterns

Do not build:

- a giant drag-and-drop flow editor as the primary interface
- decorative dashboards that do not answer operational questions
- a joyless admin console with no sense of progress or craft
- motion that hides latency instead of explaining progress
- celebration for risky or incomplete work
- hidden prompts or hidden tool selection
- vague health scores without drill-down
- migration that only imports files without parity proof
- deploy buttons without preflight and rollback
- cost dashboards that hide channel or provider line items
- settings pages that bury essential agent behavior
- AI suggestions that mutate production without review
- empty states that merely say nothing exists
- tables without search, filters, saved views, and keyboard support

---

## 29. Screen Quality Bar

Every Studio screen should pass this checklist before it is considered good enough.

### 29.1 Clarity

- The screen has one primary job.
- The page title names the object or workflow, not the internal service.
- The primary action is obvious.
- The current environment and version are visible when relevant.
- Empty, loading, error, and degraded states are designed.

### 29.2 Control

- The builder can preview high-impact changes.
- The builder can see what changed from production.
- The builder can undo or recover from non-production edits.
- Production actions show the rollback path.
- Disabled actions explain why they are disabled.

### 29.3 Precision

- Numbers include units.
- Status labels are specific.
- Health scores drill down to raw evidence.
- AI-generated summaries cite concrete traces, evals, costs, or source items.
- Tables expose sorting, filtering, saved views, and export when the data is operationally useful.

### 29.4 Friendliness

- The screen suggests the next useful action.
- First-time users get examples without losing access to advanced controls.
- Error copy says what failed and what to do.
- Forms include tested defaults.
- Complex workflows show progress by named stage, not vague percentage.

### 29.5 Enterprise readiness

- Audit-relevant actions are recorded.
- Secret and permission boundaries are visible.
- Approval requirements appear before the builder reaches a blocked deploy.
- Policy violations show the policy name and owner.
- Evidence can be exported or shared.

### 29.6 Craft

- Layout is stable under long names, long IDs, and empty data.
- Text never overlaps or truncates critical values without tooltip access.
- Interactive targets are comfortable and keyboard reachable.
- Density controls exist for heavy tables.
- Visual emphasis maps to risk and workflow importance.

### 29.7 Delight and polish

- The screen has at least one moment of pleasant responsiveness.
- Progress is visible for every operation that takes more than 1 second.
- Success states feel satisfying without becoming noisy.
- Motion clarifies cause and effect.
- Reduced-motion mode remains equally understandable.
- Visual polish supports trust, not decoration.

If a screen fails more than one category, it is not north-star quality yet.

---

## 30. Decision-Support Patterns

The best UI does not merely expose settings. It helps the builder make a better decision.

### 30.1 The "why this matters" strip

Use a compact strip when a change carries hidden consequences:

```text
Changing memory retention affects 3 agents, 2 eval suites, and 1 data policy.
Production deploy requires Security approval.
```

### 30.2 Recommendation with evidence

Recommendations should include:

- suggestion
- evidence
- expected benefit
- possible downside
- exact diff
- revert path

Bad recommendation:

```text
Improve your prompt.
```

Good recommendation:

```text
Add an escalation rule for refund disputes.
Evidence: 7 of 12 failed refund turns ended with unresolved policy conflict.
Expected effect: reduce failed refund evals.
```

### 30.3 Confidence language

Use confidence only when it is explainable:

| Confidence | Meaning |
|---|---|
| High | deterministic mapping, validated by test or exact schema match |
| Medium | likely mapping, needs builder review |
| Low | inferred from names or behavior, must be manually confirmed |
| Unsupported | no safe automatic mapping |

This applies especially to migration, retrieval, AI suggestions, and parity reports.

### 30.4 Next-best action

Every major object should compute a next-best action:

- create eval from recent failure
- reconnect secret
- run parity suite
- promote canary
- inspect cost anomaly
- add missing citation source
- approve tool permission
- rollback unhealthy deploy

The next-best action should be useful, dismissible, and grounded in data.

---

## 31. Success Metrics

### 31.1 Builder activation

- time to first successful simulator run
- time to first eval case
- time to first staging deploy
- time to first production deploy
- percentage of imported projects reaching parity threshold

### 31.2 Builder trust

- traces opened per failed turn
- replay usage after failures
- eval cases created from production
- deploy rollbacks avoided by preflight
- cost anomalies resolved before cap
- migration gaps resolved without support

### 31.3 Enterprise readiness

- approval flow completion time
- audit export usage
- policy violation rate
- SSO/role setup completion
- number of production deploys with full evidence package

### 31.4 Retention signals

- weekly active builders
- agents with eval gates enabled
- agents with at least one connected tool
- agents with monitored costs
- imported projects cut over to production

---

## 32. Minimum Lovable Product Slice

If only a narrow version can be built first, build this:

1. Agent workbench with structured profile.
2. Multi-channel simulator for web and Slack.
3. Trace theater with tool/retrieval/memory visibility.
4. Eval creation from conversation and simulator run.
5. Deploy preflight with eval gate and rollback.
6. Cost per turn and per agent.
7. Botpress import wizard with inventory, mapping, and parity report.

This slice embodies the product better than a broad but shallow admin console.

---

## 33. External Format Notes For Migration

Importer assumptions must be verified against official platform docs before implementation. Current public entry points to account for:

- Botpress supports bot import/export archives, commonly `.bpz`: https://www.botpress.com/docs/learn/reference/import-export-bots
- Voiceflow supports project export formats and APIs, including `.vf` and `.vfr`: https://docs.voiceflow.com/reference/fetchproject
- Dify supports YAML DSL import/export for app definitions: https://docs.dify.ai/en/guides/management/app-management
- Dialogflow CX supports agent export as binary or JSON package: https://cloud.google.com/dialogflow/cx/docs/reference/rest/v3/projects.locations.agents/export
- Dialogflow ES supports exporting an agent to a ZIP file: https://cloud.google.com/dialogflow/es/docs/reference/rest/v2/projects.agent/export
- Microsoft Copilot Studio supports export/import through solutions: https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-export-import-bots

These references are not UX dependencies. They exist so the migration UX does not promise an impossible source format.

---

## 34. Final Standard

The optimal Loop Studio UX is not "easy for non-technical users" at the expense of production truth. It is easy because it is clear, fast, inspectable, and honest.

The builder should leave every session with more confidence:

- the agent's behavior is understood
- the tools are safe
- the knowledge is grounded
- the evals are meaningful
- the deploy is reversible
- the cost is predictable
- the migration is measurable

That is the standard.
