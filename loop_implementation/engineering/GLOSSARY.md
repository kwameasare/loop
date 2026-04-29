# Loop — Canonical Glossary

**Status:** v0.1 · **Owner:** CTO · **Authority:** This file is the single source of truth for terminology. ARCHITECTURE.md §0 is a subset; this is the superset.

When two docs disagree on terminology, this file wins. PRs that introduce new terms must add them here in the same change.

---

## A

**ADR (Architecture Decision Record).** A short, dated, structured document recording a single technical decision with its context, decision, consequences, and alternatives. Lives in `adrs/README.md`. Never edited after acceptance — superseded by a new ADR.

**Agent.** A long-lived, stateful Python class that handles inbound messages over one or more channels. The unit of deployment in Loop. Has versioned code + config (model, budget, tools, memory tiers).

**Agent-second.** Loop's compute meter — wall-clock time the runtime spends in an agent's reasoning loop. Billed at per-millisecond precision. One of the three transparent meters (subscription + agent-seconds + LLM tokens).

**Agent version.** A specific snapshot of an agent's code + config. Monotonically increasing integer (1, 2, 3, ...). Tags (`prod`, `staging`, `canary`) point at versions.

**Audit log.** Append-only, cryptographically chained record of every admin action (deploy, role change, secret access, eval-gate override). Each entry hashes the previous. Retained 7 years. Lives in control-plane Postgres with a ClickHouse mirror.

**Autonomous Node.** *(Botpress term, NOT used in Loop architecture.)* The flow-graph primitive Botpress added in 2024 to layer LLM reasoning on top of their state machine. Loop replaces this paradigm entirely — agents are code, not nodes.

## B

**Blackboard.** Shared-memory channel between multiple agents in a multi-agent orchestration. Backed by Redis. Used by Supervisor / Pipeline / AgentGraph patterns.

**BYOK (Bring-Your-Own-Key).** Customer supplies their own KMS key so Loop encrypts their data with a key Loop cannot read. Enterprise-only. Distinct from BYO LLM key (which is operationally trivial).

**Budget.** Soft / hard / degrade rule applied to a workspace, agent, conversation, or day. Soft warns; hard refuses new turns; degrade swaps to a cheaper model and continues.

## C

**Cassette.** A VCR-style recorded LLM response, used in eval suites to make LLM calls deterministic for regression detection. Stored in `tests/fixtures/llm/`. Refreshed monthly.

**Channel.** An inbound/outbound transport — web, WhatsApp, Slack, Teams, Telegram, SMS, email, Discord, voice, generic webhook. Each has an adapter package.

**Channel adapter.** The package that translates between a channel's native protocol and Loop's `AgentEvent` / `AgentResponse` types. Stateless. Lives in `packages/channels/<name>/`.

**ClickHouse.** Columnar OLAP database for traces, costs, and eval results. Always self-hosted in our k8s — never a hyperscaler-specific managed offering, for cloud portability.

**Cloud-agnostic.** Loop's commitment that the data plane runs on AWS / Azure / GCP / Alibaba Cloud / Oracle / OVHcloud / self-host with the same code, same Helm chart, configured per environment. Enforced by ADR-016 + the two-cloud rule.

**Control plane.** Multi-tenant SaaS that handles auth, billing, deploy, observability UI. Reachable globally; per-region copies but workspace-pinned.

**Conversation.** A thread of turns between one user and one agent on one channel. Long-lived; memory accumulates across turns. Has explicit start, idle, closed, and escalated states.

## D

**Data plane.** The runtime + state stores that actually execute agents. Self-hostable. Per-region. Identical code path in Cloud and self-host.

**DPA (Data Processing Agreement).** GDPR Article 28 contract between Loop and a customer. Signed before workspace activation; stored in audit log.

**DPIA (Data Protection Impact Assessment).** Process required by GDPR Article 35 for high-risk data processing. Loop conducts one per significant feature touching PII.

**DSAR (Data Subject Access Request).** Customer's GDPR Article 15 request to export all personal data. Loop bundles conversations + memory + traces as `tar.zst`. Completed within 30 days.

## E

**End user.** A person interacting with an agent via a channel — distinct from a "user" of Loop (a builder/operator). Identified per channel by `user_id`.

**Episodic memory.** Loop's per-user, semantically-searchable memory tier. Auto-summarizes turns and embeds them in Qdrant. Allows agents to recall semantically similar past interactions across a user's lifetime.

**Eval.** Automated test suite comparing agent outputs against scorers (LLM judge, regex, tool-call assertion, latency, cost, hallucination, etc.). Blocks deploy if a regression exceeds threshold.

**Eval cassette.** *See Cassette.*

**Eval-gated deploy.** Promotion to `prod` requires the candidate version's eval suite to pass and not regress >5% (configurable) vs. baseline. Enforced by `cp-deploy-controller`.

## F

**Feature flag.** Boolean or percentage gate on a feature, scoped to workspace and/or agent. Backed by `dp-feature-flag-service`. Used for canary rollouts and graceful kill switches.

**Firecracker.** AWS-developed lightweight VMM (~125ms cold start). Used by Loop to isolate out-of-process MCP tool execution. Wrapped in Kata Containers as a k8s runtime class.

## G

**Gateway (LLM Gateway).** `dp-gateway` — service that fronts every LLM provider. Handles caching, cost accounting, retries, model aliases, hard caps. Single chokepoint for cost and provider abstraction.

**Graceful degrade.** Behavior when a budget cap is approached: swap to a cheaper model + truncate history + complete the in-flight turn. Never drops mid-turn — the trust commitment.

## H

**Hard cap.** Workspace/agent/conversation budget that, when hit, refuses new turns but lets in-flight ones complete. Distinct from a "soft cap" (warn-only).

**HITL (Human-in-the-Loop).** Operator takeover of a conversation when the agent escalates or gets flagged. Loop ships escalation rules + shared inbox + CRM connectors as first-class.

**Hub.** Loop's MCP marketplace — public registry of installable MCP servers customers can grant their agents access to. Started with ~25 servers at MVP, target 200+ by month 12.

## I

**Idempotency.** Safety property where the same request twice produces the same observable result. Enforced via `Idempotency-Key` headers (POST endpoints), `request_id`-keyed gateway cache (LLM calls), and 24h dedup windows on inbound webhooks.

**Inbound webhook.** Event from a third-party (channel, integration) into Loop. Validated by signature, deduped by idempotency key, buffered in NATS, replayed on retry.

**In-process MCP.** A tool implemented as a decorated Python function in the agent's own code. Runs in the runtime process (no sandbox) because the agent owns it. Trusted by definition.

## K

**KB (Knowledge Base).** A collection of documents (PDFs, web pages, Notion, Slack threads, etc.) ingested, chunked, embedded, and searchable. Backed by Qdrant + Postgres metadata.

**Kata Containers.** OCI-compatible container runtime that wraps Firecracker (or QEMU) microVMs. Lets us run Firecracker-isolated tools as k8s pods via a `RuntimeClass`.

**KMS (Key Management Service).** Cloud-agnostic interface (`KMS` Protocol) backed by HashiCorp Vault Transit (default) or cloud-native (AWS KMS, Azure Key Vault, GCP KMS, Alicloud KMS).

## L

**LLM Gateway.** *See Gateway.*

**LMSz.** *(Botpress term, NOT used in Loop architecture.)* Botpress's proprietary closed-source inference engine. Loop's equivalent is the `TurnExecutor` — open-source, observable, no black box.

**LiveKit.** Open-source WebRTC SFU that Loop uses for voice channel media routing. Cloud-neutral (runs on any k8s).

**Loop Hub.** *See Hub.*

## M

**MCP (Model Context Protocol).** Anthropic-developed open standard for AI agent tool interfaces. Loop's universal tool ABI per ADR-003 — every tool conforms; the runtime is an MCP client.

**Memory.** Agent + user state. Four tiers in Loop: **session** (Redis, 24h TTL), **episodic** (Qdrant, semantic recall, unlimited), **user** (Postgres, persistent, unlimited), **bot** (Postgres, shared across users, unlimited).

**Model alias.** Logical name (`fast`, `cheap`, `best`, `claude-sonnet-4-7`) that resolves to a concrete provider/model at runtime. Lets workspaces configure provider routing without code changes.

## N

**NATS / NATS JetStream.** Cloud-neutral OSS event bus used by Loop for tool dispatch, channel events, eval triggers, and traces. Replaces Kafka/Kinesis/Event Hubs/Pub-Sub/MNS for portability.

**na-east, eu-west, apac-sg, cn-shanghai.** Loop's abstract region names. Map to concrete cloud regions in `infra/terraform/regions.yaml`. Code never references concrete cloud regions.

## O

**Observability.** Token-level traces + tool calls + retrievals + memory diffs + costs, recorded per turn, queryable in Studio and exportable to any OTLP backend. The product moat per ADR-010.

**OpenTelemetry / OTLP.** Vendor-neutral instrumentation standard. Loop instruments every span via OTel; collectors export to ClickHouse (default) and customer-configured destinations.

**Operator.** A human user (in a customer's organization) who supervises agents — takes over conversations, triages escalations, reviews traces. Distinct from a builder (writes code) and an end user (talks to the agent).

## P

**PASETO.** Platform-Agnostic SEcurity TOkens. Loop's API-token format (preferred over JWT for safer defaults). v4 only, workspace-scoped, with explicit scopes.

**pgvector.** Postgres extension for vector search. Supported as an alternate vector backend for self-hosters at small scale (<1M vectors). Default is Qdrant per ADR-002.

**PII (Personally Identifiable Information).** Customer data classified for redaction in logs, special encryption at rest, and DSAR scope. Patterns: email, phone, credit card, SSN, passport, JWT, API key, OAuth token.

## Q

**Qdrant.** Rust-implemented OSS vector database. Loop's default vector backend per ADR-002. Self-hosted on every cloud (Helm chart) for portability.

## R

**Rate limit.** Sliding-window counter (Redis-backed) on API requests, deploy frequency, eval runs, in-flight conversations per agent, tool calls per turn.

**Region.** *See `na-east`, `eu-west`, etc.* Abstract deployment zone, opaque to code.

**Reasoning loop.** The cycle inside `TurnExecutor`: prompt → LLM stream → parse tool calls → dispatch in parallel → feed results → repeat until terminal response or budget cap. Every iteration emits a span.

**Replay.** Re-running a historical turn (production or eval) with different model/temperature/tools/memory state, viewing a side-by-side diff. The signature debugging move in Studio.

**RLS (Row-Level Security).** Postgres feature enforcing tenant isolation. Every tenanted table has `workspace_id NOT NULL` and an RLS policy `USING (workspace_id = current_setting('loop.workspace_id')::uuid)`.

**RTO / RPO.** Recovery Time Objective / Recovery Point Objective. Loop's targets in `engineering/DR.md`.

**Runtime.** *See `dp-runtime`.* The Python service that executes agent reasoning loops. Stateless; scales horizontally; warm pool eliminates cold starts.

## S

**Sandbox.** Firecracker microVM that hosts an out-of-process MCP server. Strong isolation (separate kernel), ~100ms cold start via prewarmed pool.

**Scorer.** A function in the eval harness that judges an agent response — `llm_judge`, `regex_match`, `tool_call_assert`, `latency_le`, `cost_le`, `hallucination`, `toxicity`, `pii_leak`, etc.

**SemVer.** Semantic Versioning. Used for SDK and CLI versions; **not** used for agent versions (those are monotonic integers per ADR-009).

**SOC2.** Service Organization Control 2 — security/availability attestation. Loop targets Type 1 by month 12, Type 2 by month 18. Owner: Sec/Compliance Eng.

**SPIFFE / SPIRE.** Workload identity standards. Loop uses SPIFFE IDs for service-to-service mTLS; SPIRE issues + rotates certs every 24h.

**SSE (Server-Sent Events).** Streaming protocol Loop uses by default for token-level streaming from runtime to channel adapters and Studio. WebSocket only when bidirectional <100ms is required (per ADR-018).

**Studio.** Loop's web UI — debugger first, operator console second, optional flow visualizer last. Next.js. NOT a flow editor.

## T

**Tenant.** A workspace. The isolation boundary. Every database row is workspace-scoped + RLS-enforced.

**Tool.** *See In-process MCP / Out-of-process MCP.*

**Trace.** Per-turn record of every LLM call, tool call, retrieval, memory operation, with latency, cost, and status. OTel-formatted. Stored 90 days hot in ClickHouse, 1 year archived to object store.

**Turn.** One inbound message + the LLM/tool/response loop that produces an outbound response.

**TurnExecutor.** The Python class implementing the reasoning loop. Owner: Founding Eng #1.

## U

**User.** *Disambiguation:* in Loop docs "user" usually means an **end user** (talks to the agent). Builders and operators are humans on the customer's team. When clarity matters, say "end user" or "builder" or "operator."

## V

**Vault (HashiCorp Vault).** Cloud-neutral secrets backend. Loop's default for both KMS (Transit engine) and Secrets Manager. Cloud-native alternates supported per workspace.

**Version skew.** Difference between deployed control-plane version and data-plane version, or between SDK and runtime. Policy: data plane lags control plane by ≤ 1 minor; SDK supports last 3 runtime minors.

## W

**Workspace.** Tenant. Pinned to a region + cloud. Members have roles (`owner`, `admin`, `editor`, `operator`, `viewer`). All tenanted data carries `workspace_id`.

---

## Cross-references

- `architecture/ARCHITECTURE.md` §0 — short glossary (subset of this doc, for skim-reading).
- `engineering/HANDBOOK.md` §2.5 — naming conventions for code and branches.
- `adrs/README.md` — every term that has a decision behind it links to its ADR.
