# Proposed Agent Flow - Merged Implementation Standard

## Status

Merged proposal for the enterprise agent creation, editing, deployment, and operations journey.

This document combines the implementation strength of `PROPOSED_AGENT_FLOW_CODEX.md` with the strongest operational artifacts from `PROPOSED_AGENT_FLOW_CLAUDE.md`.

The goal is not inspiration. The goal is an implementable, high-quality product journey that can be decomposed into product surfaces, backend models, state machines, jobs, tests, and acceptance criteria.

## How To Read This

This is the implementation-facing agent journey spec.

Use it this way:

- Product and design should use it to validate the end-to-end agent lifecycle.
- Engineering should use it to derive schemas, routes, queues, state machines, components, and tests.
- QA should use the acceptance tests and guiding scenarios as regression pressure tests.
- The broader canonical UX standard remains the source for visual language, motion, copy tone, shell standards, and screen quality bars.
- The earlier Codex and Claude proposal docs remain useful background, but this file is the merged implementation target.

If this document conflicts with the canonical UX standard, treat the canonical standard as the higher-level product law and amend this proposal explicitly.

## Product Definition

Loop Studio is an enterprise agent control plane.

It should feel closer to GitHub + Datadog + LaunchDarkly + an audit binder for production agents than to a chatbot builder. Creation is one moment in a longer operating loop:

```text
define -> test -> deploy -> observe -> improve -> prove
```

The central product object is the production agent:

```text
Workspace -> Project -> Agent -> Branch / Change Set -> Version -> Deployment -> Evidence
```

An agent is a versioned enterprise commitment with provable behavior, deployable in controlled slices, observable in production, rollbackable in seconds when safety requires it, and auditable over time.

Every implementation decision should preserve five guarantees:

1. The builder knows what the agent is responsible for.
2. The builder knows what the agent is allowed to do.
3. The builder can explain why the agent behaved a certain way.
4. The builder can prove what changed between versions.
5. The builder can determine whether a change is safe to ship.

If a feature does not support at least one of those guarantees, it is secondary.

## Non-Negotiable Implementation Corrections

These are prominent because they are release-quality constraints, not taste preferences.

The product must not confuse showing the target UX with being the target UX. A polished surface backed by fictional operational data is worse than an unfinished surface that tells the truth. Loop's trust premise depends on this distinction.

### Truth Before Breadth

Before adding more surfaces, the implementation must make a narrow set of flows real end to end.

Required standard:

- No persistent shell component may show workspace-specific agent data, trace data, canary state, parity state, timeline events, promotion state, or preview content unless the user is authorized and the data is loaded from the selected workspace, agent, environment, branch, and version.
- No UI may say `live`, `canary`, `trace ready`, `promotion blocked`, `parity passed`, or `rollback available` unless that state is backed by a durable product object.
- Fixture, demo, deterministic, staging, and production data must be visibly distinguishable in development and test environments.
- A protected route must not render specific workspace facts while auth is unresolved.
- Animation, badges, ribbons, and confidence indicators are allowed only when they clarify real state, causality, risk, progress, or control.

Acceptance test:

```text
Can a skeptical enterprise builder point at every operational claim on screen and trace it to an authorized backend object?
```

### Enterprise Entry Is Estate First

The default enterprise landing experience is the estate, not a scripted single-agent showcase.

The estate view should answer:

- Which agents are live, blocked, watchlisted, stale, or ownerless?
- Which deploys, incidents, approvals, eval failures, cost anomalies, and channel failures need attention?
- Which shared tools, knowledge sources, policies, secrets, or model/provider settings create blast radius?
- Which agents changed recently, and what changed after those changes?
- Which actions are waiting on the current user?

The agent-specific homepage is still important, but it is reached after selecting an agent or opening a pinned task. The platform team starts from fleet truth.

### Shell Is Task-Contextual

The shell must change by task context.

Use three layout modes:

| Mode | Routes | Persistent right rail |
|---|---|---|
| Estate mode | Home, agents inventory, governance, cost, marketplace, admin | None by default |
| Workbench mode | Agent behavior, tools, knowledge, memory, channels, simulator, deploy setup | Agent preview/evidence rail, only for selected agent |
| Investigation mode | Traces, replay, eval results, incidents, inbox, observability | Inspector, diff, incident, or trace panel |

Do not mount a generic live preview, timeline, activity feed, or fictional scenario globally. Route components opt into context panels when they have a real object to inspect.

### Two Complete Journeys Beat Many Partial Surfaces

The next implementation quality bar is two real, skeptical-enterprise journeys:

1. Create, edit, test, approve, deploy, observe, and roll back a support agent.
2. Import a Botpress agent, prove parity, cut over safely, and preserve lineage.

For both journeys, `real` means:

- Durable workspace and agent state
- Real agent selection
- Real preview run
- Persisted trace
- Eval capture from trace
- Eval suite run
- Semantic and raw diff
- Release candidate
- Preflight gate
- Approval if required
- Staging or shadow run
- Canary or controlled rollout
- Rollback event
- Audit log entry
- Evidence pack

Everything outside those journeys can exist only if it is clearly scoped, clearly labeled, and does not fake operational truth.

### Traces And Evals Are The Backbone

Every serious workflow should converge on traces and evals.

A preview turn must be able to produce:

- Trace ID
- Prompt and model metadata
- Retrieved chunks
- Tool calls
- Memory reads and proposed writes
- Policy checks
- Cost and latency
- Output
- User or reviewer feedback
- Eval conversion

An eval result must link back to:

- Candidate version
- Baseline version
- Trace diff
- Tool diff
- Retrieval diff
- Memory diff
- Policy diff
- Cost delta
- Latency delta
- Suggested fix or owner

If this evidence loop is weak, the product becomes a builder demo instead of an agent control plane.

### Governance Cannot Be Cosmetic

Enterprise governance is part of the product's core interaction model.

Minimum bar:

- No workspace data before authorization.
- Real RBAC around high-risk actions.
- Immutable audit events for meaningful changes.
- Content-hash approval invalidation.
- Explicit environment boundaries.
- Versioned deploy objects.
- Secret boundary visibility.
- Policy violation messages that name policy, owner, and next action.
- Evidence export for traces, evals, deploys, approvals, incidents, and handoffs.

BYOK, SCIM, SIEM, and full residency enforcement may phase in, but the UI must not present them as operational until they are.

### State Must Read As One Sentence

Every agent surface should allow the builder to understand current state as one sentence:

```text
You are editing draft branch `refund-clarity` for agent `Acme Support Concierge` in dev preview. Production is currently v23. Canary v24 is held at 5% because eval `refund_window_basic` regressed on one Spanish paraphrase.
```

All badges, chips, banners, and controls must support that sentence. If the user has to assemble state from scattered visual fragments, the UI is not done.

### Incident And Continuity Are Core

The product must support long-term ownership, not only creation.

Every production agent needs:

- Incident response controls
- Emergency rollback and mitigation
- Owner and backup owner
- Runbook
- Continuity pack
- History walkthrough
- Approval reassignment
- Access revocation support
- Stale branch and stale owner detection

Personnel turnover and Friday-afternoon incidents are not edge cases. They are normal enterprise operating conditions.

## Guiding Acceptance Scenarios

These scenarios are not decorative examples. They are pressure tests for implementation. A surface or backend workflow that passes unit tests but fails these scenarios is not good enough.

### Scenario 1: Intake Produces A Useful Draft In Minutes

Maya, a senior platform engineer at a regulated bank, opens Studio with a messy problem: refund handling across web chat, WhatsApp, email, SMS, and voice.

She enters a business-intent paragraph and uploads transcripts, a policy PDF, a runbook, and a prior Botpress export.

Within minutes Studio should produce:

- A Commitment Document draft
- Conversation clusters
- Source contradictions
- Candidate tools
- Candidate channel bindings
- Candidate eval cases
- Risk and compliance notes
- A working draft agent she can test

Acceptance test:

```text
Can a skeptical enterprise builder get from "we need an agent" to a structured, testable draft without first building a blank bot by hand?
```

### Scenario 2: The 90-Second Editing Loop

A builder spots a bad answer in a conversation.

The intended loop:

1. Select the wrong sentence in the agent response.
2. Open the contextual action menu.
3. Choose `Fix this`.
4. Studio opens the responsible behavior, knowledge, tool, or memory object.
5. Studio proposes a focused fix with evidence.
6. Builder accepts or edits it.
7. Studio replays the current conversation and nearby examples.
8. Studio shows improved, unchanged, and regressed turns.
9. Builder saves the failure as an eval case.

Acceptance test:

```text
Can a builder move from observed failure to focused fix to replay proof to regression coverage in roughly 90 seconds?
```

### Scenario 3: The Catch

The builder writes:

```text
Never approve refunds over $500 without manual review.
```

Later, a user asks for two refunds in one conversation: $475 and $80. Each call is under $500; the cumulative refund is $555.

Studio should catch the literal-but-dangerous interpretation and ask:

```text
You said "never approve refunds over $500." This conversation would approve $555 across two refund calls. Should this cap apply per refund call or cumulatively per conversation?
```

Acceptance test:

```text
Can the platform detect rule-edge ambiguity the builder missed and turn the answer into regression tests?
```

### Scenario 4: 3 A.M. Incident With Containment

An upstream data feed changes. Escalation rate spikes.

Studio should:

- Detect the anomaly.
- Pause or roll back according to policy.
- Create an Incident.
- Link affected traces.
- Notify the owner concisely.
- Generate an incident report.
- Propose candidate evals.

Acceptance test:

```text
Can the platform tell the on-call owner what happened, what was contained, what customers were affected, and what needs review without requiring panic debugging?
```

### Scenario 5: Handoff To A New Owner

Diego covers during PTO or Priya inherits the agent after Maya leaves.

Studio should provide:

- Commitment Document
- Change Packages
- Recent incidents
- Open risks
- Eval coverage
- Tool grants
- Channel readiness
- History Walkthrough

Acceptance test:

```text
Can a qualified builder ship a low-risk fix to an unfamiliar agent in under 60 minutes using only product evidence?
```

## Implementation Thesis

The correct implementation model is not "chatbot builder" or "flow builder."

The correct implementation model is a governed lifecycle for one production agent:

```text
Intake -> Draft -> First Proof -> Workbench Editing -> Preflight -> Approval -> Rollout -> Observe -> Improve -> Handoff
```

The product should make this lifecycle explicit in data, UI, permissions, tests, and audit.

The builder journey must be implemented around durable artifacts:

- Agent Contract / Commitment Document
- Agent Workbench
- Channel Bindings
- Tool Contracts
- Knowledge Sources
- Memory Policies
- Eval Suites
- Replay Runs
- Change Sets
- Release Candidates
- Change Packages
- Evidence Packs
- Approvals
- Deployments
- Incidents
- Estate Health
- History Walkthroughs

These are not just UI concepts. They should become product objects with IDs, ownership, state, audit records, and test coverage.

### Calm Power

The product should be calm by default and precise when something matters.

Implementation implications:

- Do not use visual drama for normal state.
- Do not invent liveness.
- Do not show global decorative dashboards without next action.
- Do use stronger visual treatment for blocked deploys, stale approvals, unsafe memory rules, failed evals, incident states, and channel readiness gaps.
- Motion should clarify state transitions, not decorate static information.

### The Platform Takes The Urgency

The platform should not merely report problems. It should detect, contain, cluster, seed tests, and prepare fixes where it safely can.

Recurring implementation pattern:

```text
Detect -> contain if policy allows -> explain -> propose fix -> generate evals -> ask for human judgment
```

This pattern applies to:

- Drift
- Incidents
- Cost spikes
- Latency regressions
- Channel failures
- Knowledge gaps
- Tool failures
- Ambiguous behavior rules
- Operator takeovers
- Migration parity gaps

The builder should spend judgment, not adrenaline.

## Core Product Objects

### Workspace

Enterprise tenant boundary.

Owns:

- Users
- Teams
- Projects
- Agents
- Policies
- Integrations
- Audit log
- Estate view
- Data residency
- Billing and usage

Required fields:

- `id`
- `name`
- `slug`
- `region`
- `plan`
- `policy_profile_id`
- `created_at`
- `updated_at`

### Project

Optional grouping boundary for agents.

Owns:

- Related agents
- Shared knowledge sources
- Shared eval suites
- Shared channel defaults
- Shared reviewers

Required fields:

- `id`
- `workspace_id`
- `name`
- `description`
- `owner_user_id`
- `created_at`
- `updated_at`

### Agent

Primary product object.

Owns:

- Commitment Document
- Branches
- Versions
- Behavior
- Tools
- Knowledge
- Memory policy
- Channel bindings
- Evals
- Deployments
- Traces
- Incidents

Required fields:

- `id`
- `workspace_id`
- `project_id`
- `name`
- `slug`
- `purpose`
- `owner_user_id`
- `risk_level`
- `state`
- `active_version_id`
- `created_at`
- `updated_at`

State values:

```text
draft
saved
staged
canary
production
archived
```

### Commitment Document

Also called the Agent Contract in creation and review UI.

Versioned source of truth for what the agent is.

This is one of the most important artifacts in the product. It prevents the agent from becoming an unowned collection of prompts, tools, and channel settings.

Required sections:

- Owner
- Backup owner
- Business responsibility
- Target users
- Success metrics
- Worst-case failure
- Systems touched
- Channels served
- Languages served
- Regions served
- Regulatory posture
- Out-of-scope behavior
- Escalation policy

Required fields:

- `id`
- `agent_id`
- `version`
- `body`
- `structured_summary`
- `owner_user_id`
- `status`
- `created_from`
- `created_at`
- `updated_at`

Status values:

```text
draft
accepted
superseded
archived
```

Acceptance criteria:

- Every agent has exactly one current Commitment Document.
- Creation UI may call this an Agent Contract, but the backend object must remain the versioned contract of responsibility, boundaries, and evidence.
- Every production deployment references the Commitment Document version used during preflight.
- Changing the accepted Commitment Document creates a new version.
- Reviewers can understand the agent's purpose from this artifact without reading behavior config.

### Branch

Editable working line for an agent.

Required fields:

- `id`
- `agent_id`
- `name`
- `base_version_id`
- `created_by_user_id`
- `status`
- `created_at`
- `updated_at`

Status values:

```text
active
staged
merged
abandoned
```

### Change Set

Editable unit of work on a branch.

Small edits may accumulate inside a draft Change Set. Reviewable work should not be a pile of invisible saves.

Required fields:

- `id`
- `agent_id`
- `branch_id`
- `name`
- `summary`
- `source_type`
- `source_refs`
- `changed_objects`
- `status`
- `created_by_user_id`
- `created_at`
- `updated_at`

Status values:

```text
draft
ready_for_tests
ready_for_review
converted_to_release_candidate
abandoned
```

Acceptance criteria:

- A production issue, failed eval, trace cluster, migration gap, or manual edit can create a Change Set.
- A Change Set can collect behavior, tool, knowledge, memory, channel, and eval changes.
- A Change Set always links to its evidence sources.
- A Change Set can become a Release Candidate only after required tests run.

### Version

Immutable snapshot of agent behavior and dependencies.

Includes:

- Behavior config
- Tool grants
- Tool contract refs
- Knowledge source refs
- Memory policy refs
- Channel binding refs
- Eval suite refs
- Model settings
- Runtime policy refs

Required fields:

- `id`
- `agent_id`
- `branch_id`
- `version_number`
- `snapshot_id`
- `created_by_user_id`
- `created_at`

### Release Candidate

Candidate immutable version prepared for approval and rollout.

Required fields:

- `id`
- `agent_id`
- `branch_id`
- `change_set_id`
- `candidate_version_id`
- `readiness`
- `required_eval_suites`
- `required_approvals`
- `status`
- `created_at`
- `updated_at`

Status values:

```text
draft
testing
blocked
ready_for_approval
approved
deployable
superseded
```

Acceptance criteria:

- Release Candidate is the object reviewed before deploy.
- Release Candidate points to one Change Set and one candidate Version.
- Release Candidate cannot become deployable with failed required gates.

### Channel Binding

Connects one agent to one channel.

Supported channel types:

- `web_chat`
- `whatsapp`
- `telegram`
- `slack`
- `teams`
- `sms`
- `email`
- `voice`
- `webhook_api`

Required fields:

- `id`
- `agent_id`
- `channel_type`
- `provider`
- `display_name`
- `status`
- `identity_config`
- `auth_config_ref`
- `readiness`
- `last_traffic_at`
- `last_failure_at`
- `created_at`
- `updated_at`

Status values:

```text
not_configured
draft
ready
staged
live
paused
error
archived
```

Acceptance criteria:

- Voice is never represented as the category. It is one channel binding type.
- Every channel binding has readiness checks.
- Every channel binding is visible from the Agent Workbench.
- Every trace records the channel binding that produced it.

### Tool Contract

Plain-English and structured permission contract for an external action the agent can perform.

Required fields:

- `id`
- `workspace_id`
- `agent_id`
- `tool_id`
- `name`
- `description`
- `side_effect_level`
- `pii_access`
- `money_movement`
- `rate_limits`
- `budget_limits`
- `sandbox_status`
- `live_status`
- `owner_user_id`
- `approval_policy_id`
- `created_at`
- `updated_at`

Acceptance criteria:

- New tools default to sandbox mode.
- Live mode requires explicit promotion.
- Mutating tools require side-effect classification.
- Money-moving tools require caps.
- Tool contract changes invalidate related approvals.

### Memory Policy

Rules for what the agent can remember.

Required fields:

- `id`
- `agent_id`
- `scope`
- `allowed_memory_types`
- `retention`
- `consent_requirement`
- `pii_policy`
- `delete_behavior`
- `approval_status`
- `created_at`
- `updated_at`

Scope values:

```text
turn
conversation
session
user
workspace
```

Acceptance criteria:

- Every durable memory write can be traced to a source turn.
- Every memory rule shows privacy implications before activation.
- Memory policy changes appear in preflight.

### Eval Case

Testable expected behavior.

Sources:

- Manual authoring
- Production conversation
- Simulator run
- Human handoff
- Reviewer comment
- Migration parity gap
- Adversarial catch
- Incident cluster

Required fields:

- `id`
- `agent_id`
- `suite_id`
- `source_type`
- `source_ref`
- `input`
- `expected_behavior`
- `channel_type`
- `risk_tags`
- `status`
- `created_at`
- `updated_at`

Acceptance criteria:

- Any production turn can become an eval case.
- Any resolved comment can become an eval case.
- Any operator resolution can become an eval case.
- Eval cases preserve provenance.

### Change Package

Deploy/review artifact generated for every promotion.

This is the implementation-critical review object. External-facing UI may call the final deployed proof bundle an Evidence Pack; internally, the Change Package is the immutable promotion artifact.

Required fields:

- `id`
- `agent_id`
- `branch_id`
- `from_version_id`
- `to_version_id`
- `commitment_document_id`
- `summary`
- `semantic_diff`
- `eval_results_ref`
- `replay_results_ref`
- `risk_summary`
- `cost_summary`
- `latency_summary`
- `channel_readiness_summary`
- `tool_changes`
- `memory_changes`
- `knowledge_changes`
- `required_approvals`
- `approval_status`
- `rollback_target_version_id`
- `evidence_pack_id`
- `created_at`
- `updated_at`

Acceptance criteria:

- Every production promotion requires a Change Package.
- Every claim in the Change Package links to evidence.
- Approvers review the Change Package, not raw implementation details.
- The Change Package is immutable after submission.
- Edits create a new Change Package or invalidate the current one.

### Evidence Pack

Proof bundle attached to a deployed version.

The Evidence Pack is what a reviewer, auditor, customer security team, or regulator can inspect/export after deployment.

Required fields:

- `id`
- `workspace_id`
- `agent_id`
- `version_id`
- `deployment_id`
- `change_package_id`
- `version_manifest`
- `behavior_diff_ref`
- `tool_permission_diff_ref`
- `knowledge_diff_ref`
- `memory_policy_ref`
- `channel_deployment_plan_ref`
- `eval_results_ref`
- `approval_records_ref`
- `canary_results_ref`
- `rollback_plan_ref`
- `audit_log_ref`
- `created_at`

Export formats:

```text
pdf
json
csv
grc_integration
api
```

Acceptance criteria:

- Every production deployment creates or updates an Evidence Pack.
- Evidence Pack can be exported without exposing secrets.
- Evidence Pack links back to the exact Version, Change Package, approvals, and audit events.
- Evidence Pack is readable by compliance and security reviewers without raw code/config context.

### Approval

Human or policy approval bound to content.

Required fields:

- `id`
- `change_package_id`
- `approver_user_id`
- `approval_type`
- `status`
- `content_hash`
- `comment`
- `created_at`
- `updated_at`

Status values:

```text
requested
approved
rejected
revoked
invalidated
expired
```

Acceptance criteria:

- Approvals bind to content hash.
- Editing after approval invalidates the approval.
- Approval invalidation is visible in UI and audit.
- Approval notifications include a concise summary and deep link.

### Deployment

Runtime rollout record.

Required fields:

- `id`
- `agent_id`
- `version_id`
- `change_package_id`
- `environment`
- `stage`
- `traffic_percentage`
- `channel_scope`
- `region_scope`
- `status`
- `rollback_target_version_id`
- `started_at`
- `completed_at`

Stages:

```text
shadow
canary
ramp
production
rolled_back
paused
failed
```

Acceptance criteria:

- Production rollout supports channel-specific and percentage rollout.
- Rollback target is known before rollout starts.
- Auto-rollback triggers are visible and configurable.
- Deployment emits audit events.

### Incident

Production issue record.

Required fields:

- `id`
- `workspace_id`
- `agent_id`
- `deployment_id`
- `severity`
- `trigger`
- `status`
- `affected_conversation_count`
- `root_cause_hypothesis`
- `rollback_action_ref`
- `candidate_eval_suite_id`
- `created_at`
- `resolved_at`

Acceptance criteria:

- Incidents link to affected traces.
- Incidents can generate eval cases.
- Incident reports include timeline, affected conversations, suspected cause, and proposed fix.
- Auto-rollback events create incident records.

### Estate Health

Workspace-level fleet view across all agents.

Required fields:

- `workspace_id`
- `agent_health`
- `cross_agent_tool_grants`
- `cross_agent_failure_clusters`
- `cost_summary`
- `latency_summary`
- `approval_summary`
- `kb_freshness_summary`
- `generated_at`

Acceptance criteria:

- Enterprise operators can see all production agents in one view.
- Tool grants are visible across agents.
- Shared failure clusters are visible across agents.
- Stale approvals and stale knowledge are visible across agents.

## Journey Overview

The end-to-end journey has ten implementable phases:

1. Intake
2. Draft Generation
3. First Proof
4. Agent Workbench Editing
5. Preflight
6. Approval
7. Rollout
8. Steady-State Observation
9. Incident Response
10. Handoff And Estate Management

Each phase should map to UI surfaces, backend objects, jobs, and tests.

## Phase 1: Intake

### Goal

Convert business intent and existing materials into a versioned Commitment Document and a structured draft plan.

### Entry Points

The builder starts through one of three doors:

1. Create from business intent
2. Import from an existing platform
3. Clone an approved enterprise template

### Required UI

Primary intake screen:

- One business-intent input
- Upload area
- Optional structured fields
- Creation path selector
- Clear progress states

The create-from-scratch path should be presented as an Agent Contract Wizard: fast, serious, and production-shaped. It should create a contract and readiness gaps, not a decorative onboarding sequence.

The first screen should ask:

```text
What agent are you building, for whom, and what must it never get wrong?
```

Required inputs:

- Business responsibility
- Target users
- Owner
- Worst-case failure
- Channels
- Systems touched
- Regions/languages

Optional inputs:

- Success metric
- Compliance domain
- Expected volume
- Launch date
- Budget target

### Supported Inputs

The intake system should support:

- Free-form description
- PDFs
- FAQ docs
- Runbooks
- Call or chat transcripts
- Botpress exports
- Dialogflow exports
- Rasa exports
- Intercom/Zendesk automation exports
- OpenAPI specs
- Postman collections
- cURL commands
- Browser DevTools fetch exports

### Required Backend Jobs

Intake creates asynchronous jobs:

- `parse_artifacts`
- `extract_intents`
- `cluster_transcripts`
- `detect_contradictions`
- `detect_sensitive_data`
- `infer_tools`
- `infer_channels`
- `draft_commitment_document`
- `draft_agent_plan`

### Required States

```text
empty
uploading
parsing
analyzing
needs_clarification
draft_ready
failed
cancelled
```

### Required Output

Intake produces:

- Agent Contract / Commitment Document draft
- Agent draft plan
- Intent/corpus map
- Candidate tools
- Candidate knowledge sources
- Candidate channel bindings
- Candidate memory policy
- Candidate eval suite
- Risk notes
- Missing information checklist

### Acceptance Criteria

- A builder can create a draft without seeing an empty agent.
- Uploaded artifacts stream progress and partial results.
- Contradictions are surfaced with source references.
- Sensitive-data findings are visible before draft generation.
- The Commitment Document can be edited before acceptance.
- Failed artifact parsing has recoverable states.

### Agent Contract Wizard Steps

The wizard should create a serious skeleton while allowing the builder to continue with mocks.

Steps:

1. Mission
2. Operating boundaries
3. Capabilities
4. Knowledge and tools
5. Channels
6. Generated tests
7. Readiness landing

#### Mission

Capture:

- Agent name
- Business function
- Primary users
- Supported tasks
- Out-of-scope tasks
- Escalation destination
- Success metric

#### Operating Boundaries

Capture:

- Risk level
- Data sensitivity
- Human approval thresholds
- Compliance requirements
- Required escalation cases

#### Capabilities

Capability categories:

- Answer from knowledge
- Create or update records
- Search customer/account data
- Trigger workflows
- Handoff to human
- Send notifications
- Voice interaction
- Channel-specific messaging

Each capability creates placeholders for tools, knowledge, evals, and policies.

#### Knowledge And Tools

Allow:

- Upload docs
- Connect enterprise source
- Add OpenAPI spec
- Add webhook
- Add internal API
- Use mock tool for now

Do not block creation on unavailable enterprise credentials.

#### Channels

Ask where the agent will eventually run, but require only one initial sandbox channel.

Supported choices:

- Web chat
- WhatsApp
- Telegram
- Slack
- Teams
- SMS
- Email
- Voice
- Webhook/API

#### Generated Tests

Generate starter evals from the Agent Contract:

- Happy paths
- Escalation paths
- Refusal paths
- Tool-use paths
- Knowledge-grounding paths
- Channel-format paths

#### Readiness Landing

The user should land in Agent Workbench -> Readiness View.

Example:

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

## Phase 2: Draft Generation

### Goal

Turn intake output into an editable, governed draft agent.

### Required UI

Draft summary screen:

- Commitment Document
- Draft readiness checklist
- Generated behavior outline
- Suggested tools
- Suggested knowledge
- Suggested memory policy
- Suggested channels
- Starter eval suite
- Risk flags

The screen should answer:

```text
What exists, what is missing, and what should I do next?
```

### Required Backend Objects

Draft generation creates:

- Agent
- Branch
- Commitment Document
- Behavior config
- Draft Channel Binding records
- Draft Tool Contract records
- Draft Memory Policy
- Starter Eval Suite

### Readiness Checklist

Readiness items:

- Commitment accepted
- Behavior reviewed
- At least one channel configured
- Required tools mocked or connected
- Knowledge source added
- Memory policy reviewed
- Starter evals run
- Risk flags reviewed
- Preflight completed

Each checklist item should deep-link to the correct workbench section.

### Acceptance Criteria

- A generated draft is inspectable before any deploy action.
- The draft is editable in the Agent Workbench.
- The readiness checklist is computed from real object states.
- The builder can skip ahead, but blocked production actions remain blocked.

## Import And Migration Center

Migration should be its own credible journey:

```text
Import -> inventory -> map -> test parity -> resolve gaps -> create Loop agent branch
```

The product should not promise one-click perfect migration. It should promise an accurate inventory, agent-native translation, parity tests, and a clear readiness report.

### Supported Sources

- Botpress `.bpz`
- Dialogflow CX export
- Rasa project/YAML
- Zendesk automations/help center/conversation exports
- Intercom content/conversation exports
- Custom JSON/YAML/CSV
- Conversation transcripts only

### Migration Inventory

Inventory should detect source artifacts:

- Intents
- Workflows/flows/pages
- Nodes/cards/responses
- Entities/slots/parameters
- Knowledge bases
- Tables/reference data
- Variables
- Hooks/custom actions
- Integrations/webhooks/tools
- Channels
- Conversation transcripts

Example:

```text
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
⚠ 3 knowledge sources are externally linked and must be reconnected
```

### Mapping View

The mapping view translates legacy structure into Loop's agent model.

```text
Source artifact                  Loop target
------------------------------------------------------------
Intent: refund_request            Capability: Refund triage
Workflow: invoice_dispute          Behavior policy + eval scenarios
Node: ask_for_account_id           Data collection rule
Hook: validate_customer            Tool: Customer lookup API
Knowledge base: billing_docs       Knowledge source: Billing docs
Table: refund_limits               Policy table / reference data
Channel: WhatsApp                  Channel binding
Transcript failures                Regression eval set
```

Migration optimizes for outcome parity, not flow parity.

### Confidence Scoring

Each mapped element should receive a confidence label.

High confidence:

- FAQ knowledge
- Intents with clear examples
- Static answer cards
- Basic escalation flows

Medium confidence:

- Conditional workflows
- Entity extraction
- Form-filling paths
- Webhook calls

Low confidence:

- Custom code hooks
- Complex fallback logic
- Multi-system workflows
- Channel-specific hacks

### Migration Board

Use a board for readiness, not a flow-builder canvas.

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
- Custom hook: normalizeInvoiceId()
- Legacy fallback workflow
```

### Migration Output

Migration creates:

- Agent
- Branch named for migration source
- Agent Contract / Commitment Document
- Behavior policies
- Capabilities
- Tool placeholders/contracts
- Knowledge sources
- Channel bindings
- Parity eval suite
- Migration evidence report
- Readiness score

Acceptance criteria:

- Import never overwrites existing production agents.
- Every mapped item preserves source reference.
- Unmapped items are visible with severity.
- Parity tests measure user-goal outcome, not old flow shape.
- Migration output lands as a branch, not direct production state.

## Phase 3: First Proof

### Goal

Let the builder talk to a working starting point as quickly as possible and convert judgment into structure.

### Required UI

First Proof surface:

- Conversation panel
- Channel selector
- Mock/live tool indicator
- Trace preview
- Turn rating controls
- Save-as-eval affordance
- Issue annotation

Ratings:

```text
good
bad
risky
unclear
```

### Required Behavior

Every rating can create a candidate artifact:

- Good turn -> few-shot candidate or positive eval
- Bad turn -> regression eval candidate
- Risky turn -> risk rule candidate
- Unclear turn -> clarification prompt or behavior note

### Required Backend Objects

- Simulator run
- Trace
- Candidate Eval Case
- Candidate Behavior Note

### Acceptance Criteria

- The builder can test the v0 draft without configuring production.
- Every rated turn preserves provenance.
- A bad turn can become an eval case in one action.
- The trace preview shows retrieved knowledge, tools, memory, latency, and cost when available.

## Phase 4: Agent Workbench Editing

### Goal

Provide a single agent-scoped cockpit for improving the agent.

### Workbench Sections

The Agent Workbench should contain:

1. Overview
2. Commitment
3. Behavior
4. Channels
5. Tools
6. Knowledge
7. Memory
8. Simulator
9. Evals
10. Deploy
11. Observe
12. History

The daily editing cockpit can use a compact four-panel layout:

```text
Brief / Behavior / Conversation / Trace / Evidence
```

But that cockpit should live inside the broader Workbench. It should not replace the full agent management model.

### Workbench Layout

The Agent Workbench should have a stable, agent-local layout.

#### Persistent Agent Top Bar

Shows:

- Agent name
- Current branch / draft change
- Production version
- Environment
- Health
- Last deploy
- Open issues

Controls:

- Branch selector
- Environment selector
- Version selector
- Run tests
- Open Change Set
- Deploy / promote
- Command palette

#### Agent-Local Left Navigation

The agent's sections live together:

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
History
```

These should not be scattered across unrelated global product pages.

#### Center Work Surface

The active editor, table, simulator, trace, deployment view, or governance review.

Do not call this a canvas in user-facing copy unless the surface is genuinely spatial. The default mental model is a work surface, not a flow canvas.

#### Right Evidence Panel

Always contextual.

If editing behavior, it shows:

- Related failed traces
- Affected evals
- Current production version
- Risk level
- Approval requirements

If editing a tool, it shows:

- Recent tool failures
- Latency
- Permissions
- Secrets status
- Audit events

If editing knowledge, it shows:

- Retrieval tests
- Stale documents
- Coverage gaps
- Recent unanswered questions

#### Bottom Test Drawer

Collapsible test console available from edit surfaces:

- One simulation
- Related evals
- Full regression suite
- Channel preview
- Tool dry run
- Replay against production

Acceptance criteria:

- Testing is adjacent to editing.
- Evidence is adjacent to editing.
- Builder does not leave the agent context to test a change.

### Overview

Overview shows:

- Agent purpose
- Owner
- State
- Active branch
- Active version
- Live channels
- Readiness checklist
- Blocking issues
- Recent changes
- Next best action

Acceptance criteria:

- Overview is a work queue, not a showcase.
- It shows real object state.
- It links to the section that resolves each blocker.

### Commitment

Commitment section shows:

- Current Commitment Document
- Version history
- Ownership
- Worst-case failure
- Success metric
- Scope and out-of-scope behavior

Acceptance criteria:

- Builders can propose a Commitment update.
- Commitment updates create versions.
- Deploy preflight references the active Commitment version.

### Behavior

Behavior editor supports three layers:

- Plain language
- Structured policy
- Code/config

Behavior sections:

- Persona
- Goals
- Promises
- Constraints
- Refusals
- Escalations
- Tone
- Channel-specific notes
- Compliance notes

Required features:

- Inline ambiguity detection
- Sentence telemetry
- Semantic diff
- Eval coverage indicators
- Risk flags
- One-click replay
- Selection-driven repair

Acceptance criteria:

- A business builder can edit behavior in prose.
- Ambiguous prose triggers clarification instead of silent guessing.
- A behavior sentence can show production usage and eval coverage.
- Risky behavior changes appear in preflight.

#### The 90-Second Editing Loop

The Behavior section must support a composed loop, not just separate features.

Required choreography:

1. Builder selects a bad sentence in an agent response.
2. Context menu appears with `Explain`, `Show source`, `Fix this`, and `Save as eval`.
3. Builder chooses `Fix this`.
4. Studio identifies the responsible object: behavior sentence, knowledge chunk, tool contract, memory policy, or channel constraint.
5. Studio opens that object in the Workbench with evidence pinned.
6. Studio proposes a narrow change.
7. Builder accepts, edits, or rejects the proposal.
8. Studio replays the current conversation and the nearest relevant examples.
9. Studio summarizes results as improved, unchanged, regressed, and needs review.
10. Builder saves the original failure and accepted fix as regression coverage.

Implementation requirements:

- The selected utterance must preserve a stable trace/span reference.
- The repair proposal must cite evidence.
- Replay must run against the edited draft, not production.
- Saving as eval must preserve source trace, channel, version, expected behavior, and risk tags.
- The loop must work without navigating away from the agent context.

#### The Catch Mechanic

The platform should proactively find ambiguous or literal-but-dangerous interpretations of behavior rules.

This is a named UX and backend behavior, not only an eval source.

Required flow:

1. Behavior rule changes.
2. Background adversarial probe job runs within configured budget.
3. Probe finds a risky interpretation.
4. Studio surfaces a calm question beside the relevant rule or simulator turn.
5. Builder chooses the intended interpretation.
6. Studio updates the rule or proposes a patch.
7. Studio generates eval cases for the rejected and accepted interpretations.

Example:

```text
You said "never approve refunds over $500." This conversation would approve $555 across two refund calls. Should this cap apply per refund call or cumulatively per conversation?
```

Required backend objects:

- `AdversarialProbeRun`
- `Catch`
- `CatchResolution`
- Candidate `EvalCase`

Acceptance criteria:

- Catches are phrased as questions, not red errors.
- Catches cite the rule and generated scenario that triggered them.
- Catches can be dismissed with a reason.
- Catch resolutions can create eval cases.
- Probe budgets are configurable per workspace and risk class.

### Channels

Channels are peer bindings.

Supported channel cards:

- Web chat
- WhatsApp
- Telegram
- Slack
- Teams
- SMS
- Email
- Voice
- Webhook/API

Each channel card shows:

- Configuration status
- Provider
- Identity
- Authentication
- Message format
- Interaction style
- Supported actions
- Channel constraints
- Auth state
- Business hours
- Consent / opt-in
- Rate limits
- Attachment rules
- Fallback behavior
- Channel-specific policy
- Readiness checks
- Last traffic
- Last failure
- Eval coverage
- Deployment status

#### Channel Preview Matrix

The channel preview matrix shows one scenario rendered across multiple channels.

Example:

```text
Scenario: Duplicate charge

Web chat
Compact answer + invoice link + escalation button.

WhatsApp
Short answer + numbered options + template-safe language.

Email
Full explanation + case summary + next steps.

Slack / Teams
Threaded answer + internal action buttons + mention-safe formatting.

Voice
Short spoken answer + confirmation prompts + escalation option.
```

Acceptance criteria:

- The same agent scenario can be previewed across all configured channels.
- Channel-specific formatting failures can become eval cases.
- Voice-specific issues are presented as channel adaptation work, not as separate-agent work.

Acceptance criteria:

- Voice is one card, not the whole channel category.
- Channel setup can be started from workspace-level Channels and agent-level Channels.
- Channel readiness blocks production if incomplete.
- Channel-specific traces preserve channel metadata.

### Tools

Tool Bench supports:

- Tool catalog
- Tool-from-cURL/OpenAPI/Postman/DevTools
- Auth setup
- Schema editing
- Mock mode
- Live mode
- Contract questionnaire
- Test call
- Rate limits
- Cost and side-effect classification
- Tool monitoring
- Failure behavior
- Compensation / rollback behavior

Tool object implementation should include:

- Name
- Description
- Owner
- Environment
- Authentication
- Input schema
- Output schema
- Timeout
- Rate limit
- Retry policy
- Idempotency
- Data classification
- Allowed agents
- Allowed channels
- Approval requirements
- Audit requirements
- Sandbox mode
- Failure behavior
- Compensation / rollback behavior

Tool risk tiers:

```text
low        read-only lookup
medium     creates records or sends notifications
high       changes customer state, billing, access, legal status, or money movement
critical   irreversible or regulated action
```

Before a tool can be enabled beyond mock/sandbox, required checks should include:

- Schema validation
- Sandbox credential test
- Example call passed
- Failure response configured
- Data classification reviewed
- Tool-use eval created
- Owner assigned

Acceptance criteria:

- New tools start sandboxed.
- Mutating tools require side-effect classification.
- Money-moving tools require caps.
- Tool contract changes require approval if live.
- Tool calls appear in traces.
- Tool page shows production usage, success rate, p95 latency, retry rate, failed calls, PII sent, and last schema change.

### Knowledge

Knowledge section supports:

- Source management
- Live chunk inspection
- Retrieval lab
- Inverse retrieval lab
- Freshness checks
- Duplicate detection
- Superseded chunks
- Citation review
- Coverage map by capability
- Contradiction detection

Acceptance criteria:

- Builders can mark chunks superseded.
- Retrieval misses can become knowledge tasks.
- Knowledge source changes appear in preflight.
- Knowledge citations are traceable.
- Knowledge coverage is visible per capability.
- Contradictions identify affected behavior policies and evals.

### Memory

Memory section supports:

- Memory policy editing
- Memory explorer
- Memory write diff
- Source trace links
- Retention review
- Consent requirements
- Delete/replay impact
- Memory write preview
- Runtime memory explanation

Memory scopes:

```text
session
user
account
organization
task
agent
```

Memory write preview should show:

- Proposed memory value
- Scope
- Reason
- Source trace
- Policy check
- Retention
- Action: approve automatically, require review, block, or never store this type

Acceptance criteria:

- Durable memory writes have source traces.
- Privacy implications are shown before enabling a memory policy.
- Memory changes appear in preflight.
- Memory delete actions are audited.
- Traces show memory used and memory blocked by policy.

### Simulator

Simulator supports:

- Channel switching
- Draft vs production comparison
- Tool disabling
- Context injection
- Memory clearing
- Model switching
- Replay from turn
- Save as eval
- Persona tests
- Variant generation

Acceptance criteria:

- Simulator changes do not affect production.
- Channel switch preserves the current conversation unless explicitly reset.
- Failures can become evals.
- Draft vs production diffs are visible.

### Evals

Eval Foundry supports:

- Suites
- Cases
- Judges
- Production-derived cases
- Channel coverage
- Risk coverage
- Regression history
- Required gates

Acceptance criteria:

- Eval cases preserve provenance.
- Comments, takeovers, incidents, simulator failures, and migration gaps can become evals.
- Eval results are linked in Change Packages.

### Deploy

Deploy section supports:

- Preflight
- Change Package
- Approval status
- Shadow
- Canary
- Ramp
- Rollback

Acceptance criteria:

- Production deploy requires a Change Package.
- Required approvals derive from policy.
- Rollback target is visible before rollout.

### Observe

Observe section supports:

- Live trace list
- Failure clusters
- Cost
- Latency
- Channel health
- Escalations
- Tool failures
- Knowledge misses
- Memory writes

Acceptance criteria:

- Production failures link back to edit surfaces.
- Failure clusters can generate tasks and evals.
- Observed behavior can be compared against intended behavior.

### History

History section supports:

- Change packages
- Ownership changes
- Approval history
- Deployments
- Rollbacks
- Incidents
- Important comments
- History walkthrough

Acceptance criteria:

- A new owner can understand the agent without tribal knowledge.
- History walkthrough summarizes major changes and rationale.

## Phase 5: Preflight

### Goal

Generate a Change Package that proves whether a draft is safe to promote.

### Release Candidate Flow

The production path should be:

```text
Branch / draft change
-> Change Set
-> Tests
-> Candidate Version
-> Release Candidate
-> Change Package
-> Approval
-> Deployment plan
-> Canary
-> Production
-> Evidence Pack
```

Implementation rule:

- Builder edits accumulate in a Change Set.
- Passing required tests creates or updates a Release Candidate.
- Preflight generates a Change Package for that Release Candidate.
- Production deployment creates an Evidence Pack.

### Required Inputs

- Current Commitment Document
- Change Set
- Release Candidate
- From-version
- To-version
- Behavior diff
- Tool diff
- Knowledge diff
- Memory diff
- Channel diff
- Eval results
- Replay results
- Cost estimate
- Latency estimate
- Risk analysis

### Required UI

Preflight screen shows:

- Plain-English summary
- Semantic diff
- Version manifest
- Eval scorecard
- Replay against production-like conversations
- Channel readiness
- Tool risk
- Memory risk
- Cost and latency delta
- Required approvals
- Rollback target

### Version Manifest

Each candidate version should have an immutable manifest:

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

### Change Package Example Shape

```text
Change Package: CP-2026-05-09-142

Purpose:
Promotes refund agent v12 to canary for web chat and WhatsApp.

Customer-visible changes:
- Adds account verification before refund eligibility.
- Uses May refund policy instead of older April policy.
- Escalates legal threats earlier.

Eval impact:
- 247 pass
- 0 fail
- 4 new cases added

Replay impact:
- 31 conversations improve
- 12 unchanged
- 4 escalate earlier
- 0 known regressions

Risk:
- No new tool grants
- Memory policy unchanged
- WhatsApp template approval complete
- Cost +$0.002 per turn estimated

Approvals:
- Product required
- Compliance required

Rollback:
- v11 last known safe
```

### Acceptance Criteria

- Change Package generation is deterministic enough to test.
- All claims link to underlying evidence.
- Approvers can review without opening raw config.
- If the draft changes, the Change Package becomes stale.

## Phase 6: Approval

### Goal

Let the right reviewers approve the right evidence without leaving the product.

### Required UI

Approval view:

- 30-second summary
- Full Change Package
- Evidence links
- Comment thread
- Approve/reject/request changes
- Content hash status
- Staleness warning

### Required Behavior

- Approval requirements derive from policy.
- Approvals bind to content hash.
- Edits invalidate approvals.
- Pre-approved classes can exist but must be narrow, explicit, and time-boxed.

### Pre-Approved Classes

Pre-approved classes are corridors of trust, not approval bypasses.

They allow a reviewer to say:

```text
For the next 7 days, Maya may ship instruction-only edits that do not change tool grants, memory policy, PII scope, refusal rules, channel bindings, or budget caps.
```

Required fields:

- `id`
- `workspace_id`
- `agent_id`
- `granted_by_user_id`
- `granted_to_user_id` or `team_id`
- `allowed_change_types`
- `excluded_change_types`
- `risk_ceiling`
- `expires_at`
- `status`
- `created_at`

Rules:

- Must be explicit.
- Must be time-boxed.
- Must name allowed and excluded change types.
- Must be visible in preflight.
- Must be revoked automatically when expired.
- Must be invalidated by policy changes that affect its scope.

Acceptance criteria:

- Low-risk changes can move quickly without pretending risk is zero.
- High-risk changes cannot hide inside a pre-approved class.
- Reviewers can inspect every deployment that used a pre-approved class.

### Acceptance Criteria

- A reviewer can approve from a concise summary for low-risk changes.
- High-risk changes require full evidence review.
- Stale approvals cannot be used for production promotion.
- Approval actions are audited.

## Phase 7: Rollout

### Goal

Deploy safely in slices with rollback ready.

### Rollout Stages

```text
shadow -> canary -> ramp -> production
```

### Required Controls

- Traffic percentage
- Channel scope
- Region scope
- Segment scope
- Hold time
- Auto-rollback thresholds
- Manual pause
- Manual rollback

### Required Metrics

- Error rate
- Escalation rate
- Eval-from-prod pass rate
- Cost per turn
- p95 latency
- Tool failure rate
- Channel failure rate
- Safety violations

### Acceptance Criteria

- A rollout can target specific channels.
- Rollout can pause without rollback.
- Rollback can execute quickly.
- Rollout state is visible in Workbench and Estate view.

## Phase 8: Steady-State Observation

### Goal

Keep production agents understandable and improvable.

### Required Surfaces

Agent Observe:

- Live trace list
- X-Ray / observed behavior
- Drift watch
- Failure clusters
- Operator mailbox
- Cost and latency
- Channel health

Estate View:

- Fleet health
- Cross-agent failures
- Cross-agent tool grants
- Stale approvals
- Stale knowledge
- Workspace cost
- Workspace incidents

### Required Jobs

- `cluster_failures`
- `detect_drift`
- `detect_cost_anomaly`
- `detect_latency_anomaly`
- `detect_stale_knowledge`
- `detect_dead_behavior_sections`
- `summarize_operator_takeovers`

### Acceptance Criteria

- Every production failure can become a task or eval.
- Estate view shows fleet-level risk.
- Cross-agent patterns are visible.
- Dashboards always include next actions.

## Phase 9: Incident Response

### Goal

Detect, contain, explain, and learn from production failures.

### Required Flow

1. Trigger fires.
2. Incident record is created.
3. Auto-rollback or pause executes if configured.
4. Affected traces are collected.
5. Root-cause hypothesis is generated.
6. Incident report is created.
7. Candidate evals are generated.
8. Builder reviews fix.
9. Change Package is created.
10. Fix rolls out.

### Required Incident Report Sections

- Timeline
- Trigger
- Affected conversations
- Affected channels
- Customer impact
- Actions taken
- Suspected cause
- Proposed fix
- Candidate regression tests
- Rollback status

### Acceptance Criteria

- Incident reports are generated from real traces and deployment events.
- Auto-rollback is audited.
- Incidents can seed eval suites.
- On-call users receive concise notifications.

## Phase 10: Handoff And Estate Management

### Goal

Make agents survive personnel changes and scale to enterprise fleets.

### Compliance Reviewer Journey

Compliance and security reviewers are not generic approvers. They need dedicated evidence and investigation flows.

Required surfaces:

- Approval queue filtered by risk class
- Evidence export
- Policy violation history
- Data residency view
- Tool grant review
- Memory policy review
- Channel compliance readiness
- Incident investigation
- Audit log explorer

Required jobs:

- `run_industry_probe_suite`
- `detect_policy_conflicts`
- `summarize_data_access_changes`
- `generate_evidence_export`
- `flag_stale_risk_review`

Acceptance criteria:

- A compliance reviewer can understand a Change Package without reading raw config.
- Evidence exports include Commitment, Change Package, eval results, replay results, approvals, incidents, and audit events.
- Tool grants and memory policies can be reviewed across agents.
- Industry-specific probe libraries can attach required eval suites to high-risk agents.

### Ownership Transfer

Required UI:

- Transfer owner
- Assign backup owner
- Review open risks
- Review pending approvals
- Review recent incidents
- Start history walkthrough

Acceptance criteria:

- Ownership transfer is one audited action.
- New owner receives a history walkthrough.
- Open risks remain visible after transfer.

### History Walkthrough

History walkthrough summarizes:

- Commitment changes
- Major behavior changes
- Tool grants
- Memory policy changes
- Deployments
- Rollbacks
- Incidents
- Important reviewer comments
- Current eval coverage
- Current risk posture

Acceptance criteria:

- A successor can understand why the agent is shaped the way it is.
- History links to source artifacts.

### Estate Management

Estate view supports:

- Agent fleet health
- Agents by traffic
- Agents by risk
- Agents by cost
- Agents by stale knowledge
- Tool grants across agents
- Channel health across agents
- Open approvals
- Recent incidents

Acceptance criteria:

- Platform teams can see shared risk across all agents.
- Compliance can review tool grants across agents.
- Operations can identify unhealthy agents without opening each one.

## Channel Requirements

Channels are first-class and equal.

### Web Chat

Required configuration:

- Embed snippet
- Domain allowlist
- Theme
- Session identity
- Handoff route
- Transcript capture

Readiness checks:

- Domain verified
- Snippet minted
- Test conversation passed
- Trace capture enabled

### WhatsApp

Required configuration:

- Business account
- Provider connection
- Template approvals
- Session window policy
- Media policy
- Opt-in/out policy

Readiness checks:

- Business identity verified
- Template approved
- Test inbound message passed
- Handoff route configured

### Telegram

Required configuration:

- Bot token
- Command policy
- Group/direct policy
- Attachment policy
- Abuse controls

Readiness checks:

- Token verified
- Test command passed
- Trace capture enabled

### Slack And Teams

Required configuration:

- Workspace installation
- Mention policy
- Thread policy
- Slash commands
- Internal identity mapping
- Private channel policy

Readiness checks:

- Workspace installed
- Test mention passed
- Thread reply passed
- Permissions approved

### SMS

Required configuration:

- Number
- Provider
- Opt-out policy
- Carrier compliance
- Message length policy

Readiness checks:

- Number active
- Opt-out verified
- Test message passed

### Email

Required configuration:

- Inbox
- Sender identity
- Routing rules
- Attachment policy
- SLA policy
- Signature policy

Readiness checks:

- Sender verified
- Inbound route tested
- Reply route tested

### Voice

Required configuration:

- Phone number
- ASR provider
- TTS provider
- Barge-in policy
- Transfer policy
- Recording policy
- Latency budget

Readiness checks:

- Number provisioned
- Test call passed
- ASR/TTS spans captured
- Transfer route tested

### Webhook/API

Required configuration:

- Endpoint
- Auth
- Signature verification
- Retry policy
- Idempotency key
- Rate limits

Readiness checks:

- Signed request verified
- Retry behavior tested
- Trace capture enabled

## Implementation Sequencing

### Foundation

Build first:

1. Authorization and data-provenance boundary
2. Workspace, project, agent, environment, branch, and version selection context
3. Estate Health model
4. Agent model
5. Agent Contract / Commitment Document model
6. Branch / Change Set / Version model
7. Release Candidate model
8. Deployment model
9. Evidence Pack model
10. Audit event model
11. Channel Binding model
12. Tool Contract model
13. Trace model with replay and eval-conversion provenance
14. Eval Case provenance
15. Approval content-hash binding
16. Deployment state machine
17. Incident and rollback event model

The first two foundation items are blockers. Do not build shell chrome, live badges, preview rails, or operational dashboards before the product can determine who the user is, which workspace/agent/environment they are viewing, and whether the displayed data is fixture, staging, or production.

This is the hardest layer to fix later.

### Recommended MVP Slice

The MVP should be narrow but feel like the real control plane. Do not build a lightweight chatbot builder.

MVP must include:

1. **Estate Overview**
   Fleet health, owner coverage, blocked deploys, failed evals, incidents, approvals waiting on the user, cost anomalies, stale agents, and shared dependency risk.

2. **Agent Registry**
   Agents, status, owner, environment, current version, health, open issues.

3. **Agent Workbench Shell**
   Overview, Contract, Behavior, Tools, Knowledge, Channels, Evals, Traces, Deployments, Governance.

4. **Agent Contract Wizard**
   Mission, scope, boundaries, escalation rules, starter behavior, starter evals.

5. **Structured Behavior Editor**
   Mission, allowed tasks, disallowed tasks, escalation rules, tool-use rules, tone, examples, compiled instruction preview.

6. **Basic Tool Catalog**
   OpenAPI import, REST tool, mock tool, secret vault placeholder, sandbox test, tool trace logging.

7. **Basic Knowledge Management**
   File upload, URL/source connector, retrieval preview, source status, citation requirement, retrieval evals.

8. **Omnichannel Foundation**
   Web chat, Slack or Teams, WhatsApp or SMS, Webhook/API. Voice may be sandboxed early if strategically necessary, but must not distort the architecture.

9. **Simulation Lab**
   Manual simulation, scripted scenario, channel preview, tool mock mode, assertions.

10. **Evals And Deployment Gates**
   Generated starter evals, regression suite, pass/fail release gate, version comparison.

11. **Deployment With Approvals And Rollback**
    Staging, production, immutable version, approval request, canary percentage, rollback to previous version.

12. **Traces**
    Timeline, retrieval, tool calls, policy checks, cost, latency, create Change Set from trace.

13. **Work Queue Homepage**
    Approvals, failed evals, agents needing attention, deployment candidates, trace clusters, migration blockers.

14. **Migration MVP**
    Botpress `.bpz` import inventory, Dialogflow CX JSON import inventory, Rasa YAML import inventory, custom transcript import, artifact mapping, migration readiness report, generated parity tests.

MVP completion requires two complete flows, not just route coverage:

1. Support agent creation/edit/test/approve/deploy/observe/rollback.
2. Botpress import/parity/cutover/lineage.

Any feature outside those flows must be clearly labeled as preview, hidden from default navigation, or deferred.

### Phase 1 Product Slice

Implement:

- Authorization and route-level data boundary
- Real workspace, agent, environment, branch, and version context
- Estate Overview v1
- Agent Registry
- Agent Contract Wizard
- Agent Workbench shell
- Agent Workbench Overview
- Structured Behavior editor
- Web chat channel binding
- Tool sandbox contract
- Knowledge source upload
- Simulator
- Starter eval generation
- Eval case from simulator failure
- Trace timeline
- Change Set from trace
- Preflight Change Package
- Approval
- Canary deploy
- Rollback
- Audit log entries for every mutating step
- Evidence Pack generated from the release flow

Exit criteria:

- A builder can complete the support-agent journey without fixture-only operational claims.
- A protected route never leaks workspace-specific data before auth is resolved.
- Every visible `live`, `canary`, `blocked`, `trace`, `eval`, `approval`, and `rollback` claim resolves to a backend object.

### Phase 2 Product Slice

Implement:

- Migration Center
- Botpress import inventory
- Dialogflow CX import inventory
- Rasa import inventory
- Migration mapping view
- Migration parity
- WhatsApp or SMS channel binding
- Slack/Teams channel binding
- Memory policy UI
- Memory write preview
- Replay against draft
- Operator handoff to eval
- Evidence Pack v1
- Incident report v1
- Estate view v2 with shared dependency blast radius

### Phase 3 Product Slice

Implement:

- Telegram, email, voice, webhook/API
- Channel preview matrix
- Advanced channel readiness
- Adversarial catches
- Failure clustering
- X-Ray/dead behavior detection
- History walkthrough
- Cross-agent estate insights
- Auto-rollback

## State Machines

### Agent State

```text
draft -> saved -> staged -> canary -> production
draft -> archived
production -> archived
canary -> rolled_back -> saved
```

### Channel Binding State

```text
not_configured -> draft -> ready -> staged -> live
live -> paused
live -> error
error -> ready
paused -> live
any -> archived
```

### Change Package State

```text
draft -> generated -> submitted -> approved -> deployable -> deployed
submitted -> changes_requested
submitted -> stale
approved -> stale
approved -> revoked
```

### Change Set State

```text
draft -> ready_for_tests -> ready_for_review -> converted_to_release_candidate
draft -> abandoned
ready_for_tests -> draft
ready_for_review -> changes_requested
```

### Release Candidate State

```text
draft -> testing -> ready_for_approval -> approved -> deployable
testing -> blocked
ready_for_approval -> blocked
approved -> superseded
deployable -> superseded
```

### Approval State

```text
requested -> approved
requested -> rejected
approved -> invalidated
approved -> revoked
requested -> expired
```

### Deployment State

```text
created -> shadow -> canary -> ramp -> production
shadow -> failed
canary -> paused
canary -> rolled_back
ramp -> paused
ramp -> rolled_back
production -> rolled_back
```

### Incident State

```text
open -> contained -> investigating -> fix_staged -> resolved -> archived
open -> resolved
```

## Quality Bar

Every implemented surface must pass:

- Has one clear primary job.
- Shows real object state, not fixture liveness.
- Has empty, loading, error, degraded, and permission states.
- Links to evidence for any recommendation.
- Supports audit for mutating actions.
- Has one obvious next action.
- Respects object state and permissions.
- Handles no-agent, no-channel, no-eval, and no-data cases.
- Does not make voice the only channel.
- Does not require code editing for normal behavior work.
- Does not allow production changes without gates.

## Acceptance Tests By Journey

### Creation

- Given a business intent, the system creates an Agent and Commitment Document.
- Given uploaded transcripts, the system creates analysis jobs and shows progress.
- Given missing owner or worst-case failure, the system asks for clarification.
- Given draft generation failure, the user can retry or continue manually.

### Import

- Given a Botpress export, the system maps intents, variables, tools, and fallback behavior.
- Given unmapped items, the review screen lists them with severity.
- Given historical conversations, parity replay compares old and new behavior.

### Channels

- Given an agent, the Channels section lists all supported channel types.
- Given no voice setup, other channels remain available.
- Given an incomplete WhatsApp setup, production deploy is blocked for WhatsApp only.
- Given a live channel, traces include channel binding ID.

### Tools

- Given a cURL command, the system drafts a typed tool.
- Given a mutating tool, the system requires side-effect classification.
- Given a money-moving tool, the system requires caps.
- Given a live tool contract change, approvals are required.

### Behavior

- Given ambiguous prose, the system asks a clarification question.
- Given a behavior edit, the system produces a semantic diff.
- Given a behavior sentence, telemetry shows usage and eval coverage when available.

### Evals

- Given a bad simulator turn, the user can save it as an eval.
- Given a reviewer comment, the user can convert it to an eval.
- Given an operator takeover, the resolution can become an eval.

### Preflight

- Given a staged version, the system generates a Change Package.
- Given failed required evals, deploy is blocked.
- Given stale approvals, deploy is blocked.
- Given incomplete channel readiness, deploy is blocked for that channel scope.

### Rollout

- Given an approved Change Package, rollout can start in shadow or canary.
- Given threshold breach, rollout pauses or rolls back according to policy.
- Given rollback, audit records the action and target version.

### Incident

- Given an anomaly trigger, an Incident is created.
- Given auto-rollback, the Incident links to the deployment and affected traces.
- Given resolution, candidate evals can be accepted into a suite.

### Handoff

- Given ownership transfer, the new owner receives a history walkthrough.
- Given a historical Change Package, the new owner can inspect evidence.
- Given open risks, transfer UI surfaces them before completion.

## Concrete Example Flows

### Flow A: Create A New Billing Support Agent

1. User clicks `Create or import agent`.
2. Selects `Create new production agent`.
3. Enters mission: billing support for enterprise customers.
4. Studio generates Agent Contract.
5. User selects capabilities: answer billing questions, check invoice status, create refund ticket.
6. User connects billing docs and uses a mock invoice API.
7. Studio generates starter evals.
8. User runs simulations.
9. Studio reports readiness.
10. User adds web chat sandbox.
11. User invites Billing Owner to review refund policy.

Result:

```text
Draft agent created.
Not production-ready.
Clear next steps.
Evidence already exists.
```

### Flow B: Migrate From Botpress

1. User uploads `.bpz`.
2. Studio inventories intents, workflows, knowledge, tables, hooks, variables, integrations, and channels.
3. Studio maps workflows to capabilities and policies.
4. Studio flags custom hooks and missing credentials.
5. Studio generates parity tests from intents and transcripts.
6. User reviews migration board.
7. Studio creates `migration/botpress-billing-bot` branch.
8. User resolves credentials and policy conflicts.
9. User runs parity suite.
10. User stages a candidate.

Result:

```text
Legacy flow complexity translated into capabilities, policies, tools, knowledge, channels, and evals.
```

### Flow C: Fix A Production Issue

1. Homepage shows escalation rate up after latest version.
2. User opens trace cluster.
3. Studio suggests root cause: billing dispute rule too broad.
4. User creates Change Set from traces.
5. User edits escalation policy.
6. Studio creates new evals.
7. Regression passes.
8. Compliance approval is required because escalation policy changed.
9. Canary deploy starts for web chat.
10. Metrics recover.
11. Roll forward completes.

Result:

```text
Production improvement is trace-linked, tested, approved, deployed, observable, reversible, and auditable.
```

### Flow D: Add A High-Risk Tool

1. Builder adds `Issue refund` API.
2. Studio classifies it as high risk.
3. Studio requires sandbox test, approval threshold, audit logging, caps, and human confirmation rule.
4. Tool-use evals are generated.
5. Compliance reviews tool permission diff.
6. Tool deploys only to staging.
7. Production enablement requires separate approval.

Result:

```text
Powerful capability added without hiding risk.
```

### Flow E: Add Voice After Web And WhatsApp

1. User opens Channels.
2. Clicks `Add voice`.
3. Configures ASR, TTS, recording disclosure, escalation phone number, and latency budget.
4. Studio previews existing behavior as spoken turns.
5. Studio flags responses too long for voice.
6. User adds voice-specific presentation rules.
7. Runs voice evals.
8. Deploys voice to staging.

Result:

```text
Voice becomes a first-class adapter, not a separate bot or roadmap distortion.
```

## Relationship To Canonical UX Standard

This proposal sharpens the broader canonical target by defining the buildable agent lifecycle.

| Canonical concern | This proposal adds |
|---|---|
| Product promise | Durable implementation objects and five guarantees. |
| Studio shell | Agent-scoped Workbench and route-aware surfaces that never fake liveness. |
| Agent Workbench | Concrete sections, object states, and the 90-second editing loop. |
| Behavior editor | Selection-driven repair, sentence telemetry, semantic diff, and catch mechanic. |
| Channels | Equal channel bindings with per-channel readiness checks. |
| Tools | Tool Contract model, sandbox default, live promotion gates. |
| Knowledge | Ingestion jobs, source states, retrieval/inverse retrieval requirements. |
| Memory | Memory Policy model and source-trace requirement. |
| Evals | Provenance model and conversion from comments, takeovers, incidents, catches. |
| Deploy | Change Package, approval hash binding, rollout state machine. |
| Observe | Incident, drift, failure clustering, and Estate Health objects. |
| Govern | Compliance reviewer journey, evidence exports, tool/memory review. |

Conflict rule:

```text
Canonical UX standard governs visual language, screen quality, copy tone, and broad product principles.
This document governs the proposed agent lifecycle implementation.
If they conflict, update the conflicting document explicitly rather than resolving silently in code.
```

## Open Questions

These are not blockers to beginning implementation, but they should be answered before the relevant phase ships broadly.

1. **v0 quality bar:** How useful must a generated draft be before the product shows it to an enterprise builder?
2. **Corpus privacy boundary:** Which intake analysis jobs must run inside the customer's data plane when uploaded transcripts contain PII?
3. **Adversarial probe budget:** How often can the catch mechanic run without creating unacceptable cost or latency?
4. **Cluster thresholds:** How many similar failures should create a surfaced cluster, and how does that vary by severity?
5. **Pre-approved class policy:** Which change types are safe to pre-approve by industry and risk class?
6. **Mobile approval scope:** Which approvals may be completed on mobile, and which must force desktop review?
7. **Cross-agent learning:** When a fix in one agent may help another, how should the system recommend it without unsafe copying?
8. **Cross-tenant learning:** Is there any opt-in path for anonymized learnings across enterprises, or should tenant isolation forbid this entirely?
9. **Incident auto-rollback authority:** Which incident triggers may roll back automatically and which require human confirmation?
10. **History Walkthrough fidelity:** What evidence must be present before the system claims a new owner can understand an inherited agent?

## Glossary

- **Agent:** Versioned enterprise commitment with provable behavior, channel bindings, tools, knowledge, memory, evals, deployments, traces, and audit history.
- **Commitment Document:** Versioned source of truth describing what the agent is responsible for, what it must never do, who owns it, and what success means.
- **Channel Binding:** Connection between an agent and a user-facing channel such as web chat, WhatsApp, Telegram, Slack, Teams, SMS, email, voice, or webhook/API.
- **Tool Contract:** Plain-English and structured permission contract for a tool, including side effects, PII access, money movement, caps, owner, and approval requirements.
- **Memory Policy:** Rules for what an agent may remember, at what scope, for how long, with what consent and deletion behavior.
- **Eval Case:** Testable expected behavior with provenance from manual authoring, production, simulator, handoff, comment, migration gap, catch, or incident.
- **Change Package:** Evidence-backed review artifact generated for promotion, including semantic diff, evals, replay, risk, cost, channel readiness, approvals, and rollback target.
- **Approval:** Human or policy decision bound to a Change Package content hash.
- **Pre-Approved Class:** Narrow, explicit, time-boxed approval corridor for low-risk change types.
- **Catch:** Adversarially discovered ambiguity or edge case surfaced as a calm question to the builder.
- **Adversarial Probe Run:** Background job that tests behavior rules for literal-but-dangerous interpretations.
- **Deployment:** Runtime rollout record across shadow, canary, ramp, production, pause, failure, or rollback.
- **Incident:** Production issue record linking triggers, affected traces, containment, suspected cause, proposed fix, and candidate evals.
- **Estate Health:** Workspace-level fleet view of agents, tool grants, failures, costs, approvals, knowledge freshness, and incidents.
- **History Walkthrough:** Successor onboarding view derived from Commitment changes, Change Packages, approvals, deployments, rollbacks, incidents, comments, and open risks.

## Anti-Patterns

Do not implement:

- More surfaces before the two complete journeys are real.
- Persistent shell components that present agent-specific operational truth everywhere.
- Protected pages that render workspace facts while auth is unresolved.
- `live`, `canary`, `trace ready`, `promotion blocked`, or `parity passed` labels without durable backend state.
- Single-agent theater as the default enterprise entry point.
- Voice-only channel framing.
- Empty blank-agent starts as the default.
- Global fixture content that pretends to be live.
- Flow-builder-first mental model.
- Production hot reload without gates.
- Approval workflows outside the product.
- Commit messages as the review artifact.
- Dashboards without next actions.
- Tool grants without contracts.
- Memory writes without source traces.
- Evals without provenance.
- Estate-level enterprise management as an afterthought.
- Generic dashboards with no recommended action.
- Omnichannel abstraction that erases channel-specific constraints.
- Evidence packs as manual documentation projects.
- Change Sets that hide risk behind generic "save" events.
- Decorative motion that does not clarify state, causality, risk, progress, or control.
- State chips and badges that force the user to assemble current state from scattered fragments.
- Governance features that look enabled before RBAC, audit, content-hash binding, or evidence export are operational.

## Friday-Afternoon Test

After 90 days, a senior builder at a regulated enterprise should be able to say:

```text
I can explain what this agent owns, prove every important behavior with evidence, ship changes through approvals without slowing down, roll back in seconds when policy allows, and hand this agent to a new owner without a separate documentation project.
```

That sentence is an implementation acceptance test.

It implies four users are served:

| User | Required outcome |
|---|---|
| Builder | Can create, edit, prove, and ship safely. |
| Reviewer | Can approve from evidence, not trust. |
| On-call owner | Can contain and repair production issues quickly. |
| Successor | Can inherit the agent without tribal knowledge. |

## Final Implementation Standard

The correct implementation is a product where:

- Operational truth comes before breadth.
- Enterprise users enter through estate health and pending work, not a scripted single-agent showcase.
- The shell changes by task context and never displays generic fake liveness.
- Every visible operational claim resolves to an authorized backend object.
- Creation starts from business intent or import.
- The Commitment Document defines the agent.
- Change Sets make edits reviewable.
- Release Candidates make deployable versions explicit.
- The Agent Workbench is the daily cockpit.
- Channels are equal peer bindings.
- Tools are sandboxed by default and governed by contracts.
- Behavior is editable in prose, measurable in production, and testable through evals.
- Knowledge and memory are inspectable.
- Evals emerge from real work.
- Change Packages are the review and deploy artifact.
- Evidence Packs are the deployed proof artifact.
- Approvals bind to content.
- Rollout happens in controlled slices.
- Incidents create reports and regression tests.
- Estate view manages the fleet.
- History Walkthrough makes the work survive the worker.
- The first implementation milestone is two complete real journeys: support-agent lifecycle and Botpress migration/cutover.

This is the implementable enterprise journey: one agent, one governed lifecycle, many channels, continuous proof, and production trust.
