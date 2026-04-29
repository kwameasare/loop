# Botpress Deep Dive & Build-Ready Spec for a Next-Gen Agentic Competitor

**Prepared for:** Praise Asare
**Date:** 29 April 2026
**Working codename for the product:** **Loop** *(placeholder — the founder should swap)*
**Reading time:** ~45 minutes
**Companion files:** `botpress_competitor_spec.docx` (polished report), `botpress_competitor_pitch.pptx` (15-slide strategy deck)

---

## Table of Contents

1. Executive Summary
2. Why Now: The Agentic Inflection Point
3. Botpress Today — Product, Architecture, Stack
4. Botpress Pricing & Business Model
5. Channels, Integrations, and the "Hub"
6. Competitive Gaps & What Users Actually Complain About
7. Loop — Product Thesis & Positioning
8. Loop — High-Level Architecture
9. Loop — Module-by-Module Build Spec
10. Data Model & Core Schemas
11. API Surface (Public and Internal)
12. Tech Stack Choices & Rationale
13. Deployment Topology & Infrastructure
14. Pricing Model & Unit Economics
15. MVP Scope (First 6 Months)
16. 12-Month Roadmap
17. Repository Layout
18. Hiring Plan — First 8 Engineers
19. Go-to-Market & Distribution
20. Risks, Counter-Arguments, and Open Questions
21. Appendix A — Sources

---

## 1. Executive Summary

Botpress is a Montreal-based AI agent platform that pivoted in 2023 from an open-source flow-builder (v12) to a cloud-native, proprietary "agent infrastructure" play. They raised a $25M Series B in June 2025 at a $120M post-money valuation on roughly $7.8M ARR, employ ~120 people, and have logo customers including Kia, Electronic Arts, Shell, American Express, and UPS. Under the hood they run a TypeScript/Node monorepo on AWS, with a proprietary inference engine called **LMSz**, a four-tier memory model, vector storage on Postgres + pgvector, and ~190 pre-built integrations on a "Hub" marketplace.

They are not winning because they are technically dominant — they are winning because they are early, polished, and well-funded. **Their architecture is full of seams a competitor can exploit:**

- **Flow-first paradigm** dressed up as agentic — the Autonomous Node still lives inside a flow graph.
- **No native voice** — voice requires bolting on Twilio + Deepgram + ElevenLabs.
- **No MCP-native runtime** — every tool is custom boilerplate.
- **Opaque pricing** — token costs are passed through but not surfaced predictively, so customers get renewal shocks.
- **Cloud-only proprietary core** — v12 OSS is archived with no migration path; enterprises with on-prem requirements have nowhere to go.
- **TypeScript-only SDK** — locks out the 80% of ML teams that work in Python.
- **Observability theatre** — dashboards exist but lack token-level traces, retrieval debugging, or eval harnesses.
- **No multi-agent primitives** — coordination happens inside LMSz as black-box magic.

**Loop's thesis:** ship a code-first, eval-driven, MCP-native, multi-agent, voice + chat-unified runtime with a fully open-source core (Apache 2.0) and a transparent cloud control plane. Be the "Stripe of agents" — the boring, observable, fairly-priced infrastructure layer that real engineering teams actually want to put into production.

The MVP is achievable in 6 months with 5 engineers. The go-to-market is bottom-up developer adoption (open-source, npx/pip install, MCP marketplace), with a paid Cloud tier for teams that don't want to self-host. Price transparently per "agent-second" of compute plus pass-through LLM tokens at 5% margin. Make the bill predictable.

---

## 2. Why Now: The Agentic Inflection Point

Three shifts make 2026 the right moment to launch:

**The flow-graph paradigm is dying.** From 2017–2023, chatbots were finite-state machines: intents → entities → flow nodes → responses. LLMs collapse most of that scaffolding into a single tool-calling loop. Botpress, Voiceflow, Cognigy, and the rest are mid-pivot from "flow builder with AI" to "agent runtime" — but their data models, UIs, and marketing still smell like 2021. A platform built agent-first from day one wins on architectural coherence.

**MCP (Model Context Protocol) is becoming the USB-C of agents.** Anthropic shipped MCP in late 2024, and through 2025 the ecosystem exploded — hundreds of community MCP servers, official Slack/Notion/GitHub/Linear/Postgres/Stripe servers, and adoption by Cursor, Windsurf, Claude Desktop, and OpenAI's Agent SDK. Botpress added basic MCP support in 2025 but it's grafted on. A competitor that makes MCP the *native tool model* — every tool is an MCP server, every integration ships with one — gets the entire MCP ecosystem for free.

**Voice is now table-stakes.** Vapi raised a Series A and crossed eight figures of ARR by selling sub-500ms voice agents. Retell, Bland, Synthflow, and ElevenLabs Agents all launched competing products. Botpress has *no native voice*. Any new platform that doesn't ship voice + chat unified is shipping an artifact.

The window: probably 18–24 months before incumbents (OpenAI Agents SDK, Anthropic Claude Agent SDK, LangChain Cloud, Vercel AI Cloud, Sierra) close it.

---

## 3. Botpress Today — Product, Architecture, Stack

### 3.1 What Botpress is

A SaaS platform for building, deploying, and operating AI agents that talk to users over chat channels. Customers get:

- **Studio** — visual flow builder with autonomous nodes, integration cards, knowledge bases, tables.
- **Agent Development Kit (ADK)** — TypeScript framework for building agents, integrations, and actions in code.
- **`bp` CLI** — auth, scaffolding, deploy, watch.
- **Hub** — marketplace of ~190 pre-built integrations.
- **Cloud runtime** — managed multi-tenant runtime on AWS that hosts the agent and its state.

### 3.1a The "Four Pillars" abstraction

Botpress's documentation organizes the platform around four primitives: **Bots** (the conversational applications), **Integrations** (connections to external platforms — Slack, Telegram, CRMs), **Plugins** (modular reusable functionality injected into a bot's workflow), and **Interfaces** (abstract behavioral contracts that standardize how components communicate). This is a cleaner abstraction than ours-by-default and worth borrowing the *vocabulary* if not the implementation. In Loop terms: Agents, Channels, Tools (MCP servers), and Protocols.

### 3.1b Codebase composition

Botpress's public OSS repo is **99.6% TypeScript** by line count, with Node.js as the runtime and pnpm as the package manager. The publicly maintained components — the `@botpress/cli`, `@botpress/client` (type-safe API client), `@botpress/sdk` (integration authoring kit), and the `integrations/` directory — are all licensed **MIT** (permissive). This is distinct from the legacy v12 self-hosted product, which was AGPL-licensed and is now archived. Bottom line: the SDK and CLI are open, but the *runtime* (LMSz, Studio, control plane) is closed.

### 3.2 Core runtime: LMSz

LMSz is Botpress's proprietary inference engine. It sits between the chat input and the LLM and orchestrates:

- Prompt construction (system prompt + memory + tool catalog + user message).
- Tool selection — emits structured tool calls (in parallel, not sequential like vanilla OpenAI function calling).
- Sandboxed JavaScript execution — the LLM can write code that LMSz executes inside a 60-second-timeout V8 sandbox.
- Memory updates — reads and writes to user/session/temp/bot stores.
- Response generation — streams (or batches) the final agent response back to the channel.

Botpress claims LMSz is ~5× cheaper than naive sequential function calling for multi-tool tasks because it batches tool decisions in fewer round trips. Plausible, but unverifiable — the engine is closed.

### 3.3 Autonomous Node

The Studio-facing abstraction over LMSz. A node on the canvas with:
- A natural-language instruction.
- A list of tools the LLM is allowed to call.
- Read/write permissions on workflow variables.
- Optional vision capability.
- Configurable LLM (GPT-4, Claude, Cohere, Ollama, vLLM, etc.).

Crucially, an Autonomous Node still lives **inside a flow graph**. Inputs come from a previous node, outputs route to the next. This is "agent inside a flow," not "agent-first."

### 3.4 Memory model

| Tier | Lifetime | Scope | Notes |
|------|----------|-------|-------|
| **User** | Persistent | Per end-user | Lifetime of the user record |
| **Session** | TTL | Per conversation | Configurable expiry |
| **Temp** | Flow-only | Per flow instance | Cleared on flow exit |
| **Bot** | Persistent | Shared across users | Global state |

Hard cap: **128 KB per conversation** state. Forces agent designers to actively prune older state — a real production headache.

### 3.5 Knowledge base / RAG

- Sources: PDF, DOCX, web crawl, Notion, Slack threads, plain text. Google Drive and Zendesk Help Center are integration-mediated.
- Embeddings: OpenAI's `text-embedding-3-small` by default (with optional model swap on enterprise plans).
- Vector store: **Postgres with `pgvector`** — not Pinecone, Weaviate, or a dedicated DB. Workspace-scoped, not bot-scoped (a security/multi-tenancy concern at scale).
- Chunking: undocumented; appears to be ~500-token semantic boundary with ~50-token overlap.
- Retrieval: top-k + similarity threshold, exposed as a "knowledge base" tool the agent can call.
- **Web crawling is outsourced to Firecrawl** (third-party partnership) rather than a homegrown crawler — an interesting outsourcing choice that shows the team prioritizes shipping over owning every component.
- **Vision Indexing** — Botpress can extract data from charts, technical diagrams, and visual structures inside PDFs, not just text. This is a real feature gap a competitor must match for technical-support and enterprise document use cases.
- Industry stat (cited in their materials): grounding answers in uploaded KB documents reduces conversational errors by up to **90%** vs ungrounded LLM responses, and businesses with effective KB systems report **92%** customer-satisfaction vs 78% without. These are useful pitch numbers for any RAG-centric platform.

### 3.6 Hooks & lifecycle

Three injection points:
1. **Message hooks** — `onBeforeMessage`, `onAfterMessage`.
2. **LLMz iteration hooks** — `onBeforeTool`, `onAfterTool`, `onIterationEnd`.
3. **Conversation hooks** — `onBeforeExecution`, `onExit`.

Useful for logging, redaction, custom auth — but Botpress-specific and non-portable.

### 3.7 Tech stack snapshot

| Layer | Choice |
|-------|--------|
| Language (backend) | TypeScript / Node.js |
| Language (frontend Studio) | React |
| Monorepo tool | pnpm workspaces |
| Database (structured) | PostgreSQL (≥9.5), SQLite for dev |
| Vector store | Postgres + pgvector |
| LLM gateway | Multi-provider (OpenAI, Anthropic, Cohere, Ollama, vLLM, etc.) |
| Code sandbox | V8 isolates inside the runtime |
| Hosting | AWS (managed); Elestio offered for "BYO AWS" |
| Auth | OAuth2 + workspace-scoped credentials |
| CLI | `@botpress/cli` (npm) |
| SDK | `@botpress/sdk` (TypeScript only) |

### 3.8 v12 OSS — quietly archived

Botpress v12 was AGPL-licensed, self-hostable, intent-based NLU + flow engine. Now archived on GitHub with no maintenance, no migration path to Cloud, broken deployment tutorials, and no roadmap. Customers who relied on self-hosting either rebuilt on Cloud, migrated to Rasa / LangGraph / Dify / CrewAI, or stayed frozen on v12.

This is **the single most important fact** for a competitor: there is a frustrated diaspora of ex-Botpress OSS users with no good home. Win them.

---

## 4. Botpress Pricing & Business Model

### 4.1 Plan tiers (April 2026)

| Tier | Monthly | Included | Seats | Best for |
|------|---------|----------|-------|----------|
| Pay-as-you-go | $0 | $5 AI credit, 500 messages | 1 | Eval / hobby |
| Plus | $89 | Higher caps, $100 AI cap | 2–3 | Solo builders |
| Team | $495 | Higher caps, $500 AI cap | 5+ | SMB / mid-market |
| Managed | $1,495 | Concierge build services | Unlimited | Hands-off |
| Enterprise | Custom (~$2K+ minimum, multi-year) | SSO, SLA, custom limits | Custom | F500 |

Annual prepay shaves up to 33% off the headline price.

### 4.2 The two-line bill

Customers see **subscription + AI credit usage**. AI credits cover LLM tokens for KB Q&A, "Personality Agent" rewrites, "Translator Agent," summarization, AI Task cards, AI transitions, code-assist, and capture/table searchability. Botpress claims zero markup on tokens.

**Hard monthly caps** turn the bot off when hit:
- Pay-as-you-go / Plus: $100/mo
- Team: $500/mo
- Enterprise: negotiated

When successful campaigns push traffic up, the bot goes dark mid-month. Top complaint on G2, Capterra, and the Botpress Discord.

### 4.3 Channels are billed externally

WhatsApp ($0.008–$0.063/conversation via Meta), SMS via Twilio, voice via Twilio Voice — all billed direct to the customer's Meta/Twilio account. Botpress shows zero of this on their invoice. Customers running campaigns get blindsided when the *external* bill arrives.

### 4.3a Infrastructure quotas and overage rates (the punitive table)

This is where Botpress monetizes hardest beyond LLM tokens. Every quota has a hard rate-card overage:

| Resource | PAYG | Plus | Team | Overage rate |
|----------|------|------|------|--------------|
| Incoming messages / events | 500 / mo | 5,000 / mo | 50,000 / mo | **$20 per extra 5,000** |
| Database table rows | 1,000 | 100,000 | 100,000 | **$25 per extra 100,000** |
| Simultaneously active bots | 1 | 2 | 3 | **$10 per extra bot** |
| Vector DB storage (RAG) | 100 MB | 1 GB | 2 GB | **$20 per extra 1 GB** |
| File storage (images/media) | 100 MB | 10 GB | 10 GB | **$10 per extra 10 GB** |
| Workspace collaborator seats | 1 | 2 | 3 | **$25 per extra seat** |

**$20 per extra GB of vector storage is the most aggressive line.** Raw S3-equivalent compute cost for that GB is fractions of a cent. This is a 1000×+ markup, and it is the single most exploitable economic seam in Botpress's pricing.

### 4.3b "Always Alive" — paying to avoid cold starts

Botpress's runtime has cold-start latency, and they monetize the fix separately. The "Always Alive" feature reserves dedicated compute so a bot doesn't go cold between conversations — included for **only 1 bot on Plus** and **3 bots on Team**, with extras at **$10/month per bot**. Two implications:

1. The architecture has cold starts. Loop should design to eliminate them entirely (warm runtime pool, or per-tenant agent process pinning) rather than upcharge for them.
2. This is another invisible-on-the-quote line item that surprises customers at scale.

### 4.4 Funding & financials

- **Total raised:** ~$45M (Seed, Series A in 2021 at $50M post, Series B June 2025 at $120M post).
- **Series B leads:** Framework Venture Partners, Inovia Capital, Deloitte Ventures, HubSpot Ventures, Decibel Partners.
- **Reported ARR (Q2 2025):** ~$7.8M.
- **Implied multiple:** ~15× revenue.
- **Headcount:** ~120 (March 2026, per ZoomInfo + LinkedIn).
- **HQ:** Montreal, distributed.

### 4.5 Customers

- **Logos:** Kia, Electronic Arts, Shell, Husqvarna, Windstream, American Express, UPS, Aidoc.
- **Use cases:** support automation, internal HR/IT helpdesks, conversational commerce, knowledge Q&A, lead gen.
- **Estimated mix:** ~40–50% SMB, ~35–45% mid-market, ~5–15% enterprise.

### 4.6 Where pricing breaks

- **Cost forecasting is impossible** — agent success = higher bills, with no per-conversation budget visibility.
- **Hard caps blackhole the bot** — no graceful degradation, no warning thresholds, no "soft mode."
- **No published token rates** — to do the math you have to email support.
- **Channel costs invisible on the invoice** — finance departments are surprised by the Meta bill.
- **Renewal shock** — overages + extra seats + channel growth typically 2× the year-2 bill.

These are all design problems, not pricing-strategy problems. They are fixable in a competitor and they create a clean wedge.

---

## 5. Channels, Integrations, and the "Hub"

### 5.1 Channel coverage

First-party / verified:
- Web chat widget (proprietary, light/dark)
- WhatsApp (Cloud API + BSP)
- Messenger
- Instagram DM
- Slack
- Microsoft Teams
- Telegram
- SMS (via Twilio)
- Webhook / HTTP

Notably **absent or community-only**: Email (no first-party), Discord (no native), Webex, RCS, voice (no native).

### 5.2 Voice — the hole

Botpress has no native voice agent. The "voice" path is:

```
phone caller → Twilio Voice → Twilio ConversationRelay → Botpress runtime
            → Deepgram (STT) → LLM → ElevenLabs (TTS) → Twilio → caller
```

Three external hops, no integrated VAD (voice activity detection), no streaming barge-in, no phone-number provisioning at the Botpress layer. End-to-end latency typically 1.2–2.5s vs Vapi's 500–800ms. For voice-first products this is unusable.

### 5.3 The Hub (~190 integrations)

Categories: messaging, CRM (HubSpot, Salesforce, Pipedrive, Bigin), ticketing (Zendesk), payments (Stripe), workflow (Zapier, n8n, Make), knowledge (Notion, Confluence, GDrive), data (Postgres, Mongo, Sheets), comms (Twilio, SendGrid, Discord).

### 5.4 How an integration is built

```typescript
// integration.definition.ts
export default {
  id: "my-integration",
  name: "My Integration",
  channels: { slack: { /* message types */ } },
  actions: { postMessage: { /* JSON-schema params */ } },
  events: { onMessage: { /* trigger schema */ } },
}

// src/index.ts
export default new Integration(definition, {
  hooks: {
    onMessage: async (req) => { /* handle */ },
  },
})
```

Deploy with `bp deploy`. Workspace-scoped credentials (OAuth client_id/secret stored at workspace level, **not per bot** — credential-leakage risk that bigger orgs flag).

### 5.5 MCP

Botpress shipped a basic MCP server in mid-2025 for letting external IDEs (Cursor, Claude Desktop) introspect a Botpress workspace — listing bots, conversations, issues. **Inbound MCP — using external MCP servers as agent tools — is not the native pattern.** Each tool is still a hand-rolled action with a hand-rolled schema.

### 5.6 Where channels & integrations break

- WhatsApp template approval friction (Meta's 2025 ML-based moderation rejects more templates).
- Web widget CSS customization is shallow; users hit limits at any meaningful brand work.
- Teams permissioning is fiddly (Bot Framework registration, OAuth scopes).
- No per-bot credential isolation.
- No native voice.
- No native email.
- No Discord.

---

## 6. Competitive Gaps & What Users Actually Complain About

Synthesized from G2, Capterra, the Botpress Discord, GitHub issues, and Reddit r/Botpress:

### 6.1 Conversation takeover is broken

**The single most-cited production blocker.** When the bot misroutes or hallucinates, agents cannot manually take over the conversation through Botpress. Teams build their own front-ends to handle handoff. *("Users almost need a custom front end to handle everything.")*

### 6.2 Renewal shock

Year-2 bills routinely 2× the initial quote. Driven by AI-credit overages, seat creep, and channel-cost growth. No spend-control primitives strong enough to prevent it.

### 6.3 Free tier is a marketing gimmick

500 messages/month is unusable for any real evaluation. Most evaluators bounce before reaching meaningful usage.

### 6.4 Flow editor degrades at scale

At ~100+ nodes the canvas becomes a mess. Connectors disappear during edits because the editor performs hidden saves before allowing wires to be drawn. Users have requested grouping / labels / shapes for years; not delivered.

### 6.5 Knowledge base is a black box

Why did the bot ignore the KB? Why did it hallucinate? No confidence scores exposed. No "I don't know" fallback chain. PDF support is uneven (text-based works, image-based fails silently). Multi-source KBs hit retrieval bugs.

### 6.6 Tool calls silently drop

GitHub issues document tools that simply don't fire under certain trigger conditions (e.g., webhook trigger + KB agent). No retry telemetry. Users wrap tool calls in custom try/catch that defeats the abstraction.

### 6.7 No observability that matters

Conversation-count dashboards exist. **Token-level traces, retrieval debugging, tool execution history, latency breakdowns, agent decision logs — none.** You cannot answer "why did the bot do X" after the fact.

### 6.8 No evals

There's an `adk-evals` skill but it's poorly documented and requires a manual harness. No pre-built templates (accuracy, latency, cost, hallucination, toxicity). No CI integration. No A/B harness. No regression alerts.

### 6.9 Python-hostile

SDK is TypeScript-only. ML teams that want to wire in scikit-learn, HuggingFace, or LlamaIndex have to rewrite in JS or run a separate Python sidecar. Hard exit ramp for the data-science wing of any org.

### 6.10 No multi-agent

LMSz orchestrates a single agent's tool loop. There is no first-class concept of *multiple agents* with explicit handoffs, shared blackboards, supervisor/worker patterns, or DAG-based pipelines. Users coordinate via flow nodes — brittle and not composable.

### 6.11 No on-prem, no real OSS

v12 is archived. Cloud is closed. Elestio gives you "managed Botpress on your AWS" but you still depend on Botpress's proprietary engine. For HIPAA / SOC2 / data-residency / EU GDPR-stringent customers, this is a deal-breaker.

### 6.12 No git-native flows

Flows export as opaque zipped JSON. You cannot do a meaningful diff. Branches do not exist. Rollbacks are manual upload-of-old-zip.

### 6.13 Voice gap

Already covered. No native voice. Bolt-on path is high-latency.

### 6.14 Cold starts (and the Always-Alive upcharge)

Botpress's runtime cold-starts under low traffic, hurting first-message latency on idle bots. They turn this into a $10/bot/month upcharge ("Always Alive") rather than fixing the architecture. A second seam.

### 6.15 The competitive landscape Botpress actually faces

Beyond LangGraph/Voiceflow:

- **Rasa** — open-source, self-hosted, custom-trained ML models, code-centric. Loved by enterprise data-science teams that need on-prem and full data sovereignty. A valid alternative for the *exact* segment Botpress abandoned when v12 was archived.
- **n8n / Make.com / Zapier** — workflow automation that cannibalizes the segment that wants "agent" but really just needs CRM-glue + LLM-call. n8n especially is open-source and stealing PLG mindshare from Botpress.
- **Pure RAG products** — YourGPT, CustomGPT.ai, Heroic KB. They eat the simple-FAQ end of the market with dead-simple ingest-a-PDF-and-go UX. Botpress's flow-builder is overkill for that use case, so this segment leaks downward.

Loop must hold the *agent-platform* center of gravity while specifically positioning against each of these — not against Botpress alone.

---

## 7. Loop — Product Thesis & Positioning

### 7.1 One-liner

> **Loop is the open-source, agent-first runtime for production AI agents — voice + chat unified, MCP-native, eval-driven, with a transparent cloud control plane.**

### 7.2 The five wedges

1. **Agent-first, not flow-first.** Agents are stateful, long-lived, composable Python objects. Flows are an *optional* visualization, not the substrate.
2. **MCP everywhere.** Every tool is an MCP server. Bring your own MCP servers, or use the 200+ in the public registry. Zero custom-action boilerplate.
3. **Eval-driven dev loop.** Every agent ships with a test suite. Every deploy gates on regression. Pre-built eval templates for accuracy, latency, cost, safety, hallucination.
4. **Voice + chat unified from day one.** One agent, one memory, runs on phone, Slack, web, WhatsApp, email simultaneously. Native sub-700ms voice.
5. **Transparent costs, hard caps, OSS core.** Apache 2.0 runtime. Cloud is a paid convenience, not a lock-in. Token costs visible per call. Per-conversation budgets.

### 7.3 Who Loop is for (in priority order)

- **Tier 1 (wedge):** ML / platform engineers at Series A–C startups currently fighting LangChain/LangGraph + their own scaffolding. They want a real platform, not a toy. Python-fluent.
- **Tier 2 (volume):** Botpress / Voiceflow refugees who've outgrown the flow paradigm and want to keep their bot but move to code.
- **Tier 3 (revenue):** Mid-market enterprises (200–2000 employees) with a real need for compliance, on-prem, audit logs.

### 7.4 Who Loop is *not* for

- Non-technical SMB owners who want a 10-minute drag-and-drop FAQ bot. Voiceflow / Intercom Fin / Tidio own that segment and we should not chase it.
- Pure consumer chatbot toys.

### 7.5 Tagline candidates

- *"Agents that ship."*
- *"The runtime your evals deserve."*
- *"Open-source agent infrastructure."*

---

## 8. Loop — High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           CONTROL PLANE (Cloud)                          │
│  Auth · Billing · Workspace mgmt · Deploy API · Eval orchestrator        │
│  Observability backend (ClickHouse) · MCP marketplace                    │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                  DATA PLANE (Cloud or Self-Hosted)                       │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Agent      │  │   Tool /     │  │   Memory &   │  │  LLM Gateway │ │
│  │   Runtime    │←→│   MCP Layer  │  │   State      │←→│  (multi-     │ │
│  │   (Python)   │  │              │  │   Store      │  │  provider)   │ │
│  └──────┬───────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
│         │                                                                │
│         ▼                                                                │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │           Channel Layer (chat + voice unified)                   │   │
│  │  Web · WhatsApp · Slack · Teams · SMS · Telegram · Email · Voice │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────┐   ┌─────────────────────────────────┐      │
│  │  Knowledge / RAG Engine │   │  Eval Harness (in-runtime)      │      │
│  └─────────────────────────┘   └─────────────────────────────────┘      │
│                                                                          │
│  Postgres (state, metadata) · Qdrant (vectors) · NATS (events) ·         │
│  Redis (cache, rate limits) · S3-compat (artifacts)                      │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    DEVELOPER SURFACES                                    │
│  Python SDK · TS SDK · `loop` CLI · Studio (web debugger, not flow ed.) │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key design principles:**

- **Control plane / data plane split.** The control plane is multi-tenant SaaS. The data plane is a single binary you can run yourself. Self-hosted Loop = same data plane, no control plane (use the OSS dashboard).
- **Stateless runtime, stateful storage.** The agent runtime is horizontally scalable. All state lives in Postgres + Redis + Qdrant + S3.
- **NATS for everything async.** Tool execution, channel events, eval triggers, multi-agent handoffs all flow through NATS. Auditable, replayable.
- **MCP as the universal tool ABI.** No "actions," no "integrations" — just MCP servers. The runtime is an MCP client.
- **Channels are stateless adapters.** They translate `inbound channel event → AgentEvent` and `AgentResponse → outbound channel message`. No business logic.
- **Voice is a channel.** Same agent code, same state. The voice channel handles VAD, STT, TTS, barge-in, but the agent doesn't know it's voice.

---

## 9. Loop — Module-by-Module Build Spec

### 9.1 Agent Runtime (Python core)

**Responsibility:** execute an agent's reasoning loop given an inbound message + memory + tools.

**Interface (Python):**

```python
from loop import Agent, Tool, Memory, Channel

class SupportAgent(Agent):
    name = "support"
    model = "claude-sonnet-4-7"  # any provider
    instructions = "You help customers resolve order issues."

    tools = [
        Tool.mcp("github://stripe/refund-server"),
        Tool.mcp("loop://kb/orders"),
        Tool.fn(lookup_order),  # plain Python function auto-MCP'd
    ]

    memory = Memory(
        user="postgres",       # persistent
        session=Memory.ttl("24h"),
        scratch=Memory.in_run(),
    )

    async def on_message(self, msg, ctx):
        return await self.act(msg, ctx)
```

**Reasoning loop:**

1. Receive `AgentEvent` (inbound message + channel + user_id).
2. Load memory: user, session, scratch.
3. Build prompt: system instructions + memory snapshot + tool catalog (MCP-introspected) + user message.
4. Call LLM (via Gateway). Stream tokens out. Parse structured tool calls.
5. For each tool call, dispatch to MCP layer (parallel by default).
6. Append tool results to context. Loop until LLM emits a terminal response or hits `max_iterations` or `max_cost`.
7. Persist memory diff. Emit `AgentTrace` to observability backend.
8. Return final response.

**Hard limits, all configurable:**
- `max_iterations: 10`
- `max_cost_usd: 0.50` per turn
- `max_tool_calls_per_turn: 20`
- `max_runtime_seconds: 300` (vs Botpress's hard 60s)

**Streaming:** first-class. The runtime emits an SSE/WebSocket stream of tokens, tool-call starts/ends, and trace events. Channels can choose to render incrementally (web widget, Slack block kit edits) or buffer (SMS, voice).

### 9.2 Tool / MCP Layer

**Responsibility:** expose tools to the agent runtime via MCP.

- **Built-in MCP client** in the runtime — no shimming, no "action manifest."
- **MCP server registry** — the Loop Hub. Equivalents to Botpress's "integrations" except they're plain MCP servers anyone can publish.
- **Auto-MCP for Python functions** — decorate a function and Loop wraps it as an in-process MCP server with auto-generated JSON schema from type hints + docstring.
- **Sandboxing** — out-of-process MCP servers run in gVisor or Firecracker microVMs. Never V8 isolates (Botpress's trade-off). Cold start ~100ms via prewarmed pool.
- **Tool selection:** the LLM picks tools by name from the catalog. The runtime enforces allow-lists per agent.
- **Per-call cost budgeting:** every tool call records its USD cost (LLM + compute + 3rd-party). The runtime can refuse a call if it would exceed the per-turn budget.
- **Built-in MCP servers shipped with Loop:** Postgres, HTTP, filesystem, web search (Brave/Tavily), browser automation (Playwright), shell, Python REPL, S3, Redis, Stripe, Slack, GitHub, Google Calendar, Gmail, Notion, Linear, Jira, Salesforce, HubSpot, Zendesk.

### 9.3 Memory & State Store

**Goal:** flexible memory tiers without Botpress's 128 KB cap.

| Tier | Backend | Default size | Notes |
|------|---------|--------------|-------|
| `user` | Postgres | unlimited | Per end-user, persistent |
| `session` | Redis | 1 MB soft, 16 MB hard | TTL, per conversation |
| `scratch` | In-process | 64 KB | Cleared per run |
| `bot` | Postgres | unlimited | Shared across users |
| `episodic` | Postgres + Qdrant | unlimited | Semantic recall over past turns |

**Episodic memory** is a Loop-specific primitive that Botpress lacks: every conversation turn is auto-embedded and stored in Qdrant, with optional summarization. The agent can call `memory.episodic.recall(query, k=5)` to retrieve semantically similar past interactions across all conversations the user has had — a real moat for long-running agents.

**Memory diffs** are stored, not just snapshots. Time-travel debugging is possible — replay any conversation with any memory state.

### 9.4 LLM Gateway

**Responsibility:** route LLM calls across providers with caching, retries, and cost accounting.

- **Providers:** OpenAI, Anthropic, Google Gemini, Mistral, Cohere, Groq, Fireworks, Together, vLLM (self-hosted), Ollama (self-hosted), Bedrock, Azure OpenAI.
- **Model aliases:** `model = "fast"` → cheapest provider satisfying constraints. `model = "best"` → highest-quality. `model = "claude-sonnet-4-7"` → exact pin.
- **Semantic cache:** Redis-backed, configurable similarity threshold. Cuts repeat-query costs ~30–50%.
- **Streaming everywhere.** The gateway never buffers.
- **Per-call cost accounting:** `cost = input_tokens × in_rate + output_tokens × out_rate + provider_overhead`. Recorded to ClickHouse.
- **Hard spend caps:** per-agent, per-conversation, per-workspace, per-day. Cap hit → graceful degrade to a smaller model or canned response, *not* a hard cutoff.
- **BYO key:** customers can plug their own OpenAI/Anthropic key; Loop charges only the per-second runtime fee.

### 9.4a Human-in-the-Loop (HITL) — explicit primitive

Botpress treats HITL as bolt-on; Loop treats it as a first-class agent capability. Every agent ships with:

- **Escalation rules** — declarative triggers (`confidence < 0.5`, `negative_sentiment`, `keyword: "manager"`, `tool_failed > 3 times`) that route the conversation to human queue.
- **Shared inbox** — built-in operator UI that shows the full conversation transcript, agent traces, retrieved KB chunks, and tool calls. Operator can take over, draft-as-AI, or hand back.
- **Native CRM connectors** for the inbox: Zendesk, Salesforce Service Cloud, Front, HelpScout, Intercom (as ticketing target, not as a competitor).
- **Audit trail** — every handoff is logged with timestamp, reason, operator, resolution, replayable in Studio.

This is one of Botpress's genuine strengths and we should not under-build it.

### 9.5 Channel Layer

**Built-in adapters:**

| Channel | Primitives |
|---------|-----------|
| Web widget | Loop-hosted (custom CSS/JS allowed), or self-hosted React component |
| WhatsApp | Cloud API (direct) + 360dialog + Twilio BSP |
| Slack | Block Kit, Slash Commands, threaded conversations |
| Microsoft Teams | Bot Framework, adaptive cards |
| Telegram | Native |
| SMS | Twilio, Bandwidth, Sinch |
| Email | SES, SendGrid, Resend, IMAP poll |
| Discord | Native (gap Botpress has) |
| RCS | Native (forward-looking) |
| Voice | See 9.6 |
| Webhook / HTTP | Generic — bring your own UI |

**Channel adapter contract:**

```python
class ChannelAdapter(Protocol):
    async def receive(self) -> AsyncIterator[InboundEvent]: ...
    async def send(self, response: AgentResponse) -> None: ...
    async def takeover(self, agent_id: str, by: str) -> ConversationHandle: ...
```

`takeover()` is the production-blocker fix for Botpress's #1 complaint. Any channel adapter must implement it. The web widget's React component ships with a "human takeover" UI out of the box; Slack ships with an `/takeover` slash command; voice ships with a "transfer to human" tool.

### 9.6 Voice subsystem

The most engineering-intensive module and the biggest moat.

**Pipeline:**

```
SIP/WebRTC ↔ Voice Gateway (Pion or Asterisk) ↔ VAD (Silero) ↔ Streaming STT
                                                                    │
                                                                    ▼
                                       Agent Runtime (streams tokens)
                                                                    │
                                                                    ▼
                                              Streaming TTS (ElevenLabs Turbo,
                                                  Cartesia, Inworld, OpenAI)
                                                                    │
                                                                    ▼
                                                    Voice Gateway → caller
```

**Latency budget (target ≤700ms p50):**
- VAD endpoint: ~50ms
- STT first-partial: ~150ms
- LLM first-token: ~250ms (with prompt caching)
- TTS first-audio: ~150ms
- Network: ~100ms

**Features:**
- Barge-in (user interrupts the bot mid-sentence; bot stops, listens).
- Phone-number provisioning via Twilio/Bandwidth at the Loop layer (Botpress doesn't do this).
- Background-noise suppression (RNNoise).
- Hot-keyword detection ("speak to a human" → instant transfer).
- Real-time transcription + translation tools available to the agent.

### 9.6a Cold-start avoidance (architectural commitment)

Cold starts are a Botpress upcharge, not an engineering accomplishment. Loop's runtime is designed so cold starts are impossible at the agent level:

- Runtime pods are warm and stateless; agent context loads from Postgres + Redis on-demand in <50ms.
- For voice (where cold starts are unacceptable), tool sandboxes use a prewarmed Firecracker pool with target ~100ms launch.
- No "Always Alive" upcharge. Ever. Bake the latency into the architecture, not the price.

### 9.7 Knowledge / RAG Engine

- **Sources:** PDF (text + OCR via Tesseract for scans), DOCX, HTML/web crawl, Notion, Confluence, GDrive, S3 buckets, Slack threads, GitHub, Zendesk, Salesforce KB, Postgres SQL, plain text.
- **Chunking:** configurable strategies — semantic boundary, fixed-size, sliding window, table-aware (Unstructured.io), code-aware (tree-sitter).
- **Embeddings:** pluggable — OpenAI `text-embedding-3-large`, Voyage, Cohere, BGE, GTE, NV-Embed, custom.
- **Vector store:** Qdrant (default, OSS, fast). Optional: Pinecone, Weaviate, pgvector.
- **Retrieval:** hybrid (BM25 + vector) by default. Reranker optional (Cohere Rerank, BGE-reranker).
- **Per-bot scoping** (vs Botpress's workspace-only): every KB ingestion belongs to a `kb_id` scoped to a bot, with optional cross-bot sharing.
- **Confidence + fallback:** every retrieval returns a confidence score. The agent can branch on `if confidence < 0.6: answer "I don't know"` — first-class, not a workaround.
- **Explainability:** every answer can return `cited_chunks` with byte-range source links. Debuggable.
- **Vision indexing (parity with Botpress):** ingestion pipeline parses charts, technical diagrams, and figures from PDFs into structured representations using a vision model (Claude Sonnet, GPT-4o-vision, or InternVL self-hosted). Critical for technical-support and engineering-doc use cases.

#### Why Qdrant over pgvector — concrete numbers

Industry benchmarks on 50M × 768-dim embeddings at 99% recall:

| Metric | pgvector (with pgvectorscale) | Qdrant |
|--------|-------------------------------|--------|
| Implementation language | C (Postgres extension) | Rust |
| Single-node throughput | ~471 QPS | ~41 QPS |
| p99 query latency | ~74.6 ms | **~38.7 ms** |
| Quantization support | half-vector only | scalar / product / binary |
| Horizontal scale-out | constrained to a single instance | native sharding to billions |
| Practical ceiling | 1–10M vectors | 100M–1B+ vectors |
| Index-build time on heavy ingest | slow, can starve OLTP traffic | fast, isolated |

pgvector is fine if you're starting out and already on Postgres. **Loop's enterprise customers will exceed the pgvector ceiling almost immediately.** Qdrant from day 1 is the right call. Botpress chose pgvector for operational simplicity; Loop chooses Qdrant for ceiling. Customers with smaller workloads can still self-host with pgvector via the pluggable backend.

### 9.8 Eval Harness

The single biggest competitive feature.

**Concepts:**
- **Eval suite** — a collection of test cases (input → expected behaviors).
- **Eval template** — pre-built scorer (accuracy, latency, cost, hallucination, toxicity, refusal, JSON-validity, citation-presence, tool-call-correctness).
- **Eval run** — execution of a suite against a deployed (or candidate) version of an agent.

**Workflow:**

```bash
# author a suite
loop eval init my-suite
# add cases (yaml + jsonl)
# run locally
loop eval run my-suite --against=local
# run against a candidate version
loop eval run my-suite --against=staging --baseline=prod
# CI gate
loop eval run my-suite --against=PR-123 --fail-on=regression>5%
```

**Built-in scorers:**
- LLM-as-judge with structured rubric.
- Embedding similarity to golden response.
- Regex / JSON schema match.
- Tool-call assertion (must call X with args Y).
- Latency / cost thresholds.
- Hallucination check (groundedness against KB).
- Safety classifiers (toxicity, PII leakage, jailbreak resistance).

**Replay / time-travel:** any production conversation can be re-run as an eval case with a different agent version. Replays auto-capture and become regression cases.

**Public eval registry:** community-shared eval suites (similar to a HuggingFace datasets ecosystem). "Run the `customer-support-en-v2` benchmark against your agent in one command."

### 9.9 Observability

| Concern | Implementation |
|---------|----------------|
| Token-level traces | OpenTelemetry + ClickHouse |
| Tool call history | NATS event log → ClickHouse |
| Retrieval debugging | Each KB query stores: candidates, scores, chosen chunks, full prompt |
| Cost attribution | Per-call USD, rolled up per-agent / per-conversation / per-workspace |
| Latency breakdown | Per-stage spans (LLM, STT, TTS, tools, memory) |
| Live tail | `loop tail --agent=support` streams real-time traces |
| Replay | Click any conversation → re-run with diff version / diff model |
| Evals dashboard | Trends over time, regressions highlighted |

Built on OpenTelemetry. Traces export to any OTLP-compatible backend (Datadog, Honeycomb, Grafana Tempo). The Loop Cloud dashboard is the default UI.

### 9.10 Studio (debugger UI)

Botpress's Studio is a flow editor with a debugger bolted on. Loop's "Studio" is a **debugger first**, with optional flow visualization for users who want it.

- **Conversations view** — paginated, filterable, with inline traces.
- **Trace view** — waterfall of LLM calls, tool calls, retrievals, memory diffs.
- **Replay panel** — re-run with knobs (model, temperature, tools, memory state).
- **Eval dashboard** — runs, scores, regression alerts.
- **Cost dashboard** — token/dollar breakdown over time.
- **Agent code view** — read-only mirror of the deployed Python (with version diff).
- **Optional flow visualization** — auto-generated DAG view for users who want a picture; not the editing surface.

No drag-and-drop flow editor. We are not Voiceflow.

### 9.11 SDKs

**Python (primary):** `pip install loop-agents`. Async-first. Type-hinted. Pydantic models everywhere.

**TypeScript (secondary):** `npm install @loop/agents`. Auto-generated from Python type definitions via Pydantic-to-TS-types pipeline. Same surface area, same semantics.

**Go (deferred):** Months 9–12.

### 9.12 CLI

`loop` (single binary, written in Go for fast startup):

```
loop init                # scaffold a new agent
loop dev                 # run locally with hot reload
loop deploy              # deploy to Cloud or self-hosted control plane
loop tail                # live trace stream
loop eval run            # run an eval suite
loop replay <conv-id>    # interactive replay session
loop kb ingest <path>    # ingest a knowledge source
loop mcp install <pkg>   # install an MCP server from the Hub
loop secrets             # manage workspace secrets
```

### 9.12a Generative Copilot inside the SDK

Borrow one idea from Botpress's local-dev story: AI coding assistants (Copilot, Cursor) work better when the framework's TypeScript types are precise. Loop goes further — ship a **`loop copilot`** subcommand and a Cursor-/Claude-Desktop-aware MCP server that knows Loop's APIs, schemas, and idioms. When the user types "I want to add an MCP server that calls the Stripe refund API," the copilot generates the exact decorator, schema, and test stub. This is a real reduction in time-to-first-agent and a documentation force-multiplier.

### 9.12b Hybrid deterministic / autonomous nodes (lessons from Botpress)

Botpress's most defensible architectural idea is the **Standard Node + Autonomous Node hybrid**: deterministic flow steps for high-stakes actions (payment, compliance, identity verification) interleaved with LLM-driven autonomous reasoning for everything else. Loop ships the same primitive in code, not flows:

```python
class CheckoutAgent(Agent):
    @deterministic  # never an LLM here
    async def collect_payment(self, ctx):
        return await stripe.charge(ctx.user.card, ctx.amount)

    @autonomous  # LLM-driven
    async def help_with_returns(self, msg, ctx):
        return await self.act(msg, ctx)
```

Decorators are explicit, code-reviewable, and unit-testable. Same conceptual win as Botpress's hybrid; better engineering ergonomics.

### 9.13 Multi-agent orchestration

First-class primitives, not a flow hack.

**Patterns built into the SDK:**

```python
# Supervisor pattern
supervisor = Supervisor(
    workers=[support_agent, billing_agent, escalation_agent],
    routing="llm",  # or "rule", or a custom callable
)

# Sequential pipeline
pipeline = Pipeline([extract_agent, classify_agent, respond_agent])

# Parallel fanout-fanin
fanout = Parallel([sentiment_agent, intent_agent, language_agent], merge=combine_results)

# Graph (cyclic allowed, unlike Botpress)
graph = AgentGraph()
graph.edge(intake, triage)
graph.edge(triage, support, when=lambda s: s.category == "support")
graph.edge(support, intake, when=lambda s: s.needs_clarification)  # cycle OK
```

State is shared via an explicit **blackboard** (Redis-backed) or passed as typed messages via NATS. Either way: visible, replayable, debuggable. No LMSz black box.

---

## 10. Data Model & Core Schemas

### 10.1 Postgres tables (simplified)

```sql
-- Workspace & auth
workspaces (id, name, plan, created_at, ...)
users (id, workspace_id, email, role, ...)
api_keys (id, workspace_id, hashed_key, scopes, ...)

-- Agents
agents (id, workspace_id, name, version, code_artifact_url, model, ...)
agent_versions (id, agent_id, version_number, deployed_at, code_hash, ...)
agent_tools (agent_id, tool_id, allow_list_config)
agent_kbs (agent_id, kb_id, scope)

-- Conversations & memory
conversations (id, agent_id, channel, user_id, started_at, last_at, status, ...)
turns (id, conversation_id, role, content, token_in, token_out, cost_usd, ts, ...)
memory_user (user_id, agent_id, key, value_json, updated_at)
memory_session (conversation_id, key, value_json, ttl_at)
memory_bot (agent_id, key, value_json, updated_at)
episodic_memory (id, user_id, agent_id, content, embedding, ts) -- Qdrant in practice

-- Tools / MCP
mcp_servers (id, workspace_id, name, source_url, version, install_status)
tool_calls (id, turn_id, tool_id, args_json, result_json, latency_ms, cost_usd, error)

-- KB / RAG
knowledge_bases (id, workspace_id, name, scope, embedding_model)
kb_documents (id, kb_id, source_uri, content_hash, ingested_at, status)
kb_chunks (id, doc_id, position, content, embedding) -- Qdrant in practice

-- Evals
eval_suites (id, workspace_id, name, repo_path, ...)
eval_cases (id, suite_id, input_json, expected_json, scorers_json)
eval_runs (id, suite_id, agent_version_id, status, started_at, ended_at)
eval_results (id, run_id, case_id, score, traces_url, regression_flag)

-- Observability
traces (id, conversation_id, turn_id, span_json, ts) -- ClickHouse in practice
costs_daily (workspace_id, date, llm_usd, compute_usd, tool_usd) -- materialized

-- Channels
channel_configs (id, agent_id, channel_type, config_json, secrets_ref)
```

### 10.2 Core Python types

```python
class AgentEvent(BaseModel):
    conversation_id: UUID
    user_id: str
    channel: ChannelType  # web | whatsapp | slack | voice | ...
    content: list[ContentPart]   # text, image, audio, file
    metadata: dict
    received_at: datetime

class AgentResponse(BaseModel):
    conversation_id: UUID
    content: list[ContentPart]
    streaming: bool = True
    suggested_actions: list[Action] = []
    end_turn: bool = True

class Trace(BaseModel):
    turn_id: UUID
    spans: list[Span]            # llm | tool | retrieval | memory | channel
    total_cost_usd: float
    total_latency_ms: int
    iteration_count: int

class ToolCall(BaseModel):
    name: str
    server: str                  # MCP server URI
    args: dict
    result: Any | None
    error: str | None
    latency_ms: int
    cost_usd: float
```

---

## 11. API Surface

### 11.1 Public REST API (Cloud + self-hosted)

```
POST   /v1/agents                          create agent
GET    /v1/agents                          list agents
GET    /v1/agents/{id}                     get agent
POST   /v1/agents/{id}/versions            deploy new version
POST   /v1/agents/{id}/invoke              run a turn (sync or stream)
GET    /v1/agents/{id}/conversations       list conversations
GET    /v1/conversations/{id}              get conversation + traces
POST   /v1/conversations/{id}/takeover     human takeover

POST   /v1/eval-suites                     create suite
POST   /v1/eval-suites/{id}/runs           start a run
GET    /v1/eval-runs/{id}                  results

POST   /v1/kb                              create KB
POST   /v1/kb/{id}/ingest                  ingest source
GET    /v1/kb/{id}/search?q=               retrieve
POST   /v1/mcp/install                     install MCP server

GET    /v1/usage                           per-workspace cost rollup
GET    /v1/traces/{turn_id}                trace detail
```

### 11.2 Streaming endpoints (SSE / WS)

```
POST /v1/agents/{id}/invoke?stream=true → SSE stream of:
   - token deltas
   - tool_call_start / tool_call_end
   - retrieval events
   - trace events
   - final response
```

### 11.3 MCP

The runtime *speaks* MCP outbound (as a client) and *exposes* MCP inbound (so external IDEs can introspect — Claude Desktop, Cursor, Windsurf can list your agents, tail conversations, deploy from a chat).

---

## 12. Tech Stack Choices & Rationale

| Layer | Choice | Why |
|-------|--------|-----|
| **Agent runtime language** | **Python 3.12+** | Where the ML/LLM ecosystem lives. Pydantic, FastAPI, async-native. Botpress's biggest miss is being TS-only. |
| **Cross-language SDK** | **TypeScript** auto-generated | Web devs expected; Pydantic → TS via OpenAPI codegen ensures parity. |
| **CLI** | **Go** | Single static binary, instant startup, easy distribution. |
| **Studio frontend** | **React + TypeScript + tRPC** | Standard. Tailwind for styling. |
| **Database** | **PostgreSQL 16** + Citus for sharding at scale | Boring, reliable, JSONB for flex. |
| **Vector store** | **Qdrant** | OSS, fast, great filtering, scale-out. Drop-in Pinecone alternative. |
| **Cache / TTL state** | **Redis 7** | Session memory, rate limits, semantic LLM cache. |
| **Event bus** | **NATS JetStream** | Fast, OSS, supports request/reply + streams. Replaces Kafka for our scale. |
| **Object storage** | **S3-compatible** (MinIO for self-host) | Code artifacts, audio recordings, document originals. |
| **Trace storage** | **ClickHouse** | Columnar, perfect for trace/event aggregation. |
| **Container runtime** | **Firecracker microVMs** for tool sandboxes; **K8s** for the runtime fleet. | Strong isolation for arbitrary tool code; standard ops for the fleet. |
| **LLM gateway library** | **Custom** (with LiteLLM fork as reference) | We need cost accounting, semantic caching, streaming; existing OSS isn't quite enough. |
| **STT** | **Deepgram Nova-3** (cloud) + **Whisper-V3-Turbo** (self-host) | Lowest latency commercial; Whisper for OSS path. |
| **TTS** | **ElevenLabs Turbo / Cartesia / OpenAI TTS** (cloud) + **Piper** (self-host) | Streaming, sub-200ms. |
| **VAD** | **Silero VAD** | OSS, fast, accurate. |
| **Voice gateway** | **Pion (Go WebRTC)** + **LiveKit** for SFU | Battle-tested, sub-100ms RTC. |
| **Auth** | **Auth0** (Cloud) / **Ory Kratos** (self-host) | SSO, SAML, MFA out of the box. |
| **Billing** | **Stripe** + custom usage metering | Subscriptions + metered. |
| **IaC** | **Terraform + Pulumi (TypeScript)** | Standard. |
| **Observability** | **OpenTelemetry → ClickHouse + Grafana** | Vendor-neutral. |

---

## 13. Deployment Topology & Infrastructure

### 13.1 Cloud (managed multi-tenant)

```
[Cloudflare] → [Envoy ingress (k8s)] → [API gateway pods]
                                          │
              ┌───────────────────────────┴────────────────┐
              │                                            │
        [Runtime pods (Python)]                  [Channel adapter pods]
              │                                            │
              ├── Postgres (Aurora multi-AZ)               │
              ├── Redis (ElastiCache cluster)              │
              ├── Qdrant (k8s statefulset)                 │
              ├── NATS (k8s cluster)                       │
              ├── ClickHouse (managed Altinity)            │
              ├── S3                                       │
              └── Tool sandbox pool (Firecracker)
```

- **Region:** us-east-1 + eu-west-1 from day 1 (data residency wins enterprise deals).
- **Voice:** dedicated low-latency edge POPs (Cloudflare Spectrum or self-hosted).
- **Tenant isolation:** workspace-scoped namespaces in Postgres + per-workspace KMS keys.

### 13.2 Self-hosted (single-binary or k8s helm chart)

- `docker compose up` — single-node dev / small prod.
- Helm chart for k8s — production self-host. Same code, no proprietary inference layer.
- BYO LLM keys; BYO Postgres / Redis / Qdrant if desired.
- No phone-home telemetry by default; opt-in usage stats only.

### 13.3 Hybrid

- Customer runs the data plane in their VPC.
- Loop Cloud provides the control plane (deploy, observability dashboard, evals UI, billing).
- Common pattern for regulated enterprises.

---

## 14. Pricing Model & Unit Economics

### 14.1 What we charge for

Three meters, all transparent on the bill:

1. **Platform subscription** (predictable, per seat).
2. **Agent-seconds** (compute time the runtime spends on an agent's reasoning loop).
3. **LLM tokens** (pass-through with a 5% margin — explicitly disclosed).

Everything else (channels, KB storage, tool calls) rolls up into agent-seconds + tokens. No surprise line items.

### 14.2 Plans

| Plan | Monthly | Included | Seats | Notes |
|------|---------|----------|-------|-------|
| **Open Source** | $0 | Everything | ∞ | Self-host. Apache 2.0. |
| **Hobby (Cloud)** | $0 | 1 agent, 100K agent-seconds, $5 LLM credit | 1 | Real free tier — usable |
| **Pro** | $49/seat | 5 agents, 1M agent-seconds, BYO LLM key option | 1+ | Replaces Botpress Plus |
| **Team** | $299/seat | Unlimited agents, 10M agent-seconds, evals, full obs | 3+ | Replaces Team |
| **Enterprise** | Custom | SSO, SOC2, on-prem, audit logs, dedicated runtime | Custom | Multi-year |

### 14.3 The wedge: hard caps that don't blackhole

Every workspace can set:
- A **soft budget** (warning at 80%, 100% — agent keeps running).
- A **hard budget** (stops new conversations, finishes in-flight ones gracefully — never drops mid-turn).
- A **graceful-degrade rule** (when over budget, swap to a cheaper model and keep running).

Botpress's "bot goes dark mid-month" failure mode is impossible by design.

### 14.4 Channel costs

We don't mark up Meta or Twilio. We *do* show their costs on our invoice as line items so customers see the full picture in one place. Optional: we can resell Twilio numbers at cost + 10% for convenience.

### 14.5 Target unit economics

- Gross margin target: **75%** at steady state (LLM pass-through is ~95% margin on the 5%; compute is ~70%; storage ~85%).
- LTV:CAC target: **3:1** at month 18.
- ARR per FTE target: **$300K** by month 24.

---

## 15. MVP Scope (First 6 Months)

The "ship something real" cut. Six months, five engineers, one designer.

**In:**
- Python SDK (Agent, Tool, Memory, Channel base classes).
- Agent runtime with single-agent reasoning loop (no multi-agent yet).
- LLM Gateway: OpenAI + Anthropic + Bedrock + vLLM. Streaming. Cost accounting. Semantic cache.
- MCP layer (client + auto-MCP for Python functions). Sandboxed tool execution.
- Memory: user (Postgres) + session (Redis) + scratch (in-process). No episodic yet.
- KB / RAG: PDF + web crawl + Notion ingestion. Qdrant + hybrid retrieval. Citation in responses.
- Channel adapters: web widget, Slack, WhatsApp, SMS, generic webhook.
- **Voice MVP:** WebRTC voice channel via LiveKit + Deepgram + ElevenLabs Turbo. Sub-1s latency target (we'll hit 700ms in a later iteration).
- Eval harness: 6 built-in scorers (LLM-judge, embedding similarity, regex, JSON-schema, tool-call assert, latency).
- CLI: `init`, `dev`, `deploy`, `tail`, `eval run`.
- Studio: conversations list, trace view, replay, cost dashboard. No flow visualization yet.
- Cloud control plane: auth, workspace mgmt, billing (Stripe), deploy API.
- Self-hosted: docker-compose path. (Helm chart in month 7.)
- Hub v0: built-in MCP server bundle (~25 servers covering CRM, KB sources, dev tools).

**Out:**
- Multi-agent orchestration primitives (month 7–9).
- Visual flow auto-generation (month 9+).
- Episodic memory (month 7).
- TS SDK auto-gen (month 5–6).
- Go SDK (post-MVP).
- Email / Discord / Telegram / Teams channels (month 7+; web/WhatsApp/Slack/SMS + voice cover the wedge).
- Public eval registry (month 9).
- On-prem helm chart (month 7).

---

## 16. 12-Month Roadmap

| Month | Milestone |
|-------|-----------|
| **0** | Hire engineers 1–4. Tech-stack lock-in. Start runtime + SDK. |
| **1** | Runtime alpha. Python SDK skeleton. LLM gateway w/ OpenAI + Anthropic. Single Slack channel. |
| **2** | Tool/MCP layer. Auto-MCP. KB ingestion v0. Web widget channel. |
| **3** | Eval harness v0 with 6 scorers. CLI v0. Cloud control plane (auth, deploy). |
| **4** | **Closed alpha** — 10 design partners. WhatsApp channel. Studio v0 (conversations + traces). |
| **5** | Voice channel MVP. Memory tiers (user/session/scratch). Cost dashboard. |
| **6** | **Public beta launch.** Open-source the runtime (Apache 2.0). Hub v0. Free hobby tier. |
| **7** | Episodic memory. Helm chart for self-host. Email + Telegram channels. Multi-agent primitives v0 (Supervisor, Pipeline). |
| **8** | TS SDK GA. Discord + Teams channels. Replay / time-travel debugging. |
| **9** | **Multi-agent GA** (Graph, Parallel, Blackboard). Public eval registry. Series A fundraise. |
| **10** | EU region (Frankfurt). SOC2 Type 1 attestation kicks off. Salesforce + Zendesk first-party MCP servers. |
| **11** | Voice latency ≤ 700ms p50. Phone-number provisioning. RCS channel. |
| **12** | **Enterprise GA.** SSO/SAML, audit logs, data residency controls, on-prem with full feature parity. SOC2 Type 1 done. |

---

## 17. Repository Layout

Monorepo (Turborepo or Nx). Open-source half on GitHub, closed control-plane half private until launch.

```
loop/
├── packages/
│   ├── runtime/              # Python — Agent runtime core (OSS)
│   ├── sdk-py/               # Python SDK (OSS)
│   ├── sdk-ts/               # TypeScript SDK (OSS, auto-generated)
│   ├── cli/                  # Go (OSS)
│   ├── gateway/              # Python — LLM gateway service (OSS)
│   ├── mcp-client/           # Python (OSS)
│   ├── channels/
│   │   ├── web/              # React widget + server (OSS)
│   │   ├── slack/            # (OSS)
│   │   ├── whatsapp/         # (OSS)
│   │   ├── voice/            # (OSS, but vendored deps for STT/TTS)
│   │   └── ...
│   ├── kb-engine/            # Python (OSS)
│   ├── eval-harness/         # Python (OSS)
│   └── observability/        # OTEL exporters (OSS)
├── apps/
│   ├── studio/               # Next.js — debugger UI (OSS)
│   ├── docs/                 # Docusaurus (OSS)
│   ├── control-plane/        # Internal: auth, billing, multi-tenant orchestration (closed)
│   └── eval-registry/        # Public eval marketplace (OSS UI, hosted DB)
├── examples/
│   ├── support-agent/
│   ├── voice-receptionist/
│   ├── shopping-assistant/
│   └── code-review-bot/
├── infra/
│   ├── terraform/
│   ├── helm/
│   └── docker-compose.yml
├── docs/
└── tools/
    ├── mcp-codegen/          # Auto-MCP from Python functions
    └── sdk-codegen/          # Pydantic → TS types
```

---

## 18. Hiring Plan — First 8 Engineers

| # | Role | Why first |
|---|------|-----------|
| 1 | **Founding engineer — runtime / Python core** | Owns the agent loop. Senior, opinionated. |
| 2 | **Founding engineer — infra / platform** | Postgres, Redis, NATS, k8s, Terraform. Builds the data plane. |
| 3 | **Founding engineer — voice / real-time** | WebRTC, STT/TTS, latency. The voice moat. |
| 4 | **Founding engineer — observability + eval harness** | ClickHouse, OTEL, eval scorers. The other moat. |
| 5 | **Founding engineer — full-stack / Studio** | Next.js, React, tRPC. Debugger UI. |
| 6 | **DevRel / docs engineer** | Examples, blog, docs, MCP server contributions. Critical for OSS adoption. |
| 7 | **Senior engineer — channel integrations** | WhatsApp, Slack, Teams, email — the integration grunt work that compounds. |
| 8 | **Security / compliance engineer** | SOC2, HIPAA-readiness, audit logs, secrets — unlocks enterprise. |

Plus: 1 designer (part-time month 1, full-time month 4), 1 PM (month 4), 1 founding GTM (month 6).

**Founder distribution:**
- CEO: vision, fundraising, GTM.
- CTO: architecture, hiring, code reviews. Should still ship code in months 0–6.

---

## 19. Go-to-Market & Distribution

### 19.1 Distribution sequence

1. **Month 0–4:** stealth. 10 design partners hand-picked from the founder's network. Free, white-glove.
2. **Month 5:** **HN launch + ProductHunt** of the OSS runtime + free hobby tier. Position: "Open-source, agent-first, MCP-native."
3. **Month 6:** content engine spins up — eng blog, talks at LangChain Interrupt / AI Engineer / KubeCon, MCP server contributions to the public registry as visibility hooks.
4. **Month 7+:** SEO-led PLG. "Botpress alternative," "LangChain in production," "voice agent latency."
5. **Month 9+:** outbound to mid-market — anyone with a Botpress/Voiceflow/Cognigy contract renewing.
6. **Month 12+:** named-account enterprise sales. Co-sell with cloud marketplaces (AWS Marketplace, Azure, GCP).

### 19.2 The wedge customer

Mid-market companies (200–2000 employees) running customer support or internal IT/HR helpdesks, currently on Intercom Fin / Ada / Botpress, frustrated with cost and lock-in, with at least one engineer who can write Python.

### 19.3 Pricing levers we will not touch

- Never hard-cap a paying customer mid-conversation. Ever.
- Never mark up tokens beyond 5%, and always disclose it.
- Never charge for self-hosted use.

These three commitments are the trust moat. Botpress can't credibly match any of them without burning their pricing model.

---

## 20. Risks, Counter-Arguments, and Open Questions

### 20.1 Strongest counter-arguments

**"OpenAI's Agent SDK and Anthropic's Claude Agent SDK will eat this category."**
True risk. Mitigation: be the *agnostic* layer. Run on either. Run on Bedrock. Run on Ollama. The frontier-lab SDKs are vendor-locked by design — Loop is the Switzerland.

**"LangChain / LangGraph already does most of this."**
Partly true on the SDK; not true on the runtime, observability, evals, voice, or channels. LangChain is a library; we are a platform. Different category.

**"Sierra (Bret Taylor's company) is going after enterprise agents with $4B in capital."**
True. Sierra is sales-led, services-heavy, vertical (CX). We are PLG, OSS-led, horizontal. Different ICP.

**"The flow-builder market is bigger than the code-first market."**
Probably true today. We are explicitly *not* chasing it. Voiceflow can have it.

**"Voice is engineering-heavy and will burn 30% of the team's bandwidth."**
True. That's why we ship it as a real channel from day one — the moat compounds. Without voice we are a LangGraph-with-better-UI; with voice we are a category.

### 20.2 Real risks

- **Runtime engineering complexity.** Python async + streaming + multi-agent + sandboxed tools is genuinely hard. A bad first runtime = death. Hire #1 must be exceptional.
- **MCP standardization risk.** If MCP fragments (OpenAI ships a competing standard, Google ships theirs), our "MCP-native" wedge weakens. Mitigation: be MCP-first but adapter-flexible — speak OpenAI's tool format too.
- **Voice latency ceiling.** Hitting sub-700ms requires edge POPs and careful engineering. Underestimating this is the #1 schedule risk.
- **Botpress catches up.** They have the funding. If they ship native voice + MCP + true OSS in 12 months, our wedge narrows. Counter: their architecture is mid-pivot; doing all three well in 12 months is unlikely.

### 20.3 Open questions for the founder

1. Codename — what's the actual product name? Domain availability? Trademark search needed.
2. Founding team composition — solo founder or co-founder? CTO already lined up?
3. Initial capital plan — bootstrap, pre-seed, seed? Target $4–6M seed for 18 months of runway with 8 engineers feels right.
4. License choice — Apache 2.0 (recommended) vs SSPL (Mongo) vs BSL (HashiCorp)? Apache wins on adoption; BSL wins on monetization protection. Lean Apache + paid Cloud + commercial enterprise add-ons (SSO, audit, dedicated support).
5. Geographic HQ — affects hiring pool and EU data-residency story.
6. Vertical focus — pure horizontal, or lead with one vertical (CX support is the obvious one)?

---

## 21. Appendix A — Sources

Primary research compiled by sub-agents on 29 April 2026.

**Botpress official:**
- [botpress.com/](https://botpress.com/), [/pricing](https://botpress.com/pricing), [/enterprise](https://botpress.com/enterprise), [/customers](https://botpress.com/customers), [/hub](https://botpress.com/hub)
- [Series B announcement (June 2025)](https://botpress.com/en/blog/series-b)
- [Autonomous Node docs](https://botpress.com/docs/studio/concepts/nodes/autonomous-node)
- [LMSz / inference engine post](https://botpress.com/blog/how-botpress-interfaces-with-llms)
- [ADK GitHub](https://github.com/botpress/adk)
- [v12 archived repo](https://github.com/botpress/v12)
- [Knowledge base docs](https://botpress.com/docs/studio/concepts/knowledge-base/introduction)
- [Memory state best practices](https://botpress.com/docs/studio/guides/advanced/best-practices-for-state-management)
- [MCP blog post](https://botpress.com/blog/model-context-protocol)
- [Twilio Voice integration](https://botpress.com/integrations/plus-twiliovoice)
- [WhatsApp integration guide](https://botpress.com/docs/integrations/integration-guides/whatsapp/introduction)

**Reviews & community:**
- [G2 Botpress reviews](https://www.g2.com/products/botpress/reviews)
- [Capterra Botpress reviews](https://www.capterra.com/p/199292/Botpress/reviews/)
- [Botpress Discord — KB issues thread](https://discord.botpress.com/t/13161375)
- [GitHub: KB agent webhook bug #12814](https://github.com/botpress/botpress/issues/12814)
- [GitHub: connector bug v12 #1225](https://github.com/botpress/v12/issues/1225)
- [GitHub: deployment tutorial broken #498](https://github.com/botpress/botpress/issues/498)

**Pricing analyses:**
- [eesel.ai — Botpress pricing](https://www.eesel.ai/blog/botpress-pricing)
- [bigsur.ai — Botpress pricing explained](https://bigsur.ai/blog/botpress-pricing)
- [pagergpt.ai — Botpress pricing](https://pagergpt.ai/alternative/botpress-pricing)
- [Lindy — Botpress pricing guide](https://www.lindy.ai/blog/botpress-pricing)

**Funding & company:**
- [Crunchbase — Botpress](https://www.crunchbase.com/organization/botpress)
- [GlobeNewswire — Series B announcement](https://www.globenewswire.com/news-release/2025/06/23/3103351/0/en/Botpress-Raises-25M-Series-B-to-Scale-AI-Agent-Infrastructure.html)

**Competitive analyses:**
- [Retell AI — Voiceflow alternatives](https://www.retellai.com/blog/voiceflow-ai-alternatives)
- [ZenML — Botpress alternatives](https://www.zenml.io/blog/botpress-alternatives)
- [Lindy — Botpress vs Voiceflow](https://www.lindy.ai/blog/botpress-vs-voiceflow)
- [Multi-agent orchestration comparison (Medium)](https://medium.com/@arulprasathpackirisamy/mastering-ai-agent-orchestration-comparing-crewai-langgraph-and-openai-swarm-8164739555ff)

---

*End of document.*
