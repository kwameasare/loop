# Loop — System Architecture Document

**Status:** Draft v0.1
**Owners:** CTO + Founding Eng #1 (Runtime), Founding Eng #2 (Infra)
**Last reviewed:** 2026-04-29

This document is the canonical technical reference for the Loop platform. It uses a C4-style layered model: Context → Containers → Components → Code-level. Every team should be able to find the contract, ownership, and dependencies of their service here.

---

## 0. Glossary

| Term | Definition |
|------|------------|
| **Agent** | A long-lived, stateful Python class that handles inbound messages over one or more channels. The unit of deployment. Every agent has versioned code + config (model, budget, tools). |
| **Tool** | An MCP server (in-process or out-of-process) the agent can invoke. In-process tools run in the runtime; out-of-process tools run in Firecracker sandboxes. |
| **Channel** | An inbound/outbound transport (web, WhatsApp, Slack, voice, etc.). Each channel has adapter code + credentials. |
| **Turn** | One inbound message + the LLM/tool/response loop that produces an outbound response. Persisted with full trace in Postgres + ClickHouse. |
| **Conversation** | A thread of turns with a single user on a single agent. Long-lived; memory is accumulated across turns. |
| **Workspace** | Tenant boundary. Contains agents, channels, KBs, secrets, members. Pinned to a region + cloud. RLS enforced. |
| **Control plane** | Multi-tenant SaaS that handles auth, billing, deploy, observability UI. Deployed once; reachable globally. |
| **Data plane** | The runtime + state stores that actually execute agents. Self-hostable. Per-region. Agents run here. |
| **MCP** | Model Context Protocol (Anthropic). Loop's universal tool ABI. Every tool conforms; every runtime is an MCP client. |
| **Trace** | OpenTelemetry-style record of one turn — LLM calls, tool calls, retrievals, memory reads, latency, cost. Exported to ClickHouse. |
| **Memory** | Agent + user state. Four tiers: session (Redis, 24h), episodic (Qdrant, unlimited), user (Postgres, unlimited), bot (Postgres, unlimited). |
| **Eval** | Automated test suite that compares agent outputs (new version vs baseline) using scorers (LLM judge, regex, code function). Blocks deploy if regressed. |
| **Region** | Abstract deployment zone (`na-east`, `eu-west`, `apac-sg`, `cn-shanghai`). Maps to concrete cloud region; opaque to code. |
| **Tenant isolation** | Cross-customer data protection via Postgres RLS + per-workspace Qdrant collections + k8s network policies. |

---

## 1. Context (C4 Level 1)

```
                ┌──────────────┐                ┌──────────────┐
                │  End user    │                │  Operator    │
                │  (chat/voice)│                │  (HITL)      │
                └──────┬───────┘                └──────┬───────┘
                       │                                │
                       │                                │
                       ▼                                ▼
               ┌────────────────────────────────────────────┐
               │                                            │
               │             LOOP PLATFORM                  │
               │                                            │
               │   Agents · Channels · Tools · KB · Evals   │
               │                                            │
               └────────────┬───────────────────────────────┘
                            │
                            ▼
                ┌─────────────────────────┐
                │  Builder / Engineer     │
                │  (Python SDK · CLI ·    │
                │   Studio debugger)      │
                └─────────────────────────┘

External systems Loop talks to:
   • LLM providers     (OpenAI, Anthropic, Bedrock, Ollama, vLLM, ...)
   • Channel providers (Meta WhatsApp, Twilio, Slack, Teams, Telegram, LiveKit, ...)
   • MCP servers       (Loop Hub + customer-supplied)
   • Observability     (OTLP backends — Datadog, Honeycomb, customer)
   • Identity          (Auth0 cloud / Ory Kratos self-host)
   • Billing           (Stripe)
```

**Three actors:** end user (talks to the agent), operator (humans supervising via HITL inbox), builder (engineers writing agents).

---

## 2. Containers (C4 Level 2)

A "container" here means an independently deployable runtime: a process, a managed service, or a database. Loop is split into a **control plane** (multi-tenant SaaS) and a **data plane** (the agent runtime + storage), connected only by deployment manifests and observability streams.

### 2.1 Control plane containers

| Container | Tech | Responsibility |
|-----------|------|----------------|
| `cp-api` | Python (FastAPI), distroless OCI image `ghcr.io/loop-ai/cp-api` | Public REST API, auth, workspace mgmt, deploy ingest |
| `cp-billing` | Python | Stripe webhooks, usage rollup, invoice generation |
| `cp-eval-orchestrator` | Python | Schedules and shards eval runs across agent versions |
| `cp-mcp-registry` | Python + S3 | Catalog of installable MCP servers, versions, signatures |
| `cp-deploy-controller` | Python + k8s API | Promotes agent versions, blue/green, rollbacks |
| `studio-web` | Next.js (TS) | React UI for builders/operators |
| `cp-postgres` | Postgres 16 | Control-plane state (workspaces, users, deploys, eval runs) |
| `cp-redis` | Redis 7 | Sessions, rate limits, deploy locks |
| `cp-clickhouse` | ClickHouse | Trace + cost telemetry from all data planes |

S901 wires `cp-api` as `loop_control_plane.app:app`, a FastAPI ASGI process
served by Uvicorn on port 8080. The image entrypoint runs that app directly;
health, auth exchange, workspace, agent, and audit routes share the existing
control-plane service facades.

### 2.2 Data plane containers

| Container | Tech | Responsibility |
|-----------|------|----------------|
| `dp-runtime` | Python 3.12 (asyncio) | Executes agent reasoning loops |
| `dp-gateway` | Python | LLM gateway with caching, cost accounting, retries |
| `dp-webhook-ingester` | Python | Receives and validates incoming channel webhooks, buffers to NATS |
| `dp-channel-{web,wa,slack,voice,...}` | Python or Go | Channel adapters |
| `dp-tool-host` | Firecracker microVM pool | Out-of-process MCP server execution |
| `dp-kb-engine` | Python | Document ingestion, embedding, retrieval |
| `dp-eval-runner` | Python | Eval suite execution |
| `dp-feature-flag-service` | Python | Feature gates (circuit breaker, canary %, graceful degrades) |
| `dp-postgres` | Postgres 16 (Citus sharded) | Conversations, turns, memory, agent state; sharded by `workspace_id` |
| `dp-pgbouncer` | PgBouncer | Connection pool router; per-shard + per-workspace connection slots |
| `dp-redis` | Redis 7 | Session memory, semantic LLM cache, rate limits |
| `dp-qdrant` | Qdrant | Vector store for KB and episodic memory |
| `dp-nats` | NATS JetStream | Async events: tool dispatch, channel events, eval triggers |
| `dp-objstore` | S3-compatible object storage (any cloud or MinIO) | Code artifacts, recordings, doc originals |
| `dp-otel-collector` | OpenTelemetry Collector | Traces from runtime → control plane ClickHouse |

### 2.3 Container interaction (high level)

```
   builder pushes → cp-api → cp-deploy-controller → k8s manifest → dp-runtime (new pods)

   end user msg → channel adapter → NATS → dp-runtime → dp-gateway → LLM
                                                     ↘ dp-tool-host (MCP)
                                                     ↘ dp-postgres / dp-redis
                                                     ↘ dp-qdrant (KB / episodic)
                                              → response → channel adapter → end user

   trace events → dp-otel-collector → cp-clickhouse → studio-web
```

---

## 3. Components (C4 Level 3) — `dp-runtime`

This is the heart of Loop. Detail every other service in the same level of fidelity in their own component sections (TODO: split into per-service docs once the runtime is firm).

### 3.1 Process model

`dp-runtime` runs as a stateless Python process inside a Kubernetes pod. Many pods per workspace (autoscaled). Each pod can serve any agent's traffic — no per-agent pinning. Affinity rules pin a conversation_id to a pod for the duration of a turn (sticky on `(workspace, conversation_id)` via NATS subject hashing) but state is reloaded on every turn from Postgres + Redis, so loss of a pod mid-turn is recoverable (retry from last persisted memory diff).

Cold starts: the runtime image carries Python deps + agent SDK pre-imported. Agent code is loaded lazily per workspace and cached in-process. A "warm pool" maintains N pods per region with the latest agent image; new agent code triggers a rolling update, not a cold-start storm.

### 3.2 Components

```
┌─────────────────────────── dp-runtime pod ────────────────────────────┐
│                                                                       │
│  ┌─────────────────────┐   ┌────────────────────┐                     │
│  │  AgentEvent ingress │ → │  TurnExecutor      │                     │
│  │  (NATS sub + HTTP)  │   │  (per-turn task)   │                     │
│  └─────────────────────┘   └─┬──────────────────┘                     │
│                              │                                        │
│        ┌─────────────────────┼─────────────────────────────────┐      │
│        ▼                     ▼                                 ▼      │
│  ┌──────────────┐     ┌──────────────────┐         ┌──────────────┐   │
│  │ MemoryLoader │     │ PromptBuilder    │         │ ToolDispatcher│  │
│  │  (Postgres+  │     │ (system+memory+  │         │ (MCP client) │   │
│  │   Redis+     │     │  tools+history)  │         │              │   │
│  │   Qdrant)    │     └────────┬─────────┘         └───────┬──────┘   │
│  └──────────────┘              │                           │          │
│                                ▼                           │          │
│                        ┌────────────────┐                  │          │
│                        │ LLMGatewayCli  │ ◄────────────────┤          │
│                        │ (HTTP to       │                  │          │
│                        │  dp-gateway)   │                  │          │
│                        └───────┬────────┘                  │          │
│                                │                           │          │
│                                ▼                           ▼          │
│                        ┌─────────────────────────────────────┐        │
│                        │   ResponseStreamer + TraceWriter    │        │
│                        │   (SSE/WS out + OTLP trace export)  │        │
│                        └─────────────────────────────────────┘        │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

### 3.3 Key types (Python, abridged)

```python
class AgentEvent(BaseModel):
    workspace_id: UUID
    conversation_id: UUID
    user_id: str
    channel: ChannelType
    content: list[ContentPart]
    metadata: dict[str, Any]
    received_at: datetime

class TurnExecutor:
    async def execute(self, evt: AgentEvent) -> AsyncIterator[TurnEvent]:
        agent = await self.load_agent(evt.workspace_id)
        memory = await MemoryLoader.load(evt)
        prompt = PromptBuilder.build(agent, memory, evt)
        async for chunk in self.gateway.stream(prompt):
            if chunk.is_tool_call:
                result = await self.tools.dispatch(chunk.tool_call)
                yield TurnEvent.tool_call(chunk.tool_call, result)
                # feed result back into prompt for next iteration
            elif chunk.is_text:
                yield TurnEvent.token(chunk.text)
            if self.over_budget() or self.over_iterations():
                yield TurnEvent.degrade()  # graceful fallback
                break
        await MemoryLoader.persist_diff(evt, memory)
        await self.trace.flush()
```

### 3.4 Reasoning loop invariants

1. **Budget-bounded.** Every turn has `max_iterations`, `max_cost_usd`, `max_runtime_seconds`, `max_tool_calls_per_turn`. Hitting any cap triggers graceful degrade, never a hard drop.
2. **Idempotent.** A turn can be retried if the runtime pod dies before persisting memory; the LLM gateway has a request_id-keyed cache window so the second attempt doesn't re-bill.
3. **Streaming-first.** Tokens stream out as the LLM emits them. Tool calls trigger inline events so the channel can show "calling Stripe…" before the full response.
4. **Observable.** Every component emits OTel spans with `workspace_id`, `agent_id`, `conversation_id`, `turn_id`, `tool_id`, `provider`, `model`, `cost_usd`, `latency_ms`.

---

## 4. Sequence diagrams

### 4.1 Web chat — happy path

```
End user        Web widget       Channel-Web      NATS         Runtime         Gateway        OpenAI
   │                │                 │             │              │              │              │
   │ "what's my    │                  │             │              │              │              │
   │  order?"      │                  │             │              │              │              │
   ├───────────────►                  │             │              │              │              │
   │                │ POST /messages  │             │              │              │              │
   │                ├────────────────►│             │              │              │              │
   │                │                 │ pub event   │              │              │              │
   │                │                 ├────────────►│              │              │              │
   │                │                 │             │ deliver      │              │              │
   │                │                 │             ├─────────────►│              │              │
   │                │                 │             │              │ load memory  │              │
   │                │                 │             │              │ build prompt │              │
   │                │                 │             │              │ stream LLM   │              │
   │                │                 │             │              ├─────────────►│              │
   │                │                 │             │              │              │ POST /v1/... │
   │                │                 │             │              │              ├─────────────►│
   │                │                 │             │              │              │ stream tokens│
   │                │                 │             │              │              ◄──────────────┤
   │                │                 │             │              │ tool_call:   │              │
   │                │                 │             │              │ lookup_order │              │
   │                │                 │             │              │ → MCP        │              │
   │                │                 │             │              │              │              │
   │                │                 │             │              │ resume LLM   │              │
   │                │                 │             │              ├─────────────►│              │
   │                │                 │             │              │              ├─────────────►│
   │                │                 │             │              │ tokens       │              │
   │                │                 │             │              ◄──────────────┤              │
   │                │                 │             │ stream out   │              │              │
   │                │                 ◄─────────────┤              │              │              │
   │                ◄─SSE tokens──────┤              │              │              │              │
   ◄─render─────────┤                 │              │              │              │              │
   │                │ persist memory  │              │              │              │              │
   │                │ flush trace     │              │              │              │              │
```

### 4.2 Voice — ultra-low-latency path

```
Caller          LiveKit/SIP    VAD(Silero)   Deepgram(STT)  Runtime    Gateway+Anthropic    Cartesia(TTS)
   │                │              │              │              │              │              │
   │ phone call     │              │              │              │              │              │
   ├───────────────►│              │              │              │              │              │
   │                │ audio frames │              │              │              │              │
   │                ├─────────────►│              │              │              │              │
   │                │              │ endpoint     │              │              │              │
   │                │              ├──audio──────►│              │              │              │
   │                │              │              │ partial txt  │              │              │
   │                │              │              ├─────────────►│              │              │
   │                │              │              │              │ stream LLM   │              │
   │                │              │              │              ├─────────────►│              │
   │                │              │              │              │ tokens       │              │
   │                │              │              │              ◄──────────────┤              │
   │                │              │              │              │ stream tts   │              │
   │                │              │              │              ├──────────────────────────────►
   │                │              │              │              │              │ audio chunks │
   │                ◄─audio────────┴──────────────┴──────────────┴──────────────┴──────────────┤
   ◄─speech─────────┤              │              │              │              │              │

Latency budget p50 ≤ 700 ms total:
   VAD endpoint:  50 ms
   STT 1st token: 150 ms
   LLM 1st token: 250 ms (with prompt caching)
   TTS 1st audio: 150 ms
   Network:       100 ms
```

<!-- S908 -->
Deepgram STT and ElevenLabs TTS adapters open provider websocket
connections with the `websockets` runtime dependency by default, sending
provider auth headers on the real wire path. The adapter-level `open_ws`
seam remains for warm pooling, cassette replay, and failure injection.

### 4.3 Eval-gated deploy

```
Builder        CLI            cp-api        cp-eval         dp-runtime     cp-deploy-ctrl
   │            │                │             │                │                │
   │ loop deploy│                │             │                │                │
   ├───────────►│ POST /agents/X/versions     │                │                │
   │            ├───────────────►│             │                │                │
   │            │                │ create v42  │                │                │
   │            │                │ status=eval │                │                │
   │            │                │             │ run suite vs   │                │
   │            │                ├────────────►│ v41 (baseline) │                │
   │            │                │             │ + v42 (new)    │                │
   │            │                │             │ → score diff   │                │
   │            │                │             ◄────────────────┤                │
   │            │                │ status=passed                │                │
   │            │                ├──────────────────────────────► promote v42    │
   │            │                │             │                │ → blue/green   │
   │            │                │             │                ├───────────────►│
   │            │                │             │                ◄─completed─────┤
   │            ◄────deploy ok───┤             │                │                │
   ◄─prompt─────┤                │             │                │                │
```

### 4.4 Webhook ingestion (channel adapters)

```
Channel provider        dp-webhook-ingester    NATS              dp-runtime
   (WhatsApp,          (signature verify,      (inbound event   (TurnExecutor
    Slack, etc.)        dedup, buffer)         stream)           consumed)
   │                         │                   │                  │
   │ POST /webhook/{channel} │                   │                  │
   ├────────────────────────►│                   │                  │
   │                         │ validate sig+ts   │                  │
   │                         │ check idempotency │                  │
   │ 200 OK (immediate)      │                   │                  │
   ◄─────────────────────────┤                   │                  │
   │                         │ pub AgentEvent    │                  │
   │                         ├──────────────────►│                  │
   │                         │ to inbound stream │ deliver (NATS    │
   │                         │                   │ sticky routing)  │
   │                         │                   ├─────────────────►│
   │                         │                   │                  │ execute turn
```

### 4.5 Retry & idempotency (runtime pod death mid-turn)

```
End user        Channel-Web   NATS         Runtime        Gateway      Database
   │                │           │            │              │            │
   │ message        │           │            │              │            │
   ├───────────────►│           │            │              │            │
   │                │ pub ev    │            │              │            │
   │                ├──────────►│            │              │            │
   │                │           │ deliver ev │              │            │
   │                │           ├───────────►│              │            │
   │                │           │            │ load memory  │            │
   │                │           │            ├─────────────►│            │
   │                │           │            │ req_id cache │
   │                │           │            │ → stream LLM │            │
   │                │           │            ├─────────────►│ (streaming)│
   │                │           │            │              ◄────tokens──┤
   │ **POD CRASH**  │           │            │              │            │
   │                │           │            ✗              │            │
   │                │           │ redeliver  │              │            │
   │                │           │ (after 30s)│              │            │
   │                │           ├───────────►│ (new pod)    │            │
   │                │           │            │ reload memory│            │
   │                │           │            │ req_id hit   │            │
   │                │           │            │ cache → 200  │            │
   │                │           │            │ resume state │            │
   │                │           │ stream out │              │            │
   │                ◄────────────┤            │              │            │
   ◄─render─────────┤            │            │              │            │
```

---

## 5. State stores

### 5.1 Postgres (data plane)

- **Schema:** see `data/SCHEMA.md` for full DDL.
- **Sharding:** Citus by `workspace_id`. Single-tenant pgsql for self-hosted < 100 RPS workloads.
- **Backups:** WAL-G to S3-compatible object storage every 5 min. PITR window 14 days.
- **Connection pooling:** PgBouncer in front of the managed Postgres endpoint (RDS, Azure DB, Cloud SQL, ApsaraDB, or self-hosted CloudNativePG).

### 5.2 Redis

- **Use cases:** session memory, semantic LLM cache, rate-limit counters, deploy locks.
- **Eviction:** allkeys-lru for the cache database; noeviction for session memory.
- **Persistence:** AOF every 1s for session DB, RDB-only for cache DB.
- **Cluster:** managed Redis cluster (ElastiCache / Azure Cache / Memorystore / Tair) or self-hosted via Redis Operator on k8s; single node OK for small self-host.

### 5.3 Qdrant

- **Collections:**
  - `kb_<workspace_id>_<kb_id>` — KB chunks. Points carry `doc_id`, `chunk_id`, `position`, `source_uri`, `metadata`.
  - `episodic_<workspace_id>` — long-running episodic memory. Filtered by `user_id`, `agent_id`.
- **Vector dim:** default 3072 (OpenAI text-embedding-3-large), configurable per workspace.
- **Quantization:** binary on collections > 5M points.
- **Replicas:** 2 in Cloud; 1 OK for self-host.
- <!-- S213 --> **KB integration path:** `loop_kb_engine.QdrantRestVectorStore`
  uses Qdrant REST with `kb_<workspace_id_short>_<kb_id_short>` collection
  names; S213 covers PDF ingest → Qdrant retrieval → Postgres metadata citation.

### 5.4 ClickHouse

- **Tables:** see `data/SCHEMA.md` (`otel_traces`, `costs_daily`, `eval_results`).
- **Retention:** 90 days hot, then S3-compatible object-storage archive.
- **Partition:** by `(workspace_id, toDate(ts))` for fast workspace-scoped scans.
- **Hosting:** ClickHouse statefulset on k8s in every cloud (managed offerings exist on each — Altinity on AWS, ClickHouse Cloud, Aiven, etc. — but we self-host on k8s for portability).

### 5.5 NATS JetStream

- **Streams:**
  - `EVENTS.inbound.{workspace}` — channel events.
  - `TOOLS.dispatch.{workspace}` — tool execution requests.
  - `TRACE.{workspace}` — trace events to OTel collector.
  - `EVAL.{workspace}` — eval triggers.
- **Replication:** R3 in Cloud, single-server OK for self-host.

---

## 6. Deployment topology

### 6.1 Cloud (multi-tenant)

Loop is **cloud-agnostic** — every region runs on whatever cloud (AWS, Azure, GCP, Alibaba Cloud, OVHcloud, …) or on customer-supplied k8s. See `architecture/CLOUD_PORTABILITY.md` for the per-cloud mapping table and the internal abstractions that keep us honest.

- **Regions at launch:** abstract names `na-east` and `eu-west`. `apac-sg` and `cn-shanghai` (mainland China — Alibaba) Phase 2. Concrete cloud per region is a deployment decision, not a code one.
- **Per region:** dedicated managed k8s cluster, managed Postgres (RDS / Azure DB / Cloud SQL / ApsaraDB / CloudNativePG), managed Redis, Qdrant statefulset, NATS cluster, ClickHouse statefulset, S3-compatible object storage.
- **Tenant isolation:**
  - Workspace-scoped Postgres rows + RLS policies.
  - Per-workspace Qdrant collections.
  - Per-workspace data keys via the `KMS` interface (Vault Transit by default; cloud-native KMS as alternate per workspace).
  - Per-workspace network policies in k8s.
- **Voice:** dedicated low-latency edge POPs co-located with LiveKit + Twilio. Cloudflare for global CDN/WAF/Spectrum (cloud-neutral).

### 6.2 Self-hosted (Helm)

- One Helm chart deploys the entire data plane. Optional control-plane lite (auth + workspace mgmt + deploy UI) deploys alongside or points at Loop Cloud.
- Defaults: single Postgres, Redis, Qdrant, NATS — all with PVC + RWO storage. Production self-host path adds replicas + multi-AZ.
- BYO LLM API keys; BYO Postgres/Redis/Qdrant if desired (Helm values can disable bundled charts).
- No phone-home telemetry. Anonymous opt-in usage stats only.

### 6.3 Hybrid

- Customer hosts data plane in their VPC.
- Loop Cloud control plane → outbound HTTPS to customer's data plane API (mTLS).
- Common pattern for regulated enterprises.

---

## 7. Cross-cutting concerns

### 7.1 Authentication & authorization

- **Builder auth:** OIDC via Auth0 (cloud) or Ory Kratos (self-host). MFA required.
- **API auth:** signed bearer tokens (PASETO v4) scoped to workspace + permission. Tokens are workspace-scoped, not global.
- **Service-to-service:** mTLS inside the data plane via SPIFFE IDs. Certificates rotated every 24h via SPIRE.
- **End-user auth on channel:** delegated to the channel (Slack OAuth, WhatsApp BSP token, web widget JWT).

**Authorization flow (builder API):**
```
SDK / CLI             cp-api                Auth0/Kratos         Postgres (cp)
  │                     │                        │                    │
  │ Bearer token        │                        │                    │
  ├────────────────────►│ verify PASETO sig      │                    │
  │                     │ extract workspace_id   │                    │
  │                     │ extract scopes         │                    │
  │                     ├───────────────────────►│ validate signature  │
  │                     ◄───────ok──────────────┤                    │
  │                     │ check scope + role     │                    │
  │                     ├─────────────────────────────────────────────►
  │                     │ SELECT * FROM roles WHERE (workspace, user) │
  │                     ◄─────────────────────────────────────────────┤
  │                     │ allow / deny           │                    │
  │ 200 / 401           │                        │                    │
  ◄─────────────────────┤                        │                    │
```

### 7.2 Secrets

- **Storage:** **HashiCorp Vault by default** (works on every cloud and self-host); cloud-native KMS/secrets (AWS Secrets Manager, Azure Key Vault, GCP Secret Manager, Alicloud KMS) as an *optional alternate* per workspace. Engineering implementation goes through the `SecretsBackend` interface — the runtime never imports a cloud SDK directly.
- **Per-bot scoping:** secrets attached to a specific agent version, not to the workspace, so different agents can have different Stripe keys, etc. This is an explicit improvement over Botpress.
- **Rotation:** policy-driven; secrets older than 90 days emit a warning event.

### 7.3 Cost accounting

- **Three meters:** platform subscription (Stripe), agent-seconds (compute), LLM tokens (pass-through + 5% margin).
- **Recording:** every turn writes a `costs_turn` row; nightly job rolls up to `costs_daily`.
- **Budgets:** workspace, agent, conversation, day. Soft / hard / graceful-degrade rules.

### 7.4 Rate limiting

- **Per workspace:** API requests, deploy frequency, eval runs.
- **Per agent:** in-flight conversations, tool calls/turn.
- **Per IP:** anonymous public widget endpoints.
- Implementation: Redis sliding-window counters via the `cp-api` middleware.

### 7.5 Observability stack

- **Traces:** OpenTelemetry → OTel Collector → ClickHouse.
- **Logs:** structlog → stdout → Loki (or customer's stack via OTLP).
- **Metrics:** Prometheus scrapers; Grafana dashboards shipped.
- **Alerts:** PagerDuty integration; default alert pack ships with the platform.

---

## 8. Failure modes & mitigation

| Failure | Detection | Mitigation |
|---------|-----------|------------|
| Runtime pod crash mid-turn | k8s liveness | Re-deliver from NATS; idempotent gateway via request_id |
| LLM provider outage | Gateway error rate | Auto-fallback to secondary provider via model alias router |
| Postgres primary fails | Managed Postgres failover (or Patroni/CNPG) | <60s; turns retry from NATS |
| Qdrant unavailable | Health check | Agent gracefully answers "I don't have that info" instead of crashing |
| NATS partition | Cluster monitor | Channel adapters buffer events to local disk; flush on reconnect |
| Tool sandbox OOM | cgroup signal | Tool dispatcher returns timeout error to LLM, agent recovers |
| Cost cap hit mid-turn | Gateway pre-flight check | Graceful degrade: swap to cheaper model + truncate history |
| Workspace under DDoS | Rate limit + WAF | Per-IP throttle, optional Turnstile challenge for web widget |

---

## 9. Non-functional requirements & capacity planning

| Concern | Target | Notes |
|---------|--------|-------|
| Voice latency p50 | ≤ 700 ms (end-to-end) | Budget: VAD 50ms, STT 150ms, LLM 250ms, TTS 150ms, net 100ms |
| Chat latency p50 (first token) | ≤ 600 ms | Includes LLM prompt caching; RLS eval time < 10ms |
| Chat latency p99 | ≤ 2000 ms | Error budget 200ms for retry / fallback |
| API availability | 99.9% (Cloud Pro/Team), 99.95% (Enterprise) | Excl. LLM provider outages; own SLO is 99.95% |
| Trace ingestion lag | ≤ 5 s from event to dashboard | OTLP batch interval + ClickHouse write-through |
| Cold start | none at the agent level (warm pool) | N pre-warmed pods per region, replaced on code update |
| Deploy time | ≤ 60 s from `loop deploy` to live | Blue/green rollout; eval gate ≤ 90s not in SLA window |
| Eval suite of 100 cases | ≤ 90 s | Single-threaded on one runner; parallelizable |
| **Capacity per pod (per-workspace)** | 100 concurrent conversations | Sticky NATS routing; each conversation ≤ 5 MB session state |
| **Capacity per pod (multi-tenant)** | 500 concurrent conversations | Across all workspaces; per-workspace isolation via RLS + network policy |
| Max in-flight tool calls / turn | 20 (configurable) | Parallel dispatch; exceeding hard-loops agent with error |
| Max iterations / turn | 10 (configurable) | Budget: cost cap hit → graceful degrade |
| Per-conversation memory | unlimited (Postgres-backed); session 16 MB hard | Episodic memory indexed in Qdrant for retrieval |
| **Postgres throughput per pod** | ≤ 1000 tps (Citus-sharded) | Per-shard; total across cluster scales with shards |
| **Redis throughput** | ≤ 100K ops/s (cluster mode) | Session memory + LLM cache; cluster auto-scales |
| **Qdrant throughput** | ≤ 10K vector searches/s (single collection) | Binary quantization at 5M+ points |
| **NATS throughput** | ≤ 100K msgs/s (cluster R3) | Event streams; adequate for < 10k rps agents globally |

---

## 10. Version skew policy

**Control plane ↔ Data plane:**
- Control plane can be any released version; data plane must be within ±1 minor version (e.g., cp-2.1 ↔ dp-2.0, dp-2.2 OK; dp-1.9 NOT OK).
- Deploys via HTTPS only; uses versioned agent artifact manifests (includes schema version).
- Breaking schema changes: control plane deploys first, then data plane.

**SDK ↔ Runtime:**
- SDK uses same versioning as runtime. SDK major bumps block agent deploy to newer runtime versions.
- Pydantic public types in `api/` are versioned separately via OpenAPI `x-api-version`.

**Feature flags:**
- `dp-feature-flag-service` serves per-workspace flags fetched every 30s from cp-api.
- Ungraceful flag flips (a feature suddenly disabled) logged and alerted; circuit breaker activates for 5 min.

---

## 11. Back-pressure & load-shedding

When the runtime is overloaded:

1. **Per-workspace rate limit** (Redis sliding window) rejects requests with 429 *before* queuing to NATS.
2. **NATS backpressure:** if inbound stream lag > 10s, channel adapters buffer to local disk and flush on reconnect.
3. **Gateway overload:** if LLM provider fails or queues, gateway returns a synthetic `degrade` event; agent gracefully swaps to a cheaper model or returns a cached response.
4. **Memory budget:** if session memory exceeds 16 MB hard cap, oldest entries are evicted; logged as a warning.
5. **Tool sandbox overload:** if Firecracker pool is exhausted, tool calls queue with a 60s timeout; exceeding timeout returns error to agent.

---

## 12. Tenant onboarding/offboarding

**Onboarding (sync path in cp-api):**
1. User creates workspace via OIDC.
2. cp-api writes `workspaces` row + default RLS policy to control-plane Postgres.
3. Returns workspace_id + region to SDK.
4. SDK specifies region in Helm values or IaC; data-plane Postgres schema auto-creates per-tenant DDL via custom migrator (reads `workspace_id` from env).
5. Per-workspace Qdrant collection created on first KB upload.
6. Per-workspace data key generated in KMS (Vault or cloud).

**Offboarding (async multi-step):**
1. Admin clicks "delete workspace" → soft delete (set `deleted_at` timestamp).
2. Existing conversations continue for 30 days (grace window).
3. Day 30: background job calls `DELETE FROM *` where `workspace_id = ?` and `deleted_at < now() - 30 days`.
4. KMS key destruction via Vault / cloud KMS destroys all envelope keys, invalidating backups + encrypted blobs.
5. Audit logged with cryptographic chain.

---

## 13. Networking & certificates

**Egress allowlists:**
- `dp-tool-host` Firecracker VMs declare egress destinations in their MCP manifest; `dp-runtime` validates against the allowlist before dispatching.
- Default deny; explicit whitelist per tool. E.g., Stripe tool only allows `api.stripe.com:443`.
- Network policies in k8s enforce namespace boundaries (workspace ↔ workspace isolated).

**Private link per cloud:**
- Cloud: AWS PrivateLink / Azure Private Link / GCP Private Service Connect for data plane ↔ control plane.
- Self-host: mTLS over standard HTTPS with customer's reverse proxy.

**Certificate rotation:**
- SPIFFE IDs rotated every 24h via SPIRE; zero-downtime (old cert honored for 1h after rotation).
- TLS handshake certs (api.loop.example) rotated every 90 days; staged over 48h window.
- Per-workspace KMS data keys rotated every 90 days (background job; no downtime).

**DNS:**
- Regional abstract names (`api.na-east.loop.example`, `api.eu-west.loop.example`) resolve via Cloudflare; Cloudflare itself is multi-cloud.
- DNSSEC enabled; CAA records restrict cert issuance to approved CAs.
- TTL = 60s for resilience; traffic shaping via Cloudflare Workers if needed.

---

## 14. Open architectural questions (track as ADRs)

All major decisions through 2026-04-29 are now captured as Accepted ADRs (001–028). Remaining truly-open questions:

1. Cross-cloud DR replication target — formalize when first Enterprise customer requests it. Currently in `engineering/DR.md` §5.
2. Per-customer tenant DB sharding (one-DB-per-tenant) trigger threshold — currently single Postgres + RLS per ADR-020; revisit at 100 enterprise customers.
3. Multi-cloud single-pane-of-glass for the control plane — see `architecture/CLOUD_PORTABILITY.md` §11.
4. Public eval registry monetization model — registry ships under CC-BY (ADR-027) but commercial premium tier TBD post-M9.
5. End-user MFA step-up for high-stakes agent actions (money-moving, compliance) — design pending.

See `adrs/` for the running log.

---

## 15. Service ownership matrix

| Service | Primary owner (role) | Secondary |
|---------|----------------------|-----------|
| `dp-runtime` | Founding Eng #1 (Runtime) | Founding Eng #4 (Obs) |
| `dp-gateway` | Founding Eng #1 (Runtime) | Founding Eng #2 (Infra) |
| `dp-webhook-ingester` | Sr. Eng — Channel Integrations | Founding Eng #1 |
| `dp-channel-{web,wa,slack,...}` | Sr. Eng — Channel Integrations | DevRel |
| `dp-channel-voice` | Founding Eng #3 (Voice) | Founding Eng #1 |
| `dp-tool-host` | Founding Eng #2 (Infra) | Founding Eng #1 |
| `dp-kb-engine` | Founding Eng #1 (Runtime) | DevRel |
| `dp-eval-runner` | Founding Eng #4 (Obs/Eval) | Founding Eng #1 |
| `dp-feature-flag-service` | Founding Eng #2 (Infra) | Founding Eng #1 |
| `dp-pgbouncer` | Founding Eng #2 (Infra) | — |
| `cp-api`, `cp-deploy-ctrl` | Founding Eng #2 (Infra) | Founding Eng #5 (Studio) |
| `studio-web` | Founding Eng #5 (Studio) | PM |
| Postgres / Redis / Qdrant ops | Founding Eng #2 (Infra) | — |
| Networking / mTLS / certificates | Founding Eng #2 (Infra) | Security Eng |
| Security / SOC2 / threat model | Sec/Compliance Eng | CTO |
| Observability stack (OTLP / ClickHouse / dashboards) | Founding Eng #4 (Obs) | Founding Eng #2 |

---

## 12. References

- `architecture/CLOUD_PORTABILITY.md` — per-cloud mapping table + interface definitions
- `data/SCHEMA.md` — full data model
- `api/openapi.yaml` — REST API spec
- `adrs/*.md` — decision records (see ADR-016 for cloud-portability rationale)
- `engineering/HANDBOOK.md` — coding conventions, dev setup
- `ux/UX_DESIGN.md` — Studio screens & IA
- `engineering/SECURITY.md` — threat model, controls
- `engineering/TESTING.md` — testing pyramid + eval harness
- `tracker/` — sprint plan, epics, stories
