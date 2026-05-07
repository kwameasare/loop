# Canonical UX System Gap Register

Status: draft gap register for the canonical target UX standard  
Canonical source: `loop_implementation/ux/00_CANONICAL_TARGET_UX_STANDARD.md`  
Created: 2026-05-06  
Scope: backend, services, packages, data systems, control-plane, data-plane, runtime, infra, and product platform systems required to make the canonical Studio UX real.

## 1. Executive Summary

The canonical UX standard describes Studio as a live, agent-native, evidence-rich operating environment: builders should be able to build, test, ship, observe, migrate, govern, replay, fork, inspect, and collaborate with precise control. The current repository has many strong foundations: a FastAPI control plane, a runtime turn executor, gateway routing, a KB engine, memory stores, an eval harness, a tool host, voice primitives, Helm charts, observability infrastructure, and security documentation.

The main gap is not that nothing exists. The main gap is that most of the systems the new UX depends on are not yet connected into durable, queryable, replayable product services. Several capabilities are currently implemented as in-memory facades, pure Python protocols, local test seams, or architectural plans. The canonical UX requires those seams to become production-grade control-plane and data-plane systems with persistent schemas, worker orchestration, real-time streams, analytics stores, permission models, and scale controls.

Highest priority blockers:

1. Durable canonical agent state is missing. Branches, snapshots, object states, staged/canary/production promotion, behavior policies, comments, approvals, semantic diffs, and deploy lineage are not represented as first-class persistent objects.
2. Trace and replay infrastructure is too shallow for Trace Theater, Trace Scrubber, Agent X-Ray, production replay, fork-from-frame, and "what could break" deploy previews.
3. Eval and migration are mostly primitives, not full systems. There is no durable eval orchestrator, production replay service, persona/property simulation, scenes library, Botpress migration pipeline, parity harness, or cutover lineage service.
4. Control-plane services frequently default to in-memory state. Agent versions, eval suites, conversations, KB document metadata, budgets, usage events, traces, data deletion queues, and secrets need production-grade stores or external service adapters.
5. Real-time Studio infrastructure is incomplete. The UI needs subscriptions for traces, deploys, evals, inbox, collaboration, notifications, production tail, and health. Today SSE exists primarily for runtime turns.
6. Enterprise governance is not deep enough for the UX. The current role model is workspace-level and simple; the target UX needs object-level permissions, approval policies, evidence packs, policy explanations, content-hash-bound approvals, and audit search across every important object.
7. Infra charts exist for core dependencies, but the product services that consume NATS, ClickHouse, Redis, Qdrant, object storage, and workers are not consistently wired for the canonical workload.

## 2. Source Inventory Reviewed

This register is based on a pass through the canonical UX standard and the implemented system areas below.

Canonical UX and implementation docs:

- `loop_implementation/ux/00_CANONICAL_TARGET_UX_STANDARD.md`
- `loop_implementation/architecture/ARCHITECTURE.md`
- `loop_implementation/data/SCHEMA.md`
- `loop_implementation/api/openapi.yaml`
- `loop_implementation/engineering/*` where relevant to infra, security, performance, observability, and runbooks

Packages and services:

- `packages/control-plane`
- `packages/data-plane`
- `packages/runtime`
- `packages/gateway`
- `packages/kb-engine`
- `packages/eval-harness`
- `packages/memory`
- `packages/tool-host`
- `packages/voice`
- `packages/channels/*`
- `packages/mcp-client`
- `packages/mcp-servers/*`
- `apps/studio`

Infra:

- `infra/docker-compose.yml`
- `infra/helm/loop`
- `infra/helm/loop-observability`
- `infra/terraform`
- `infra/otel-collector.yaml`
- `infra/prometheus`, `infra/grafana`, `infra/falco`

## 3. Severity Levels

P0 means the canonical UX cannot be real without this system. These are platform foundations.

P1 means a major surface can exist only as a demo or fake without this system. These should be implemented during the first complete UX implementation cycle.

P2 means the product can ship a narrower first version without it, but it is required for the uncompromising target UX.

## 4. What Already Exists

The repository is not blank. It has many useful primitives that should be reused.

Control plane:

- Workspace, membership, auth exchange, API key, secrets, audit, SAML, budgets, KB document, eval-suite, agent-version, conversation, trace-search, usage, and webhook route modules.
- Postgres-backed implementations exist for some core objects such as workspaces, API keys, refresh tokens, agents, and audit events.
- Many newer Studio-facing services still default to in-memory state through `CpApiState`.

Data plane:

- Runtime turn API with JSON and SSE endpoints.
- Auth enforcement on turn requests.
- Prometheus and OpenTelemetry middleware.

Runtime:

- `TurnExecutor` supports streaming, budget checks, multi-iteration reasoning, and parallel tool dispatch.
- Graph and multi-agent primitives exist as pure runtime models.
- Memory isolation and memory redaction helpers exist.
- Turn persistence protocol exists, with an in-memory sink.

Gateway:

- Provider abstraction, streaming client, alias resolution, idempotency cache, failover, provider routing, cost/preflight logic, and semantic cache primitives.

Knowledge:

- Chunking, parsers, embeddings adapters, Qdrant REST vector store, BM25/hybrid retrieval, lexical index migration, cost tracking, refresh scheduler, tombstones, and content hash diff primitives.

Eval:

- Suite loading, scorers, sequential and parallel runners, cassette replay, regression detection, turn frame replay models, and production failure capture primitives.

Memory:

- Postgres-backed encrypted user/bot memory, Redis session memory, in-memory stores, episodic memory primitives, and adapter seams.

Tool host:

- MCP runtime, schema validation, tool governance, sandbox warm pool, runc sandbox, rate limiting, result cache, and in-memory test hosts.

Voice:

- Voice session orchestration, ASR/TTS adapters, LiveKit room management, phone provisioning primitives, latency budgets, pipeline tracing, WebSocket pooling, SIP/Twilio helpers, and provider failover.

Infra:

- Local Docker stack with Postgres, Redis, Qdrant, NATS JetStream, MinIO, ClickHouse, and OTel collector.
- Helm chart for control-plane, runtime, gateway, KB engine, tool-host, and stateful dependencies.
- Observability chart with Prometheus, Grafana, Loki, Tempo, and Falco.
- Regional Terraform skeletons and runbooks.

## 5. Foundation Gaps

### UX-SYS-001 - Canonical Agent Object Model

Severity: P0  
Primary packages: `control-plane`, `data-plane`, `runtime`, `apps/studio`  
Canonical UX surfaces: Build, Test, Ship, Observe, Migrate, Govern

Current state:

- `agent_versions.py` is an in-memory service with `spec`, `notes`, and `promote`.
- The CP migration has `agents` and `agent_versions`, but the implemented service does not fully use a durable version table.
- `agent_versions` has an old `promoted_to` shape, not the canonical object state taxonomy.
- There are no persistent first-class records for branches, drafts, staged versions, canaries, production versions, archived versions, snapshots, behavior diffs, scenes, approvals, comments, migration lineage, or replay baselines.

Required target:

- A canonical object model that all Studio surfaces share:
  - `agents`
  - `agent_branches`
  - `agent_versions`
  - `agent_snapshots`
  - `agent_environments`
  - `agent_deployments`
  - `agent_behavior_sections`
  - `agent_behavior_policies`
  - `agent_graphs`
  - `agent_tools`
  - `agent_memory_policies`
  - `agent_channel_configs`
  - `agent_eval_bindings`
  - `agent_comments`
  - `agent_approvals`
  - `agent_lineage_events`
- Explicit object states matching the canonical UX:
  - Draft
  - Saved
  - Staged
  - Canary
  - Production
  - Archived
- Every important object should carry:
  - workspace id
  - agent id
  - branch id
  - version id
  - snapshot id where relevant
  - created by
  - created at
  - updated at
  - content hash
  - source surface
  - audit event id

Close criteria:

- Studio can load a real agent workspace entirely from durable APIs.
- Draft, saved, staged, canary, production, and archived states are enforced in backend state transitions.
- A production incident can be tied to the exact snapshot that generated it.
- Branches, snapshots, approvals, eval runs, deploys, traces, and comments all reference stable IDs.

### UX-SYS-002 - Durable Event, Trace, and Product Telemetry Lake

Severity: P0  
Primary packages: `control-plane`, `data-plane`, `runtime`, `eval-harness`, `infra`  
Canonical UX surfaces: Trace Theater, Observatory, Eval Foundry, Deployment Flight Deck, Agent X-Ray

Current state:

- OTel middleware exists and the infra includes ClickHouse and OTel collector.
- `trace_search.py` only exposes `TraceSummary` with trace id, turn id, duration, span count, and error flag.
- `TurnFrameRecorder` exists in `eval-harness` with an in-memory log protocol; it is not integrated into the runtime hot path as a durable frame log.
- Usage events are stored in an in-memory `UsageLedger`.
- Product-level events such as behavior edits, comments, approvals, eval case creation, migration mappings, deploy decisions, and replay jobs are not modeled.

Required target:

- A product telemetry lake with typed, queryable tables or streams for:
  - trace summaries
  - trace spans
  - trace frames
  - model context frames
  - prompt section attribution
  - tool call details
  - retrieval events
  - memory read/write/diff events
  - cost events
  - latency stage events
  - eval run results
  - deployment events
  - migration parity events
  - inbox/operator events
  - collaboration events
  - command palette and search events where consent allows
- Backend APIs for:
  - trace detail
  - trace scrubber playback
  - production tail
  - aggregate health
  - agent X-Ray
  - prompt sentence telemetry
  - cost and latency breakdowns

Close criteria:

- A single production turn can be replayed as a frame-by-frame trace with model input, tool calls, retrieval chunks, memory changes, cost, and latency.
- Observatory metrics are backed by server-side aggregates, not client-side summaries.
- Trace Theater can scrub, fork, diff, and explain without inventing.

### UX-SYS-003 - Async Job Orchestration and Worker System

Severity: P0  
Primary packages: `control-plane`, `eval-harness`, `kb-engine`, `voice`, `infra`  
Canonical UX surfaces: Eval Foundry, Migration Atelier, Deployment Flight Deck, Knowledge Atelier, Observatory

Current state:

- The architecture and Helm values mention NATS JetStream.
- The Docker and Helm stacks provision NATS.
- Several services describe "enqueue a job" in comments but currently mutate in-memory state or return `PENDING`.
- Eval runs, KB refresh, migration import, replay sweeps, canary analysis, evidence pack generation, and deploy preflight do not have a shared durable job system.

Required target:

- A distributed job system with:
  - durable job table
  - NATS JetStream streams
  - idempotency keys
  - per-workspace queues
  - priorities
  - retry policy
  - dead-letter queues
  - cancellation
  - progress events
  - worker heartbeats
  - lease/lock ownership
  - artifact storage
  - result summaries
- Worker deployments for:
  - eval orchestration
  - replay orchestration
  - migration imports
  - KB ingestion and refresh
  - embedding projection generation
  - deploy preflight
  - canary analysis
  - evidence pack generation
  - notification delivery
  - search indexing

Close criteria:

- Every long-running UX action has a job id, progress stream, retry semantics, audit event, and durable result.
- Job workers can scale horizontally without duplicate writes.
- Studio can reconnect and resume progress for any running job.

### UX-SYS-004 - Real-Time Studio Transport

Severity: P0  
Primary packages: `control-plane`, `data-plane`, `apps/studio`, `infra`  
Canonical UX surfaces: Shell, Simulator, Trace Theater, Observatory, Inbox, Collaboration, Deploys

Current state:

- Runtime turn streaming exists through SSE.
- There is no general Studio real-time service for traces, deploys, eval jobs, notifications, inbox claims, comments, presence, production tail, or observatory updates.

Required target:

- A real-time transport layer that supports:
  - server-sent events for job progress and trace tail
  - WebSockets for collaboration, presence, command streams, and live preview
  - per-workspace subscription authorization
  - backpressure
  - replay from last event id
  - heartbeat and reconnect
  - fan-out from NATS or Redis pub/sub
  - typed event envelopes for Studio

Close criteria:

- Studio can show live trace updates, live deploy stages, live eval progress, live inbox state, and live collaborator presence without polling.
- Reconnect does not lose state.

### UX-SYS-005 - API Contract and Generated Client Hygiene

Severity: P0  
Primary packages: `control-plane`, `apps/studio`, `loop_implementation/api`
Canonical UX surfaces: all Studio surfaces

Current state:

- `apps/studio/src/lib/cp-api.ts` uses a generated client plus a `withDefaultWorkspaceHeader` shim because workspace headers are not consistently declared in OpenAPI.
- `openapi.yaml` contains overlapping audit paths that create duplicate generated names such as `GetAuditEvents`.
- The OpenAPI surface is much smaller than the canonical UX requires.

Required target:

- A clean versioned API contract for Studio, with:
  - no duplicate operation ids
  - explicit `X-Loop-Workspace-Id` or path workspace scoping on every route
  - typed event streams
  - consistent pagination
  - consistent error envelopes
  - generated TypeScript client with no post-generation hacks
  - stable API groups for build, test, ship, observe, migrate, govern

Close criteria:

- Studio typecheck passes using only generated clients and small domain wrappers.
- Every canonical surface has route contracts before UI teams build against it.

### UX-SYS-006 - In-Memory Service Replacement Program

Severity: P0  
Primary packages: `control-plane`, `runtime`, `eval-harness`, `memory`, `tool-host`, `voice`
Canonical UX surfaces: all production surfaces

Current state:

`CpApiState` defaults many Studio-facing services to in-memory implementations:

- `data_deletion_store`
- `data_deletion_queue`
- `secrets_backend`
- `trace_store`
- `usage_ledger`
- `conversations`
- `budgets`
- `kb_documents`
- `eval_suites`
- `agent_versions`

Other packages also contain in-memory defaults:

- `InMemoryFrameLog`
- `InMemoryTurnSink`
- `InMemoryReplaySink`
- `InMemoryEvalGate`
- `InMemoryBaselineRegistry`
- `InMemorySecretsBackend`
- `PhoneNumberStore`
- `LatencyTracker`
- `SemanticCache`
- tool-host in-memory test hosts

Required target:

- Production adapters for each service:
  - Postgres for control-plane transactional state
  - ClickHouse for analytics and traces
  - Redis for caches, sessions, rate limits, locks, and presence
  - NATS JetStream for event and job streams
  - object storage for artifacts, snapshots, imports, recordings, and evidence packs
- Startup should fail closed when a production mode requires durable backing.

Close criteria:

- Production profiles cannot silently start with in-memory storage for user-facing or compliance-critical data.
- Dev/test profiles can still use in-memory stores intentionally.

### UX-SYS-007 - Object-Level Authorization and Policy Engine

Severity: P0  
Primary packages: `control-plane`, `runtime`, `tool-host`, `apps/studio`
Canonical UX surfaces: Govern, Ship, Tools Room, Collaboration, Enterprise UX

Current state:

- `authorize.py` has workspace-level roles: owner, admin, member, viewer.
- Tool governance has useful primitives, but not an integrated workspace policy center.
- Approval, deploy, memory, tool grant, KB, eval, and comment operations do not share a policy engine.

Required target:

- A policy engine that can answer:
  - who can edit prompts
  - who can change tools
  - who can connect secrets
  - who can view traces with PII
  - who can approve deploys
  - who can canary to production
  - who can export evidence packs
  - who can share demo links
  - who can publish private skills
  - who can resolve comments into eval specs
- Policy should be object-scoped and environment-aware.
- Policy decisions should be visible in UI copy with evidence and next-best actions.

Close criteria:

- Every write API checks a named permission.
- Every blocked action can explain what policy blocked it and how to proceed.

### UX-SYS-008 - Scale, Concurrency, and Fairness Controls

Severity: P0  
Primary packages: `control-plane`, `data-plane`, `runtime`, `gateway`, `eval-harness`, `tool-host`, `infra`
Canonical UX surfaces: all high-throughput surfaces

Current state:

- Runtime tool calls use `asyncio.gather` for parallel dispatch.
- Eval harness has a bounded-concurrency runner.
- Tool-host warm pool has local concurrency caps.
- Gateway has in-process and Redis-backed idempotency seams.
- There is no unified distributed concurrency model for eval sweeps, replay, migration, deploy, and production turn bursts.

Required target:

- Per-workspace and per-agent concurrency quotas.
- Queue-backed fairness so one workspace cannot starve others.
- Backpressure surfaced to Studio with precise copy.
- Distributed locks for deploys, migrations, imports, and eval writes.
- KEDA/HPA scaling driven by queue depth, stream lag, and latency.
- Load-shedding and graceful degrade policies.

Close criteria:

- Large replay, migration, and eval jobs can run while production traffic remains healthy.
- Operators can see why a job is queued, throttled, or degraded.

## 6. Surface Gap Register

### UX-SYS-010 - Agent Workbench and Behavior Editor Backend

Severity: P1  
Primary packages: `control-plane`, `runtime`

Current state:

- Agents have name, slug, description, active version, and rough version specs.
- Runtime accepts a plain `system_prompt`.
- There is no structured behavior model for goals, constraints, refusals, escalation, tone, compliance, memory policy, or tool grant intent.

Required target:

- Persisted behavior model with three levels:
  - plain language summary
  - structured policies
  - code or low-level config
- Inline risk flags:
  - ambiguous instruction
  - tool not granted
  - missing eval coverage
  - cost risk
  - memory overreach
  - conflicting policy
  - compliance-sensitive behavior
- API support for:
  - read behavior sections
  - edit section
  - lint section
  - semantic diff
  - run targeted evals
  - preview against real traces
  - lock sections under policy

Close criteria:

- Builders can edit behavior in structured form and the backend can validate, diff, version, evaluate, and deploy it.

### UX-SYS-011 - Semantic Diff and Behavior Review Service

Severity: P1  
Primary packages: `control-plane`, `eval-harness`, `runtime`

Current state:

- Textual version notes exist.
- Regression detection compares eval reports.
- No semantic behavior diff service exists.

Required target:

- A service that compares drafts and versions by meaning, not only text.
- It should produce:
  - added constraints
  - removed constraints
  - changed refusals
  - changed tool permissions
  - changed memory behavior
  - likely risk changes
  - eval coverage gaps
  - cost and latency implications
- The adversarial "second pair of eyes" review should cite traces, evals, or policies.

Close criteria:

- A deploy preflight can say precisely what changed and why it matters.

### UX-SYS-012 - Prompt Sentence Telemetry and Agent X-Ray

Severity: P1  
Primary packages: `runtime`, `control-plane`, `eval-harness`, `data-plane`

Current state:

- Runtime emits token/tool events but does not attribute behavior to prompt sections.
- No model exists for prompt sections being cited, contradicted, ignored, or dead-weight.

Required target:

- Runtime instrumentation that records:
  - prompt section ids included in context
  - prompt sentence ids
  - retrieval/source citations
  - tool decisions linked to behavior section ids where possible
  - memory writes linked to policy ids
- Analytics that power:
  - hover-a-sentence telemetry
  - Agent X-Ray
  - dead-context detection
  - branch hot-path analysis
  - cost contribution by behavior area

Close criteria:

- Builder can hover a prompt sentence and see observed use, contradiction, and representative traces.

### UX-SYS-013 - Agent Map Persistence and Round-Trip Model

Severity: P1  
Primary packages: `control-plane`, `runtime`, `apps/studio`

Current state:

- `agent_graph.py`, `graph_executor.py`, and `flow_validation.py` provide runtime graph primitives.
- These are pure code models, not a persisted Studio domain with layout, comments, ownership, branches, graph comprehension state, and deploy integration.

Required target:

- Persisted graph model:
  - nodes
  - edges
  - node positions
  - layout metadata
  - validation issues
  - graph version hash
  - graph-to-code mapping
  - code-to-graph mapping
  - comments on stable node ids
  - hazards
- Clear product stance: graph is primarily for comprehension and control, not a Botpress-style flow gravity center.

Close criteria:

- Agent Map can load, validate, diff, comment, and fork real agent graphs without becoming a separate source of truth.

### UX-SYS-014 - Tools Room and Connector Lifecycle

Severity: P1  
Primary packages: `control-plane`, `tool-host`, `mcp-client`, `runtime`, `gateway`

Current state:

- Tool-host has governance primitives, sandboxing, warm pools, and MCP runtime pieces.
- Marketplace primitives exist but are mostly pure/in-memory.
- Secrets backend defaults to in-memory.
- There is no complete product service for tool grants, mock/live modes, credential status, tool metrics, or tool import from curl/Postman/OpenAPI.

Required target:

- Tool registry and grant service:
  - installed tools
  - tool versions
  - tool schema
  - side effect class
  - read/write/admin risk
  - secrets references
  - scopes
  - mock response fixtures
  - live credential health
  - rate limits
  - kill switch
  - eval coverage per tool
  - per-tool cost, latency, error rate
- Tool import pipeline:
  - paste curl
  - import OpenAPI
  - import Postman collection
  - infer typed MCP tool
  - generate mock contract
  - require approval for write/admin tools

Close criteria:

- A builder can connect, test, mock, observe, revoke, and evaluate tools with the same precision as prompts.

### UX-SYS-020 - Preview and Multi-Channel Simulator Sessions

Severity: P1  
Primary packages: `data-plane`, `runtime`, `channels`, `control-plane`, `apps/studio`

Current state:

- `/v1/turns` can run a turn with an ad hoc prompt and model.
- Channel packages exist.
- Studio does not have a durable preview session model or channel simulation service.

Required target:

- Preview sessions:
  - isolated from production memory and secrets
  - tied to branch/version/snapshot
  - selectable channel chrome
  - selectable user persona
  - injected context
  - mock tool/memory/retrieval controls
  - replay and fork support
- Multi-channel simulator:
  - web
  - Slack
  - Teams
  - WhatsApp
  - SMS
  - email
  - voice
- Single-keystroke channel switching should use the same underlying conversation replay.

Close criteria:

- The simulator can render the same conversation against multiple channels and versions using durable preview state.

### UX-SYS-021 - Inline ChatOps Command Runtime

Severity: P2  
Primary packages: `runtime`, `control-plane`, `apps/studio`

Current state:

- No slash-command parser or preview command executor exists.

Required target:

- Safe command parser and executor for preview-only commands such as:
  - `/swap model=...`
  - `/disable tool=...`
  - `/inject ctx=...`
  - `/as-user persona=...`
  - `/replay turn=...`
  - `/diff against=...`
- Commands must be audited as preview actions and must never mutate production unless explicitly promoted through normal gates.

Close criteria:

- Preview becomes a power surface without bypassing governance.

### UX-SYS-022 - Trace Theater Detail API and Scrubber

Severity: P0  
Primary packages: `runtime`, `data-plane`, `control-plane`, `eval-harness`, `infra`

Current state:

- Trace search returns only trace summaries.
- Runtime events include tokens, tool call start/end, degrade, and complete.
- Eval harness has `TurnFrame`, but runtime does not persist full canonical frames.

Required target:

- Trace detail should expose:
  - ordered frames
  - model input context at each LLM call
  - assistant deltas
  - tool call args and redacted results
  - retrieval query and chunks
  - memory reads
  - memory diffs
  - budget/cost events
  - latency spans
  - policy decisions
  - fallback/degrade events
  - channel envelopes
- Scrubber support:
  - frame seek
  - play at 1x, 2x, 4x
  - fork from frame
  - explain selected frame

Close criteria:

- Trace Theater can behave like a debuggable timeline rather than a static span list.

### UX-SYS-023 - Fork and Replay From Trace Frame

Severity: P1  
Primary packages: `runtime`, `eval-harness`, `control-plane`, `data-plane`

Current state:

- Deterministic replay primitives exist in `eval-harness`.
- No runtime/control-plane API can fork a branch from a trace frame with captured state.

Required target:

- A fork service that can create a draft branch from:
  - a full trace
  - a specific frame
  - a production conversation
  - an eval failure
- It must capture:
  - agent snapshot
  - prompt state
  - tool state
  - KB version
  - memory state or selected memory variant
  - channel state
  - user input sequence

Close criteria:

- Pressing `f` on a trace frame creates a branch that can be replayed and edited without losing provenance.

### UX-SYS-024 - Production Replay Against the Future

Severity: P1  
Primary packages: `eval-harness`, `runtime`, `control-plane`, `data-plane`

Current state:

- `FailedTurn` capture and deterministic replay models exist.
- Parallel eval runner exists.
- No durable service can select production conversations and replay them against drafts at scale.

Required target:

- Replay service:
  - sample production conversations
  - replay against draft or branch
  - compare old/new behavior
  - compute behavioral distance
  - rank likely risky conversations
  - store results
  - expose side-by-side diffs
- Should support "100 worst conversations last week" and "top 5 likely to change" flows.

Close criteria:

- Deploy preflight can run real production traffic against a draft before promotion.

### UX-SYS-025 - Agent X-Ray Analytics

Severity: P1  
Primary packages: `runtime`, `control-plane`, `data-plane`, `infra`

Current state:

- There is no observed-behavior analytics model.

Required target:

- Analytics should answer:
  - which prompt sections are used
  - which sections are dead weight
  - which tools are called from where
  - which tool results are ignored
  - which branches are hot paths
  - which low-frequency branches create high cost
  - which KB chunks dominate answers
  - which memory policies write most often
- Every claim must link to representative traces.

Close criteria:

- The builder can see what the agent actually does, not just what the config says.

### UX-SYS-026 - Honest Trace Identity and Signed Snapshots

Severity: P1  
Primary packages: `runtime`, `data-plane`, `control-plane`, `infra`

Current state:

- Request ids and trace ids exist, but the target "honest first message" contract is not implemented.
- Snapshots are not first-class.

Required target:

- Every production turn should carry stable internal identity:
  - trace id
  - version id
  - snapshot id
  - environment
  - channel
- Snapshot should freeze:
  - prompts
  - tools
  - KB version
  - memory policies
  - eval suite
  - deploy state
  - model settings
- Snapshots should be signed and replayable.

Close criteria:

- A regulator, operator, or customer-support engineer can identify exactly what agent version produced a response.

### UX-SYS-030 - Knowledge Atelier Lifecycle and Query Analytics

Severity: P1  
Primary packages: `kb-engine`, `control-plane`, `data-plane`, `infra`

Current state:

- KB engine has chunking, embeddings, Qdrant, BM25, parsers, refresh scheduler, and content diff primitives.
- CP KB document service is in-memory and only tracks source URL, title, state, chunk count, and refresh state.
- Query logs and missed-retrieval analytics do not exist as a product service.

Required target:

- Durable KB lifecycle:
  - source records
  - ingestion jobs
  - parser version
  - chunker version
  - embedding model version
  - content hash
  - document lineage
  - tombstones
  - permissions
  - refresh cadence
  - failure diagnostics
- Query analytics:
  - production queries
  - retrieved chunks
  - cited chunks
  - missed chunks
  - confidence
  - rerank decisions
  - chunk-level usage

Close criteria:

- Knowledge Atelier can explain why a chunk was or was not retrieved and safely fix it.

### UX-SYS-031 - Inverse Retrieval Lab and Embeddings Explorer

Severity: P2  
Primary packages: `kb-engine`, `eval-harness`, `infra`

Current state:

- No inverse retrieval or UMAP/projection service exists.

Required target:

- Inverse retrieval:
  - for a selected chunk, find production queries that should have matched it
  - rank misses by closeness
  - suggest re-chunk, metadata, rerank, or instruction fixes
- Embeddings explorer:
  - offline projection jobs
  - cluster metadata
  - outlier detection
  - duplicate detection
  - source and citation links

Close criteria:

- KB curation becomes measurable and visual rather than manual guessing.

### UX-SYS-032 - Memory Studio Diff Ledger and Safety System

Severity: P0  
Primary packages: `memory`, `runtime`, `data-plane`, `control-plane`

Current state:

- Persistent encrypted memory exists.
- Runtime memory isolation and redaction helpers exist.
- There is no durable memory diff ledger, policy explanation, or safety review workflow.

Required target:

- Memory Studio backend:
  - memory facts
  - memory scopes
  - before/after diffs
  - source turn
  - policy id
  - actor
  - retention class
  - PII/secret classifier result
  - conflict markers
  - deletion events
  - legal hold events
- Runtime should emit memory read/write frames into traces.

Close criteria:

- Builder can see exactly what memory changed, why, from which source, and whether it is safe.

### UX-SYS-033 - Eval Foundry Persistent Orchestrator

Severity: P0  
Primary packages: `eval-harness`, `control-plane`, `runtime`, `infra`

Current state:

- Eval suite metadata service is in-memory and run creation returns queued/pending style records.
- Eval harness has useful local runners and scorers.
- There is no persistent eval case/result model deeply tied to agents, branches, deploys, and production traces.

Required target:

- Durable eval system:
  - suites
  - cases
  - case variants
  - expected behaviors
  - scorers
  - judge rubrics
  - runs
  - per-case results
  - artifacts
  - baselines
  - flaky markers
  - coverage by behavior section/tool/channel/persona
  - owner and review state
- Distributed eval runner:
  - job scheduling
  - concurrency caps
  - cancellation
  - cost limits
  - result streaming

Close criteria:

- Eval Foundry can create, run, compare, and govern evals as durable product objects.

### UX-SYS-034 - Production Conversations, Scenes, and Comments as Specs

Severity: P1  
Primary packages: `eval-harness`, `control-plane`, `data-plane`, `apps/studio`

Current state:

- Production failure capture can convert failed turns into samples.
- No scenes library exists.
- Comments are not modeled as durable product objects.

Required target:

- Conversation-to-eval workflows:
  - save turn as eval
  - save conversation as scene
  - canonicalize production conversation
  - resolve comment as expected behavior
  - spawn eval case from comment
- Scenes library:
  - workspace-scoped scenes
  - production source lineage
  - tags
  - owners
  - replay button
  - review links

Close criteria:

- Reviewer criticism can become a regression test without manual YAML editing.

### UX-SYS-035 - Persona and Property Simulation

Severity: P2  
Primary packages: `eval-harness`, `runtime`, `control-plane`, `gateway`

Current state:

- No persona simulator or conversation property tester exists.

Required target:

- Persona simulator:
  - generated but explainable personas
  - scenario generation
  - provenance
  - safety rails
  - eval case export
- Property tester:
  - mutate real turns across typos, tone, language, paraphrase, context missing, context added
  - cluster failure modes
  - produce robustness score

Close criteria:

- Builder can scale-test a single real failure pattern into a robust eval set.

### UX-SYS-036 - LLM Judge Tuning and Explainable Scoring

Severity: P1  
Primary packages: `eval-harness`, `control-plane`, `gateway`

Current state:

- Scorers exist, but no productized judge rubric service exists.

Required target:

- Judge rubric model:
  - rubric text
  - sample previews
  - judge reasoning
  - calibration examples
  - disagreement markers
  - versioning
  - audit trail
- Live preview on sample turns while editing the rubric.

Close criteria:

- Builders can tune judge rubrics until the judge agrees with their human review.

### UX-SYS-037 - Regression Bisect for Agent Changes

Severity: P2  
Primary packages: `control-plane`, `eval-harness`, `runtime`

Current state:

- No branch/change commit history service exists beyond rough versions.

Required target:

- A bisect service that can:
  - list ordered changes between two times or versions
  - replay regressing cases
  - binary-search the change set
  - identify the exact prompt/tool/KB/memory/eval change that caused failure

Close criteria:

- When evals go red, Studio can identify the causing change without manual archaeology.

### UX-SYS-040 - Migration Atelier Import Service

Severity: P0  
Primary packages: new `migration` service, `control-plane`, `runtime`, `tool-host`, `kb-engine`, `eval-harness`

Current state:

- No importer service exists for Botpress, Dialogflow, Rasa, Copilot Studio, Custom GPTs, or similar platforms.
- Canonical UX explicitly requires easy porting from Botpress and similar platforms.

Required target:

- Migration importer framework:
  - source platform registry
  - verified/planned/aspirational source status
  - file upload and object storage
  - source parsing
  - flow/prompt/tool/KB/intent/entity extraction
  - mapping into Loop agent objects
  - unsupported feature detection
  - secrets reconnection
  - channel reconnection
  - owner assignment
  - import audit log
- Botpress should be the first-class import path:
  - exported bot files
  - nodes/workflows
  - intents
  - entities
  - knowledge bases
  - actions/integrations
  - channel configs where exportable

Close criteria:

- A Botpress builder can import a real project and receive a mapped Loop draft with unsupported items clearly called out.

### UX-SYS-041 - Migration Parity Harness, Cutover, and Lineage

Severity: P0  
Primary packages: `migration`, `eval-harness`, `control-plane`, `runtime`, `data-plane`

Current state:

- No migration parity harness exists.

Required target:

- Parity harness:
  - run imported Loop agent against source transcripts
  - compare structure, behavior, cost, and risk
  - produce parity score
  - generate remediation tasks
  - convert migrated conversations into evals
- Cutover support:
  - staging endpoint
  - canary import
  - rollback to source
  - customer-facing migration report
  - persistent migration workspace after cutover

Close criteria:

- Migration Atelier can prove parity and preserve lineage months after cutover.

### UX-SYS-050 - Deployment Flight Deck State Machine

Severity: P0  
Primary packages: `control-plane`, `eval-harness`, `runtime`, `infra`

Current state:

- `DeployController` has a useful local state machine and protocols for builder, registry, kube, eval gate, baseline, and provenance.
- Deploy state is in-memory.
- It handles one deploy at a time inside a process-local lock.
- It does not model staged/canary/production object states, approvals, traffic splits, rollback targets, or persistent deploy events.

Required target:

- Durable deployment system:
  - deployment records
  - environment records
  - state transitions
  - artifact records
  - preflight reports
  - approval requests
  - content-hash approvals
  - traffic split records
  - canary metrics
  - rollback plan
  - post-deploy verification
  - deploy event stream
- Production changes must flow through explicit gates.

Close criteria:

- Flight Deck can promote, block, canary, rollback, and explain every deployment from durable state.

### UX-SYS-051 - Preflight and "What Could Break" Service

Severity: P1  
Primary packages: `control-plane`, `eval-harness`, `runtime`, `gateway`, `tool-host`

Current state:

- Eval gate in deploy controller compares pass rate to baseline.
- There is no integrated preflight report across evals, policies, tools, cost, latency, memory, KB, and production replay.

Required target:

- Preflight report sections:
  - behavior diff
  - eval status
  - top likely changed production conversations
  - cost delta
  - latency delta
  - tool grant changes
  - secret/config changes
  - memory policy changes
  - KB version changes
  - approval state
  - rollback target
  - recommended next action

Close criteria:

- A builder knows why shipping is safe or unsafe before touching production.

### UX-SYS-052 - Persistent Canary and Traffic Controller

Severity: P1  
Primary packages: `control-plane`, `runtime`, `channels`, `infra`

Current state:

- There are canary-related files, but the core deploy controller shown is not a durable production traffic router.

Required target:

- Canary controller:
  - percentage-based traffic split
  - channel-aware canary
  - workspace and agent scoping
  - sticky assignment
  - automatic rollback policy
  - metric thresholds
  - audit and approval
  - per-region rollout

Close criteria:

- Production can run v23 and v24 side by side with controlled traffic and automatic rollback.

### UX-SYS-053 - Observatory Metrics, Tail, and Ambient Health

Severity: P1  
Primary packages: `control-plane`, `data-plane`, `runtime`, `gateway`, `infra`, `apps/studio`

Current state:

- Prometheus middleware exists.
- Usage ledger is in-memory.
- Trace search is summary-only.
- Grafana dashboards exist outside the product.

Required target:

- Product observability service:
  - agent health aggregate
  - eval pass trend
  - cost trend
  - p50/p95/p99 latency
  - escalation rate
  - tool error rate
  - retrieval miss rate
  - memory safety events
  - production tail
  - custom pinned charts
  - anomaly detection
  - health mood ring composite
- APIs should power in-product cards, not only external Grafana.

Close criteria:

- Builder can understand production health from Studio without leaving Studio.

### UX-SYS-054 - Cost, Capacity, and Latency Budget Visualizer

Severity: P1  
Primary packages: `gateway`, `runtime`, `voice`, `control-plane`, `infra`

Current state:

- Gateway cost/preflight logic exists.
- Voice latency budgets exist.
- There is no product service that turns span data into optimization recommendations.

Required target:

- Cost/capacity service:
  - per-agent cost model
  - per-turn cost breakdown
  - per-span latency breakdown
  - provider/model what-if simulation
  - cache recommendation
  - second-iteration elimination suggestion
  - KB/tool latency contribution
  - budget drag target
  - draft change suggestions

Close criteria:

- The latency budget visualizer can explain which spans must shrink and offer previewable fixes.

### UX-SYS-055 - In-Product Runbooks and Incident Integration

Severity: P2  
Primary packages: `control-plane`, `infra`, `apps/studio`

Current state:

- Engineering runbooks exist in markdown.
- There is no in-product runbook service or incident status integration.

Required target:

- Product runbook system:
  - one-page operational playbooks linked from surfaces
  - incident status
  - alert links
  - recent related traces
  - owner contacts
  - action checklist
  - evidence capture

Close criteria:

- An operator can respond to a cost spike or degradation from the Observatory context.

### UX-SYS-060 - Inbox and HITL Production Queue

Severity: P0  
Primary packages: `control-plane`, `data-plane`, `runtime`, `channels`, `apps/studio`

Current state:

- `InboxQueue` is in-memory and has claim/release/resolve semantics.
- `ConversationService` is an in-memory facade for Studio demos.
- Runtime and channels are not fully integrated with a durable operator handoff workflow.

Required target:

- HITL service:
  - durable inbox items
  - assignment and locking
  - SLA timers
  - escalation reasons
  - operator notes
  - agent silence/resume
  - operator send message
  - channel-specific send adapters
  - resolution categories
  - comments-as-specs hook
  - audit log
  - real-time updates

Close criteria:

- Human operators can safely take over and resolve production conversations from Studio.

### UX-SYS-061 - Multiplayer Collaboration and Commenting

Severity: P1  
Primary packages: `control-plane`, `apps/studio`, `infra`

Current state:

- No durable comment, presence, or collaborative editing backend exists.

Required target:

- Collaboration service:
  - presence
  - cursor/selection state
  - comments on stable IDs
  - comments on traces, eval cases, KB chunks, prompt sections, deploys
  - review requests
  - activity feed
  - content-hash-bound approvals
  - conflict resolution
  - operational transform or CRDT for prompt text

Close criteria:

- Multiple builders can review, comment, edit, and approve without losing context or invalidating safety guarantees.

### UX-SYS-062 - Comments as Specifications

Severity: P1  
Primary packages: `control-plane`, `eval-harness`, `apps/studio`

Current state:

- No comment-to-eval workflow exists.

Required target:

- Backend workflow:
  - comment says "this should have done X"
  - resolver accepts expected behavior
  - eval case is generated
  - case is linked to original turn/comment
  - future deploys run it

Close criteria:

- Resolved comments can become regression specifications automatically.

### UX-SYS-063 - Notifications, Activity, and Home Pins

Severity: P2  
Primary packages: `control-plane`, `apps/studio`

Current state:

- No general notification or activity service exists.

Required target:

- Notification system:
  - workspace activity feed
  - user notification inbox
  - quiet hours
  - severity
  - dedupe
  - dismiss/acknowledge
  - object links
- Pin-anything-to-homepage:
  - saved chart
  - saved search
  - trace
  - eval suite
  - KB source
  - audit filter

Close criteria:

- Studio home is personalized and operationally useful.

### UX-SYS-064 - Command, Search, Saved Searches, and Share Links

Severity: P1  
Primary packages: `control-plane`, `apps/studio`, `infra`

Current state:

- No global search index or command registry service exists.

Required target:

- Global search:
  - agents
  - versions
  - traces
  - conversations
  - KB docs/chunks
  - eval cases
  - tools
  - comments
  - deployments
  - audit events
- Saved searches and filters.
- Share/link governance:
  - RBAC-gated links
  - redacted trace shares
  - demo links
  - branch quick-review links
  - expiration and audit

Close criteria:

- Builder can navigate Studio by command/search and share precise artifacts safely.

### UX-SYS-070 - Voice Stage Control Plane

Severity: P1  
Primary packages: `voice`, `control-plane`, `runtime`, `channels`, `apps/studio`

Current state:

- Voice package has session, ASR/TTS adapters, phone, LiveKit, latency, and tracing primitives.
- No productized Voice Stage APIs exist for full configuration, demos, voice evals, consent, recordings, or preview links.

Required target:

- Voice control plane:
  - voices
  - ASR/TTS provider settings
  - call numbers
  - LiveKit room records
  - phone routing
  - demo share links
  - consent config
  - recording config
  - interruption policy
  - turn-taking settings
  - voice eval suites

Close criteria:

- Builder can configure, test, share, and evaluate voice agents as first-class products.

### UX-SYS-071 - Voice Debugging and Queued Speech Preview

Severity: P2  
Primary packages: `voice`, `runtime`, `data-plane`, `apps/studio`

Current state:

- Voice latency tracing exists, but not the UX-specific debug stream.

Required target:

- Voice debugging telemetry:
  - queued TTS transcript before audio
  - ASR partials/finals
  - VAD events
  - interruption events
  - first audio byte
  - audio duration
  - model/tool spans inside call trace

Close criteria:

- Voice Stage can show what the agent is about to say and why the call felt slow.

### UX-SYS-072 - Phone Provisioning and Call Records

Severity: P1  
Primary packages: `voice`, `control-plane`, `channels`

Current state:

- Phone provisioning has an in-process store and E.164 validation.
- LiveKit rooms have a Postgres manager.

Required target:

- Persistent phone/control APIs:
  - claim/release number
  - carrier integration
  - inbound route
  - outbound permissions
  - call record
  - consent flag
  - recording artifact
  - transcript artifact
  - trace linkage
  - audit log

Close criteria:

- Phone and voice production traffic can be operated and audited end to end.

### UX-SYS-080 - Enterprise Evidence, Compliance, and Procurement Workflows

Severity: P1  
Primary packages: `control-plane`, `infra`, `apps/studio`

Current state:

- Audit event system exists.
- SAML has a stub/optional implementation.
- Security and compliance docs are extensive.
- Evidence packs, procurement pages, RBAC matrix views, and audit explorer product APIs are not complete.

Required target:

- Enterprise backend:
  - audit explorer with payload fetch and redaction policy
  - evidence pack generator
  - SSO/SCIM product state
  - RBAC matrix
  - data residency status
  - BYOK/HYOK status
  - DPA and compliance artifact state
  - procurement/security profile page
  - export logs with approvals

Close criteria:

- Enterprise buyers and admins can self-serve governance evidence from Studio.

### UX-SYS-081 - Secrets, Credentials, and Reconnect Flow

Severity: P1  
Primary packages: `control-plane`, `tool-host`, `channels`, `voice`

Current state:

- In-memory secrets backend exists.
- Vault/cloud backend seams exist in docs and packages.
- Tool/channel credential lifecycle is not fully productized.

Required target:

- Credential lifecycle:
  - connect
  - verify
  - rotate
  - reconnect
  - expire
  - revoke
  - repair migration mappings
  - audit access
  - show redacted status
  - environment-specific credential bindings

Close criteria:

- Migration, tools, channels, and voice can safely reconnect secrets without exposing raw values.

### UX-SYS-082 - Marketplace and Private Skills Platform

Severity: P2  
Primary packages: `control-plane`, `tool-host`, `mcp-client`, `apps/studio`

Current state:

- MCP marketplace registry, installs, reviews, signing, and analytics primitives exist as pure/in-memory service code.
- No complete hosted marketplace service or private workspace skills system is wired into Studio.

Required target:

- Marketplace service:
  - browse
  - install
  - pin version
  - update
  - review
  - private workspace catalog
  - publisher verification
  - dependency scanning
  - signatures
  - usage analytics
  - approval flow for risky tools

Close criteria:

- Platform teams can publish private skills and downstream teams can install them with governance.

### UX-SYS-083 - AI Co-Builder and Rubber Duck Backend

Severity: P1  
Primary packages: `control-plane`, `runtime`, `eval-harness`, `gateway`

Current state:

- No AI co-builder service exists beyond general LLM gateway primitives.

Required target:

- Co-builder backend:
  - Suggest/Edit/Drive consent grammar
  - read-only context boundary
  - proposed changes as diffs
  - provenance and evidence
  - user approval
  - rollback
  - action log
  - risk review
  - rubber duck diagnostic mode
  - adversarial behavior review mode

Close criteria:

- The AI co-builder can propose and apply changes without bypassing builder control.

### UX-SYS-084 - Telemetry Consent, Feedback, and In-Product Help

Severity: P1  
Primary packages: `control-plane`, `apps/studio`, `infra`

Current state:

- Engineering observability exists, but builder-facing telemetry consent and product feedback workflows are not productized.
- There is no backend service for in-product help surfaces, feedback capture, consent state, or support handoff tied to current trace/screen context.

Required target:

- Consent and help backend:
  - workspace telemetry policy
  - user telemetry preference
  - product analytics consent
  - event redaction mode
  - feedback tickets
  - screen/trace/context attachment
  - support escalation
  - public status integration
  - help article/runbook linking
  - audit of consent changes

Close criteria:

- Studio can collect feedback, show help, and emit product telemetry only inside explicit workspace/user consent boundaries.

### UX-SYS-085 - Whitelabel, Branding, and Share Experience Controls

Severity: P2  
Primary packages: `control-plane`, `apps/studio`, `voice`, `channels`

Current state:

- No durable workspace branding or whitelabel configuration service is visible in the inspected backend.
- Voice demo links, external trace shares, and customer-facing migration reports need branding and domain controls.

Required target:

- Branding/whitelabel service:
  - workspace logo
  - brand colors within accessibility limits
  - custom domain
  - email/sms sender identity
  - voice demo branding
  - external share branding
  - migration report branding
  - allowed domains
  - audit and approval for public-facing changes

Close criteria:

- Enterprise builders can send demos and reports that feel native to their organization without weakening security or accessibility.

### UX-SYS-090 - Channel Config and Multi-Channel Production Sync

Severity: P1  
Primary packages: `channels`, `control-plane`, `data-plane`, `runtime`

Current state:

- Channel packages exist for many destinations.
- Persistent channel configuration, simulator chrome metadata, and production conversation sync are not complete as a unified product model.

Required target:

- Channel system:
  - channel configs
  - credentials
  - webhook verification state
  - inbound/outbound adapters
  - channel-specific formatting
  - channel chrome metadata for simulator
  - delivery status
  - retry state
  - message audit

Close criteria:

- A builder can test and deploy the same agent across channels with correct channel behavior and trace linkage.

## 7. Package-Level Gap Summary

### Control Plane

Gaps:

- Too many product services default to in-memory state.
- Agent version model is not canonical enough for branches, snapshots, deploys, approvals, or state taxonomy.
- Eval suite, conversation, KB document, trace, usage, budget, and data deletion services need durable production adapters.
- Policy model is workspace-role based, not object/action/environment based.
- OpenAPI is missing most canonical UX contracts.
- No job orchestration, notification, collaboration, search, migration, or co-builder services.

Recommended additions:

- `loop_control_plane.agent_state`
- `loop_control_plane.branches`
- `loop_control_plane.snapshots`
- `loop_control_plane.deployments`
- `loop_control_plane.approvals`
- `loop_control_plane.comments`
- `loop_control_plane.notifications`
- `loop_control_plane.jobs`
- `loop_control_plane.search`
- `loop_control_plane.migrations`
- `loop_control_plane.preflight`
- `loop_control_plane.policies`
- `loop_control_plane.realtime`

### Data Plane

Gaps:

- Turn API streams results but does not persist full trace frames or model context snapshots.
- Turn persistence is a protocol with in-memory sink, not wired as a production hot-path system.
- Conversation storage exists in migrations but CP conversation service is still a demo facade.
- No preview session isolation model.
- No replay/fork state capture.

Recommended additions:

- Runtime frame recorder integrated into every turn.
- Durable turn write path with async outbox.
- Preview-session tables and APIs.
- Production conversation export/replay APIs.
- Data-plane event publisher to NATS/ClickHouse.

### Runtime

Gaps:

- Uses a plain `system_prompt`; no structured behavior policies.
- Emits basic turn events, but not enough for Trace Scrubber, X-Ray, memory diffs, retrieval explainability, or prompt sentence telemetry.
- Graph primitives are not integrated into persisted Studio objects.
- Tool, memory, retrieval, and policy decisions are not fully linked by stable IDs.

Recommended additions:

- Behavior section compiler.
- Policy linter and risk flag emitter.
- Trace frame emission contract.
- Prompt section attribution hooks.
- Replay/fork hooks.
- Memory diff hooks.
- Tool grant enforcement hooks.

### Gateway

Gaps:

- Good provider, failover, idempotency, and cost primitives exist.
- Needs product-grade what-if modeling, per-draft budget simulation, latency recommendation data, and prompt/model cache telemetry.
- Semantic cache is in-process unless Redis is configured.

Recommended additions:

- Provider/model recommendation API.
- Cost/latency simulator.
- Cache telemetry events.
- Per-workspace provider policy integration.

### KB Engine

Gaps:

- Strong retrieval and ingestion primitives exist.
- Query logs, missed retrieval, inverse retrieval, embeddings map, source lineage UI APIs, and durable ingestion jobs are missing.
- CP KB metadata service is in-memory and not fully linked to DP KB tables.

Recommended additions:

- Ingestion worker and job progress.
- Query log storage.
- Inverse retrieval service.
- Embedding projection worker.
- KB readiness and quality scoring.
- Chunk lineage and citation analytics APIs.

### Eval Harness

Gaps:

- Local runners and replay primitives are strong.
- No durable orchestrator, persistent results store, production replay service, scenes library, persona/property generator, or judge tuning backend.

Recommended additions:

- Eval worker service.
- Eval result tables.
- Replay sweep service.
- Scene library service.
- Judge rubric service.
- Regression bisect service.

### Memory

Gaps:

- Persistent encrypted memory exists.
- Memory Studio needs before/after diffs, source turn linkage, safety flags, retention policy, and audit-level explanation.

Recommended additions:

- Memory write ledger.
- Memory safety classifier.
- Memory policy records.
- Memory retention and deletion workflows.
- Trace frame integration for memory reads/writes.

### Tool Host

Gaps:

- Strong sandbox and governance primitives exist.
- Product services for tool lifecycle, grants, mock/live mode, tool import, credential status, and tool observability are missing.
- Pool eviction/drain controller is noted as out of scope in current warm pool.

Recommended additions:

- Tool grant service.
- Tool import service.
- Sandbox pool controller.
- Tool metrics exporter.
- Tool mock/live environment service.
- Workspace kill-switch integration.

### Voice

Gaps:

- Voice primitives exist but are not productized into Studio-facing APIs.
- Demo links, voice evals, consent, recordings, queued speech preview, and full trace integration are missing.
- Phone provisioning store is in-process.

Recommended additions:

- Voice control-plane routes.
- Voice demo share service.
- Voice trace frame integration.
- Call record store.
- Recording/transcript artifact store.
- Voice eval runner integration.

### Channels

Gaps:

- Many channel packages exist.
- A unified channel config, simulator, webhook state, delivery status, and channel trace model is missing.

Recommended additions:

- Channel config tables.
- Channel simulator metadata.
- Delivery status events.
- Webhook verification and health APIs.
- Outbound operator message APIs.

### Studio App

Gaps:

- Target UX foundation components exist from the UI pass.
- Many data sources are currently static fixtures or thin wrappers around incomplete CP APIs.
- Generated API client needs cleanup.

Recommended additions:

- Route-level data loaders backed by real APIs.
- Real-time event client.
- Error/permission state handling from backend policy.
- Product analytics consent integration.

## 8. Infra and Platform Gaps

### INFRA-UX-001 - Worker Deployments Are Missing

Severity: P0

Helm deploys control-plane, runtime, gateway, KB engine, and tool-host. The canonical UX needs additional worker deployments:

- eval worker
- replay worker
- migration worker
- KB ingestion worker
- embedding projection worker
- deploy controller worker
- canary analyzer
- notification worker
- search indexer
- evidence pack worker
- collaboration/realtime service

Close criteria:

- Worker charts exist with HPA/KEDA, resource limits, secrets, queues, metrics, and PDBs.

### INFRA-UX-002 - NATS JetStream Is Provisioned but Not Productized

Severity: P0

Current state:

- NATS is present in Docker and Helm.
- Product code does not consistently publish or consume durable JetStream events for jobs, trace frames, deploys, evals, or replay.

Required target:

- Named streams:
  - `loop.jobs`
  - `loop.trace.frames`
  - `loop.deploy.events`
  - `loop.eval.events`
  - `loop.migration.events`
  - `loop.kb.events`
  - `loop.inbox.events`
  - `loop.collaboration.events`
- Stream retention, consumers, DLQs, and replay policy documented and enforced.

### INFRA-UX-003 - ClickHouse Product Schema Is Missing

Severity: P0

Current state:

- ClickHouse is provisioned.
- OTel collector can write generic traces/logs.
- Product query schemas for Trace Theater, Observatory, X-Ray, cost, and replay are not defined.

Required target:

- Product tables/materialized views for:
  - turn facts
  - span facts
  - frame facts
  - cost facts
  - prompt section facts
  - tool facts
  - retrieval facts
  - memory facts
  - health rollups
  - canary rollups
  - eval rollups

### INFRA-UX-004 - Autoscaling Defaults Are Too Conservative

Severity: P1

Current state:

- HPA templates exist, but autoscaling is disabled by default for core services.
- No queue-depth autoscaling exists for the future worker classes.

Required target:

- Enable production autoscaling profiles.
- Add KEDA or equivalent queue scaling for workers.
- Add scale-to-zero where appropriate for expensive non-hot-path workers.
- Define load-test gates for p95 and p99 UX targets.

### INFRA-UX-005 - Stateful Data Plane Scale Is Not Fully Realized

Severity: P1

Current state:

- Architecture mentions Citus/PgBouncer and sharded data plane direction.
- Helm currently bundles standard Postgres by default.
- Runbooks mention PgBouncer, but chart support is not present in the inspected Helm templates.

Required target:

- Production-grade data plane profile:
  - PgBouncer
  - read replicas where useful
  - partitioning/sharding strategy
  - retention strategy
  - online migrations
  - query performance gates
  - tenant-level data residency controls

### INFRA-UX-006 - Secrets Delivery Conflicts With Security Posture

Severity: P1

Current state:

- Security docs say production secrets should not live in environment variables.
- Helm still exposes `secrets.llmApiKey` and `jwtSigningKey` as chart secret values and services consume envFrom.

Required target:

- Vault/Secrets Manager projected file or sidecar integration as production default.
- Clear dev-only env secret mode.
- Credential rotation events exposed to Studio.

### INFRA-UX-007 - Search Index Infrastructure Is Missing

Severity: P1

Current state:

- No dedicated search service/index for Studio objects.

Required target:

- Search backend:
  - Postgres FTS for first pass or OpenSearch/Tantivy service for scale
  - object indexer workers
  - permission-aware queries
  - saved searches
  - rank signals

### INFRA-UX-008 - Artifact Storage Needs Product Conventions

Severity: P1

Current state:

- MinIO/S3 is present.
- No canonical artifact layout is documented for snapshots, imports, replays, eval outputs, recordings, evidence packs, and generated reports.

Required target:

- Object storage paths and metadata for:
  - snapshots
  - trace exports
  - migration imports
  - eval artifacts
  - replay artifacts
  - voice recordings
  - transcripts
  - compliance packs
  - generated demos

## 9. Schema and Documentation Drift

### DOC-SYS-001 - `SCHEMA.md` Is Behind Actual Migrations

Severity: P1

Current state:

- `loop_implementation/data/SCHEMA.md` says the as-shipped state includes older migration endpoints and lists some deferred fields that have since moved in later migrations.
- Actual migration files include newer CP and DP migrations, including agent alignment, API key alignment, KB tables, memory encryption, lexical index, channel conversation index, and voice rooms.

Required target:

- Regenerate or update `SCHEMA.md` so it distinguishes:
  - shipped migrations
  - implemented services
  - planned schema
  - canonical UX-required schema
- Add a schema coverage matrix tied to this gap register.

Close criteria:

- Engineers can trust the schema doc while implementing canonical UX services.

### DOC-SYS-002 - Architecture Mentions Services Not Yet Implemented

Severity: P1

Current state:

- `ARCHITECTURE.md` names services such as eval orchestrator, deploy controller, MCP registry, webhook ingester, ClickHouse-backed analytics, and NATS event buses.
- Some of these exist as primitives, not deployed services.

Required target:

- Architecture should mark each system as:
  - implemented and wired
  - implemented as library primitive
  - in-memory/demo only
  - planned
  - canonical UX gap

Close criteria:

- Product and engineering planning can tell what exists versus what is aspirational.

## 10. Recommended Dependency Order

This is the dependency order that minimizes fake UI and merge conflict risk.

Phase 0 - Contract and foundations:

1. Fix OpenAPI/client hygiene.
2. Create canonical object/state schema.
3. Add jobs/outbox/event primitives.
4. Add Studio real-time event transport.
5. Replace in-memory service defaults for production mode.
6. Add object-level authorization framework.

Phase 1 - Trace, replay, and eval core:

1. Runtime frame recorder.
2. Trace detail API.
3. Snapshot service.
4. Eval persistent service.
5. Production replay service.
6. Preflight report service.

Phase 2 - Build and ship surfaces:

1. Behavior editor backend.
2. Semantic diff/risk review.
3. Agent map persistence.
4. Tool grants and tool lifecycle.
5. Deployment flight deck state machine.
6. Canary controller.

Phase 3 - Knowledge, memory, migration:

1. KB lifecycle and query logs.
2. Memory diff ledger and safety classifier.
3. Botpress importer.
4. Migration parity harness.
5. Scenes and comments-as-specs.

Phase 4 - Enterprise, collaboration, polish:

1. Collaboration/presence/comments.
2. Search/saved searches/share links.
3. AI co-builder.
4. Voice Stage product APIs.
5. Evidence packs and procurement workflows.
6. Agent X-Ray, inverse retrieval, embeddings explorer, and advanced polish systems.

## 11. Minimum Backend Slice for a Non-Fake Canonical UX

If one cycle must make the new Studio feel real, the minimum backend slice should be:

1. Canonical agent object model with branches, snapshots, versions, object states, and deploy environments.
2. Runtime trace frame recorder and trace detail API.
3. Persistent eval service with production conversation to eval.
4. Production replay against draft versions.
5. Behavior editor structured policy storage and semantic diff.
6. Deployment preflight with eval, replay, cost, policy, and rollback sections.
7. KB lifecycle with durable ingestion status and retrieval trace linkage.
8. Memory diff ledger.
9. HITL durable inbox with operator takeover and resolution-to-eval.
10. Botpress migration importer plus parity harness v1.
11. Real-time Studio subscriptions for jobs, traces, evals, deploys, and inbox.
12. Object-level authorization and content-hash-bound approvals.

Without these, the UI can look excellent but will not embody the canonical UX. With these, the UI can be incomplete in polish and still behave like the intended product.

## 12. Final Gap Thesis

The current platform has good ingredients. The canonical UX needs those ingredients promoted into a coherent product operating system.

The largest missing system is the connective tissue: durable state, event history, replayable traces, job orchestration, policy decisions, and analytics that every surface can trust. Once that connective tissue exists, the extravagant UX is not decoration. It becomes the natural frontend for a system that genuinely knows what the agent is, what changed, what happened, what might break, who approved it, and how to recover.
