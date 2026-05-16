# Verdict: Loop Studio should be an **agent control plane**, not an agent builder.

The best UX is closer to **GitHub + Datadog + LaunchDarkly + an audit binder**, wrapped around the central object: the **production agent**. Creation is only one moment. The real product is the loop: **define → test → deploy → observe → improve → prove**.

The premise is mostly right, but I would add three missing product objects:

**Agent Contract** — the plain-English and structured definition of what the agent is allowed to do, for whom, with what boundaries.

**Change Set / Release Candidate** — every edit should become a reviewable, testable change, not an invisible save.

**Evidence Pack** — every deployed version should carry proof: evals, approvals, policy diffs, tool permissions, data sources, and audit trail.

The hierarchy should become:

**Workspace → Project → Agent → Branch / Change Set → Version → Deployment → Evidence**

Channels are not agents. Prompts are not the product. Flows are not the mental model. The product is a governed operating system for production agents.

---

## 1. Ideal mental model

Loop Studio should teach users this mental model:

> “An agent is a production service with a mission, capabilities, policies, evidence, versions, and deployments.”

Not:

> “An agent is a prompt.”
>
> “An agent is a flow.”
>
> “An agent is a chatbot.”

The core metaphor should be **mission control for AI agents**.

Each agent has:

**A contract**
What it exists to do, who it serves, what it must never do, what success means, when it escalates, and what systems it may touch.

**Capabilities**
Tools, APIs, workflows, retrieval, memory, and channel adapters.

**Evidence**
Tests, evals, traces, simulations, approvals, monitoring, and audit records.

**Lifecycle state**
Draft, staging, release candidate, production, canary, rolled back, deprecated.

**Operational posture**
Healthy, degraded, blocked, risky, under review, or needing action.

The interface should constantly answer five questions:

1. What is this agent supposed to do?
2. What changed?
3. Is the change safe?
4. What is happening in production?
5. What should we do next?

That is the enterprise UX.

---

## 2. Best possible agent creation journey

Do not start with a blank canvas. Start with an **Agent Contract Wizard**.

The creation journey should feel fast, but it should create a serious production skeleton.

### Entry point

Primary CTA:

> **Create or import agent**

Then two strong paths:

> **Create new production agent**
> Define a mission, connect capabilities, generate tests, and deploy safely.

> **Migrate existing bot or automation**
> Import from Botpress, Dialogflow, Rasa, Zendesk, Intercom, or custom exports.

### New agent creation flow

#### Step 1: Mission

User enters:

* Agent name
* Business function
* Primary users
* Supported tasks
* Out-of-scope tasks
* Escalation destination
* Success metric

Example UI copy:

> **What job should this agent own?**
> Describe the business outcome, not the personality.

Example input:

> “Help enterprise customers troubleshoot billing issues, explain invoices, collect missing information, and escalate refund requests over $500.”

Loop should generate an initial **Agent Contract**:

```text
Mission
Resolve common billing support issues for enterprise customers.

Allowed work
- Explain invoice line items.
- Collect missing billing details.
- Check payment status.
- Create refund review tickets.
- Escalate disputed charges.

Not allowed
- Promise refunds.
- Change billing plans without approval.
- Reveal another customer’s invoice.
- Handle legal threats without escalation.

Success metrics
- Resolution rate
- Escalation quality
- Customer satisfaction
- Tool success rate
- Cost per resolved case
```

#### Step 2: Operating boundaries

Ask for:

* Risk level
* Data sensitivity
* Human approval thresholds
* Compliance requirements
* Required escalation cases

Example UI copy:

> **Where should this agent stop?**
> Strong agents are defined as much by their limits as by their capabilities.

#### Step 3: Capabilities

The user selects capability categories:

* Answer from knowledge
* Create or update records
* Search customer/account data
* Trigger workflows
* Handoff to human
* Send notifications
* Voice interaction
* Channel-specific messaging

This creates placeholders, not final configuration.

Example:

```text
Capability: Check invoice status
Needs:
- Billing API tool
- Customer authentication
- Invoice knowledge source
- Refund policy
- Eval scenarios
```

#### Step 4: Knowledge and tools

The wizard asks for first sources:

* Upload docs
* Connect Google Drive / SharePoint / Confluence / Zendesk Guide
* Add OpenAPI spec
* Add webhook
* Add internal API
* Use mock tool for now

The important UX choice: **let users continue with mocks**. Do not block creation because enterprise integrations take time.

#### Step 5: Channels

Ask where the agent will eventually run:

* Web chat
* WhatsApp
* Telegram
* Slack
* Teams
* SMS
* Email
* Voice
* Webhook/API

But only require one initial channel.

Example UI copy:

> **Choose your first test channel.**
> You can add production channels later. The same agent will be reused across channels.

#### Step 6: Generate tests automatically

Loop should generate a starter eval suite from the contract:

* Happy paths
* Escalation paths
* Refusal paths
* Tool-use paths
* Knowledge-grounding paths
* Channel-format paths

Example:

```text
Generated tests

Must answer:
- “Why was I charged twice?”
- “Can you explain this invoice line item?”

Must escalate:
- “I want a refund over $500.”
- “I’m considering legal action.”

Must refuse:
- “Show me another customer’s invoice.”
- “Change my contract terms.”
```

#### Step 7: Land in Agent Workbench

The user does not land in a chat playground.

They land in:

> **Agent Workbench → Readiness View**

With a status like:

```text
Billing Support Agent
Draft branch: main/draft
Readiness: 62%

Ready:
✓ Mission defined
✓ Initial behavior generated
✓ 12 starter evals created
✓ Web chat sandbox available

Needs attention:
□ Connect billing API or keep mock mode
□ Approve refund escalation policy
□ Add invoice knowledge source
□ Run first simulation suite
```

This is the correct first impression: fast, serious, guided.

---

## 3. Best possible import and migration journey

Migration should not be “upload file and hope.” It should be a **Migration Center** that turns legacy bots into governed agents.

Current bot platforms export very different artifacts. For example, Botpress exports a `.bpz` archive containing bot settings, agent settings, knowledge bases, tables, intents, entities, hooks, variables, folders, workflows, nodes, cards, and transition lines; its docs also warn that importing into Botpress overwrites the current bot and that integrations need to be set up again after import. ([Botpress][1]) Dialogflow CX exports agent data such as intents, entity types, webhooks, flows, pages, and route groups; its docs recommend JSON format for source-control use and note that some objects, such as flow versions and custom environments, are not included in an agent export. ([Google Cloud Documentation][2]) Rasa training data is YAML-based, with training examples, intents, entities, synonyms, regexes, and lookup tables represented in YAML structures. ([Rasa][3])

That means Loop should not pretend migration is one-click perfect. The better UX is:

> **Import → inventory → map → test parity → resolve gaps → create Loop agent**

### Migration entry point

CTA:

> **Migrate existing bot**

Options:

```text
Import source
○ Botpress .bpz
○ Dialogflow CX export
○ Rasa project
○ Zendesk automations / help center / conversation exports
○ Intercom Fin / Resolution bot content
○ Custom JSON / YAML / CSV
○ Conversation transcripts only
```

### Step 1: Upload or connect

For Botpress:

> **Upload Botpress `.bpz` archive**

For Dialogflow:

> **Upload Dialogflow CX JSON export or connect Google Cloud project**

For Rasa:

> **Upload Rasa project folder or YAML files**

For custom:

> **Upload exports, docs, transcripts, and API specs**

### Step 2: Migration inventory

Loop parses the source and shows a structured inventory:

```text
Imported from Botpress: “Billing Bot”

Detected
✓ 42 intents
✓ 19 workflows
✓ 88 nodes
✓ 13 knowledge sources
✓ 6 tables
✓ 4 integrations
✓ 7 hooks
✓ 3 channels
✓ 2,914 conversation transcripts

Needs review
⚠ 4 integrations require new credentials
⚠ 11 workflows contain hard-coded business rules
⚠ 8 nodes have no clear Loop equivalent
⚠ 3 knowledge sources are linked externally and must be reconnected
```

### Step 3: Mapping view

The migration UI should not preserve flows as sacred. It should map legacy artifacts into Loop’s agent model.

```text
Source artifact                  Loop target
------------------------------------------------------------
Intent: refund_request            Capability: Refund triage
Workflow: invoice_dispute          Task policy + eval scenarios
Node: ask_for_account_id           Slot/data collection rule
Hook: validate_customer            Tool: Customer lookup API
Knowledge base: billing_docs       Knowledge source: Billing docs
Table: refund_limits               Policy table / reference data
Channel: WhatsApp                  Channel adapter
Transcript failures                Regression eval set
```

This is the most important migration idea:

> Convert legacy flow structure into **capabilities, policies, tools, knowledge, and evals**.

Do not recreate a giant visual spaghetti canvas.

### Step 4: Confidence scoring

Each migrated element gets a confidence label:

```text
High confidence
- FAQ knowledge
- Intents with clear examples
- Static answer cards
- Basic escalation flows

Medium confidence
- Conditional workflows
- Entity extraction
- Form-filling paths
- Webhook calls

Low confidence
- Custom code hooks
- Complex fallback logic
- Multi-system workflows
- Channel-specific hacks
```

### Step 5: Parity test generation

Loop should automatically turn imported intents, transcripts, and known failure cases into regression tests.

Example UI copy:

> **We created 128 parity tests from your imported bot.**
> These tests check that the new agent can handle the same user goals, not that it follows the same old flow.

That distinction matters. Loop should optimize for outcome parity, not flow parity.

### Step 6: Migration board

A Kanban-like board is useful here, but not as a flow builder:

```text
Ready to migrate
- Billing FAQ
- Invoice explanation
- Payment status

Needs credentials
- Customer lookup API
- Refund ticket creation

Needs policy review
- Refund approval thresholds
- Contract cancellation handling

No direct equivalent
- Custom Botpress hook: normalizeInvoiceId()
- Legacy fallback workflow
```

### Step 7: Create Loop agent branch

The output of migration should be:

```text
Agent: Billing Support Agent
Branch: migration/botpress-billing-bot
Migration status: 74% ready

Generated:
✓ Agent Contract
✓ Behavior rules
✓ 6 capabilities
✓ 4 tools
✓ 13 knowledge sources
✓ 128 regression tests
✓ 3 channel adapters
✓ Migration evidence report
```

### Migration UX principle

Never say:

> “Migration complete.”

Say:

> “Production readiness: 74%. Here are the gaps to resolve before launch.”

That is enterprise-serious.

---

## 4. Best possible Agent Workbench structure

The **Agent Workbench** is the core product surface.

It should be a single place where the team can design, test, deploy, observe, and improve one agent.

### Overall layout

#### Persistent top bar

```text
Billing Support Agent       Draft: refund-policy-update
Production: v18             Health: Degraded
Last deploy: 2h ago         Open issues: 4
```

Controls:

* Branch selector
* Environment selector
* Version selector
* Deploy button
* Run tests button
* Open change set
* Command palette

#### Left navigation

Inside the agent only:

```text
Overview
Contract
Behavior
Tools
Knowledge
Memory
Channels
Simulations
Evals
Traces
Deployments
Observability
Governance
```

These should not be scattered across unrelated top-level product pages.

#### Center canvas

The active editor, table, simulator, trace, or deployment view.

#### Right evidence panel

Always contextual.

If editing behavior, the right panel shows:

* Related failed traces
* Affected evals
* Current production version
* Risk level
* Approval requirements

If editing a tool, it shows:

* Recent tool failures
* Latency
* Permissions
* Secrets
* Audit events

If editing knowledge, it shows:

* Retrieval tests
* Stale documents
* Coverage gaps
* Recent unanswered questions

#### Bottom test drawer

A collapsible test console:

> **Test this change**

From any edit surface, the user can run:

* One simulation
* Related evals
* Full regression suite
* Channel preview
* Tool dry run

This is crucial. Testing should be adjacent to editing, not somewhere else.

---

## 5. Best possible editing loop

The editing loop should be evidence-driven:

```text
Observe issue
→ Open trace or metric
→ Create change set
→ Edit behavior/tool/knowledge/memory/channel
→ Run targeted tests
→ Compare against production
→ Request approval
→ Deploy canary
→ Monitor
→ Roll forward or roll back
```

### Example: fixing a bad production answer

A support lead sees this in the homepage work queue:

```text
Issue detected
Refund disputes are escalating 23% more often after v18.

Recommended action
Review 14 traces where the agent escalated despite refund amount under $100.
```

They click it.

Loop opens a filtered trace set:

```text
Root cause hypothesis
The agent is treating “duplicate charge” as “billing dispute requiring human escalation.”

Suggested fix areas
1. Behavior rule: duplicate charge handling
2. Knowledge source: refund policy
3. Eval gap: no low-value duplicate-charge test
```

The user clicks:

> **Create change set from issue**

Loop creates:

```text
Change set: fix-duplicate-charge-escalation
Evidence linked:
- 14 production traces
- 1 metric anomaly
- 0 existing evals
```

The user edits behavior, adds a new eval, runs tests, then sees:

```text
Before
Escalated 14/14 duplicate-charge cases.

After
Resolved 11/14.
Escalated 3/14 because account verification failed.

Regression
Passed 214/216 tests.
Failed 2 refund-boundary tests.
```

This is the product’s core loop.

Not “edit prompt and try chat.”

---

## 6. How behavior, instructions, and policies should be edited

Behavior should not be edited as one giant prompt box.

It should be edited as a structured **Agent Contract + Behavior Policy** system.

### Behavior editor sections

```text
Mission
User types
Supported tasks
Boundaries
Escalation rules
Tool-use rules
Knowledge-use rules
Memory rules
Tone and communication
Channel presentation rules
Refusal rules
Compliance rules
Examples
```

### Policy cards

Example policy card:

```text
Policy: Refund approval boundary

Rule
The agent may explain refund eligibility and create a refund review ticket.
The agent must not promise or issue refunds.

Threshold
Refund amount greater than $500 requires escalation to Billing Operations.

Applies to
- Web chat
- Email
- WhatsApp
- Voice

Examples
✓ “I can create a refund review ticket for our billing team.”
✕ “Your refund has been approved.”
```

### Better than prompt editing

Loop can still show a compiled prompt, but it should be behind:

> **View compiled instructions**

Not the default editing interface.

The compiled version should be read-only or advanced-edit only.

### Semantic diffs

Approvals should not show raw text diffs only.

They should show semantic diffs:

```text
Changed policy: Refund approval boundary

Before
Refunds over $250 require human review.

After
Refunds over $500 require human review.

Risk impact
Higher financial exposure.

Required approvals
- Billing Owner
- Compliance Reviewer
```

### Instruction quality checks

When a user edits behavior, Loop should warn:

```text
Potential conflict detected

You added:
“Always resolve refund requests without escalation.”

This conflicts with:
“Refunds over $500 require Billing Operations approval.”
```

And:

```text
Coverage gap

This new rule has no evals.
Create 3 tests for refund approval boundaries?
```

This makes governance feel helpful, not bureaucratic.

---

## 7. How tools should be added, tested, governed, and monitored

Tools should be treated as **production capabilities**, not just function calls.

### Tool object model

Each tool should have:

```text
Name
Description
Owner
Environment
Authentication
Input schema
Output schema
Timeout
Rate limit
Retry policy
Idempotency
Data classification
Allowed agents
Allowed channels
Approval requirements
Audit requirements
Sandbox mode
Failure behavior
Compensation / rollback behavior
```

### Add tool journey

Entry:

> **Add tool**

Options:

```text
○ Import OpenAPI spec
○ Add REST endpoint
○ Add webhook
○ Add database query
○ Add internal workflow
○ Add human approval action
○ Add from tool catalog
```

### Tool setup flow

Example:

```text
Tool: Create refund review ticket

What this tool does
Creates a ticket in Zendesk for Billing Operations.

Risk level
Medium — creates operational records but does not move money.

Authentication
Service account via secret vault.

Allowed use
Only after customer identity is verified.

Requires approval
No, unless refund amount is greater than $500.

Failure behavior
Apologize, collect details, and escalate to human support.
```

### Tool test harness

Before a tool can be enabled:

```text
Required checks
✓ Schema validation
✓ Sandbox credential test
✓ Example call passed
✓ Failure response configured
✓ Data classification reviewed
✓ Tool-use eval created
```

### Tool monitoring

Tool page should show:

```text
Create refund review ticket

Production usage
- Calls: 8,492 this week
- Success rate: 97.8%
- p95 latency: 840ms
- Retry rate: 2.1%
- Failed calls linked to unresolved conversations: 43
- PII sent: customer_id, invoice_id, email
- Last schema change: v12
```

### Tool governance

Dangerous tools need explicit controls.

Example UI copy:

> **This tool can change customer entitlements.**
> Require human approval, restrict to verified users, or limit to staging only.

Tool risk tiers:

```text
Low
Read-only lookup.

Medium
Creates records or sends notifications.

High
Changes customer state, billing, access, legal status, or money movement.

Critical
Irreversible or regulated action.
```

---

## 8. How knowledge and retrieval should be managed

Knowledge should be managed as a **source registry with retrieval evidence**, not as a pile of uploaded files.

### Knowledge source object

```text
Name
Type
Owner
Connector
Sync status
Last indexed
Access permissions
Data classification
Region
Allowed agents
Allowed topics
Freshness requirement
Citation requirement
Fallback behavior
```

### Knowledge overview

```text
Billing Knowledge

Sources
✓ Zendesk Guide: Billing articles
✓ Confluence: Enterprise billing policies
✓ PDF: Refund policy Q2
⚠ SharePoint: Invoice FAQ — stale for 91 days
⚠ Website crawl: pricing pages — 14 contradictory chunks
```

### Retrieval testing

Each source should have a test console:

```text
Test query
“Why was I charged twice?”

Retrieved chunks
1. Duplicate charge policy — confidence 0.91
2. Invoice retry FAQ — confidence 0.76
3. Payment authorization hold — confidence 0.62

Answer grounded?
Yes

Missing?
No article explains duplicate charge timeline by region.
```

### Knowledge coverage map

Loop should show coverage by agent capability:

```text
Capability                    Knowledge coverage
------------------------------------------------
Explain invoice line items     Strong
Duplicate charge handling      Medium
Refund eligibility             Weak
Contract cancellation          Missing
```

### Contradiction detection

Example UI:

```text
Contradiction detected

Source A says:
Refund review threshold is $250.

Source B says:
Refund review threshold is $500.

Affected policies:
- Refund approval boundary
- Refund escalation rule

Recommended action:
Choose authoritative source or create explicit policy override.
```

### Knowledge should produce tests

When a source changes:

```text
Knowledge update detected
Refund policy changed.

Suggested actions:
- Re-run 18 refund-related evals.
- Review 4 behavior rules that reference refund thresholds.
- Create new version if production behavior should change.
```

This prevents silent drift.

---

## 9. How memory should be controlled and explained

Memory must be explicit, inspectable, and scoped.

No enterprise buyer wants mysterious memory.

### Memory scopes

```text
Session memory
Only for this conversation.

User memory
Persistent facts about one user.

Account memory
Facts about a customer account.

Organization memory
Shared facts for a customer organization.

Task memory
Temporary state for a workflow.

Agent memory
Operational learning for the agent, never private user facts.
```

### Memory rule cards

Example:

```text
Memory rule: Billing contact preference

May remember
Preferred billing contact email.

When
Only after user confirms.

Scope
Account memory.

Retention
180 days.

Never store
Credit card numbers, passwords, access tokens, tax IDs.

User control
Can be viewed and deleted on request.
```

### Memory write preview

During simulation or trace review:

```text
Proposed memory write

“The customer prefers invoices sent to finance@example.com.”

Scope
Account

Reason
User explicitly requested this preference.

Policy check
Allowed

Action
Approve automatically / Require review / Never store this type
```

### Memory explorer

Per agent:

```text
Stored memories
- 12,492 user memories
- 4,019 account memories
- 0 high-risk memories
- 83 deletion requests completed
- 4 blocked write attempts this week
```

Each memory should show:

* Source trace
* Created by which agent version
* Last used
* Retention
* Delete button
* Legal hold status
* Policy reason

### Runtime explainability

In traces:

```text
Memory used
- Account billing preference
- Preferred language: French
- Open invoice dispute ID

Memory not used
- Prior refund complaint, blocked by policy because unrelated to current task
```

That is the right level of explainability.

---

## 10. How omnichannel setup should work

Channels should be first-class peers, but the agent remains central.

The model:

```text
Agent core
→ Channel adapters
→ Channel deployments
```

Not:

```text
WhatsApp bot
Slack bot
Voice bot
Email bot
```

### Channel adapter object

Each channel has:

```text
Identity
Authentication
Message format
Interaction style
Supported actions
Handoff destination
Business hours
Consent / opt-in
Rate limits
Attachment rules
Fallback behavior
Channel-specific policy
Deployment status
```

### Channel overview

```text
Channels for Billing Support Agent

Web chat     Production v18    Healthy
WhatsApp     Canary v19        Watch latency
Slack        Staging v19       Awaiting approval
Email        Draft             Needs routing address
Voice        Sandbox           Needs escalation script
API          Production v18    Healthy
```

### Channel setup flow

Example: adding WhatsApp

```text
Add WhatsApp channel

1. Connect WhatsApp Business account
2. Configure identity and templates
3. Set opt-in and consent rules
4. Choose production version
5. Preview channel rendering
6. Run WhatsApp compatibility tests
7. Deploy to staging
```

### Channel preview matrix

For the same scenario, Loop should show:

```text
Scenario: Duplicate charge

Web chat
Compact answer + invoice link + escalation button.

WhatsApp
Short answer + numbered options + template-safe language.

Email
Full explanation + case summary + next steps.

Voice
Short spoken answer + confirmation prompts + escalation option.
```

This is where omnichannel becomes real.

### Voice as a peer channel

Voice needs special configuration, but should not dominate the product.

Voice adapter should include:

```text
ASR provider
TTS voice
Barge-in behavior
Silence timeout
Latency budget
Recording disclosure
DTMF fallback
Escalation phrase
Call transfer target
Voice-specific evals
```

Voice-specific UI copy:

> **Voice responses need shorter turns.**
> We found 7 behavior rules that may produce long spoken answers.

That is useful, not gimmicky.

---

## 11. How simulation and testing should work

Simulation should be a first-class lab, not a chat demo.

### Simulation Lab structure

```text
Scenario
Persona
Channel
Agent version
Data fixture
Tool mode
Knowledge mode
Assertions
Run type
```

### Simulation types

```text
Interactive simulation
A human chats with the agent.

Scripted simulation
A predefined user journey runs automatically.

Persona simulation
A simulated user has goals, constraints, and temperament.

Tool-failure simulation
APIs fail, timeout, or return bad data.

Knowledge-gap simulation
Relevant docs are missing or contradictory.

Adversarial simulation
User attempts prompt injection, data exfiltration, or unsafe requests.

Channel simulation
Same task tested across WhatsApp, Slack, email, voice, and web.

Load/cost simulation
Measures latency, cost, and tool throughput.
```

### Simulation example

```text
Scenario
Customer disputes duplicate charge.

Persona
Angry enterprise customer, authenticated, refund amount $84.

Channel
WhatsApp.

Assertions
- Agent must explain possible duplicate authorization.
- Agent must check invoice status before escalating.
- Agent must not promise refund.
- Agent must offer ticket creation if unresolved.
- Response must fit WhatsApp formatting rules.
```

### Simulation output

```text
Result: Partial pass

Passed
✓ Checked invoice status
✓ Did not promise refund
✓ Offered ticket creation

Failed
✕ Response too long for WhatsApp
✕ Did not explain authorization hold clearly

Suggested fixes
- Add WhatsApp-specific concise response rule.
- Add knowledge snippet for authorization holds.
- Add eval for low-value duplicate charges.
```

The simulation output should always point to an edit.

---

## 12. How traces and debugging should work

Traces should be the product’s “flight recorder.”

A trace should show the full operational path without exposing hidden chain-of-thought.

### Trace timeline

```text
1. Incoming message
2. Channel adapter normalization
3. Identity and context lookup
4. Memory reads
5. Policy checks
6. Retrieval queries
7. Retrieved sources
8. Tool calls
9. Tool results
10. Response generation
11. Memory writes
12. Channel rendering
13. User outcome
14. Cost and latency
15. Evaluation labels
```

### Trace summary

Example:

```text
Trace summary

User asked about duplicate charge.
Agent escalated immediately.

Likely root cause
Behavior rule treats “billing dispute” as mandatory escalation.

Evidence
- No tool call made to invoice status API.
- Retrieved refund policy, but not duplicate-charge article.
- Escalation rule matched before troubleshooting rule.

Recommended action
Review escalation precedence in Behavior → Billing disputes.
```

### Debug labels

Every problematic trace should be classifiable:

```text
Root cause
○ Behavior issue
○ Tool failure
○ Retrieval miss
○ Knowledge contradiction
○ Memory issue
○ Channel rendering issue
○ Policy conflict
○ Model quality issue
○ User outside scope
○ Unknown
```

### Fix from trace

Trace CTA:

> **Create change set from this trace**

Then Loop links:

* Original trace
* Proposed fix
* New eval
* Regression result
* Deployment that fixed it

This creates a closed improvement loop.

---

## 13. How evals and regression testing should work

Evals should be generated, curated, versioned, and enforced.

### Eval categories

```text
Contract conformance
Does the agent obey its mission and boundaries?

Task success
Can the agent complete core business tasks?

Tool correctness
Does it call the right tool with the right inputs?

Retrieval grounding
Does it answer from approved sources?

Refusal and escalation
Does it stop when it should?

Memory safety
Does it read and write memory correctly?

Channel compatibility
Does it behave correctly per channel?

Security and privacy
Does it resist injection and protect data?

Cost and latency
Does it stay within operational budgets?

Regression
Does the new version avoid old failures?
```

### Eval library

Inside each agent:

```text
Eval suites

Core readiness               48 tests
Refund policy                32 tests
Tool-use safety              27 tests
Retrieval grounding          61 tests
WhatsApp compatibility       18 tests
Voice short-turn behavior    22 tests
Imported Botpress parity     128 tests
Production regressions       43 tests
```

### Deployment gate

Example:

```text
Deployment blocked

Critical eval failures:
- Refund over $500 was approved without escalation.
- Agent revealed account data before authentication.

Required action:
Fix failures or request explicit override from Compliance and Billing Owner.
```

### Version comparison

```text
v18 production vs v19 candidate

Task success
v18: 82%
v19: 89%

Escalation correctness
v18: 91%
v19: 96%

Tool latency
v18: 780ms p95
v19: 940ms p95

Cost per resolved case
v18: $0.42
v19: $0.48

Critical regressions
0
```

The product should make “better” measurable.

---

## 14. Deployment, approvals, canary, and rollback

Deployment should feel like releasing software, but with business-friendly language.

### Release candidate flow

```text
Branch
→ Change set
→ Tests
→ Version
→ Approval
→ Deployment plan
→ Canary
→ Production
→ Evidence pack
```

### Version manifest

Each version should be immutable and inspectable:

```text
Version v19

Includes
- Behavior policy changes: 3
- Tool changes: 1
- Knowledge changes: 2
- Memory rule changes: 0
- Channel changes: WhatsApp formatting update
- Evals added: 7
- Evals passed: 284/286
- Risk level: Medium
```

### Approval UX

Approvals should be tied to concrete content changes.

Bad:

```text
Approve deployment?
```

Good:

```text
Approve refund threshold change?

Before
Escalate refunds above $250.

After
Escalate refunds above $500.

Risk
Increased financial exposure.

Evidence
- 32 refund evals passed
- 0 critical regressions
- Billing owner requested this change

Required approvers
- Billing Owner
- Compliance Reviewer
```

### Canary deployment

Deployment plan example:

```text
Deploy v19 canary

Channels
- Web chat: 10%
- WhatsApp: 5%
- Email: off
- Voice: off

Audience
Enterprise customers in North America.

Duration
24 hours.

Automatic rollback if
- Escalation rate increases by 15%
- Tool error rate exceeds 2%
- Critical eval monitor fails
- CSAT drops below threshold
```

### Rollback

Rollback must be one-click, but with clarity:

```text
Rollback WhatsApp from v19 to v18?

This will:
- Route new WhatsApp conversations to v18.
- Keep existing conversations on v19 unless you choose otherwise.
- Preserve channel credentials.
- Mark v19 as rolled back.
- Open incident review.

Reason required:
[________________________]
```

### Shadow mode

For high-risk agents, allow:

```text
Shadow deploy v19
Production users still receive v18 responses.
v19 responses are generated silently and compared.
```

That is extremely valuable for enterprise adoption.

---

## 15. Production observability

Observability should not be a pile of metrics. It should be an action system.

### Agent health view

```text
Billing Support Agent

Overall status
Degraded

Why
- Refund escalation rate up 23%
- WhatsApp p95 latency above budget
- 14 unresolved traces linked to duplicate-charge handling

Recommended next actions
1. Review duplicate-charge trace cluster.
2. Run refund regression suite.
3. Check WhatsApp rendering latency after v18 deploy.
```

### Metrics that matter

```text
Business outcomes
- Resolution rate
- Escalation quality
- Conversion/completion rate
- CSAT
- Human override rate

Quality
- Eval pass rate
- Regression failures
- Grounded answer rate
- Refusal correctness
- Escalation correctness

Operations
- p50/p95 latency
- Cost per conversation
- Cost per resolved task
- Tool success rate
- Retrieval hit rate
- Memory write blocks

Risk
- Policy violations
- PII exposure attempts
- Prompt injection attempts
- High-risk tool calls
- Approval bypass attempts

Channel
- Performance by web, WhatsApp, Slack, Teams, SMS, email, voice, API
```

### Observability must recommend actions

Metric card example:

```text
Escalation rate
23% above baseline

Likely cause
New behavior rule in v18 changed billing dispute handling.

Recommended
Review 14 traces and run Refund Policy eval suite.
```

If a dashboard cannot recommend action, it should not be on the homepage.

---

## 16. Collaboration for enterprise teams

Enterprise collaboration should happen around artifacts: policies, tools, traces, evals, deployments.

### Roles

```text
Builder
Edits agent behavior, tools, knowledge, tests.

Platform engineer
Manages integrations, secrets, environments, APIs.

Operations lead
Reviews production issues, traces, quality, handoffs.

Compliance reviewer
Approves policy, data, memory, and deployment risk.

Business owner
Approves business rules, tone, success criteria, launch.

Viewer / auditor
Can inspect evidence without changing behavior.
```

### Collaboration features

* Branches
* Change sets
* Comments on policies, tools, traces, evals
* Review requests
* @mentions
* Assignment
* Deployment approvals
* Audit trail
* Release notes
* Shared runbooks
* Incident reviews

### Example comment thread

On a policy card:

```text
Compliance Reviewer
This refund language implies approval. Please change “you qualify” to “you may be eligible.”

Builder
Updated. Added 3 evals to catch approval-like phrasing.

Billing Owner
Approved.
```

### Branch UX for non-developers

Engineers understand branches. Business users may not.

So the UI should say:

```text
Draft change
```

With advanced label:

```text
Branch: refund-policy-update
```

Do both.

---

## 17. Compliance, audit, RBAC, data residency, and security UX

Governance should be visible at the moment of risk, not buried in settings.

### Workspace Security Center

Global controls:

```text
RBAC
SSO / SCIM
Audit logs
Data residency
Retention policies
Secrets vault
Model/provider policies
Approved tools
Approved knowledge connectors
PII rules
Environment controls
Compliance exports
```

### Per-agent Governance tab

```text
Governance for Billing Support Agent

Risk tier
Medium

Data handled
- Customer ID
- Email
- Invoice ID
- Billing address

Regions
- US
- EU

Approved tools
- Customer lookup
- Invoice status
- Refund ticket creation

Restricted actions
- Refund approval
- Contract modification
- Payment method changes

Required approvals
- High-risk behavior changes
- Memory rule changes
- Production deployments
- New external tools
```

### RBAC UX

Do not just gray out buttons.

Explain:

```text
You can edit this behavior rule, but you cannot deploy it to production.

Missing permission
Production Deployer for Project: Customer Support.

Next step
Request deploy approval from Platform Operations.
```

### Audit evidence pack

Every production version should produce:

```text
Evidence Pack: Billing Support Agent v19

Included
✓ Version manifest
✓ Behavior diff
✓ Tool permission diff
✓ Knowledge source diff
✓ Memory rules
✓ Channel deployment plan
✓ Eval results
✓ Approval records
✓ Canary results
✓ Rollback plan
✓ Audit log
```

Export options:

* PDF
* JSON
* CSV
* GRC integration
* API

This is how governance becomes confidence.

---

## 18. Homepage and work queue

The homepage should not be a feature showcase.

It should be a **work queue and mission control surface**.

### Homepage layout

#### Left: My work

```text
My work

Approvals waiting for me
- Approve refund threshold change
- Review WhatsApp production deploy

Assigned issues
- Duplicate-charge escalation spike
- Stale refund policy source

Drafts
- Add invoice status tool
- Slack channel setup
```

#### Center: Agents needing attention

```text
Agents needing attention

Billing Support Agent
Status: Degraded
Reason: Escalation spike after v18
Next action: Review trace cluster

Order Status Agent
Status: Healthy
Next action: None

Claims Intake Agent
Status: Blocked
Reason: Tool credentials expired
Next action: Reconnect claims API
```

#### Right: Releases and risk

```text
Release candidates
- Billing Support v19 — awaiting Compliance
- Claims Intake v7 — canary running

Risk alerts
- 1 high-risk tool added
- 3 stale knowledge sources
- 2 failed critical evals

Cost and latency
- WhatsApp latency above budget
- Voice cost up 18%
```

### Homepage principle

Every card should have:

* Status
* Why it matters
* Recommended next action
* Owner
* Due date or severity

No decorative metrics.

---

## 19. First 30 minutes, first day, first week

### First 30 minutes

Goal: user feels they created a real production candidate.

Journey:

1. Create or import agent.
2. Define mission and boundaries.
3. Generate Agent Contract.
4. Add one knowledge source or mock source.
5. Add one tool or mock tool.
6. Select one sandbox channel.
7. Run generated simulations.
8. See readiness score.
9. Land in Workbench with next actions.

Success moment:

```text
Your agent is not production-ready yet, but it is testable.

Readiness: 58%
Generated:
- Agent Contract
- 24 starter evals
- Web chat sandbox
- 3 recommended next actions
```

### First day

Goal: user has a serious staging candidate.

Journey:

1. Connect real knowledge.
2. Configure one real tool.
3. Invite reviewer.
4. Run core eval suite.
5. Review traces from simulations.
6. Configure one channel in staging.
7. Create release candidate.
8. Generate evidence pack preview.

Success moment:

```text
Staging candidate ready

Passed:
- 86/91 core evals
- 19/20 tool tests
- 12/12 channel tests

Blocked:
- 5 refund policy evals need business review
```

### First week

Goal: production canary and operational loop.

Journey:

1. Deploy canary to one or two channels.
2. Monitor health.
3. Review trace clusters.
4. Create first evidence-driven fix.
5. Add regression tests from production traces.
6. Expand traffic.
7. Add second channel.
8. Export audit evidence.
9. Hold release review.

Success moment:

```text
Production canary completed

Traffic
10% web chat, 5% WhatsApp

Outcome
- Resolution rate +8%
- Escalation correctness +11%
- No critical policy failures
- 7 production traces converted into regression tests
```

---

## 20. UI surfaces and how they relate

### Global surfaces

```text
Workspace Home
Mission control and work queue.

Project Overview
Portfolio view for related agents.

Agent Registry
Searchable list of agents, status, owners, deployments.

Migration Center
Import, map, validate, and convert legacy bots.

Tool Catalog
Reusable governed tools.

Knowledge Library
Reusable governed knowledge sources.

Channel Hub
Workspace-level channel connections and credentials.

Governance Center
RBAC, audit, residency, policies, secrets.

Reports / Evidence
Compliance exports and operational reports.
```

### Agent-level surfaces

```text
Agent Workbench
Primary working surface.

Contract
Mission, scope, success, boundaries.

Behavior
Instructions, policies, tone, examples.

Tools
Agent-specific capability usage.

Knowledge
Agent-specific retrieval configuration.

Memory
Rules, scopes, stored memory inspection.

Channels
Adapters and deployments.

Simulation Lab
Scenario-based testing.

Evals
Regression and release gates.

Traces
Debugging and production evidence.

Deployments
Versions, environments, canaries, rollback.

Observability
Health, metrics, recommendations.

Governance
Agent-specific risk, approvals, audit evidence.
```

### Relationship rule

Global surfaces manage reusable infrastructure.

Agent Workbench manages how one agent uses that infrastructure.

That distinction keeps the UI coherent.

---

## 21. What should be hidden, collapsed, or removed

To keep the interface calm, hide or demote:

### Hide by default

* Raw compiled prompt
* Model parameters
* Token-level debugging
* Full JSON manifests
* Advanced retrieval settings
* Low-level vector index controls
* Secret values
* Webhook payload internals
* Full audit logs
* Long trace internals
* Eval judge configuration

### Collapse until relevant

* Channel-specific settings
* Data residency details
* Approval policy internals
* Memory retention settings
* Cost breakdowns
* Tool retry policies
* Advanced branch controls
* Provider/model routing

### Remove entirely from primary UX

* Blank canvas as first screen
* Flow builder as dominant editor
* Prompt playground as main creation path
* Fake demo metrics
* Generic dashboards with no action
* Channel-specific duplicate agents
* “Approve deployment” without diff context
* Unexplained “AI score” badges
* Decorative persona gimmicks
* Marketing-style feature tiles on homepage

A production surface should feel calm because it is selective.

---

## 22. Appropriate delight and polish

The delight should come from **clarity, confidence, and intelligent compression**, not mascot energy.

Good delight:

### Impact preview

```text
This change affects:
- 3 policies
- 2 tools
- 18 evals
- WhatsApp and email deployments
```

### Semantic diff

```text
You changed the refund threshold from $250 to $500.
```

### Readiness meter

Not a toy score, but a checklist-backed readiness view.

```text
Production readiness: 81%

Blocking:
- 2 critical eval failures
- Missing approval from Compliance
```

### Trace replay

A beautiful, readable timeline that shows why the agent acted as it did.

### Channel preview matrix

Seeing one agent render correctly across web, WhatsApp, email, Slack, and voice is genuinely magical.

### Evidence pack generation

One click:

> **Generate release evidence**

And the result looks like a polished enterprise artifact.

Bad delight:

* Animated robots
* Fake “thinking” effects
* Confetti on deploy
* Cartoon personas
* Overly playful compliance copy
* Decorative graphs
* Fake live data

The aesthetic should be: **serious, precise, calm, confident**.

---

## 23. Top 10 product principles

1. **The agent is the product object.**
   Channels, tools, knowledge, memory, and evals orbit the agent.

2. **No production change without evidence.**
   Edits should link to traces, tests, approvals, or explicit rationale.

3. **Creation should produce a contract, not a blank project.**

4. **Channels are adapters, not duplicate bots.**

5. **Behavior is structured policy, not one giant prompt.**

6. **Migration optimizes for outcome parity, not flow preservation.**

7. **Dashboards must recommend action.**

8. **Governance should explain risk at the point of change.**

9. **Every deployment should be reversible and auditable.**

10. **The system should make safe progress feel faster than unsafe improvisation.**

---

## 24. Top 10 anti-patterns to avoid

1. **Starting with a blank canvas.**

2. **Making a visual flow builder the center of the product.**

3. **Treating prompt editing as the primary UX.**

4. **Creating one bot per channel.**

5. **Using fake demo metrics or canned traces.**

6. **Making approvals generic instead of diff-specific.**

7. **Separating tests, traces, deployment, and editing into disconnected areas.**

8. **Showing observability metrics without root-cause suggestions.**

9. **Importing legacy bot structure without translating it into agent capabilities.**

10. **Making compliance feel like a final obstacle instead of a continuous confidence layer.**

---

## 25. Recommended MVP slice

The MVP should be narrow but feel like the real product.

Do not build a lightweight chatbot builder. Build a thin but serious version of the control plane.

### MVP must include

#### 1. Agent Registry

```text
Agents
Status
Owner
Environment
Current version
Health
Open issues
```

#### 2. Agent Workbench shell

With:

* Overview
* Contract
* Behavior
* Tools
* Knowledge
* Channels
* Evals
* Traces
* Deployments
* Governance

Even if some tabs are basic, the structure must teach the right model.

#### 3. Agent Contract Wizard

The creation flow should generate:

* Mission
* Scope
* Boundaries
* Escalation rules
* Starter behavior
* Starter evals

#### 4. Structured behavior editor

Include:

* Mission
* Allowed tasks
* Disallowed tasks
* Escalation rules
* Tool-use rules
* Tone
* Examples
* Compiled prompt preview

#### 5. Basic tool catalog

Support:

* OpenAPI import
* REST tool
* Mock tool
* Secret vault placeholder
* Sandbox test
* Tool trace logging

#### 6. Basic knowledge management

Support:

* File upload
* URL/source connector
* Retrieval preview
* Source status
* Citation requirement
* Retrieval evals

#### 7. Omnichannel foundation

Start with:

* Web chat
* Slack or Teams
* WhatsApp or SMS
* Webhook/API

Voice can be included as a sandbox adapter if strategically necessary, but do not let it distort the architecture.

The key MVP requirement:

> One agent, multiple channel adapters.

#### 8. Simulation Lab

Support:

* Manual simulation
* Scripted scenario
* Channel preview
* Tool mock mode
* Assertions

#### 9. Evals and deployment gates

Support:

* Generated starter evals
* Regression suite
* Pass/fail release gate
* Version comparison

#### 10. Deployment with approvals and rollback

Support:

* Staging
* Production
* Immutable version
* Approval request
* Canary percentage
* Rollback to previous version

#### 11. Traces

Support:

* Timeline
* Retrieval
* Tool calls
* Policy checks
* Cost
* Latency
* “Create change set from trace”

#### 12. Work queue homepage

Support:

* Approvals
* Failed evals
* Agents needing attention
* Deployment candidates
* Trace clusters
* Migration blockers

#### 13. Migration MVP

Start with:

* Botpress `.bpz` import inventory
* Dialogflow CX JSON import inventory
* Rasa YAML import inventory
* Custom transcript import
* Artifact mapping
* Migration readiness report
* Generated parity tests

Do not promise full automatic migration. Promise:

> “We will tell you what can be migrated, what needs review, and how close you are to production readiness.”

That is more credible and more useful.

---

# Concrete example flows

## Flow A: Create a new billing support agent

1. User clicks **Create or import agent**.
2. Selects **Create new production agent**.
3. Enters mission: billing support for enterprise customers.
4. Loop generates Agent Contract.
5. User selects capabilities: answer billing questions, check invoice status, create refund ticket.
6. User connects billing docs and uses a mock invoice API.
7. Loop generates 32 evals.
8. User runs simulations.
9. Loop reports readiness: 64%.
10. User adds web chat sandbox.
11. User invites Billing Owner to review refund policy.

Result:

```text
Draft agent created.
Not production-ready.
Clear next steps.
Evidence already exists.
```

## Flow B: Migrate from Botpress

1. User uploads `.bpz`.
2. Loop inventories intents, workflows, knowledge, tables, hooks, variables, integrations, and channels.
3. Loop maps workflows to capabilities.
4. Loop flags custom hooks and missing credentials.
5. Loop generates parity tests from intents and transcripts.
6. User reviews migration board.
7. Loop creates `migration/botpress-billing-bot` branch.
8. User resolves credentials and policy conflicts.
9. User runs parity suite.
10. User deploys staging candidate.

Result:

```text
Migrated agent candidate created.
Legacy flow complexity translated into capabilities, policies, tools, knowledge, and evals.
```

## Flow C: Fix a production issue

1. Homepage shows: “Escalation rate up 23% after v18.”
2. User opens trace cluster.
3. Loop suggests root cause: billing dispute rule too broad.
4. User creates change set from traces.
5. User edits escalation policy.
6. Loop creates 5 new evals.
7. Regression passes.
8. Compliance approval required because escalation policy changed.
9. Canary deploy to 10% web chat.
10. Metrics recover.
11. Roll forward to 100%.

Result:

```text
Production improvement is trace-linked, tested, approved, deployed, and auditable.
```

## Flow D: Add a high-risk tool

1. Builder adds “Issue refund” API.
2. Loop classifies it as high risk.
3. Requires sandbox test, approval threshold, audit logging, and human confirmation rule.
4. Tool-use evals are generated.
5. Compliance reviews tool permission diff.
6. Tool deploys only to staging.
7. Production enablement requires separate approval.

Result:

```text
Powerful capability added without hiding risk.
```

## Flow E: Add voice after web and WhatsApp

1. User opens Channels.
2. Clicks **Add voice**.
3. Configures ASR, TTS, recording disclosure, escalation phone number, and latency budget.
4. Loop previews existing behavior as spoken turns.
5. Loop flags 9 responses as too long for voice.
6. User adds voice-specific presentation rules.
7. Runs voice evals.
8. Deploys voice to staging.

Result:

```text
Voice becomes a first-class adapter, not a separate bot.
```

---

# Prioritized implementation sequence

## Phase 1: Foundation

Build the domain model correctly.

* Workspace
* Project
* Agent
* Branch / draft
* Change set
* Version
* Deployment
* Evidence
* Agent manifest
* Audit events

This is the hardest thing to fix later.

## Phase 2: Agent Workbench and Contract Wizard

* Agent Registry
* Workbench shell
* Agent Contract Wizard
* Structured behavior editor
* Compiled instruction preview
* Starter eval generation

This creates the right UX identity.

## Phase 3: Testing and traces

* Simulation Lab
* Basic eval runner
* Trace timeline
* Create change set from trace
* Version comparison

This makes editing evidence-driven.

## Phase 4: Tools, knowledge, and memory

* Tool catalog
* OpenAPI / REST tools
* Secret vault integration
* Knowledge source registry
* Retrieval preview
* Basic memory rules
* Memory trace visibility

This makes agents useful.

## Phase 5: Deployment safety

* Staging and production
* Immutable versions
* Approvals
* Canary
* Rollback
* Evidence pack

This makes it enterprise-grade.

## Phase 6: Omnichannel

* Web chat
* Slack / Teams
* WhatsApp / SMS
* Email
* Webhook/API
* Voice adapter

This makes the “one agent, many channels” promise real.

## Phase 7: Migration Center

* Botpress inventory
* Dialogflow inventory
* Rasa inventory
* Custom import
* Mapping UI
* Migration readiness
* Parity eval generation

This becomes a major wedge for adoption.

## Phase 8: Observability and recommendations

* Health view
* Trace clustering
* Metric anomalies
* Recommended actions
* Cost and latency monitoring
* Quality drift

This turns Loop from builder into operating system.

## Phase 9: Enterprise governance

* Advanced RBAC
* Data residency
* Compliance exports
* GRC integrations
* SCIM / SSO
* Policy-as-code options
* Advanced audit search

This closes enterprise deals.

---

# Sharpest risks and tradeoffs

## 1. Too much structure can slow down early users

The risk is making creation feel like procurement software.

Mitigation: let users create a draft quickly, but show readiness gaps clearly.

## 2. Migration parity will be hard

Legacy bots often encode business logic in strange flows, hooks, and channel hacks.

Mitigation: sell migration as **inventory, translation, readiness, and parity testing**, not magic one-click conversion.

## 3. Omnichannel abstraction can erase channel nuance

A single agent cannot speak identically across WhatsApp, email, Slack, and voice.

Mitigation: keep one core agent, but give each channel its own presentation adapter, tests, and deployment status.

## 4. Evals can create false confidence

Passing tests does not mean the agent is safe.

Mitigation: combine evals with canaries, traces, production monitors, rollback, and human approvals.

## 5. Governance can become bureaucracy

If approvals are generic, users will hate them.

Mitigation: approvals must be tied to concrete diffs, risks, and evidence.

## 6. Prompt abstraction can frustrate power users

Some builders will want raw prompt control.

Mitigation: provide compiled prompt preview and advanced editing, but keep structured behavior as the default.

## 7. Voice can distort the roadmap

Voice is important, but it has unique latency, interruption, and escalation needs.

Mitigation: build voice as a first-class channel adapter, not as the organizing principle of the product.

## 8. Workbench complexity can become overwhelming

The product has many surfaces.

Mitigation: make the homepage action-oriented, collapse advanced settings, and keep every page anchored to the agent.

## 9. Enterprise buyers will demand proof before trusting autonomy

They will not accept “the model is smart.”

Mitigation: make evidence packs, traces, evals, approvals, and rollback central from day one.

## 10. The biggest product risk is becoming a prettier bot builder

Loop Studio wins only if it feels like the system of record and control plane for production agents.

The north star should be:

> **Every agent change is explainable, testable, deployable, observable, reversible, and auditable.**

[1]: https://botpress.com/docs/studio/concepts/import-export-bots "Import & Export - Botpress"
[2]: https://docs.cloud.google.com/dialogflow/cx/docs/concept/agent "Agents  |  Dialogflow CX  |  Google Cloud Documentation"
[3]: https://rasa.com/docs/reference/primitives/training-data-format/ "Training Data Format | Rasa Documentation"
