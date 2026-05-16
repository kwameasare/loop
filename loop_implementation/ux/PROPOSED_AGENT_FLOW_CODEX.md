# Proposed Agent Flow - Codex

## Status

This document proposes the ideal enterprise journey for creating, editing, operating, and improving agents in Loop Studio.

It is written as a product and UX north-star for the agent lifecycle specifically. It should be treated as a focused companion to the broader target UX standard, not as a replacement for it.

## Executive Summary

The best enterprise agent builder should feel like a mission control system for intelligent labor.

It is not a chatbot maker, a visual flow tool, or a prompt playground. It is a place where an enterprise creates, governs, improves, and operates digital workers with the same confidence it expects from production software.

The central product object is the agent:

```text
Workspace -> Project -> Agent -> Branch -> Version -> Deployment
```

Every major screen should help a builder answer five questions:

1. What is this agent responsible for?
2. What is it allowed to do?
3. Why did it behave the way it did?
4. What changed between versions?
5. Is it safe to ship?

If the product cannot answer those questions clearly, the experience is not enterprise-ready.

## Product Thesis

Enterprise builders do not want to "make a bot." They want to assign a business responsibility to an agent, connect it to real systems, prove it behaves correctly, deploy it safely, and improve it continuously.

The best UX is therefore not centered on drawing conversational paths. It is centered on making an agent understandable, testable, governable, and deployable.

The builder should never feel they are managing fragments. The agent should hold together:

- Behavior
- Tools
- Knowledge
- Memory
- Channels
- Evals
- Versions
- Deployments
- Traces
- Approvals
- Cost
- Risk

The product should make the agent feel like a production asset, not a demo artifact.

## Core Principles

### 1. The Agent Is The Unit Of Work

The builder should not start from an empty canvas, a prompt box, or a channel-specific bot. They start from an agent with a business responsibility.

Good:

```text
Create a subscription cancellation support agent for US and EU customers.
```

Weak:

```text
Create a chat flow.
```

The UI should consistently reinforce this mental model. Tools, knowledge, memory, channels, evals, traces, and deployments all belong to the agent.

### 2. Creation Starts From Business Intent

The builder begins by describing the outcome. Studio turns the business intent into a governed draft.

The builder should be able to say:

```text
Create an enterprise support agent for subscription cancellations. It should work across web chat, WhatsApp, Telegram, Slack, email, SMS, and voice. It can look up accounts, explain refund policy, offer retention options, escalate legal threats, and must never store payment data.
```

Studio should produce:

- Agent purpose
- Draft behavior
- Suggested tools
- Knowledge requirements
- Channel plan
- Memory policy
- Eval suite
- Risk profile
- Approval requirements
- Deployment plan
- Cost estimate
- Missing information checklist

The builder is never dropped into a blank state. They land in a structured draft.

### 3. Editing Starts From Evidence

Enterprise builders should rarely begin by hunting through configuration. Most edits should begin from evidence:

- A bad production conversation
- A failed eval
- A human handoff
- A user complaint
- A cost spike
- A migration mismatch
- A channel-specific failure
- A compliance review comment

The product should guide the builder from evidence to cause to focused repair.

### 4. Channels Are Equal

Voice is important, but it is one channel among peers.

The same agent should bind to:

- Web chat
- WhatsApp
- Telegram
- Slack
- Teams
- SMS
- Email
- Voice
- Webhook/API

Each channel has unique constraints, but the builder should not create separate bots for each channel. The same agent brain runs through channel-specific adapters.

### 5. Governance Creates Confidence

Enterprise governance should feel like a safety system, not a bureaucratic tax.

Every meaningful change should have:

- Owner
- Diff
- Eval impact
- Cost impact
- Risk impact
- Data impact
- Approval state
- Audit trail
- Rollback path

Production changes should be protected by gates. Preview changes should remain fast and playful.

### 6. The Product Should Be Calm Until Something Matters

The product should not be loud by default.

It should be quiet, focused, and dense enough for real work. When something matters, it becomes precise and urgent:

- A canary is drifting
- A policy blocks promotion
- A tool grant changed
- A memory rule may store PII
- A channel adapter is not ready
- A migration parity gap remains

The UI should reserve visual drama for proof, risk, and consequence.

## Primary Enterprise Personas

### Builder

Creates and improves agents. Needs speed, control, explanation, and safe iteration.

Primary jobs:

- Create agents from business intent
- Edit behavior
- Bind tools and knowledge
- Test changes
- Replay failures
- Promote drafts

### Enterprise Builder

Builds agents in a regulated or scaled organization. Needs governance, auditability, and collaboration.

Primary jobs:

- Follow approval policy
- Maintain evidence trails
- Coordinate with compliance and engineering
- Manage multiple channels
- Prove safe production behavior

### Platform Engineer

Owns shared tools, channel packs, auth, runtime constraints, and integrations.

Primary jobs:

- Publish reusable tools
- Configure channel adapters
- Enforce workspace policies
- Monitor system-level reliability
- Support teams without duplicating work

### Support Or Operations Lead

Owns outcomes in production. May not edit implementation details but needs to understand failures.

Primary jobs:

- Review bad conversations
- Resolve handoffs
- Comment on expected behavior
- Convert failures into evals
- Approve business behavior

### Compliance Or Security Reviewer

Reviews risk, data handling, approvals, and audit posture.

Primary jobs:

- Review changes in plain English
- Confirm data handling
- Approve memory and tool permissions
- Export evidence
- Investigate incidents

## The Ideal Creation Journey

### Step 1: Start With The Mission

The first screen asks the builder for the agent mission, not implementation details.

Required fields:

- Agent responsibility
- Target users
- Business outcome
- Supported channels
- Risk level
- Owner
- Success criteria

Optional structured fields:

- Region
- Language requirements
- Escalation policy
- Compliance domain
- Expected volume
- Budget target
- Launch date

Example mission:

```text
Handle order status and refund questions for US and EU customers across web chat, WhatsApp, email, SMS, and voice.
```

The UI should immediately produce a draft agent plan.

### Step 2: Choose One Of Three Doors

The creation entry should have three clear paths:

1. Create from business intent
2. Import from an existing platform
3. Clone an approved enterprise template

No fourth vague option. No hidden advanced route. Advanced controls appear after the draft exists.

### Step 3: Studio Generates A Governed Draft

After the builder enters the mission, Studio creates a draft workspace with visible structure:

- Purpose
- Behavior outline
- Channel plan
- Tool candidates
- Knowledge sources needed
- Memory proposal
- Eval starter suite
- Risk profile
- Approval requirements
- Missing information

The draft should include clear statuses:

```text
Behavior: Drafted
Tools: Needs connection
Knowledge: Needs source
Memory: Proposed
Channels: Not bound
Evals: Starter suite generated
Deploy: Blocked until preflight
```

The builder sees exactly what exists and what remains.

### Step 4: Complete The Readiness Checklist

The setup journey should be guided but not childish. A builder can jump anywhere, but the system should keep the readiness model visible.

Readiness checklist:

- Define agent responsibility
- Confirm behavior rules
- Connect required tools
- Add or verify knowledge
- Approve memory policy
- Bind at least one channel
- Run starter evals
- Review risk flags
- Stage first version
- Complete preflight

Each item should open the exact work surface needed to finish it.

## The Import Journey

Import is a first-class enterprise journey, not an afterthought.

The product should support imports from:

- Botpress
- Dialogflow
- Rasa
- Intercom-style bots
- Zendesk-style automations
- Custom JSON/YAML
- Transcript archives
- FAQ and knowledge bases
- Existing API docs

The goal is not to preserve the old product's mental model. The goal is to translate old assets into agent-native objects.

### Import Should Produce Agent-Native Objects

Imported material should map into:

- Behavior rules
- Tool contracts
- Knowledge sources
- Variables and session state
- Escalation rules
- Channel constraints
- Eval candidates
- Migration notes

It should not dump a visual flow into the product and call that success.

### Import Review

The import review should show:

- What imported cleanly
- What could not be mapped
- What changed semantically
- What is risky
- What needs human review
- What can be tested immediately

Example:

```text
Imported:
- 42 intent examples
- 18 behavior branches
- 5 escalation paths
- 3 API actions
- 2 channel-specific fallback rules

Needs review:
- 4 unmapped variables
- 2 custom code actions
- 1 channel handoff rule
```

### Migration Parity

The builder should see a parity score based on behavior, not just structure.

Parity dimensions:

- Structure parity
- Behavior parity
- Tool parity
- Knowledge parity
- Channel parity
- Cost parity
- Risk parity

The most important screen is side-by-side replay:

```text
Old system response vs Loop draft response
```

The builder should be able to replay historical conversations against the new draft and inspect differences.

### Cutover

Cutover should include:

- Shadow traffic
- Canary traffic
- Rollback route
- Channel-by-channel readiness
- Stakeholder approvals
- Parity evidence
- Launch checklist

The migration workspace should remain after cutover for lineage and incident review.

## The Template Journey

Templates should be approved enterprise patterns, not decorative examples.

A template should include:

- Behavior
- Tools
- Knowledge requirements
- Memory rules
- Channel defaults
- Eval suite
- Risk posture
- Deploy policy
- Example traces

Template examples:

- Support cancellation agent
- Claims intake agent
- Internal IT helpdesk agent
- Sales qualification agent
- Appointment booking agent
- Procurement assistant
- Voice receptionist
- Field operations assistant

Templates should answer:

```text
What does a well-built agent of this type look like?
```

## The Agent Workbench

The Agent Workbench is the center of the product.

It should feel like a clean cockpit for one agent. Every section belongs to the same agent and keeps the builder oriented.

### Workbench Header

The header should show:

- Agent name
- Purpose
- Owner
- State
- Branch
- Active version
- Risk level
- Channels
- Last deploy
- Next required action

The object state must be visible:

```text
Draft -> Saved -> Staged -> Canary -> Production -> Archived
```

### Workbench Sections

The workbench should include:

1. Overview
2. Behavior
3. Channels
4. Tools
5. Knowledge
6. Memory
7. Simulator
8. Evals
9. Deploy
10. Observe

These should feel like sections of one cockpit, not scattered apps.

### Overview

Overview answers:

- What is this agent for?
- Who owns it?
- Where is it live?
- What needs attention?
- What changed recently?
- What is blocking deploy?

The Overview should not be a marketing page. It should be a work queue for the agent.

### Behavior

Behavior defines what the agent should do and what it must not do.

It should include:

- Goals
- Constraints
- Refusals
- Escalations
- Tone
- Compliance rules
- Channel-specific behavior notes
- Risk flags
- Eval coverage

### Channels

Channels binds the same agent to user surfaces.

Supported channel types:

- Web chat
- WhatsApp
- Telegram
- Slack
- Teams
- SMS
- Email
- Voice
- Webhook/API

Each channel card should show:

- Status
- Setup completeness
- Identity
- Auth or provider
- Channel constraints
- Last traffic
- Last failure
- Eval coverage
- Deploy readiness

### Tools

Tools define what the agent can do.

Tool UI should show:

- API schema
- Auth status
- Permissions
- Side-effect risk
- Mock/live mode
- Test calls
- Rate limits
- Cost
- Audit policy
- Example traces

The builder should be able to paste a cURL command, OpenAPI URL, Postman export, or browser network request and draft a typed tool.

### Knowledge

Knowledge defines what the agent can cite.

Knowledge UI should show:

- Sources
- Freshness
- Chunk quality
- Retrieval examples
- Citation behavior
- Gaps
- Duplicates
- Outdated documents
- Inverse retrieval misses

The builder should be able to ask:

```text
What questions should have retrieved this chunk but did not?
```

### Memory

Memory defines what the agent can remember.

Memory UI should show:

- Memory rules
- Durable facts
- Source trace
- Scope
- Retention
- Consent
- Delete impact
- Replay impact
- Safety flags

Memory should never feel invisible. Every durable memory write should be explainable.

### Simulator

Simulator is the safe playground.

The builder can:

- Switch channel shells
- Run the same input across channels
- Disable tools
- Inject context
- Clear memory
- Compare draft vs production
- Replay from a turn
- Save failures as evals
- Generate variants
- Run persona tests

Simulator changes never affect production unless explicitly staged.

### Evals

Evals prove behavior.

Eval UI should show:

- Suites
- Cases
- Judges
- Production-derived coverage
- Regression history
- Channel coverage
- Risk coverage
- Owner
- Required gates

Every production failure should be easy to convert into an eval case.

### Deploy

Deploy is where the builder stages, promotes, canaries, and rolls back.

Deploy UI should show:

- Diff
- Eval status
- Risk status
- Tool changes
- Memory changes
- Channel readiness
- Cost changes
- Required approvals
- Canary plan
- Rollback path

Promotion should be blocked when proof is missing.

### Observe

Observe shows production reality.

Observe UI should show:

- Live traces
- Incidents
- Escalations
- Latency
- Cost
- Channel failures
- Eval drift
- Tool errors
- Knowledge misses
- Memory writes

Observation should connect directly back to editing.

## The Best Editing Loop

The golden loop is:

```text
Find evidence -> understand cause -> make focused edit -> replay impact -> approve -> deploy -> observe
```

### Example: Failed WhatsApp Conversation

1. Builder opens a failed WhatsApp cancellation conversation.
2. Trace timeline shows the agent retrieved an outdated policy.
3. The relevant behavior sentence is highlighted.
4. The stale knowledge chunk is identified.
5. Studio shows similar failures from the last seven days.
6. Builder updates the knowledge source or behavior constraint.
7. Studio replays the original turn and related turns.
8. Eval impact updates.
9. Cost and latency impact update.
10. A plain-English behavioral diff appears.
11. Builder stages the change.
12. Required approvers review evidence.
13. Canary deploy starts.
14. Observatory watches for drift.
15. Rollback remains one click.

The product should make this loop feel obvious and fast.

## Behavior Editor

The behavior editor should be usable by business builders and precise enough for engineers.

It should have three layers.

### Plain Language Layer

Example:

```text
Always verify the customer's account before discussing refund eligibility.
```

This is the default layer for business builders.

### Structured Policy Layer

Example:

```text
Goal: verify account ownership
Constraint: do not reveal refund eligibility before verification
Escalation: legal threat, chargeback, abusive user
Refusal: medical, legal, financial advice outside company policy
Tone: calm, concise, accountable
```

This layer gives precision without forcing code.

### Code Or Config Layer

The advanced layer provides exact versionable representation.

It should be available but not required for normal business users.

### Sentence Telemetry

Every behavior sentence should be measurable.

Hovering a sentence should show:

- Used in 1,204 turns
- Cited in 188 responses
- Contradicted 7 times
- Covered by 42 eval cases
- Last changed by Maya
- Last changed 3 days ago
- Production impact: medium
- Cost impact: none

Prompt editing should stop being guesswork.

### Behavioral Diff

When behavior changes, Studio should produce a semantic diff:

```text
You added a requirement to verify account ownership before refund eligibility.
You removed the instruction to offer retention discounts before cancellation.
You narrowed escalation to legal threats and chargebacks.
```

The diff should be plain enough for a reviewer and precise enough for an engineer.

## Channel Experience

Channels should be peer surfaces.

The builder configures one agent and binds it to many channels. Each channel has unique constraints, but behavior remains agent-native.

### Web Chat

Requirements:

- Embed snippet
- Identity/session handling
- Theme configuration
- Domain allowlist
- Transcript capture
- Handoff routing
- Trace linking

### WhatsApp

Requirements:

- Business identity
- Template approval
- Session window behavior
- Media handling
- Opt-in/out policy
- Handoff rules
- Message length constraints

### Telegram

Requirements:

- Bot token
- Command handling
- Group vs direct message policy
- Attachment handling
- Thread or reply mapping
- Abuse controls

### Slack And Teams

Requirements:

- Workspace installation
- Threaded replies
- Mentions
- Slash commands
- Internal identity
- Approval workflows
- Channel privacy rules

### SMS

Requirements:

- Number provisioning
- Character limits
- Opt-out policy
- Carrier compliance
- Abbreviation handling
- Low-context recovery

### Email

Requirements:

- Inbox routing
- Async SLA
- Long-form tone
- Attachments
- Thread history
- Signature policy
- Escalation routing

### Voice

Requirements:

- Phone number provisioning
- ASR provider
- TTS provider
- Barge-in behavior
- Latency budget
- Call transfer
- Recording policy
- Voice-specific evals

### Webhook/API

Requirements:

- Signed events
- Retry policy
- Idempotency
- Structured input and output
- Rate limits
- Audit trail

## Simulator Experience

The simulator should feel like a lab, not a fake chat window.

It should let a builder:

- Switch channels instantly
- Run the same turn in multiple channels
- Inject user context
- Disable a tool
- Switch model
- Clear memory
- Replay from a selected turn
- Compare draft vs production
- Save a failure as an eval
- Generate conversation variants
- Run persona tests

### Channel Switching

A builder should be able to switch channel shells with one click or keystroke:

```text
1 = Slack
2 = WhatsApp
3 = SMS
4 = Voice
```

The content should remain the same conversation unless the builder explicitly starts a new one.

### Safe Experimentation

Simulator changes should be scoped to the simulation:

- Tool disabled only for the run
- Context injected only for the run
- Memory cleared only for the run
- Model switched only for the run

The builder should feel free to experiment because production is protected.

## Trace Theater

Trace Theater should make the agent understandable.

It should show:

- User message
- Channel metadata
- Model context
- Retrieved knowledge
- Tool calls
- Tool responses
- Memory reads
- Memory writes
- Policy checks
- Cost
- Latency
- Confidence
- Final answer
- Version
- Snapshot

### Trace Scrubber

The trace should be scrubbable like a timeline.

At each frame, the builder sees:

- What the agent knew
- What it was about to do
- Which tool was queued
- Which memory was available
- Which knowledge chunks were ranked
- Which policy checks fired

At any frame, the builder can:

- Fork from here
- Save as eval
- Comment
- Compare to production
- Replay against draft
- Open the responsible object

### Replay Against Draft

The builder should be able to replay production conversations against a draft before shipping.

The replay should compare:

- Final answer
- Tool calls
- Knowledge retrieval
- Memory behavior
- Cost
- Latency
- Risk flags

This turns production traffic into future regression coverage.

## Evals And Continuous Proof

Evals should be generated from real work, not only written manually.

Eval sources:

- Production conversations
- Human handoff resolutions
- Reviewer comments
- Migration parity gaps
- User complaints
- Simulator failures
- Persona tests
- Tool failures
- Knowledge misses

### Comments As Specifications

When a reviewer comments:

```text
This should have escalated to billing support.
```

The product should offer:

```text
Create eval case from this comment?
```

The expected behavior becomes regression coverage.

### Eval Coverage Map

The builder should see coverage across:

- Behaviors
- Channels
- Tools
- Knowledge sources
- Memory rules
- Risk classes
- Languages
- Personas
- Regions

No agent should ship with invisible gaps.

## Deployment Journey

Deployment should feel like promoting software, not publishing content.

### Preflight

Preflight checks:

- Required eval suites pass
- No unresolved high-risk regressions
- Tool grants approved
- Memory rules approved
- Channel readiness complete
- Cost within budget
- Latency within target
- Residency policy satisfied
- Rollback path armed

### Approval

Approvals should bind to content.

If the draft changes after approval, the approval becomes stale.

Approval UI should show:

- What changed
- Why it matters
- Evidence
- Eval impact
- Risk impact
- Reviewer responsibility

### Canary

Canary should support:

- Percentage rollout
- Channel-specific rollout
- Region-specific rollout
- Segment-specific rollout
- Automatic rollback conditions
- Live drift monitoring

### Rollback

Rollback should be one click and evidence-backed.

The UI should show:

- Current live version
- Last known safe version
- What will revert
- Expected impact
- Audit entry

## Home Screen

The home screen should be a command center.

It should not be a hero page, showcase, or component demo.

It should show work needing attention:

- Agents with failed evals
- Canary drift
- Incomplete channel setup
- Unresolved human handoffs
- Migration parity gaps
- Cost anomalies
- Tool failures
- Knowledge freshness issues
- Approval requests

Every row should answer:

1. What happened?
2. Why does it matter?
3. What should I do next?

Example:

```text
Refund agent has 3 failed evals
Why it matters: blocks production promotion
Next action: open regression diff
```

## Collaboration

Enterprise agent building is multiplayer.

The product should support:

- Branches
- Comments
- Presence
- Review requests
- Approval queues
- Change ownership
- Comment-to-eval conversion
- Shared snapshots
- Incident rooms
- Role-based permissions

Different roles should see the right level of detail.

Builder:

- Behavior, tools, knowledge, evals, deploy

Support lead:

- Conversations, handoffs, expected behavior, eval conversion

Compliance reviewer:

- Data handling, risk, approvals, audit evidence

Platform engineer:

- Tool contracts, channel packs, auth, runtime policy

## Governance

Enterprise governance should be visible and specific.

Governance surfaces:

- Policy center
- Audit log
- Approval queue
- Data residency
- BYOK/encryption
- SCIM and SSO
- Role permissions
- Evidence exports

Every governance block should be connected to a user-facing consequence.

Weak:

```text
Policy failed.
```

Strong:

```text
Promotion blocked because the new memory rule may store payment data. Remove the rule, narrow it to non-sensitive account preferences, or request Security approval.
```

## Empty States

Every empty state should be a starting line.

No empty state should say only "nothing here."

Examples:

### No Agents

```text
Create or import your first agent.
Start from a blank mission, import from Botpress, or clone an approved template.
```

### No Evals

```text
Create starter evals from yesterday's production conversations.
```

### No Channels

```text
Bind this agent to web chat, WhatsApp, Telegram, Slack, SMS, email, or voice.
```

### No Knowledge

```text
Add policy docs, upload FAQs, or connect a knowledge source.
```

### No Production Traffic

```text
Run simulator scenarios, send a test conversation, or replay imported transcripts.
```

## Visual And Interaction Standard

The product should feel:

- Calm
- Precise
- Fast
- Premium
- Operational
- Trustworthy
- Alive when evidence changes

### Motion

Motion should clarify state changes:

- Stage transitions
- Eval completion
- Canary progression
- Replay diff
- Trace scrub
- Approval invalidation

Motion should not decorate fake liveness.

### Delight

Delight should be earned by proof:

- First eval suite passes
- Migration parity crosses threshold
- Canary completes safely
- A comment becomes an eval
- A production issue is resolved

The UI should celebrate evidence, not hope.

## Success Metrics

Creation metrics:

- Time to first useful draft
- Time to first channel binding
- Time to first eval run
- Time to first safe deploy
- Import parity score

Editing metrics:

- Time from failure to root cause
- Time from root cause to patch
- Replay coverage before deploy
- Regression rate after deploy

Enterprise metrics:

- Approval cycle time
- Audit completeness
- Policy violation reduction
- Rollback frequency
- Mean time to resolution

Channel metrics:

- Channel readiness
- Channel-specific eval pass rate
- Channel-specific latency
- Channel-specific escalation rate
- Channel-specific cost

Trust metrics:

- Builder confidence before deploy
- Reviewer clarity
- Incident explainability
- Production trace completeness

## Anti-Patterns

Avoid these:

- Making the canvas the primary mental model
- Treating voice as the only channel surface
- Showing fake live data globally
- Hiding behavior behind prompts only
- Shipping channel-specific duplicate bots
- Letting production changes bypass gates
- Making approvals generic
- Showing dashboards without next action
- Creating empty states with no recommended start
- Separating tools, memory, evals, and deploy from the agent context
- Celebrating visual polish that does not reveal evidence, control, or consequence

## Ideal First 30 Minutes

A new enterprise builder should be able to:

1. Describe an agent mission.
2. Get a structured draft.
3. Confirm behavior.
4. Add a knowledge source.
5. Connect or mock one tool.
6. Bind one channel.
7. Run simulator tests.
8. Generate starter evals.
9. Review risk flags.
10. Understand exactly what blocks production.

They do not need to deploy in 30 minutes, but they should understand the path to deploy.

## Ideal First Day

By the end of day one, an enterprise builder should be able to:

1. Import or create a production-shaped agent.
2. Bind at least two channels.
3. Run a meaningful eval suite.
4. Replay historical or simulated conversations.
5. Resolve the main risk flags.
6. Request approvals.
7. Run a canary or stage a deployment.
8. Show leadership and compliance evidence of readiness.

## Final Standard

The best enterprise agent UX is a system where:

- Creation starts from business intent.
- Editing starts from evidence.
- Channels are equal.
- Behavior is measurable.
- Tools are governed.
- Knowledge is inspectable.
- Memory is controlled.
- Evals are continuous.
- Deployment is safe.
- Collaboration is native.
- Every production incident becomes a better agent.

The builder should leave every session feeling:

- Oriented
- In control
- Protected
- Fast
- Respected
- Creative
- Certain enough to ship

This is the product standard: an enterprise agent operating system where builders do not merely create agents. They understand, govern, improve, and trust them.
