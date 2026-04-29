# Architecture Decision Records (ADRs)

ADRs capture *why* we made a decision at a point in time. Format: title, status, context, decision, consequences, alternatives. Lightweight on purpose.

| #   | Title                                                | Status   |
|-----|------------------------------------------------------|----------|
| 001 | Python as the primary runtime language               | Accepted |
| 002 | Qdrant over pgvector as the default vector store     | Accepted |
| 003 | MCP as the universal tool ABI                        | Accepted |
| 004 | NATS JetStream over Kafka for the event bus          | Accepted |
| 005 | Firecracker microVMs for tool sandboxing             | Accepted |
| 006 | Apache 2.0 license for the OSS core                  | Accepted |
| 007 | Control plane / data plane split                     | Accepted |
| 008 | Voice as a first-class channel from MVP              | Accepted |
| 009 | SemVer for agent versions, monotonically increasing  | Accepted |
| 010 | OpenTelemetry → ClickHouse for observability         | Accepted |
| 011 | Auth0 for cloud auth, Ory Kratos for self-host       | Accepted |
| 012 | Pricing model: subscription + agent-seconds + 5% LLM | Accepted |
| 013 | Multi-region control plane: active-passive until $X  | Accepted |
| 014 | Episodic memory: region-pinned, cross-region opt-in  | Accepted |
| 015 | Eval-gated deploys (block on regression)             | Accepted |
| 016 | Cloud-agnostic by default (no AWS lock-in)           | Accepted |
| 017 | Authorization: RBAC + deny-by-default per-resource   | Accepted |
| 018 | Streaming protocol: SSE by default, WebSocket opt-in | Accepted |
| 019 | RAG chunking: semantic boundaries, per-bot override   | Accepted |
| 020 | Tenant DB isolation: single Postgres + RLS at scale  | Accepted |
| 021 | Container runtime for tool sandbox: Kata + Firecracker | Accepted |
| 022 | Idempotency: request_id gateway cache + webhook dedup | Accepted |
| 023 | Eval determinism: cassette + temp=0 + 3-run averaging | Accepted |
| 024 | Deprecation policy: 30-day flag for breaking changes  | Accepted |
| 025 | Telemetry: 90d hot, customer OTLP export anytime     | Accepted |
| 026 | Agent code isolation: per-workspace runtime processes | Accepted |
| 027 | Public eval registry: CC-BY for community suites     | Accepted |
| 028 | Pricing meter precision: per-second, per-token, exact | Accepted |

Each ADR file is `NNN-slug.md`.

---

# ADR-001 — Python as the primary runtime language

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

We need a primary language for the agent runtime, the SDK developers write against, the LLM gateway, the KB engine, and the eval harness. Botpress is TypeScript-only; that's a wedge for us — but only if we don't repeat the mistake in reverse. Most ML and LLM engineers are Python-fluent. The agent ecosystem (LangChain, LlamaIndex, DSPy, OpenAI Agents SDK, Anthropic Agent SDK) is overwhelmingly Python.

## Decision

The agent runtime, the primary SDK, the LLM gateway, the KB engine, and the eval harness are written in **Python 3.12+** (asyncio everywhere, `from __future__ import annotations` enabled, Pydantic v2 for typing).

The CLI is written in **Go** (single static binary, sub-50ms startup).

The TS SDK is **auto-generated** from Pydantic types via OpenAPI codegen so it's always in parity with the Python SDK.

Channel adapters are Python by default; voice may use Go where ultra-low-latency network I/O justifies it.

## Consequences

- ✅ Direct access to the Python ML ecosystem (transformers, sklearn, langchain, llama-index, dspy).
- ✅ Aligns with the dominant developer base for AI engineering.
- ✅ Pydantic gives us strong runtime validation + JSON-schema generation for free.
- ⚠️ Some performance ceiling on hot paths — we'll mitigate with native extensions (orjson, msgspec) and shipping perf-critical bits to Go.
- ⚠️ Python deps + cold start can be slow; warm pool architecture (see ARCHITECTURE.md §3) addresses this.

## Alternatives considered

- **TypeScript everywhere** — Botpress's choice. Locks us out of the ML ecosystem.
- **Rust runtime** — fastest, most isolated, but talent pool is small and developer ergonomics suffer.
- **Go runtime** — great perf, weak ML ecosystem.
- **Polyglot from day 1** — too many moving parts for a 5-eng MVP.

---

# ADR-002 — Qdrant as the default vector store

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

We need a vector store for KB and episodic memory. Botpress uses Postgres + pgvector. Benchmarks (50M × 768-dim, 99% recall) show pgvector at ~471 QPS / 74.6 ms p99 vs Qdrant at ~41 QPS / 38.7 ms p99 — but Qdrant scales horizontally and supports advanced quantization (binary, scalar, product), while pgvector is constrained to a single instance and fights OLTP workload for resources.

For Loop's enterprise targets we will routinely exceed pgvector's practical 1–10M ceiling.

## Decision

**Qdrant** is the default vector store, deployed as a stateful service alongside the data plane.

The KB engine has a pluggable backend interface; pgvector remains supported for self-hosters who want a single-DB footprint at smaller scale. Pinecone and Weaviate are roadmap.

## Consequences

- ✅ Predictable p99 latency for end-user-facing retrieval.
- ✅ Horizontal scale-out via native sharding.
- ✅ Quantization keeps memory cost down at scale.
- ⚠️ One more service to operate. Mitigated: Qdrant has a clean Helm chart and operates well at our scale.
- ⚠️ Customers must learn a new admin surface vs Postgres-only setups.

## Alternatives considered

- pgvector — fine for self-hosters at small scale; insufficient for cloud + enterprise.
- Pinecone — closed/managed-only; conflicts with our self-host story.
- Weaviate — solid, but heavier than Qdrant and Java-based. Future option.
- Milvus — also strong, but operationally heavier; revisit at scale.

---

# ADR-003 — MCP as the universal tool ABI

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

Anthropic's Model Context Protocol (MCP) shipped in late 2024 and through 2025 became the de facto standard for AI agent tool interfaces. Cursor, Claude Desktop, OpenAI Agents SDK, Anthropic Claude Agent SDK, Windsurf, and hundreds of community servers all speak it. Botpress added MCP in 2025 but as a side feature — their primary tool model is still custom action manifests.

## Decision

Loop's tool model **is** MCP. The runtime is an MCP client. The Loop Hub is a marketplace of MCP servers. Loop ships a Python decorator that makes any function an in-process MCP server; out-of-process MCP servers run in Firecracker sandboxes (ADR-005).

We do not invent a parallel "action" abstraction. There is one tool ABI.

## Consequences

- ✅ Customers can use the entire MCP ecosystem of their already-built servers.
- ✅ Customers can use Loop agents from Claude Desktop / Cursor / etc. via Loop's MCP-server-mode (we expose Loop *as* an MCP server too).
- ✅ Standard auth, schema, and lifecycle.
- ⚠️ MCP is young and may evolve. Mitigation: pin to a major version, ship adapters when needed.
- ⚠️ If a competing standard emerges (OpenAI's tool format, Google's), we'll need adapter shims. Plan: build a minimal adapter layer behind the runtime so swapping the on-the-wire format is contained.

---

# ADR-004 — NATS JetStream over Kafka

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

We need an async event bus for tool dispatch, channel events, eval triggers, traces, and multi-agent handoffs. Kafka is the industry default but operationally heavy for our scale.

## Decision

**NATS JetStream** for all async messaging. Single-binary, Go-implemented, strong streams + request/reply, replication, and acknowledgements. Operationally tractable for self-host.

We will revisit Kafka if and only if a workspace exceeds NATS's documented ceilings (millions of msgs/s) — far beyond our 5-year planning horizon.

## Consequences

- ✅ One service, easy to deploy in self-host.
- ✅ Strong primitives: streams, KV store, object store, request/reply.
- ✅ Native cluster mode in cloud.
- ⚠️ Smaller ecosystem of tooling than Kafka. Acceptable.

---

# ADR-005 — Firecracker microVMs for tool sandboxing

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

MCP servers can be customer-supplied or community code. We must run them with strong isolation: a hostile or buggy tool cannot touch the runtime, sibling tools, or other workspaces. Botpress uses V8 isolates with a 60-second timeout — fine for JS only.

Loop tools are arbitrary languages. We need real OS-level isolation.

## Decision

**Firecracker microVMs** in a prewarmed pool. Each tool invocation lands in a microVM with a hardened minimal Linux rootfs, network policies that allow only the tool's declared egress, a CPU/RAM cap, and a strict timeout. Cold start ≤100ms via the pool.

For purely in-process MCP servers (auto-MCP'd Python functions in the agent's own code), we run them in-process in the runtime — they are trusted, and the speed savings matter.

## Consequences

- ✅ Strong isolation; equivalent to the major hyperscalers' serverless runtimes (AWS Lambda, Azure Functions on Mariner, GCP Cloud Run gen2 — all use Firecracker or gVisor).
- ✅ Fast cold start vs container-based options.
- ⚠️ Operational complexity — microVMs are not k8s-native. We use [Kata Containers](https://katacontainers.io/) on top of containerd to wrap Firecracker as a k8s runtime class.
- Alternative: gVisor. Faster cold start (~20ms), weaker isolation (shared kernel surface). Acceptable fallback if microVM ops becomes a burden; revisit at scale.

---

# ADR-006 — Apache 2.0 for OSS core

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

License choice shapes adoption and monetization. Options surveyed:
- **Apache 2.0** — maximum permissiveness, most adoption, no monetization protection.
- **AGPL** — viral; what Botpress v12 used. Scares enterprises.
- **SSPL** (MongoDB) — blocks managed-service competitors but isn't OSI-approved.
- **BSL** (HashiCorp) — time-delayed conversion; flexible but signals lock-in.
- **Elastic License v2** — protects against managed competitors with a free OSS path.

## Decision

The data plane (runtime, SDK, gateway, channels, KB engine, eval harness, observability exporters) is **Apache 2.0**.

The control plane (multi-tenant orchestration, billing, admin UI) is **closed-source, commercial**.

Enterprise add-ons (SSO, audit, dedicated support, advanced eval registry) are commercial. The OSS path is feature-complete for self-hosters at small/medium scale; the commercial path adds operations, scale, and convenience.

## Consequences

- ✅ Maximum adoption signal — Apache OSS is the most trusted license tier for enterprise.
- ✅ Permissive license attracts contributors.
- ⚠️ Cannot legally prevent a hyperscaler from offering "Loop on \<their cloud\>." Mitigation: brand, network effects, and the closed control plane.
- We will revisit if a hyperscaler launches a forked managed Loop and meaningfully threatens revenue. The OSS license is forever, but new components can adopt different licenses if needed.

---

# ADR-007 — Control plane / data plane split

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

Customers want self-host (data sovereignty, compliance) but also want the convenience of a managed dashboard, deploy pipeline, and eval orchestrator. A single monolith forces the choice; a split lets us offer both.

## Decision

The platform is split into a **control plane** (auth, billing, deploy, observability backend, MCP marketplace, eval orchestrator) and a **data plane** (runtime, channels, tools, state stores). The data plane runs in three modes:

1. **Cloud** — control plane points at our cloud data plane.
2. **Self-host** — customer runs both, no phone-home.
3. **Hybrid** — customer hosts data plane in their VPC, points at our control plane via mTLS.

## Consequences

- ✅ Same data plane code in all modes — no fork.
- ✅ Customers can adopt cloud quickly, then move to hybrid as compliance grows.
- ⚠️ More ops surface — two planes means two CI/CD targets. Acceptable.

---

# ADR-008 — Voice as first-class from MVP

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

Voice is engineering-heavy. It's tempting to defer to Phase 2.

## Decision

Voice ships in the MVP (month 5–6). Same agent code as chat. Pipeline: LiveKit/SIP → Silero VAD → Deepgram STT → runtime → Cartesia/ElevenLabs TTS. Target ≤700ms p50.

## Consequences

- ✅ Voice is a moat. Vapi/Retell sized markets in 2024–25; Botpress has nothing native.
- ⚠️ One founding engineer dedicated.
- ⚠️ Latency ceiling is the #1 schedule risk. If we miss, voice ships at month 7 instead — accept the slip.

---

# ADR-009 — Agent versioning

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

How do we identify, deploy, and roll back agent versions?

## Decision

Each agent has a monotonically increasing **integer version** (1, 2, 3, …). No SemVer. Tags (`prod`, `staging`, `canary`) point at versions. Deploys promote a version into a tag via the deploy controller; rollbacks repoint the tag.

Eval-gating: a version cannot be promoted to `prod` if its eval suite regresses ≥5% vs baseline (configurable).

## Consequences

- ✅ Simple model, easy to reason about.
- ✅ Tags decouple deployment from versioning.
- Drop SemVer because there's no API contract between agent versions to communicate.

---

# ADR-010 — Observability: OTel + ClickHouse

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

We need fast, queryable, scalable trace storage for all agent traffic. Customers also want to export traces to their own backend (Datadog, Honeycomb, New Relic).

## Decision

**OpenTelemetry** for instrumentation. **OTLP** as the wire format. OTel Collector in the data plane, exporting to:
1. ClickHouse in the control plane (the Studio dashboard backend).
2. Optionally, customer-configured OTLP destinations (Datadog, Honeycomb, etc.).

ClickHouse for storage because of cardinality + scan speed. 90-day retention hot, then S3 archive.

## Consequences

- ✅ Vendor-neutral instrumentation.
- ✅ Customers don't lose access to their traces if they leave Loop.
- ⚠️ ClickHouse is one more thing to operate. Helm-based statefulset on every cloud; managed alternatives (Altinity, ClickHouse Cloud, Aiven) supported but not required.

---

# ADR-011 — Auth: Auth0 (cloud) / Ory Kratos (self-host)

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

Identity is too important to build from scratch. We need OIDC, SAML, MFA, social login, password reset, account recovery, on day 1.

## Decision

**Auth0** for the cloud control plane. **Ory Kratos** for self-host (Apache 2.0, full feature set). Both sit behind the same OIDC interface in `cp-api` — token type and verification logic are identical.

## Consequences

- ✅ Battle-tested auth from day 1.
- ✅ SSO/SAML/MFA out of the box.
- ⚠️ Vendor cost for Auth0 in cloud. Acceptable until ~10K MAUs.
- Switch trigger: if Auth0 prices become punitive, migrate cloud to Ory Hydra (same vendor as Kratos).

---

# ADR-012 — Pricing model: 3 transparent meters

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

Botpress's bill is opaque (subscription + AI Spend + external Meta/Twilio bills + overage rate-card). We need a transparent, predictable model.

## Decision

Three meters, all on the bill:

1. **Platform subscription** — per seat, predictable.
2. **Agent-seconds** — compute time the runtime spends on reasoning loops. Per-second granularity. Usage roll-up shown in real time.
3. **LLM tokens** — pass-through with a **disclosed 5% margin**.

Channel costs (WhatsApp, Twilio) are surfaced as line items on the Loop invoice with zero markup, even though they're billed by the providers. Customers see the *full* AI cost in one place.

Hard caps degrade gracefully: swap to a cheaper model, never drop a conversation mid-turn.

## Consequences

- ✅ Predictability — the #1 trust commitment.
- ✅ Customers understand exactly what they're paying for.
- ⚠️ Margin compression on token pass-through. Acceptable; we make money on subscription + agent-seconds.

---

# ADR-013 — Multi-region control plane: active-passive until scaling trigger

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

Two abstract regions at launch (`na-east`, `eu-west`; concrete cloud regions vary). Active-passive is operationally simpler for MVP; active-active requires distributed consensus for metadata, cross-region transaction semantics, and significant complexity. Botpress is active-active but that's post-Series-B cost. We are pre-seed.

## Decision

**Active-passive control plane for MVP (through month 12).** One region is the leader; the other is hot standby. Workspaces are pinned to a region at creation-time; cross-region failover is manual (DNS flip + Postgres promotion).

Cross-region replication: Postgres logical replication to the standby region (streaming), Redis sentinel for failover coordination, ClickHouse via native replication.

**Revisit trigger:** active-active is reconsidered when either:
- ARR reaches $X (TBD via CEO/Finance at month 6; estimate $2M).
- A single customer pays for multi-region admin + they have >2 teams in different regions.

At that point: write a successor ADR proposing cross-region Postgres via Citus or distributed event log via NATS, and evaluate the cost/benefit.

## Consequences

- ✅ Single source of truth for workspace config. Simpler auth, billing, deploy gates, audit log.
- ✅ No distributed-consistency bugs (consensus, quorum, eventual consistency edge cases).
- ✅ Operator can reason about state synchronously.
- ⚠️ Non-leader region has 100–500 ms latency on admin operations (reads go to the leader). Acceptable for operations; not ideal for real-time dashboards. Mitigation: cache read-heavy queries on secondary region with 5-min TTL.
- ⚠️ Unplanned primary failure means manual intervention to promote secondary. Recovery time ≤ 15 min with runbook; acceptable for MVP. At scale, revisit to automate.

## Alternatives considered

- **Active-active with Postgres native partitioning.** Postgres 16 supports write-write replication via logical replication + conflict resolution, but conflict semantics are subtle (LWW, custom rules). Safer at scale; too complex for MVP.
- **Multi-cloud / multi-region from day 1.** Every major SaaS started single-region then expanded. First-mover penalty is smaller than overengineering.
- **Control plane entirely in a NATS global mesh.** Intriguing but NATS consensus is coarse-grained; we'd reinvent Postgres-over-NATS and lose our relational tooling.

---

# ADR-014 — Episodic memory: region-pinned with cross-region opt-in

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

Episodic memory lives in Qdrant. End users may interact across sessions, channels, and times — and conceivably across regions (e.g., an international customer with agents running in multiple regions). ADR-013 establishes that the control plane is region-pinned; the question is whether memory is likewise pinned or shared.

## Decision

**Episodic memory is pinned to the workspace's home region** (set at creation, per ADR-013). A conversation in `na-east` retrieves memories from `na-east` Qdrant; if the user context shifts to `eu-west`, the agent there cannot see the `na-east` memory without an explicit cross-region fetch.

**Cross-region opt-in:** enterprise customers requiring truly global rollout (e.g., 24/7 customer support spanning US + EU) can enable "global episodic" mode at additional cost. This ships a streaming replication pipeline (Qdrant → Kafka → Qdrant) with 2–5 min eventual-consistency lag. The app side handles stale reads explicitly.

Revisit trigger: when the first paying customer signs a $X k/month contract AND explicitly requests global memory AND our Qdrant operator signals the replication cost is < 10% of the primary cluster.

## Consequences

- ✅ Simpler. One Qdrant instance per region; no cross-region replication network overhead.
- ✅ Predictable latency: memory queries are local.
- ✅ Clear GDPR story: memories stay in the customer's chosen region.
- ⚠️ Conversations that span regions see a memory "gap." Mitigation: the agent is aware of this in its system prompt and can re-summarize context from the conversation itself, or use the cross-region API with a freshness warning.
- ⚠️ Limits the use case of seamless global-rollout chat (though this is rare for MVP). Revisit at month 12.

## Alternatives considered

- **Every episodic memory is automatically replicated to all regions.** Adds ~50% infrastructure cost and complexity (merge semantics, consistency, deletions). Unnecessary for MVP.
- **Lazy cross-region fetch on demand.** Less infrastructure; slower UX if memory is frequently cross-region. Revisit for enterprise.
- **Separate "global memory" store on top of Qdrant.** New service, new failure mode. Deferring.

---

# ADR-015 — Eval-gated deploys

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

We promised eval-driven dev as a core wedge. How tightly do we couple deploy to eval?

## Decision

**Required by default for `prod` tag promotions.** A new agent version cannot be promoted to `prod` unless:
- An eval suite is attached to the agent.
- The latest run passed (no regression > 5% vs baseline, configurable per workspace).
- Recently retraced production conversations (last 7 days) included as test cases.

Workspaces can disable eval-gating per-agent via an explicit override flag (logged to audit).

## Consequences

- ✅ Forces good practice. Builders ship with confidence.
- ⚠️ Some friction — customers must build eval suites. Mitigation: `loop eval init` scaffolds a default suite from production replay.

---

# ADR-016 — Cloud-agnostic by default

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

Customers pick their cloud for reasons unrelated to us — committed spend, data residency, regulator, regional preference, geopolitical (Chinese mainland customers must run on Alibaba; some EU public-sector must run on OVHcloud). Botpress is AWS-only and that's a real wedge for us, but only if we don't repeat the inverse mistake (Azure-only, GCP-only, …).

Beyond customer demand, the Loop runtime itself is hosted multi-cloud — different prod regions on different clouds is operationally normal, not an exception.

## Decision

Loop is **cloud-agnostic by construction**. Concretely:

1. **Compute = Kubernetes.** We use each cloud's managed k8s (EKS / AKS / GKE / ACK) and never the cloud's proprietary container service.
2. **Object storage = S3-compatible API only.** AWS S3, GCS interop, Alibaba OSS, MinIO — same client. Azure Blob via S3 gateway (or MinIO Gateway) when needed.
3. **Postgres = standard wire protocol** via managed services or self-hosted on k8s (CloudNativePG). No Aurora-only features.
4. **Redis = standard wire protocol** via managed services or self-hosted.
5. **Vector store = Qdrant** as a workload on our k8s, identical on every cloud.
6. **KMS = HashiCorp Vault** by default; cloud-native KMS as optional alternate per workspace (ADR doesn't preclude — just doesn't depend).
7. **Secrets = HashiCorp Vault** by default.
8. **Identity = OIDC.** Auth0 (multi-cloud SaaS) or Ory Kratos (self-host).
9. **CDN/WAF = Cloudflare** by default — itself cloud-neutral.
10. **IaC = Terraform / Pulumi** — never CloudFormation, ARM templates, Deployment Manager, ROS.
11. **Internal interfaces** wrap every cloud-touching primitive (`ObjectStore`, `KMS`, `SecretsBackend`, `EmailSender`). At least two implementations of each, validated in CI.
12. **Two-cloud rule.** No primitive in our code may have only one implementation.

The full mapping table and interface definitions are in `architecture/CLOUD_PORTABILITY.md`.

## Consequences

- ✅ Customer choice on day 1 (AWS, Azure, GCP, Alibaba, OVHcloud, self-host).
- ✅ Simpler internal mental model — "kubernetes + standard wire protocols" everywhere.
- ✅ Hyperscaler negotiation leverage — if AWS prices go up, we move.
- ⚠️ Some loss of cloud-specific magic (managed Step Functions–style orchestration, hyperscaler IAM-as-code).
  Mitigation: NATS + our own deploy controller fill the orchestration gap; we don't need cloud IAM if mTLS via SPIFFE handles service-to-service auth.
- ⚠️ Multi-cloud CI matrix adds runtime to our pipeline. Acceptable — runs in parallel, total wall time still under our 12-min budget.
- ⚠️ More integration surface to test. Mitigation: nightly real-cloud test job per cloud, alongside the per-PR mocked matrix.

## Alternatives considered

- **AWS-only with a "we'll port later" promise.** This is what most pre-Series-B startups do. It bakes lock-in everywhere and the port never happens.
- **Multi-cloud at platform launch but proprietary on cloud-native primitives** (e.g., DynamoDB, Cosmos DB). Hides lock-in inside our code instead of removing it.
- **Single cloud chosen by capacity** (e.g., GCP for the better k8s defaults). Trades one customer-affinity problem for another.

## Forbidden services (without explicit ADR override)

- AWS: Aurora-only extensions, DynamoDB, Lambda as primary compute, Step Functions, EventBridge, AppSync, IAM-based S2S auth as the only path.
- Azure: Cosmos DB, Service Bus as primary bus, Functions as primary compute, AAD-only auth.
- GCP: Spanner, Firestore as primary store, Pub/Sub as primary bus.
- Alibaba: MaxCompute, MNS as primary bus, Function Compute as primary compute.

Anything in this list requires a successor ADR with explicit justification.

---

# ADR-017 — Authorization: RBAC + deny-by-default per-resource

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

Multiple actors: builders, operators, analytics folks, customer success, and eventually end-user-as-admin. We need granular, auditable access control. Botpress uses role-based only (owner/editor/viewer); we need resource-scoped grants (e.g., "User A can promote agents in workspace B, but cannot delete agents; User C can only read traces, not modify agents").

## Decision

**Five built-in roles:** Owner, Admin, Editor, Operator, Viewer (see SECURITY.md §6.1). Each role has explicit scopes (e.g., `agents:deploy`, `traces:read`, `eval:gating_override`).

**Per-resource grants** for enterprise: custom roles map scope sets to API permissions; API endpoints deny by default unless the token has the required scope AND the actor has a grant for that resource.

**Scope model (scope:permission:resource):** e.g., `agents:deploy:agent-123`, `traces:read:workspace-456`. Implemented via JWT scopes in PASETO tokens; verified at the gateway before routing to services.

Audit log: every authorization decision (allow / deny) is logged with the scope evaluated.

## Consequences

- ✅ Granular + auditable.
- ✅ Scales to complex orgs without rebuilding auth.
- ⚠️ Scope explosion — we may end up with 20+ scopes if not disciplined. Mitigation: ship 5 built-in roles that cover 95% of use cases; custom roles for enterprise.

## Alternatives considered

- ABAC (attribute-based) from day 1. Simpler for large orgs, but harder to reason about and debug. We default to RBAC + per-resource; revisit at 50 enterprise customers.

---

# ADR-018 — Streaming protocol: SSE by default, WebSocket opt-in

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

Channels (web, voice, etc.) need bidirectional streaming: runtime → channel (agent tokens, tool calls) and channel → runtime (user messages). SSE is simpler; WebSocket is more efficient for high-frequency bidirectional chat.

## Decision

**Server-Sent Events (SSE) is the default transport** for all streaming responses (agent tokens, traces, eval results). Works over HTTP/2 (multiplexed). Fully stateless on the server; no persistent connections to manage.

**WebSocket is opt-in** for use cases requiring <100 ms round-trip on bidirectional messages (e.g., real-time collaborative agents, voice channels). Only when SSE latency becomes the bottleneck.

Channels pick the transport at deploy time via a config flag (`channel.streaming_transport: sse | websocket`). Default: SSE.

## Consequences

- ✅ SSE by default keeps infrastructure simple (no WebSocket state per connection, no persistent-connection pooling).
- ✅ Web widget works on HTTP/1.1 with SSE; modern HTTP/2 is faster.
- ⚠️ Bidirectional messages on SSE require a separate HTTP POST channel. Acceptable; most turn→response flows are unidirectional.

## Alternatives considered

- gRPC streaming. Too heavy for web widgets; requires HTTP/2; auth harder.
- Polling. Wasteful; we avoid.

---

# ADR-019 — RAG chunking: semantic boundaries, per-bot override

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

Knowledge base documents are chunked before embedding. Naive fixed-size chunks (e.g., 1024 tokens) cross logical boundaries, hurting retrieval quality. Different use cases need different strategies: customer support (hierarchical), research (dense), source code (AST-aware).

## Decision

**Default chunking:** semantic sentence/paragraph boundaries (use spaCy for English; fallback to fixed 1024-token). Overlap is 50 tokens to preserve context at chunk boundaries.

**Per-KB override:** `chunking_strategy` in `knowledge_bases.config_json` can be set to:
- `semantic` (default)
- `fixed_tokens:{size}` (e.g., `fixed_tokens:512`)
- `fixed_sentences:{count}` (e.g., `fixed_sentences:5`)
- `code_aware` (reserved for future; parses AST, chunks at function/class boundaries)

Changing strategy requires re-indexing the KB (async, background job).

## Consequences

- ✅ Better retrieval for most use cases.
- ✅ Customers can tune without code changes.
- ⚠️ Semantic chunking adds CPU cost at ingest time (~5–10%). Acceptable; ingest is offline.

---

# ADR-020 — Tenant DB isolation: single Postgres + RLS at current scale

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

Three isolation models: single DB + RLS, schema-per-tenant, DB-per-tenant. Each has tradeoffs. We pick based on scale (customer count, data volume per tenant).

## Decision

**Single Postgres per region with Row-Level Security (RLS) for all tenant-scoped tables.** The runtime sets `loop.workspace_id` per-connection; RLS policies enforce the filter at the Postgres layer. No application-side authorization bugs.

**Revisit trigger:** when we reach 100 enterprise customers AND at least 5 customers each have >100 GB of data. At that point, evaluate:
- Schema-per-tenant for better logical separation + custom indexes per tenant.
- Citus sharding by workspace_id.
- DB-per-tenant for the largest customers (Stripe, Shopify-class spend).

Until then, single Postgres + RLS is simpler and cheaper.

## Consequences

- ✅ Simpler operations (one DB, one backup, one migration strategy).
- ✅ Cheaper: shared resources, no per-tenant overhead.
- ⚠️ One bad query (e.g., full table scan) impacts all tenants. Mitigation: query analytics + slow-query logging; PagerDuty alert on query p99 > 1s.

---

# ADR-021 — Container runtime for tool sandbox: Kata + Firecracker

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

ADR-005 chose Firecracker microVMs for isolation. Running them directly on Linux requires custom orchestration. We integrate them into Kubernetes for portability across clouds.

## Decision

**Kata Containers as the Kubernetes runtime class.** Kata wraps Firecracker (or gVisor, qemu) as a Kubernetes runtime. Pods launched with `runtimeClassName: kata` land in a microVM instead of a traditional container.

**Concrete stack:** Kata + containerd + Kubernetes. Each cloud's managed k8s (EKS, AKS, GKE, ACK) supports Kata via custom node pools (AMI, VM image, or node config).

**Fallback:** gVisor (runtimeClassName: gVisor) if Kata adoption lags or a cloud doesn't offer it. Slightly weaker isolation (shared kernel), but ~40% faster cold start.

## Consequences

- ✅ Firecracker isolation (hardware-level) is portable across clouds via Kata.
- ✅ Kubernetes-native (no custom orchestration).
- ⚠️ Kata nodes are slightly larger than regular nodes (need nested virtualization). Acceptable; we size per-cluster.

---

# ADR-022 — Idempotency: request_id gateway cache + webhook dedup

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

Retries must be idempotent. The runtime may crash mid-turn; NATS re-delivers the event; we must not double-charge or double-execute. Different paths need different dedup.

## Decision

**Gateway-side request_id cache (Redis, 10-min TTL):** every turn execution registers a `request_id` (UUID, generated by the caller or by the channel adapter). If the same request_id arrives a second time, the gateway returns the cached result instead of re-executing. This handles runtime pod crashes mid-turn.

**Webhook dedup (NATS subject + idempotency-key):** channel adapters insert events into NATS with an idempotency-key (e.g., provider timestamp + signature). NATS streams deduplicate on that key within a 24-hour window. This prevents the same webhook from creating duplicate conversations.

**Agent-level idempotency:** tool calls use `request_id` to deduplicate within a turn. LLM calls use the request_id window (no duplicate LLM calls for the same `request_id`).

## Consequences

- ✅ Billing is never double-charged for a retried turn.
- ✅ Tool state is idempotent (re-executing a tool call with the same args returns the same result or a cached result).
- ⚠️ Requires cleanup jobs (Redis TTL, NATS compaction). Acceptable; both are standard ops.

---

# ADR-023 — Eval determinism: cassette + temp=0 + 3-run averaging

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

Evals need to detect regressions reliably. LLM outputs are stochastic; repeated runs of the same prompt can differ. We need a determinism strategy for eval scorers (especially LLM judges).

## Decision

**Three-tier approach:**

1. **Cassette (VCR-style):** LLM responses are cached by `(model, prompt_hash, params_hash)`. Every eval run uses the same cached responses. If cache miss, fetch once and record.

2. **Temperature=0 for evaluator LLMs:** when an LLM judge runs, set `temperature=0` and `top_p=0`. Deterministic output from the LLM API.

3. **3-run averaging for LLM judges:** for critical metrics (e.g., "does the response answer the user's question?"), run the evaluator 3 times with the same prompt and average the score. Require 2/3 agreement for pass/fail.

**Exceptions:** latency, cost, and tool-call assertions are deterministic by nature; no averaging needed.

## Consequences

- ✅ Regression detection is reliable (false negatives rare).
- ✅ Evals are reproducible across machines + runs.
- ⚠️ Cache grows over time; needs periodic pruning. Acceptable; cassettes are small (JSON).
- ⚠️ 3x evaluator cost for LLM judges. Acceptable; evals are offline; time-to-decision matters more than wall-clock time.

---

# ADR-024 — Deprecation policy: 30-day flag for breaking changes

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

We will change APIs, schemas, and behavior. Customers need notice and a grace period.

## Decision

**For SDK breaking changes:** ship a feature flag (`loop.deprecated_behavior = false`) that enables the old behavior. For 30 days, both old and new behaviors run in parallel, and we log a deprecation warning. After 30 days, the flag is removed and the old behavior is deleted.

**For agent-facing API changes (runtime):** same 30-day window. If an agent relies on deprecated runtime behavior, the agent logs a warning but continues to work.

**For data model changes:** migrations are always backwards-compatible within a major version. Migrations that change the schema are tested to ensure old code still reads the new schema (e.g., new columns have defaults).

**Exceptions:** security fixes skip the grace period.

## Consequences

- ✅ Customers have time to migrate.
- ✅ We can iterate on APIs without being locked into early mistakes.
- ⚠️ We carry technical debt for 30 days. Acceptable; code cleanliness is secondary to customer stability.

---

# ADR-025 — Telemetry data retention + export rights

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

Observability data (traces, metrics) is valuable for debugging but costly to store. Customers also want to export their data to their own backends (Datadog, Honeycomb, etc.).

## Decision

**Default retention:** 90 days hot (ClickHouse), then S3 cold archive indefinitely. ClickHouse itself TTL'd at 90 days; archive is customer's responsibility (they pay S3).

**Export rights:** every customer can configure one or more OTLP destinations (Datadog, Honeycomb, New Relic, Grafana Cloud, or custom endpoint). Traces flow to both ClickHouse (our dashboard) and the customer's destination in parallel.

**Per-workspace export config:** `export_targets: [{ type: "otlp", endpoint: "https://otel.honeycomb.io/...", authorization: "Bearer token" }]`. Credentials stored in Vault.

**Compliance:** a customer leaving Loop can request a full trace export within 30 days of churn. Export is delivered as S3 tarball (traces in OTEL JSON format).

## Consequences

- ✅ Customers own their data; can leave without losing observability history.
- ✅ Cost is transparent (they know traces are 90d hot then archived).
- ⚠️ Parallel export adds latency (we batch-export to OTLP destinations; ≤ 5s lag). Acceptable; observability is best-effort.

---

# ADR-026 — Agent code isolation: per-workspace runtime processes

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

Customer-written agents run in the Loop runtime. A bug in one agent should not crash others. Two models: in-process (fast, risky) vs per-workspace process isolation (safer, slower).

## Decision

**Per-workspace runtime processes for production.** Each workspace's agents run in dedicated Python process(es) within their own k8s pod (via multi-process StatefulSet). A workspace pod crash does not cascade to other workspaces.

**In-process option for dev/self-host:** when running locally or in small self-hosted deployments, a single runtime process can host multiple workspaces. This is faster but less safe. Enable via `runtime.isolation_mode: in_process` (default: per_workspace).

**Revisit trigger:** if per-workspace overhead exceeds 10% of total compute spend, evaluate container-level isolation (Kata) as an alternative.

## Consequences

- ✅ Workspace-level isolation prevents one bad agent from affecting others.
- ✅ Memory leaks in one workspace don't accumulate cluster-wide.
- ⚠️ More pods = more infra overhead (~15% per-workspace). Acceptable cost for multi-tenant isolation.

---

# ADR-027 — Public eval registry licensing: CC-BY for community suites

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

We host a public registry of eval suites (evals.loop.example). Community members will contribute. We need a license.

## Decision

**Community suites are CC-BY (Creative Commons Attribution).** Anyone can use, fork, modify; attribution required. Suites are published in a public GitHub repo (loop-ai/evals-registry) with CC-BY LICENSE file.

**Proprietary suites (e.g., from customers):** customers can host in a private repo or in our private registry (Enterprise only). No public licensing required.

**Liability:** evals are provided "as-is"; we disclaim warranty. Community contributors retain copyright; we have a right to host and redistribute under CC-BY.

## Consequences

- ✅ Open community source, low friction to contribute.
- ✅ Evals ecosystem grows faster (each company publishes their own).
- ⚠️ Attribution requirement may discourage some contributors. Acceptable; CC-BY is the industry standard (Hugging Face Hub uses it).

---

# ADR-028 — Pricing meter precision: per-second, per-token, exact

**Status:** Accepted  •  **Date:** 2026-04-29

## Context

ADR-012 defines three meters. The question is precision: do we round, sample, or meter exactly?

## Decision

**Per-second agent-seconds:** measured in milliseconds, billed per second (round up; 50 ms = 1 second). This simplifies billing and is industry-standard (AWS Lambda, Cloud Run).

**Per-token LLM tokens:** counted exactly by the LLM provider's tokenizer and our gateway. No rounding. If a call uses 1,234 tokens, we bill for 1,234.

**No sampling or statistical estimation.** Every turn records exact usage; nightly rollup is deterministic.

**Real-time usage display:** dashboard shows accruing costs live (with <5s lag) so customers can see spend before hitting budget caps.

## Consequences

- ✅ Fully transparent. Customers can audit every line item.
- ✅ No rounding errors benefiting/harming us over time.
- ⚠️ Slightly more compute for meters (but negligible at our scale). Acceptable.

---

# Cross-ADR references

- **ADR-007 (control/data split)** + **ADR-013 (multi-region):** control plane is active-passive per-region; data plane replicates via application-level consistency (RLS, workspace pinning).
- **ADR-016 (cloud-agnostic)** + **ADR-020 (tenant isolation):** cloud-agnostic interfaces (ObjectStore, KMS, etc.) enforce per-workspace isolation at the abstraction layer; Postgres RLS is the safety net.
- **ADR-003 (MCP)** + **ADR-021 (tool sandbox):** MCP servers run in Kata+Firecracker isolation; in-process MCP servers (trusted) skip the sandbox.
- **ADR-010 (observability)** + **ADR-025 (telemetry):** OTel → ClickHouse (90d hot) + customer OTLP export.
- **ADR-015 (eval-gated)** + **ADR-023 (determinism):** deploys require eval regression checks; eval scorers must be deterministic via cassette + temp=0.
- **ADR-012 (pricing)** + **ADR-028 (precision):** three meters (subscription, agent-seconds, tokens) are measured exactly and displayed in real-time.

---

## Open ADRs (deferred to later)

- **ADR-029 (Reserved):** Workspace-scoped feature flags (circuit breaker, canary % for new agents).
- **ADR-030 (Reserved):** Multi-tenant billing: chargeback per department, cost center, project.
- **ADR-031 (Reserved):** BYOK (bring-your-own-keys) for enterprise data encryption.
- **ADR-032 (Reserved):** Federated end-user identity (customer's IdP for agent users, not just builders).
