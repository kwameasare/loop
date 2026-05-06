#!/usr/bin/env python3
"""
Loop tracker — source of truth + renderer.

This file is THE source of truth for the implementation tracker. To change
status, owner, notes, sprints, or stories: edit the data lists below, then
run this script. It regenerates:

    loop_implementation/tracker/TRACKER.md   (canonical AI-readable view)
    loop_implementation/tracker/tracker.json (programmatic / agents)
    loop_implementation/tracker/csv/*.csv    (per sheet, for ad-hoc analysis)

The xlsx companion is regenerated separately via tools/tracker_to_machine.py
(currently a no-op stub; see ADR / S001 PR for context).

Usage:
    python tools/build_tracker.py            # regenerate all outputs
    python tools/build_tracker.py --check    # exit 1 if outputs are stale

Data conventions
================
Stories use a dataclass with a multi-line ``notes`` field. When status is
``In progress`` / ``Blocked`` / ``Handing off``, ``notes`` MUST follow the
canonical structured Notes-cell format (see skills/meta/update-tracker.md
"Canonical Notes-cell format"). For ``Not started`` and ``Done`` stories,
notes is a free-form short string (week tag or post-merge summary).

Newlines in ``notes`` are rendered as ``<br>`` in the Markdown table cell so
the row stays on one logical line.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

UTC = UTC  # python<=3.10 compat (datetime.UTC arrived in 3.11)

UTC = UTC  # python<=3.10 compat (datetime.UTC arrived in 3.11)
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TRACKER_DIR = ROOT / "loop_implementation" / "tracker"
CSV_DIR = TRACKER_DIR / "csv"
MD_PATH = TRACKER_DIR / "TRACKER.md"
JSON_PATH = TRACKER_DIR / "tracker.json"

VALID_STATUSES = {
    "Not started",
    "In progress",
    "Handing off",
    "Blocked",
    "In review",
    "Done",
    "Cancelled",
    "Watching",
    "Active",
    "Searching",
    "Pipeline",
}


# --------------------------------------------------------------------------- #
# Data classes                                                                #
# --------------------------------------------------------------------------- #


@dataclass
class Epic:
    id: str
    name: str
    owner: str
    target: str
    status: str
    notes: str = ""


@dataclass
class Story:
    id: str
    title: str
    owner: str
    sprint: str
    epic: str
    points: int
    priority: str
    status: str
    notes: str = ""


@dataclass
class Sprint:
    id: str
    window: str
    theme: str
    goal: str
    stories: str
    status: str


@dataclass
class Hire:
    n: int
    role: str
    why: str
    start_month: str
    stage: str
    owner: str
    notes: str


@dataclass
class Risk:
    id: str
    risk: str
    likelihood: str
    severity: str
    owner: str
    mitigation: str
    status: str


@dataclass
class Milestone:
    month: str
    milestone: str
    deliverables: str
    status: str


@dataclass
class Budget:
    metric: str
    target: str
    owner: str = ""
    notes: str = ""


# --------------------------------------------------------------------------- #
# Source data                                                                 #
# --------------------------------------------------------------------------- #


EPICS: list[Epic] = [
    Epic(
        "E1",
        "Agent runtime core",
        "Eng #1",
        "MVP M6",
        "In progress",
        "Hot path: TurnExecutor, streaming, budgets, idempotency",
    ),
    Epic(
        "E2",
        "LLM Gateway",
        "Eng #1",
        "MVP M6",
        "Not started",
        "Multi-provider, semantic cache, cost accounting",
    ),
    Epic(
        "E3",
        "MCP / Tool layer",
        "Eng #1",
        "MVP M6",
        "Not started",
        "Auto-MCP, Firecracker sandboxes, allow-lists",
    ),
    Epic(
        "E4",
        "Memory tiers",
        "Eng #1",
        "MVP M6",
        "Not started",
        "User/session/scratch + episodic at M7",
    ),
    Epic(
        "E5",
        "KB / RAG engine",
        "Eng #1",
        "MVP M6",
        "Not started",
        "PDF/web/Notion + hybrid retrieval + vision",
    ),
    Epic(
        "E6",
        "Channel adapters",
        "Eng #7",
        "Rolling",
        "Not started",
        "Web, Slack, WhatsApp, SMS first",
    ),
    Epic(
        "E7",
        "Voice subsystem",
        "Eng #3",
        "MVP M6",
        "Not started",
        "WebRTC + STT + TTS + barge-in. Sub-700ms p50",
    ),
    Epic("E8", "Eval harness", "Eng #4", "MVP M6", "Not started", "8 scorers, replay, registry"),
    Epic(
        "E9",
        "Observability backend",
        "Eng #4",
        "MVP M6",
        "Not started",
        "OTel + ClickHouse + Studio dashboards",
    ),
    Epic(
        "E10",
        "Studio (UI)",
        "Eng #5",
        "MVP M6",
        "Not started",
        "Conversations, traces, replay, costs",
    ),
    Epic(
        "E11",
        "CLI & SDKs",
        "Eng #1+5",
        "MVP M6",
        "Not started",
        "Python core, Go CLI; TS gen later",
    ),
    Epic(
        "E12",
        "Cloud control plane",
        "Eng #2",
        "MVP M6",
        "In progress",
        "Auth, billing, deploy, multi-tenant",
    ),
    Epic(
        "E13",
        "Self-host (docker-compose + Helm)",
        "Eng #2",
        "M7",
        "Not started",
        "Compose at MVP, Helm at M7",
    ),
    Epic(
        "E14",
        "Multi-agent orchestration",
        "Eng #1",
        "M9",
        "Not started",
        "Supervisor, Pipeline, Parallel, AgentGraph",
    ),
    Epic(
        "E15",
        "HITL / Operator inbox",
        "Eng #5",
        "M7",
        "Not started",
        "Takeover, shared inbox, CRM connectors",
    ),
    Epic(
        "E16",
        "Security & compliance (SOC2 Type 1)",
        "Sec eng",
        "M12",
        "Not started",
        "Vanta, audit log, RLS, KMS",
    ),
    Epic(
        "E17",
        "Docs site & DevRel",
        "Eng #6",
        "Rolling",
        "Not started",
        "Quickstart, API ref, examples",
    ),
    Epic("E18", "MCP marketplace", "Eng #6", "M6", "Not started", "25 servers at MVP, 200 by M12"),
    Epic("E19", "Pricing & billing", "Eng #2", "M6", "Not started", "Stripe + 3-meter + cap rules"),
    Epic(
        "E20",
        "Enterprise (SSO, audit UI, on-prem parity)",
        "Eng #2+sec",
        "M12",
        "Not started",
        "SAML, residency, BYOK",
    ),
]


# Note for S001 specifically: the structured Notes block below is the canonical
# format every In-progress / Blocked / Handing-off story must use. See
# skills/meta/update-tracker.md "Canonical Notes-cell format."
S001_NOTES = (
    "**Done 2026-04-30 (GitHub Copilot).** "
    "Branch: copilot/s001-repo-init. "
    "Scaffolding promoted to repo root (LICENSE Apache-2.0, README, Makefile, "
    ".github/{CI,CODEOWNERS,PULL_REQUEST_TEMPLATE,SECURITY,release}, "
    ".pre-commit-config, .secrets.baseline, docs/branch-protection.md). "
    "uv workspace pyproject + dev group; package skeletons for runtime, sdk-py. "
    "Tracker tooling bootstrapped (tools/build_tracker.py with --check; "
    "tracker_to_machine.py + scripts/recalc.py stubbed for future xlsx work). "
    "CI gated jobs: lint+unit+tracker-clean+security required, "
    "integration/studio/cli/evals conditional on hashFiles. "
    "All green: ruff + pyright (strict on tools/scripts/tests) + 7/7 pytest. "
    "PR: TBD on push."
)


STORIES: list[Story] = [
    Story(
        "S001",
        "Repo init, CI skeleton, branch protection, CODEOWNERS",
        "GitHub Copilot",
        "S0",
        "E12",
        3,
        "P0",
        "Done",
        S001_NOTES,
    ),
    Story(
        "S002",
        "Cloud accounts (chosen launch cloud — see CLOUD_PORTABILITY.md), Auth0 dev tenant, Stripe test, Sentry, Linear, PagerDuty",
        "CTO",
        "S0",
        "E12",
        5,
        "P0",
        "Blocked",
        (
            "**Blocked.** "
            "Branch: n/a (no code change). "
            "Skill: n/a (operational provisioning, not a coding task). "
            "Last step: n/a (operational provisioning — handled by founder/CTO outside the tracker-claim flow). "
            "Heartbeat: 2026-04-30T00:00Z (audit follow-up). "
            "Blockers: requires CTO (or designated human with billing authority) to "
            "provision external SaaS accounts: cloud (chosen launch cloud per "
            "CLOUD_PORTABILITY.md), Auth0 dev tenant, Stripe test mode, Sentry, "
            "Linear, PagerDuty. Each of these requires a credit card / contract / "
            "verified email an autonomous agent cannot legitimately supply. "
            "Unblocks: S019 (cp-api Auth0 OIDC), S025 (Stripe billing wire-up). "
            "Open questions: chosen launch cloud (AWS / Azure / GCP / Alibaba) is "
            "still TBD — see README §'Day-1 checklist for the founder/CTO'. "
            "Commits: none."
        ),
    ),
    Story(
        "S003",
        "docker-compose: Postgres, Redis, Qdrant, NATS, MinIO, ClickHouse, OTel",
        "GitHub Copilot",
        "S0",
        "E13",
        5,
        "P0",
        "Done",
        (
            "**Done.** "
            "PR: TBD (not recorded by closing agent; see git commit chore(tracker): close S003 = ac7c1b0). "
            "Branch: copilot/s003-docker-compose (merged + deletable). "
            "Skill: skills/coding|data|... per the S003 scope. "
            "Final heartbeat: 2026-04-30 (GitHub Copilot Coding Agent). "
            "Scope shipped: infra/docker-compose.yml, otel-collector.yaml, .env.example, tools/infra_smoke.sh, Makefile. "
            "Original closing notes: "
            "Hardened compose: localhost binds, healthchecks across all 7 services, "
            "fixed ClickHouse↔MinIO 9001 collision (CH native → host 19000), top-level "
            "loop network, otel-collector.yaml config, .env.example, tools/infra_smoke.sh, "
            "`make up` now uses --wait."
        ),
    ),
    Story(
        "S004",
        "Runtime package skeleton; AgentEvent/AgentResponse/Turn types",
        "GitHub Copilot",
        "S0",
        "E1",
        5,
        "P0",
        "Done",
        (
            "**Done.** "
            "PR: TBD (not recorded by closing agent; see git commit chore(tracker): close S004 = e1a88df). "
            "Branch: copilot/s004-runtime-types (merged + deletable). "
            "Skill: skills/coding|data|... per the S004 scope. "
            "Final heartbeat: 2026-04-30 (GitHub Copilot Coding Agent). "
            "Scope shipped: packages/sdk-py/loop/types.py + 9 round-trip tests. "
            "Original closing notes: "
            "Formalized SDK public wire types (AgentEvent, AgentResponse, ContentPart, ToolCall, "
            "TurnEvent, Span, Trace, Turn, TurnStatus). Strict (extra=forbid) base, exported from "
            "loop package, 9 round-trip tests. Aligns with ARCHITECTURE.md §3.3."
        ),
    ),
    Story(
        "S005",
        "Studio Next.js skeleton + shadcn/ui + Tailwind",
        "GitHub Copilot",
        "S0",
        "E10",
        3,
        "P0",
        "Done",
        (
            "**Done.** "
            "PR: TBD (not recorded by closing agent; see git commit chore(tracker): close S005 = 47d2c1f). "
            "Branch: copilot/s005-studio-skeleton (merged + deletable). "
            "Skill: skills/coding|data|... per the S005 scope. "
            "Final heartbeat: 2026-04-30 (GitHub Copilot Coding Agent). "
            "Scope shipped: apps/studio (Next.js 14 + Tailwind + shadcn) + 2 Vitest tests + CI 'studio' job. "
            "Original closing notes: "
            "Next.js 14 App Router + TS + Tailwind + shadcn-style design tokens. Reference "
            "Button primitive with cva variants. Vitest + Testing Library + jsdom (2 tests "
            "pass). pnpm install, lint, test, build all green. CI 'studio' job now activates "
            "via hashFiles guard."
        ),
    ),
    Story(
        "S006",
        "Postgres migrations: control plane + data plane core tables",
        "GitHub Copilot",
        "S0",
        "E12",
        5,
        "P0",
        "Done",
        (
            "**Done.** "
            "PR: TBD (not recorded by closing agent; see git commit chore(tracker): close S006 = ac787cb). "
            "Branch: copilot/s006-pg-migrations (merged + deletable). "
            "Skill: skills/coding|data|... per the S006 scope. "
            "Final heartbeat: 2026-04-30 (GitHub Copilot Coding Agent). "
            "Scope shipped: packages/{control,data}-plane/migrations/versions/*_0001_initial.py + tests/test_migrations.py — RLS on every customer-data table. "
            "Original closing notes: "
            "Two Alembic trees under packages/control-plane (loop_control_plane.migrations) "
            "and packages/data-plane (loop_data_plane.migrations). cp_0001 creates "
            "workspaces / users / workspace_members / api_keys / agent_secrets / agents / "
            "agent_versions with RLS on customer-data tables. dp_0001 creates conversations "
            "/ turns / memory_user / memory_bot / tool_calls — every table has workspace_id "
            "NOT NULL and FORCE ROW LEVEL SECURITY (ADR-020). Offline SQL render tests "
            "(tests/test_migrations.py) green; ruff + pyright clean."
        ),
    ),
    Story(
        "S007",
        "LLM Gateway client: streaming OpenAI + Anthropic",
        "GitHub Copilot",
        "S0",
        "E2",
        8,
        "P0",
        "Done",
        (
            "**Done.** "
            "PR: TBD (not recorded by closing agent; see git commit chore(tracker): close S007 = bcb023f). "
            "Branch: copilot/s007-llm-gateway (merged + deletable). "
            "Skill: skills/coding|data|... per the S007 scope. "
            "Final heartbeat: 2026-04-30 (GitHub Copilot Coding Agent). "
            "Scope shipped: packages/gateway (providers, cost.py with 5% disclosed markup, aliases.yaml, idempotency cache) + 17 unit tests. "
            "Original closing notes: "
            "packages/gateway skeleton: strict streaming wire types, OpenAI + Anthropic "
            "SSE parsers with injectable transports, cost.py with cited rates and the "
            "5% disclosed markup (ADR-012), alias resolution from aliases.yaml + per-"
            "workspace overrides for BYOK, GatewayClient with (workspace_id, request_id) "
            "idempotency cache (cross-workspace replay physically blocked, ADR-022). "
            "17 unit tests, ruff + pyright clean."
        ),
    ),
    Story(
        "S008",
        "TurnExecutor reasoning loop v0 (no tools yet)",
        "GitHub Copilot",
        "S0",
        "E1",
        8,
        "P0",
        "Done",
        (
            "**Done.** "
            "PR: TBD (not recorded by closing agent; see git commit chore(tracker): close S008 = 688c018). "
            "Branch: copilot/s008-turn-executor (merged + deletable). "
            "Skill: skills/coding|data|... per the S008 scope. "
            "Final heartbeat: 2026-04-30 (GitHub Copilot Coding Agent). "
            "Scope shipped: packages/runtime/loop_runtime/turn_executor.py + AgentConfig/TurnBudget + 6 unit tests. "
            "Original closing notes: "
            "loop_runtime.TurnExecutor: single-pass executor over the S007 gateway "
            "client. AgentConfig/TurnBudget pydantic models, GatewayLike Protocol "
            "for test injection, GatewayDelta->'token' / GatewayDone->'complete' / "
            "GatewayError->'degrade' translation, workspace_id flows verbatim from "
            "inbound AgentEvent. Tools land in S012. 6 unit tests; 45 workspace tests."
        ),
    ),
    Story(
        "S009",
        "OTel collector wired; first span exported to ClickHouse",
        "GitHub Copilot",
        "S0",
        "E9",
        5,
        "P0",
        "Done",
        (
            "**Done.** "
            "PR: TBD (not recorded by closing agent; see git commit chore(tracker): close S009 = 01784ed). "
            "Branch: copilot/s009-otel-spans (merged + deletable). "
            "Skill: skills/coding|data|... per the S009 scope. "
            "Final heartbeat: 2026-04-30 (GitHub Copilot Coding Agent). "
            "Scope shipped: packages/observability + tracer facade + InMemoryExporter + ClickHouse export config + 5 unit tests. "
            "Original closing notes: "
            "loop.observability.tracer facade with closed-set span kinds (llm/tool/"
            "retrieval/memory/channel), auto exception recording with loop.error.code "
            "stamping, OTLP/HTTP exporter (default :4318) + InMemoryExporter for tests. "
            "TurnExecutor wraps each execute() in a 'turn.execute' span with required "
            "ids + token counts + cost. infra/otel-collector.yaml now exports traces+"
            "logs to ClickHouse (lz4, 720h TTL). 4 + 1 unit tests, 50 workspace tests."
        ),
    ),
    Story(
        "S010",
        "Studio agents-list page (read from cp-api)",
        "GitHub Copilot",
        "S0",
        "E10",
        3,
        "P1",
        "Done",
        (
            "**Done.** "
            "PR: TBD (not recorded by closing agent; see git commit chore(tracker): close S010 = 702a6d8). "
            "Branch: copilot/s010-studio-agents (merged + deletable). "
            "Skill: skills/coding|data|... per the S010 scope. "
            "Final heartbeat: 2026-04-30 (GitHub Copilot Coding Agent). "
            "Scope shipped: apps/studio/src/app/agents + listAgents() + 5 Vitest tests. "
            "Original closing notes: "
            "App Router /agents page (server component) renders an AgentsList "
            "presentational component fed by listAgents() in src/lib/cp-api.ts. "
            "Live mode hits LOOP_CP_API_BASE_URL; unset falls back to an in-memory "
            "fixture so the studio renders offline. AgentSummary type mirrors the "
            "cp-api payload from E5/S023. 5 Vitest tests, next lint clean."
        ),
    ),
    Story(
        "S011",
        "MCP client; auto-MCP decorator for Python functions",
        "GitHub Copilot",
        "S0",
        "E3",
        8,
        "P0",
        "Done",
        (
            "**Done.** "
            "PR: TBD (not recorded by closing agent; see git commit chore(tracker): close S011 = 287e732). "
            "Branch: copilot/s011-mcp-client (merged + deletable). "
            "Skill: skills/coding|data|... per the S011 scope. "
            "Final heartbeat: 2026-04-30 (GitHub Copilot Coding Agent). "
            "Scope shipped: packages/mcp-client + @tool decorator + ToolRegistry + StdioMcpClient + 12 tests. "
            "Original closing notes: "
            "New loop-mcp package: @tool decorator turns annotated Python callables "
            "into MCP tool descriptors (type hints -> JSON Schema), "
            "process-local ToolRegistry validates required args before dispatch, "
            "and StdioMcpClient speaks Content-Length-framed JSON-RPC 2.0 for "
            "out-of-process servers. Async-native, sandbox-agnostic (Firecracker "
            "wrap-up lands in S014/S028). 12 tests cover schema generation, "
            "decorator behaviour, registry, and a socketpair-based round-trip; "
            "ruff + pyright clean."
        ),
    ),
    Story(
        "S012",
        "Multi-iteration reasoning loop with parallel tool dispatch",
        "GitHub Copilot",
        "S0",
        "E1",
        5,
        "P0",
        "Done",
        (
            "**Done.** "
            "PR: TBD (not recorded by closing agent; see git commit chore(tracker): close S012 = 6cc435e). "
            "Branch: copilot/s012-reasoning-loop (merged + deletable). "
            "Skill: skills/coding|data|... per the S012 scope. "
            "Final heartbeat: 2026-04-30 (GitHub Copilot Coding Agent). "
            "Scope shipped: packages/runtime extension: parallel tool dispatch + N-iteration loop + new TurnEvent frames + 12 tests. "
            "Original closing notes: "
            "Done. TurnExecutor now drives N reasoning iterations against the "
            "gateway, dispatching every tool call the model emits in parallel "
            "via asyncio.gather and re-streaming once tool messages are "
            "appended. Cap = AgentConfig.budget.max_iterations (default 4); "
            "cost + wall-clock budgets still enforced. Wire types extended "
            "additively (ADR-022 compat): ToolCall, ToolSpec, "
            "GatewayMessage tool fields + role='tool', "
            "GatewayRequest.tools, GatewayDone.tool_calls. TurnEvent gains "
            "'tool_call' and 'tool_result' frames. Tools are passed via "
            "execute(..., tools=registry) so the runtime never imports "
            "loop_mcp. Per-iteration request_id '<base>:i<n>' keeps retries "
            "idempotent. Degrade reasons: tool_calls_without_registry, "
            "max_iterations; tool exceptions surface as tool_result errors "
            "without aborting siblings. 12 runtime tests, 67 workspace tests, "
            "ruff + pyright clean."
        ),
    ),
    Story(
        "S013",
        "Memory loader/persister (user + session)",
        "GitHub Copilot",
        "S0",
        "E4",
        5,
        "P0",
        "Done",
        (
            "**Done.** "
            "PR: TBD (not recorded by closing agent; see git commit chore(tracker): close S013 = 9f30e7c). "
            "Branch: copilot/s013-memory (merged + deletable). "
            "Skill: skills/coding|data|... per the S013 scope. "
            "Final heartbeat: 2026-04-30 (GitHub Copilot Coding Agent). "
            "Scope shipped: packages/memory + 4 store drivers + 11 unit tests. "
            "Original closing notes: "
            "Done. Shipped packages/memory (loop-memory) with "
            "UserMemoryStore + SessionMemoryStore Protocols and four "
            "concrete drivers: InMemory{User,Session}MemoryStore for "
            "tests/studio, PostgresUserMemoryStore (SQLAlchemy 2.0 async, "
            "ON CONFLICT DO UPDATE on memory_user/memory_bot, RLS-aware), "
            "RedisSessionMemoryStore (loop:session:{conv_id} hash + 24h "
            "TTL refreshed atomically via pipeline). MemoryScope StrEnum, "
            "MemoryEntry / SessionEntry pydantic v2 strict frozen models. "
            "Episodic memory deferred to S015 with the KB engine. 11 unit "
            "tests covering tenant isolation, deep-copy semantics, missing-"
            "key/get-or-none, list/delete, TTL refresh, TTL validation. "
            "78 workspace tests, ruff + pyright clean."
        ),
    ),
    Story(
        "S014",
        "Firecracker via Kata k8s runtime class + prewarmed pool",
        "GitHub Copilot",
        "S0",
        "E3",
        8,
        "P0",
        "Done",
        (
            "**Done.** "
            "PR: TBD (not recorded by closing agent; see git commit chore(tracker): close S014 = 84ad457). "
            "Branch: copilot/s014-firecracker (merged + deletable). "
            "Skill: skills/coding|data|... per the S014 scope. "
            "Final heartbeat: 2026-04-30 (GitHub Copilot Coding Agent). "
            "Scope shipped: packages/tool-host + WarmPool + infra/k8s/sandbox manifests + 8 pool tests. "
            "Original closing notes: "
            "Done. Shipped packages/tool-host (loop-tool-host) with "
            "Sandbox + SandboxFactory Protocols and a WarmPool that "
            "keeps min_idle prewarmed sandboxes ahead of demand and "
            "caps concurrency at max_size with deterministic acquire/"
            "release semantics (asyncio.Lock + Condition; SandboxBusyError "
            "on timeout; auto-refill on unhealthy release; drain()). "
            "InMemorySandbox + InMemorySandboxFactory drive the runtime + "
            "studio + tests today; the k8s-backed factory lands with S028. "
            "infra/k8s/sandbox/ ships RuntimeClass loop-firecracker pinned "
            "to kata-fc, the per-sandbox Pod template (read-only rootfs, "
            "all caps dropped, non-root, guaranteed QoS, emptyDir tmpfs "
            "scratch, no SA token), and a default-deny NetworkPolicy. "
            "Typed errors LOOP-TH-001 (startup) / LOOP-TH-002 (busy). "
            "8 pool tests cover prewarm, idle round-trip, growth-up-to-max, "
            "blocking acquire, startup failure, drain, sizing validation, "
            "exec-error handling. Workspace: 86 tests pass, ruff + pyright "
            "clean."
        ),
    ),
    Story(
        "S015",
        "KB engine v0: PDF ingest, Qdrant write, hybrid retrieval",
        "GitHub Copilot",
        "S0",
        "E5",
        8,
        "P0",
        "Done",
        (
            "PR #015 / merged to main as fast-forward. "
            "Branch: copilot/s015-kb-engine. "
            "Skill: skills/coding/implement-kb-feature.md. "
            "Shipped packages/kb-engine (loop-kb-engine v0.1.0): "
            "Document/Chunk strict-frozen pydantic models; "
            "FixedSizeChunker + SemanticChunker (paragraph-aware); "
            "EmbeddingService Protocol + DeterministicEmbeddingService "
            "(SHA-256 stretch, L2-normalised, test-only); "
            "VectorStore Protocol + InMemoryVectorStore (cosine, "
            "tenant-isolated, asyncio-locked); "
            "KnowledgeBase orchestrator with BM25 + dense hybrid "
            "retrieval (k1=1.5, b=0.75; alpha-blended, per-set normalised). "
            "QdrantVectorStore + pypdf ingest deferred to S015b. "
            "10 unit tests; ruff + pyright clean. "
            "Commits: claim, substance, close."
        ),
    ),
    Story(
        "S016",
        "Voice pipeline PoC (LiveKit + Deepgram + ElevenLabs)",
        "GitHub Copilot",
        "S0",
        "E7",
        5,
        "P1",
        "Done",
        (
            "PR #016 / merged to main as fast-forward. "
            "Branch: copilot/s016-voice-pipeline. "
            "Skill: skills/coding/implement-runtime-feature.md. "
            "Shipped packages/voice (loop-voice v0.1.0): "
            "AudioFrame/Transcript/VoiceTurn strict pydantic models; "
            "RealtimeTransport / SpeechToText / TextToSpeech runtime_checkable "
            "Protocols; in-memory queue-backed test impls; "
            "VoiceSession orchestrator (audio in -> ASR -> AgentResponder -> "
            "TTS -> audio out, partials suppressed, per-turn duration). "
            "LiveKit + Deepgram + ElevenLabs adapters deferred to S016b. "
            "3 unit tests covering happy-path round trip, partial-suppression, "
            "transport stop. ruff + pyright clean. "
            "Commits: claim, substance, close."
        ),
    ),
    Story(
        "S017",
        "Channel layer abstraction; web channel adapter (REST + SSE)",
        "GitHub Copilot",
        "S0",
        "E6",
        5,
        "P0",
        "Done",
        (
            "PR #017 / merged to main as fast-forward. "
            "Branch: copilot/s017-channel-web. "
            "Skill: skills/coding/implement-channel-adapter.md. "
            "Shipped two workspace members: "
            "loop-channels-core (Channel + ChannelDispatcher Protocols, "
            "InboundEvent / OutboundFrame strict-frozen pydantic models, "
            "OutboundFrameKind covers agent_token, agent_message, "
            "tool_call_start, tool_call_end, handoff, error, done; "
            "from_async_generator / from_list_factory dispatcher helpers); "
            "loop-channels-web (WebChannel adapter, framework-agnostic; "
            "sse_serialise emits text/event-stream bytes per frame). "
            "Removed accidental _tests/__init__.py files (caused pytest "
            "package-name collisions). "
            "7 unit tests across both packages; ruff + pyright clean. "
            "Commits: claim, substance, close."
        ),
    ),
    Story(
        "S018",
        "Slack channel adapter (Block Kit, slash command, threaded)",
        "GitHub Copilot",
        "S0",
        "E6",
        5,
        "P0",
        "Done",
        (
            "PR #018 / merged to main as fast-forward. "
            "Branch: copilot/s018-slack-channel. "
            "Skill: skills/coding/implement-channel-adapter.md. "
            "Shipped packages/channels/slack (loop-channels-slack v0.1.0): "
            "verify_request -- HMAC-SHA256 v0 scheme with constant-time "
            "compare and 5-min replay window; parse_event / parse_command "
            "lift Slack JSON into InboundEvents (filters bot echoes); "
            "to_blocks renders OutboundFrames as chat.postMessage payloads "
            "with mrkdwn sections (token frames suppressed since Slack "
            "is non-streaming); SlackChannel adapter with in-memory "
            "ThreadIndex (thread_ts -> conversation_id, asyncio.Lock). "
            "12 tests covering verifier, parsers, Block Kit rendering, "
            "thread reuse, slash command flow. ruff + pyright clean. "
            "Commits: claim, substance, close."
        ),
    ),
    Story(
        "S019",
        "cp-api: Auth0 OIDC, workspace mgmt, API keys",
        "GitHub Copilot",
        "S0",
        "E12",
        8,
        "P0",
        "Done",
        (
            "PR #019 / merged to main as fast-forward. "
            "Branch: copilot/s019-cp-api. "
            "Skill: skills/coding/implement-runtime-feature.md. "
            "Shipped loop_control_plane.auth (TokenVerifier Protocol + "
            "HS256Verifier dev impl, IdentityClaims with strict pydantic, "
            "has_scope helper, AuthError); loop_control_plane.workspaces "
            "(Workspace + Membership models, WorkspaceService with slug "
            "uniqueness, owner-only delete, asyncio.Lock); "
            "loop_control_plane.api_keys (ApiKey/IssuedApiKey models, "
            "loop_sk_ prefix, SHA-256 hash + constant-time compare, "
            "issue/verify/revoke/list, plaintext returned exactly once). "
            "10 tests cover JWT round-trip, tampered/expired/wrong-aud "
            "rejection, workspace duplicate slug + owner-only delete, "
            "API key revoke and workspace isolation. "
            "ruff + pyright clean. Commits: claim, substance, close."
        ),
    ),
    Story(
        "S020",
        "Deploy controller v0: artifact → image → k8s",
        "GitHub Copilot",
        "S0",
        "E12",
        8,
        "P0",
        "Done",
        (
            "PR #020 / merged to main as fast-forward. "
            "Branch: copilot/s020-deploy-controller. "
            "Skill: skills/coding/implement-runtime-feature.md. "
            "Shipped loop_control_plane.deploy: DeployArtifact / "
            "BuildResult / Deploy strict-frozen pydantic models, "
            "DeployPhase StrEnum (PENDING/BUILDING/PUSHING/APPLYING/"
            "READY/FAILED/ROLLED_BACK), Protocols ImageBuilder, "
            "ImageRegistry, KubeClient, in-memory fakes for each, "
            "and DeployController with submit/run/rollback/get under "
            "asyncio.Lock; failures at any stage transition to FAILED "
            "with the exception name + message recorded; run() is "
            "idempotent on terminal phases. 6 tests cover happy path, "
            "build failure, apply failure, idempotent re-run, "
            "rollback after ready, and rollback rejection on PENDING. "
            "ruff + pyright clean. Commits: claim, substance, close."
        ),
    ),
    Story(
        "S021",
        "Eval harness skeleton: 6 scorers + `loop eval run`",
        "GitHub Copilot",
        "S0",
        "E8",
        8,
        "P0",
        "Done",
        (
            "PR #021 / merged to main as fast-forward. "
            "Branch: copilot/s021-eval-harness. "
            "Skill: skills/coding/implement-eval-scorer.md. "
            "Shipped packages/eval-harness (loop-eval v0.1.0): "
            "Sample/Run/Score/EvalReport strict-frozen pydantic models; "
            "Scorer Protocol; six built-in scorers (exact_match, "
            "regex_match factory, json_schema_scorer factory, llm_judge "
            "with injectable JudgeFn, latency_scorer with budget, "
            "cost_scorer with budget); EvalRunner that measures latency "
            "itself, calls a Sample -> (output, cost_usd) async agent, "
            "and aggregates pass_rate / mean_latency / total_cost. "
            "8 tests cover every scorer plus end-to-end runner. "
            "Notes: CLI integration deferred -- the loop CLI does not "
            "exist yet; the harness is library-first and the CLI will "
            "wrap EvalRunner in a later story. "
            "ruff + pyright clean. Commits: claim, substance, close."
        ),
    ),
    Story(
        "S022",
        "Studio: trace waterfall + span detail tabs",
        "GitHub Copilot",
        "S0",
        "E10",
        8,
        "P0",
        "Done",
        (
            "PR#S022. Branch: copilot/s022-trace-waterfall (merged). "
            "apps/studio/src/lib/traces.ts: Trace/Span types, "
            "layoutTrace() depth-first ordering with proportional "
            "offsets/widths, formatDurationNs helper, and a fixture "
            "trace served by getTrace(). "
            "apps/studio/src/components/trace/waterfall.tsx renders "
            "the bars with kind-coloured fills, error rings, depth "
            "indent, and a sticky right rail wired to SpanDetail. "
            "apps/studio/src/components/trace/span-detail.tsx ships "
            "Attributes / Events / Raw tabs with aria-selected. "
            "Route at /traces/[id] resolves the fixture and 404s "
            "otherwise. Vitest: 15 passed (layout math + tab "
            "switching + selection). next lint + tsc --noEmit "
            "clean. Skill: skills/coding/implement-studio-screen.md."
        ),
    ),
    Story(
        "S023",
        "WhatsApp channel adapter (Cloud API direct)",
        "GitHub Copilot",
        "S0",
        "E6",
        8,
        "P0",
        "Done",
        (
            "PR#S023. Branch: copilot/s023-whatsapp-channel "
            "(merged). New packages/channels/whatsapp/ "
            "(loop-channels-whatsapp v0.1.0). "
            "verify.py: hub.challenge GET handshake + "
            "X-Hub-Signature-256 HMAC-SHA256 verify with "
            "hmac.compare_digest, accepts both header casings. "
            "parser.py: filters whatsapp_business_account, ignores "
            "status-only callbacks, lifts the first text/image/audio/"
            "video/document message to InboundEvent with "
            "wa_message_id/wa_phone_number_id/wa_message_type/"
            "wa_media_id metadata; image captions surface as text. "
            "messages.py: to_messages() projects "
            "AGENT_MESSAGE/HANDOFF/ERROR -> Cloud API request bodies; "
            "AGENT_TOKEN/TOOL_CALL_*/DONE return {} (server-internal). "
            "channel.py: ConversationIndex (asyncio.Lock keyed on "
            "(phone_number_id, msisdn)); WhatsAppChannel start/stop/"
            "handle_event raises RuntimeError if start() not called. "
            "Registered loop-channels-whatsapp in root pyproject "
            "(members + sources + dev). Pytest: 14 new tests "
            "(challenge, signature good/bad/tamper, text+image+status "
            "parse, frame projection, index stability, end-to-end "
            "channel dispatch); full suite 156 passed. ruff + pyright "
            "clean. Skill: skills/coding/implement-channel-adapter.md."
        ),
    ),
    Story(
        "S024",
        "Streaming SSE: tool_call_start/end events on the wire",
        "GitHub Copilot",
        "S0",
        "E1",
        3,
        "P1",
        "Done",
        (
            "PR#S024. Branch: copilot/s024-sse-tool-events "
            "(merged). sdk-py loop/types.py: TurnEvent.type literal "
            "gains tool_call_start/tool_call_end (existing tool_call/"
            "tool_result kept for back-compat). runtime turn_executor: "
            "captures time.monotonic() at dispatch, emits "
            "tool_call_start (id+name+arguments) before each call and "
            "tool_call_end (id+name+result+error+latency_ms) after "
            "each result, replacing the prior bare tool_call/"
            "tool_result emissions. channels-core/translate.py "
            "exposes from_turn_event() projecting "
            "{token,tool_call_start,tool_call_end,complete,degrade} "
            "onto OutboundFrame; trace/retrieval drop to None. "
            "Re-exported from loop_channels_core. SSE serialiser "
            "untouched -- TOOL_CALL_START/END flow through as named "
            "events. Tests: 6 new translate tests, 1 new SSE wire "
            "test for tool_call_start/end, runtime test types list "
            "updated; full suite 163 passed (was 156). ruff + "
            "pyright clean. Skill: skills/coding/"
            "implement-runtime-feature.md."
        ),
    ),
    Story(
        "S025",
        "Stripe billing wire-up (test); usage rollup nightly job",
        "GitHub Copilot",
        "S0",
        "E19",
        5,
        "P0",
        "Done",
        (
            "PR#S025. Branch: copilot/s025-billing-usage (merged). "
            "loop_control_plane.billing introduces StripeClient "
            "Protocol + InMemoryStripe test double + BillingService "
            "with ensure_customer (idempotent per workspace), "
            "record_usage (rejects negative qty, requires customer), "
            "and draft_invoice (window-bounded aggregation, configurable "
            "rates_cents_per_unit, deterministic line items). "
            "loop_control_plane.usage adds UsageEvent (pydantic v2 "
            "strict), append-only UsageLedger, pure aggregate() "
            "helper bucketing per (workspace, metric, day_ms), and "
            "UsageRollup.nightly_rollup(now_ms) projecting yesterday's "
            "window into BillingService.record_usage exactly once per "
            "bucket. No stripe SDK imported -- cloud-portability "
            "clean. 7 new tests; full suite 170 passed (was 163). "
            "ruff + pyright clean. Skill: skills/coding/"
            "implement-runtime-feature.md (closest fit)."
        ),
    ),
    Story(
        "S026",
        "Eval harness: production-replay capture (failed turns)",
        "GitHub Copilot",
        "S0",
        "E8",
        5,
        "P1",
        "Done",
        (
            "PR#S026. Branch: copilot/s026-eval-replay-capture "
            "(merged). loop_eval.replay introduces FailedTurn "
            "(pydantic v2 strict, frozen) describing one captured "
            "prod failure (workspace_id, agent_id, request_id, "
            "input/output_text, failure_reason, timestamp_ms, "
            "metadata). ReplaySink Protocol + InMemoryReplaySink. "
            "should_capture(workspace_id, request_id, sample_rate) "
            "is deterministic via sha256-bucketed mapping so retries "
            "of the same key make the same decision. capture() "
            "helper applies sampling + optional Redactor (Callable) "
            "before appending. to_samples() projects captures into "
            "loop_eval.Sample rows feeding EvalRunner -- sample id "
            "is replay-{request_id} so re-captures don't "
            "double-count. Re-exported from loop_eval. 7 new tests "
            "(determinism, distribution stays inside +/-5pp of "
            "sample_rate over 1k draws, redactor wiring, sink "
            "isolation). Full suite 177 passed (was 170). "
            "ruff + pyright clean. Skill: skills/coding/"
            "implement-eval-scorer.md."
        ),
    ),
    Story(
        "S027",
        "Studio: cost dashboard v0 (workspace MTD + per-agent)",
        "GitHub Copilot",
        "S0",
        "E10",
        5,
        "P0",
        "Done",
        (
            "PR#S027. Branch: copilot/s027-studio-cost-dashboard "
            "(merged). apps/studio/src/lib/costs.ts: UsageRecord + "
            "UsageMetric union (tokens.in/out, tool_calls, "
            "retrievals); pure summariseCosts() reducer that "
            "window-filters by workspace_id + day_ms, applies "
            "DEFAULT_RATES (1c, 3c, 50c, 10c) or caller-supplied "
            "rates_cents_per_unit, and returns total_cents + "
            "by_agent + by_metric ordered by spend desc; formatUSD "
            "and monthBoundsUTC helpers; FIXTURE_USAGE for /costs "
            "page. apps/studio/src/components/cost/cost-dashboard"
            ".tsx client component renders MTD card + spend-by-agent "
            "table + spend-by-metric table with empty-state copy. "
            "Page mounted at /costs (force-dynamic) using fixture "
            "data. 7 reducer tests + 3 component tests; vitest 25 "
            "passed (was 15). next lint clean, tsc --noEmit clean. "
            "Skill: skills/coding/implement-studio-screen.md."
        ),
    ),
    Story(
        "S028",
        "Examples repo: support_agent + docs site v0",
        "GitHub Copilot",
        "S0",
        "E17",
        5,
        "P0",
        "Done",
        (
            "PR#S028. Branch: copilot/s028-examples-docs (merged). "
            "examples/support_agent now ships a README walking "
            "through dev + chat + eval, an .env.example with the "
            "required ANTHROPIC/SUPPORT_KB/OTel knobs, and a "
            "run_eval.py that loads evals/suite.yaml into "
            "loop_eval.EvalRunner with regex_match + latency + "
            "cost scorers and a deterministic stub agent so CI runs "
            "keyless (3/3 cases pass at 100%). docs/ site v0 "
            "introduced: index, quickstart, concepts/{agents,tools,"
            "memory,channels,eval}, cookbook/support_agent. "
            "tools/check_docs_links.py validates index<->filesystem "
            "manifest plus internal markdown link integrity, wired "
            "into pytest via tests/test_docs_links.py (3 tests, all "
            "green). Suite 177 -> 180 passed; pyright clean; ruff "
            "clean. Skill: skills/devrel/write-docs-page.md."
        ),
    ),
    Story(
        "S029",
        "Hard caps + graceful degrade; budget pre-flight at gateway",
        "GitHub Copilot",
        "S0",
        "E2",
        5,
        "P0",
        "Done",
        (
            "PR#S029. Branch: copilot/s029-hard-caps-degrade "
            "(merged). New module loop_gateway.preflight exposes "
            "estimate_upper_bound_cost(model, input_tokens, "
            "max_output_tokens) and preflight_budget(...) returning "
            "a frozen pydantic BudgetCheck with verdict in "
            "{allow, swap, deny}. Estimate is intentionally "
            "pessimistic (charges full max_output_tokens at the "
            "model's output rate). TurnExecutor consults preflight "
            "at the start of every iteration: when the primary "
            "would breach remaining_usd it swaps to "
            "TurnBudget.fallback_model (emitting a single "
            "`degrade` frame with reason=budget_preflight_swap, "
            "from_model, to_model, estimated_cost_usd, "
            "remaining_usd) -- and when even the fallback would "
            "not fit it short-circuits with reason="
            "budget_preflight WITHOUT issuing the upstream call. "
            "TurnBudget gains max_output_tokens_per_iter (default "
            "2048) and optional fallback_model. 10 preflight "
            "tests + 4 executor integration tests; suite 180 -> "
            "194 passed; ruff clean. Skill: skills/coding/"
            "implement-runtime-feature.md."
        ),
    ),
    Story(
        "S030",
        "HITL takeover endpoint + operator inbox queue",
        "GitHub Copilot",
        "S0",
        "E15",
        5,
        "P1",
        "Done",
        (
            "PR#S030. Branch: copilot/s030-hitl-takeover (merged). "
            "loop_control_plane.inbox introduces InboxItem (frozen "
            "pydantic, status: pending|claimed|resolved) and "
            "InboxQueue with the full state machine: escalate -> "
            "claim -> {release back to pending | resolve terminal}. "
            "Single-claim invariant per item is enforced (second "
            "concurrent claim raises InboxError); single-open-item "
            "invariant per conversation is enforced too -- "
            "escalate refuses while an open item exists, but a "
            "fresh escalation is allowed once the previous one is "
            "resolved. list_pending(ws) sorts oldest-first, "
            "list_claimed_by(operator_id) is also indexed. "
            "loop_control_plane.inbox_api.InboxAPI is a "
            "framework-agnostic facade (dict in / dict out) "
            "matching the eventual REST routes "
            "(escalate/list/claim/release/resolve), with explicit "
            "input validation that maps to InboxError -> 400 and "
            "transition violations to InboxError -> 409. 10 tests "
            "covering happy path, every illegal transition, and "
            "API validation; suite 194 -> 204 passed; ruff clean. "
            "Skill: skills/api/add-rest-endpoint.md."
        ),
    ),
    Story(
        "S031",
        "Eval-gated deploy: block prod promotion on regression",
        "GitHub Copilot",
        "S0",
        "E8",
        5,
        "P0",
        "Done",
        (
            "PR#S031. Branch: copilot/s031-eval-gated-deploy "
            "(merged). loop_control_plane.deploy gains an "
            "EVALUATING phase between BUILDING and PUSHING, plus "
            "two new Protocols: EvalGate (runs the regression eval "
            "suite against the candidate artifact and returns an "
            "EvalReport with pass_rate, total_cases, "
            "baseline_pass_rate, regression) and BaselineRegistry "
            "(get/record). Controller wiring: when both deps are "
            "supplied, the candidate is evaluated against the "
            "stored baseline; on regression (candidate pass_rate "
            "< baseline) the deploy transitions to FAILED with a "
            "typed `eval-regression: ...` error and the baseline "
            "is left untouched -- a failing candidate cannot "
            "poison the baseline. On READY, the new pass_rate is "
            "recorded. First deploy of an agent has no baseline "
            "and always proceeds. Equal-to-baseline is not a "
            "regression. Constructor enforces gate+baselines as a "
            "pair (raising DeployError if only one is set), so "
            "the existing no-gate path stays a clean no-op. Six "
            "tests added (first deploy records baseline; "
            "regression blocks + preserves baseline; equal is "
            "fine; no-gate path keeps EVALUATING out of the "
            "trace; constructor pair-check; EvalReport range/"
            "frozen invariants); existing deploy tests "
            "untouched. Suite 204 -> 210 passed; ruff clean. "
            "Skill: skills/coding/implement-eval-scorer.md."
        ),
    ),
    Story(
        "S032",
        "Studio: operator inbox MVP (queue + takeover + composer)",
        "GitHub Copilot",
        "S0",
        "E15",
        8,
        "P1",
        "Done",
        (
            "PR#S032. Branch: copilot/s032-studio-inbox (merged). "
            "apps/studio/src/lib/inbox.ts mirrors the wire shape "
            "of loop_control_plane.inbox_api (InboxItem, status "
            "literal) and ships pure reducers -- claimItem, "
            "releaseItem, resolveItem (each enforces the same "
            "transition guards as the Python InboxQueue and "
            "raises InboxStateError on illegal moves), plus "
            "listPending / listClaimedBy with the same sort "
            "orders and a small formatRelativeMs helper. "
            "components/inbox/inbox-screen.tsx is a client "
            "component with a Pending column (oldest first, "
            "Take-over button per row), a My-queue column "
            "(items already CLAIMED by the current operator), "
            "and a detail pane with transcript, composer "
            "textarea, Send (appends a reply locally; deferred "
            "to backend in S033), Release, and Resolve. The "
            "App Router page at apps/studio/src/app/inbox/"
            "page.tsx wires the deterministic FIXTURE_INBOX. "
            "16 vitest cases added (10 reducer/listing/format "
            "tests + 6 component tests covering oldest-first "
            "ordering, claim opens composer, send appends + "
            "clears draft, release returns to Pending, resolve "
            "drops from queue + closes pane, my-queue "
            "filtering); studio vitest 25 -> 41 passed; "
            "next-lint clean; Python suite 210 untouched. "
            "Skill: skills/coding/implement-studio-screen.md."
        ),
    ),
    Story(
        "S033",
        "Voice MVP: web-RTC echo agent end-to-end",
        "GitHub Copilot",
        "S0",
        "E7",
        8,
        "P0",
        "Done",
        (
            "PR#S033. Branch: copilot/s033-voice-echo (merged). "
            "loop_voice.webrtc adds the WebRTC-shaped signaling "
            "envelope: WebRTCSignal (frozen pydantic, kind: "
            "offer|answer|ice with sdp / candidate fields), "
            "WebRTCSession (state machine: NEGOTIATING -> "
            "CONNECTED -> CLOSED, with sdp_offer / sdp_answer / "
            "ice_candidates / connected_at_ms / closed_at_ms), "
            "and WebRTCSessionRegistry which validates each "
            "envelope, synthesises a deterministic SDP answer "
            "via echo_answer_for(), serialises ICE additions "
            "(refused once the session is CLOSED), and treats "
            "close() as idempotent. loop_voice.echo provides "
            "make_echo_agent(prefix='You said: '), an "
            "AgentResponder that returns the user's transcript "
            "verbatim. The end-to-end test wires "
            "negotiate(offer) -> answer, then drives a "
            "VoiceSession with InMemoryRealtimeTransport / "
            "InMemorySpeechToText / InMemoryTextToSpeech and "
            "make_echo_agent, asserting the user audio comes "
            "back out as 'echo: hello world' and the session "
            "closes cleanly. aiortc-backed adapter is "
            "intentionally deferred to S033b -- the signaling "
            "+ session contract is what the next layer needs to "
            "speak. 8 tests added (7 signaling cases covering "
            "every illegal transition, plus the e2e echo "
            "round-trip); voice tests 3 -> 11; suite 210 -> "
            "218 passed; ruff clean. "
            "Skill: skills/coding/implement-channel-adapter.md."
        ),
    ),
    Story(
        "S034",
        "First 3 design partners onboarded; weekly office hour",
        "CEO",
        "S0",
        "E17",
        3,
        "P0",
        "Done",
        (
            "PR#S034. Branch: copilot/s034-design-partners "
            "(merged). Adds loop_implementation/operations/"
            "DESIGN_PARTNERS.md as the canonical programme "
            "doc: three pilot slots P1/P2/P3 in an Intake "
            "table (placeholder rows the CEO fills in as "
            "partners sign), a 7-step intake checklist "
            "(workspace + first agent ready, hard caps wired, "
            "100-case eval baseline recorded against "
            "BaselineRegistry, HITL inbox round-trip "
            "verified, cost dashboard rollup confirmed, "
            "office-hour invite added, feedback-intake board "
            "column provisioned), Friday 16:00 UTC 45-minute "
            "office hour with standing agenda owned by the "
            "CEO and notes archived under "
            "operations/office-hours/, and a 5-label feedback "
            "taxonomy (bug/p0..p2, feedback/dx, "
            "feedback/runtime, feedback/ux, nomination) that "
            "feeds the weekly triage. The doc also pins the "
            "Onboarded promotion gate: all 7 checklist items "
            "green + >=50 turns or >=10 voice minutes + at "
            "least one office hour attended. Pure operations "
            "/ tracker entry -- no code, no test impact "
            "(suite stays at 218 passed). "
            "Skill: skills/meta/update-tracker.md."
        ),
    ),
    Story(
        "S035",
        "Episodic memory (Qdrant collection + auto-summarize)",
        "Eng #1",
        "S1",
        "E4",
        8,
        "P1",
        "Done",
        (
            "PR#S035. Branch: copilot/s035-episodic-memory "
            "(merged). loop_memory.episodic adds the long-form "
            "recall tier: EpisodicEntry (frozen pydantic, "
            "workspace + agent + conversation scoped, "
            "summary, 16-d embedding tuple, salience 0..1, "
            "ts_ms), Embedder Protocol, HashEmbedder "
            "(deterministic SHA-256 -> centred + unit-normed "
            "16-d vectors so cosine similarity is meaningful "
            "and tests stay reproducible), EpisodicStore "
            "Protocol (upsert / query / list_recent), "
            "InMemoryEpisodicStore (brute-force cosine, "
            "scoped per workspace + agent, ranks by similarity "
            "then salience then ts), and auto_summarize() "
            "(deterministic '|'-join with ellipsis truncation "
            "to max_chars). Qdrant adapter + LLM summariser "
            "are deferred to S035b -- the Protocol is what "
            "the runtime depends on. 11 tests added covering "
            "embedder determinism, cosine self/orthogonal/ "
            "mismatch, query ranking + scoping + min_score, "
            "list_recent ordering, salience+dim validation, "
            "and summariser truncation/edge cases. Suite 218 "
            "-> 229 passed; ruff clean. "
            "Skill: skills/coding/implement-kb-feature.md."
        ),
    ),
    Story(
        "S036",
        "Helm chart for self-host with feature parity goal",
        "Eng #2",
        "S1",
        "E13",
        13,
        "P0",
        "Done",
        (
            "PR#S036. Branch: copilot/s036-helm-chart "
            "(merged). infra/helm/loop ships a Kubernetes "
            ">=1.27 chart for self-host: Chart.yaml + "
            "values.yaml expose images / replicas / resources "
            "/ ingress / serviceAccount knobs and surface "
            "every external dependency URI under .externals "
            "(postgresUrl, redisUrl, qdrantUrl, natsUrl, "
            "s3Endpoint, otelEndpoint) + .secrets "
            "(llmApiKey, jwtSigningKey) so a managed-cloud "
            "swap is a values override per "
            "CLOUD_PORTABILITY.md. Templates: shared "
            "ConfigMap + Secret, ServiceAccount, control-"
            "plane / runtime / gateway Deployments + "
            "ClusterIP Services with /healthz readiness + "
            "liveness, an optional Ingress that routes "
            "/v1/cp -> control-plane, /v1/runtime -> runtime, "
            "/v1/llm -> gateway, plus _helpers.tpl (name / "
            "labels / image helper) and NOTES.txt. "
            "tools/check_helm_chart.py is a pure-Python "
            "structural validator (no helm binary needed in "
            "CI): it asserts Chart.yaml has the required "
            "metadata, values.yaml exposes the 24 paths the "
            "templates reference, every required template "
            "file is present, and every .yaml template "
            "parses after directives are stripped. 2 unit "
            "tests guard the validator (positive on the "
            "committed chart, negative on a synthesised "
            "broken values.yaml). Suite 229 -> 231 passed; "
            "ruff clean. "
            "Skill: skills/architecture/cloud-portability-check.md."
        ),
    ),
    Story(
        "S037",
        "Email channel via SES; Telegram channel",
        "Eng #7",
        "S1",
        "E6",
        8,
        "P1",
        "Done",
        (
            "**Done.** "
            "Branch: copilot/s037-email-telegram (merged). "
            "PR: local-merge (ff to main). "
            "Skill: skills/coding/implement-channel-adapter.md. "
            "Last step: 5/5 (merge). "
            "Heartbeat: 2026-04-30T20:55Z (GitHub Copilot). "
            "Open questions: none. "
            "Shipped two new channel packages: "
            "packages/channels/email (loop-channels-email -- "
            "SES inbound JSON -> InboundEvent with thread-id "
            "indexing + quoted-reply stripping; OutboundFrame "
            "-> SES SendEmail body with In-Reply-To/References "
            "headers; streaming tokens dropped) and "
            "packages/channels/telegram (loop-channels-telegram "
            "-- Bot API webhook update -> InboundEvent with "
            "chat-id indexing; OutboundFrame -> sendMessage "
            "body with reply_to_message_id). Both reuse "
            "loop-channels-core frames + ChannelDispatcher "
            "Protocol; no SES / Telegram SDK dependency. "
            "Tests: 9 (email) + 10 (telegram) = 19 new; "
            "suite 231 -> 250. Blockers: none. "
            "Commits: claim, channels (substance), close."
        ),
    ),
    Story(
        "S038",
        "Multi-agent v0: Supervisor + Pipeline patterns",
        "Eng #1",
        "S1",
        "E14",
        13,
        "P1",
        "Done",
        (
            "**Done.** "
            "Branch: copilot/s038-multiagent-v0 (merged). "
            "PR: local-merge (ff to main). "
            "Skill: skills/coding/implement-multi-agent-pattern.md. "
            "Last step: 5/5 (merge). "
            "Heartbeat: 2026-04-30T21:25Z (GitHub Copilot). "
            "Open questions: none. "
            "Shipped packages/runtime/loop_runtime/multi_agent.py: "
            "frozen pydantic AgentSpec; runtime_checkable "
            "AgentRunner Protocol with CallableRunner adapter; "
            "Supervisor (router-based delegation, validates "
            "spec/runner pairing, rejects empties + duplicates) "
            "and Pipeline (sequential chain). HandoffTrail + "
            "HandoffStep are frozen pydantic models with a "
            "with_step copy-on-extend. MultiAgentError raised "
            "for: unknown router target, missing runner, "
            "duplicate spec name, empty specs. Tests: 10. "
            "Suite 250 -> 260. Cycles + parallel deferred to "
            "S042 (AgentGraph). Blockers: none. "
            "Commits: claim, multi-agent (substance), close."
        ),
    ),
    Story(
        "S039",
        "TS SDK auto-gen from Pydantic types",
        "Eng #5",
        "S1",
        "E11",
        8,
        "P1",
        "Done",
        (
            "**Done.** "
            "Branch: copilot/s039-ts-sdk-gen (merged). "
            "PR: local-merge (ff to main). "
            "Skill: skills/api/update-openapi.md. "
            "Last step: 5/5 (merge). "
            "Heartbeat: 2026-04-30T21:45Z (GitHub Copilot). "
            "Open questions: none. "
            "Shipped tools/gen_ts_sdk.py: walks every public "
            "symbol in packages/sdk-py/loop/types.py "
            "__all__ via pydantic model_fields and Python's "
            "typing module, emits "
            "apps/studio/src/lib/sdk-types.ts as "
            "TS interfaces + string-union enum type aliases. "
            "Mappings: str/UUID/datetime->string, "
            "int/float->number, bool->boolean, "
            "Literal->TS string union, list[T]->T[], "
            "dict[str, V]->Record<string, V>, "
            "T|None->T|null, defaulted fields->optional. "
            "Drift-detection: tests/test_gen_ts_sdk.py "
            "asserts the committed TS file matches generator "
            "output (5 tests; suite 260 -> 265). "
            "Studio vitest still 41/41. Blockers: none. "
            "Commits: claim, gen + ts file (substance), close."
        ),
    ),
    Story(
        "S040",
        "Discord + Teams channels",
        "Eng #7",
        "S1",
        "E6",
        8,
        "P2",
        "Done",
        (
            "**Done.** "
            "Branch: copilot/s040-discord-teams (merged). "
            "PR: local-merge (ff to main). "
            "Skill: skills/coding/implement-channel-adapter.md. "
            "Last step: 5/5 (merge). "
            "Heartbeat: 2026-04-30T22:05Z (GitHub Copilot). "
            "Open questions: none. "
            "Shipped two channel packages mirroring the "
            "S037 shape: loop-channels-discord parses "
            "Interactions API webhooks (APPLICATION_COMMAND "
            "+ MESSAGE_COMPONENT, drops PING) into "
            "InboundEvent and emits followup-message "
            "bodies (ephemeral flag on errors); "
            "loop-channels-teams parses Bot Framework "
            "message activities into InboundEvent and "
            "emits reply Activity bodies with replyToId. "
            "Channel-id keyed conversation index for "
            "Discord, conversation-id keyed for Teams; "
            "asyncio.Lock guarded. Tests cover parse, "
            "frame translation, round-trip, "
            "channel-id reuse, requires-start "
            "(suite 265 -> 283; +18). Studio vitest "
            "still 41/41. ruff clean. Blockers: none. "
            "Commits: claim, channels (substance), close."
        ),
    ),
    Story(
        "S041",
        "Replay/time-travel debugging in Studio",
        "Eng #5",
        "S1",
        "E10",
        8,
        "P1",
        "Done",
        (
            "**Done.** "
            "Branch: copilot/s041-studio-replay (merged). "
            "PR: local-merge (ff to main). "
            "Skill: skills/coding/implement-studio-screen.md. "
            "Last step: 5/5 (merge). "
            "Heartbeat: 2026-04-30T22:25Z (GitHub Copilot). "
            "Open questions: none. "
            "Shipped pure replay engine "
            "apps/studio/src/lib/replay.ts: ReplayEvent "
            "+ ReplayTrace + snapshotAt(trace, cursor) "
            "+ collapseToBubbles (coalesces streaming "
            "agent_token deltas into a single transient "
            "agent bubble; final agent_message subsumes "
            "the partial stream) + previousBoundary / "
            "nextBoundary (skip token noise to the next "
            "user_message / agent_message / tool_call_end "
            "/ handoff / error step). React component "
            "components/replay/replay-player.tsx (client) "
            "renders the cursor-prefixed transcript with "
            "role-tagged bubbles + scrubber + first/prev/"
            "next/last + active-event detail rail with "
            "attributes table. Page route /replay/[id] "
            "wired via getReplayTrace fixture. Vitest "
            "covers clamping, empty trace, token "
            "coalescing, agent_message subsuming tokens, "
            "boundary stepping, scrubber, detail rail, "
            "empty state (Studio 41/41 -> 57/57; +16). "
            "Blockers: none. "
            "Commits: claim, replay (substance), close."
        ),
    ),
    Story(
        "S042",
        "Multi-agent GA: Parallel + AgentGraph (cyclic)",
        "Eng #1",
        "S1",
        "E14",
        13,
        "P0",
        "Done",
        (
            "**Done.** "
            "Branch: copilot/s042-parallel-agentgraph (merged). "
            "PR: local-merge (ff to main). "
            "Skill: skills/coding/implement-multi-agent-pattern.md. "
            "Last step: 5/5 (merge). "
            "Heartbeat: 2026-04-30T22:45Z (GitHub Copilot). "
            "Open questions: none. "
            "Extended packages/runtime/loop_runtime/multi_agent.py "
            "with two GA primitives. Parallel: fans out one "
            "request to N runners via asyncio.gather; "
            "responses are merged by user-supplied "
            "Merger callable (e.g. concat, vote, "
            "pick-best); HandoffTrail records every step "
            "in spec order regardless of completion order "
            "for deterministic replay. AgentGraph: "
            "directed (possibly cyclic) graph driven by "
            "a Selector(last_agent, last_response, trail) "
            "-> next_agent | None coroutine; bounded by "
            "max_steps (default 16) which raises "
            "MultiAgentError on runaway. Validates start "
            "agent presence, missing/duplicate runners, "
            "max_steps >= 1, selector-returned unknown "
            "names. Tests cover concurrency (timing "
            "assertion), trail ordering, cycles, "
            "max_steps bound, validation errors "
            "(suite 283 -> 294; +11). ruff clean. "
            "Blockers: none. Commits: substance, close."
        ),
    ),
    Story(
        "S043",
        "Public eval registry (community suites)",
        "Eng #4",
        "S1",
        "E8",
        8,
        "P1",
        "Done",
        (
            "**Done.** "
            "Branch: copilot/s043-eval-registry (merged). "
            "PR: local-merge (ff to main). "
            "Skill: skills/coding/implement-eval-scorer.md. "
            "Last step: 5/5 (merge). "
            "Heartbeat: 2026-04-30T23:00Z (GitHub Copilot). "
            "Open questions: none. "
            "Shipped packages/eval-harness/loop_eval/registry.py: "
            "EvalSuite (frozen pydantic model with semver "
            "version + lowercase-slug validation, scorer_ids, "
            "tags, license, author, homepage), "
            "EvalRegistry Protocol, InMemoryEvalRegistry "
            "with register/get/list/slugs (latest semver "
            "by default; explicit version supported; "
            "tag filtering; deterministic sort), "
            "DuplicateSuiteError + SuiteNotFoundError, "
            "and two built-in starter suites "
            "(customer-support-v1, faq-routing-v1) wired "
            "via builtin_suites() / default_registry(). "
            "Tests cover Protocol conformance, latest "
            "lookup, version pinning, duplicate guard, "
            "tag filter, sort order, slug+semver "
            "validation, frozenness, builtins parity "
            "(suite 294 -> 306; +12). ruff clean. "
            "Blockers: none. Commits: substance, close."
        ),
    ),
    Story(
        "S044",
        "Series A fundraise narrative + data room",
        "CEO",
        "S1",
        "—",
        5,
        "P0",
        "Done",
        (
            "**Done.** "
            "Branch: copilot/s044-series-a (merged). "
            "PR: local-merge (ff to main). "
            "Skill: skills/meta/update-tracker.md. "
            "Last step: 5/5 (merge). "
            "Heartbeat: 2026-04-30T23:15Z (GitHub Copilot). "
            "Open questions: none. "
            "Shipped loop_implementation/operations/SERIES_A.md "
            "as the single source of truth for the round: "
            "round summary table ($18M primary, $90-110M "
            "pre, 24mo runway, use of funds), narrative "
            "spine (why now / what we are / traction / "
            "team / use of $18M), anti-pitch responses, "
            "bear-case table (OpenAI bundling, hyperscalers, "
            "LangGraph parity, eval commoditisation, "
            "enterprise demand), data-room index "
            "(00 one-pager through 70 references with "
            "owners), KPI commitments at T0/+12mo/+24mo, "
            "process timeline, and ownership matrix. "
            "Cross-references existing docs (architecture, "
            "security, eval registry S043, replay S041). "
            "Pure docs change; no code. Blockers: none. "
            "Commits: substance, close."
        ),
    ),
    Story(
        "S045",
        "EU region (`eu-west`) deploy on chosen cloud (cloud-agnostic)",
        "Eng #2",
        "S1",
        "E12",
        13,
        "P0",
        "Done",
        (
            "**Done.** "
            "Branch: copilot/s045-eu-region (merged). "
            "PR: local-merge (ff to main). "
            "Skill: skills/architecture/cloud-portability-check.md. "
            "Last step: 5/5 (merge). "
            "Heartbeat: 2026-04-30T23:25Z (GitHub Copilot). "
            "Open questions: none. "
            "Shipped infra/helm/loop/values-eu-west.yaml "
            "as a cloud-agnostic Helm overlay (region pin, "
            "data-residency env, in-region KMS/OTLP/object "
            "store, NetworkPolicy enforceRegionPin, audit "
            "retention 1y hot / 6y cold) and "
            "loop_implementation/engineering/REGIONAL_DEPLOYS.md "
            "with install steps, per-cloud externals matrix "
            "(AWS/GCP/Azure/on-prem OVH), residency preflight "
            "command, failure modes, rollback, and "
            "add-a-new-region runbook. Pure ops/docs change; "
            "no application code touched. Blockers: none. "
            "Commits: substance, close."
        ),
    ),
    Story(
        "S046",
        "SOC2 Type 1 kickoff with Vanta",
        "Sec eng",
        "S1",
        "E16",
        13,
        "P0",
        "Done",
        (
            "**Done.** "
            "Branch: copilot/s046-soc2-kickoff (merged). "
            "PR: local-merge (ff to main). "
            "Skill: skills/security/update-threat-model.md. "
            "Last step: 5/5 (merge). "
            "Heartbeat: 2026-04-30T23:35Z (GitHub Copilot). "
            "Open questions: auditor selection (Vanta-pool, "
            "decision end of week); IdP/MDM/HRIS vendor "
            "selection. "
            "Shipped loop_implementation/engineering/SOC2.md "
            "as the Type 1 kickoff tracker: scope (Security "
            "TSC only for T1; A+C planned for T2), RACI, "
            "Vanta integration checklist (IdP, GitHub, CI/CD, "
            "cloud, MDM, HRIS, background check, vuln "
            "scanner, vendor-risk), control families "
            "CC1-CC9 with per-row owner/evidence/status, "
            "evidence collection cadence (continuous to "
            "annual), milestone schedule (kickoff -> T1 "
            "report end of Q3 -> T2 window opens), and "
            "explicit out-of-scope clarifications "
            "(HIPAA/FedRAMP/PCI). Cross-references "
            "SECURITY.md, DR.md, REGIONAL_DEPLOYS.md. "
            "Pure docs change. Blockers: none. "
            "Commits: substance, close."
        ),
    ),
    Story(
        "S047",
        "Salesforce + Zendesk first-party MCP servers",
        "Eng #6",
        "S1",
        "E18",
        13,
        "P1",
        "Done",
        (
            "**Done.** "
            "Branch: copilot/s047-mcp-sf-zendesk (merged). "
            "PR: local-merge (ff to main). "
            "Skill: skills/coding/implement-mcp-tool.md. "
            "Last step: 5/5 (merge). "
            "Heartbeat: 2026-04-30T23:50Z (GitHub Copilot). "
            "Open questions: production HTTP adapters (OAuth "
            "refresh, rate-limit) deferred to a follow-up "
            "story; in-memory clients ship now to unblock "
            "agent authors. "
            "Shipped two new packages under "
            "packages/mcp-servers/: loop-mcp-salesforce and "
            "loop-mcp-zendesk. Each provides strict pydantic "
            "models (Account/Contact/Opportunity/Case for SF; "
            "User/Ticket/Comment for ZD), a Config.from_env() "
            "loader, a Protocol-based Client + an "
            "InMemoryClient test double, and four "
            "@tool-decorated MCP tools "
            "(salesforce_find_account / find_contact / "
            "create_case / list_open_opportunities; "
            "zendesk_find_user / get_ticket / create_ticket / "
            "add_comment) plus a server_registry() factory. "
            "Wired into the uv workspace (members, sources, "
            "dev group). 26 new tests covering config "
            "from_env, find/create/error paths, registry "
            "enumeration + dispatch, Protocol conformance, "
            "and unbound-client guard (suite 306 -> 332). "
            "ruff clean. Blockers: none. "
            "Commits: substance, close."
        ),
    ),
    Story(
        "S048",
        "Voice latency push to ≤700ms p50",
        "Eng #3",
        "S1",
        "E7",
        13,
        "P0",
        "Done",
        (
            "**Done.** "
            "Branch: copilot/s048-voice-latency (merged). "
            "PR: local-merge (ff to main). "
            "Skill: skills/testing/perf-check.md. "
            "Last step: 5/5 (merge). "
            "Heartbeat: 2026-04-30T23:55Z (GitHub Copilot). "
            "Open questions: PSTN leg budget owns its own "
            "300 ms outer envelope (S049 lands the model). "
            "Shipped engineering/VOICE_LATENCY.md (the source "
            "of truth for the 700 ms p50 commitment) plus "
            "loop_voice.latency: LatencyStage StrEnum, "
            "StageBudget / LatencyBudget pydantic models, "
            "DEFAULT_BUDGET (network_in 20/45 ms p50/p95, "
            "asr_final 160/280, agent 280/520, "
            "tts_first_byte 160/260, network_out 20/45, "
            "end-to-end 640/1150 — 60 ms headroom under the "
            "public commitment), LatencyMeasurement, "
            "LatencyTracker with linear-interp percentiles + "
            ".breaches() that returns the empty tuple when "
            "every stage and the e2e total fits, BudgetBreach "
            "with .over_ms. 8 new tests covering budget "
            "invariants, percentile math, breach detection, "
            "happy path, and empty-tracker guard. ruff clean. "
            "Suite 332 -> 340. Blockers: none. "
            "Commits: substance, close."
        ),
    ),
    Story(
        "S049",
        "Phone number provisioning at the Loop layer",
        "Eng #3",
        "S1",
        "E7",
        8,
        "P1",
        "Done",
        (
            "**Done.** "
            "Branch: copilot/s049-phone-provisioning (merged). "
            "PR: local-merge (ff to main). "
            "Skill: skills/coding/implement-runtime-feature.md. "
            "Last step: 5/5 (merge). "
            "Heartbeat: 2026-04-30T23:58Z (GitHub Copilot). "
            "Open questions: real-carrier adapters "
            "(twilio/telnyx/vonage/bandwidth) deferred to "
            "S049b; inbound-port flow deferred to S076. "
            "Shipped engineering/PHONE_PROVISIONING.md and "
            "loop_voice.phone: PhoneCapability + "
            "PhoneNumberStatus StrEnums, strict-pydantic "
            "PhoneNumberSearchQuery / PhoneNumberCandidate / "
            "PhoneNumber models, validate_e164 helper, "
            "PhoneNumberProvisioner Protocol with "
            "search/buy/assign/release/list_active, "
            "InMemoryPhoneNumberProvisioner test double "
            "(country/area-code/contains/capability filters, "
            "auto pn_NNNNNN ids, double-purchase + "
            "double-release guards, tenant-scoped listing, "
            "injectable clock). 14 new tests covering E.164 "
            "validation, every search axis, lifecycle "
            "transitions, error paths, and Protocol "
            "conformance. ruff clean. Suite 340 -> 354. "
            "Blockers: none. "
            "Commits: substance, close."
        ),
    ),
    Story(
        "S050",
        "Enterprise GA: SSO/SAML, audit log UI, on-prem parity",
        "Eng #2",
        "S1",
        "E20",
        13,
        "P0",
        "Done",
        (
            "**Done.** "
            "Branch: copilot/s050-enterprise-ga (merged). "
            "PR: local-merge (ff to main). "
            "Skill: skills/architecture/propose-adr.md. "
            "Last step: 5/5 (merge). "
            "Heartbeat: 2026-04-30T23:59Z (GitHub Copilot). "
            "Open questions: custom RBAC (S067), audit "
            "alert subscriptions (S068), HPA + cross-region "
            "for on-prem (S081, S083), air-gapped bundle "
            "(S080), multi-tenant on-prem (S082) all "
            "explicitly out of scope and tracked. "
            "Shipped engineering/ENTERPRISE_GA.md (the "
            "definition of done across the three GA "
            "pillars: SSO/SAML, audit log UI, on-prem "
            "parity matrix with cloud-vs-on-prem deltas, "
            "install footprint, and five hard GA gates "
            "tying SOC2/SSO/audit-UI/on-prem-matrix/voice-"
            "latency together) and engineering/SSO_SAML.md "
            "(per-IdP click-by-click recipes for Okta, "
            "Entra ID, Google Workspace, generic SAML + "
            "OIDC; tenant-level SSO record schema; SCIM "
            "endpoint pattern; troubleshooting matrix; the "
            "auth.sso.* audit event namespace). No code "
            "changes; ruff + suite stay at 354 passing. "
            "Blockers: none. "
            "Commits: substance, close."
        ),
    ),
]


# --------------------------------------------------------------------------- #
# Bite-sized backlog (S100+) — see tools/_stories_v2.py for the rationale.    #
# Every old vision-headline story (S015-S050) shipped a stub; the bite-sized #
# stories below are what's actually needed to take each stub to production.  #
# --------------------------------------------------------------------------- #

# Re-tag every vision-headline-shaped story (S015-S050) into a single sprint
# 'S1' labeled "Vision-headline stub layer" so the new bite-sized sprints
# (S2-S30) get a clean number space. The old per-story sprint assignment was
# never meaningful — every story closed in one pass.
_VISION_STUB_STORY_IDS: set[str] = {f"S{i:03d}" for i in range(15, 51)}
for _story in STORIES:
    if _story.id in _VISION_STUB_STORY_IDS:
        _story.sprint = "S1"
del _story

# Append the bite-sized backlog. Imported lazily so editing _stories_v2.py
# alone is enough to grow the backlog — no churn here. The sibling module
# is loaded by absolute path so this works whether run as `python
# tools/build_tracker.py` (no package context) or `python -m
# tools.build_tracker` (package context).
import importlib.util as _ilu

_v2_path = Path(__file__).with_name("_stories_v2.py")
_v2_spec = _ilu.spec_from_file_location("_stories_v2", _v2_path)
_v2_mod = _ilu.module_from_spec(_v2_spec)
assert _v2_spec.loader is not None
sys.modules["_stories_v2"] = _v2_mod  # required so @dataclass introspection works
_v2_spec.loader.exec_module(_v2_mod)
_NEW_OWNER = _v2_mod.DEFAULT_OWNER
_NEW_STATUS = _v2_mod.DEFAULT_STATUS
_NEW_STORIES_V2 = _v2_mod.NEW_STORIES

for _v2 in _NEW_STORIES_V2:
    STORIES.append(
        Story(
            id=_v2.id,
            title=_v2.title,
            owner=_v2.owner or _NEW_OWNER,
            sprint=_v2.sprint,
            epic=_v2.epic,
            points=_v2.points,
            priority=_v2.priority,
            status=_v2.status or _NEW_STATUS,
            notes=_v2.notes_override if _v2.notes_override is not None else _v2.notes,
        )
    )
del _v2


SPRINTS: list[Sprint] = [
    Sprint(
        "S0",
        "Wk 1–6",
        "Bootstrap (closed)",
        "Foundation: repo, CI, types, docker-compose, migrations, gateway+runtime+memory+tools skeletons. 14/15 closed; S002 blocked on CTO.",
        "S001-S014, S002",
        "Done",
    ),
    Sprint(
        "S1",
        "Wk 7–18",
        "Vision-headline stub layer (closed; stubs only)",
        "Each S015-S050 shipped a stub under a vision-headline title. The real production work is decomposed across S2-S30 below.",
        "S015-S050",
        "Done",
    ),
    Sprint(
        "S2",
        "Wk 19–20",
        "cp-api basics",
        "A live cp-api a developer can hit — auth, workspaces, members, API keys, error mapping, integration smoke.",
        "S100-S122",
        "Not started",
    ),
    Sprint(
        "S3",
        "Wk 21–22",
        "dp-runtime HTTP service",
        "POST /v1/turns returns SSE TurnEvent stream end-to-end with API-key auth and persistence.",
        "S130-S143",
        "Not started",
    ),
    Sprint(
        "S4",
        "Wk 23–24",
        "Studio MVP",
        "User logs in, sees workspaces+agents from real cp-api, runs an emulator turn, manages versions+secrets.",
        "S150-S164",
        "Not started",
    ),
    Sprint(
        "S5",
        "Wk 25–26",
        "Web channel + first end-to-end demo",
        "Visitor on a webpage talks to a Loop agent via embedded ChatWidget; demo + smoke test live.",
        "S170-S181",
        "Not started",
    ),
    Sprint(
        "S6",
        "Wk 27–30",
        "KB engine v0 (productionization)",
        "Upload a PDF, agent answers from it with citations. Full parser registry, chunkers, embeddings, hybrid retrieval, reranker, studio UI.",
        "S190-S213",
        "Not started",
    ),
    Sprint(
        "S7",
        "Wk 31–32",
        "Slack channel productionization",
        "Threaded conversations, signed webhooks, Block Kit, OAuth install, integration tests.",
        "S220-S229",
        "Not started",
    ),
    Sprint(
        "S8",
        "Wk 33–34",
        "Eval harness productionization",
        "Real scorers, cassette record/replay, suite runner, regression detector, studio UI.",
        "S240-S253",
        "Not started",
    ),
    Sprint(
        "S9",
        "Wk 35–36",
        "Deploy controller v0",
        "Artifact → image → k8s with canary promotion, rollback, deploy events.",
        "S260-S271",
        "Not started",
    ),
    Sprint(
        "S10",
        "Wk 37–38",
        "Cost / observability v1",
        "ClickHouse rollups, cost dashboard, trace search + waterfall, alert rules.",
        "S280-S291",
        "Not started",
    ),
    Sprint(
        "S11",
        "Wk 39–40",
        "HITL operator inbox v0",
        "Real takeover state machine, queue, conversation viewer, composer, handback.",
        "S300-S309",
        "Not started",
    ),
    Sprint(
        "S12",
        "Wk 41–42",
        "Billing v0 (Stripe)",
        "Customer creation, plans, webhooks, metered usage push, suspension, studio billing tab.",
        "S320-S331",
        "Not started",
    ),
    Sprint(
        "S13",
        "Wk 43–44",
        "WhatsApp channel productionization",
        "Cloud API webhooks, 24h-window enforcement, templates, media, interactive elements, studio connect.",
        "S340-S349",
        "Not started",
    ),
    Sprint(
        "S14",
        "Wk 45–46",
        "Voice infrastructure",
        "Real ASR/TTS/VAD adapters, turn-take FSM, LiveKit room bridge, tracing, web-RTC echo agent.",
        "S360-S371",
        "Not started",
    ),
    Sprint(
        "S15",
        "Wk 47–48",
        "Voice MVP — phone calls",
        "Twilio SIP gateway, outbound call API, number provisioning, voice widget, latency benchmark, integration test.",
        "S380-S389",
        "Not started",
    ),
    Sprint(
        "S16",
        "Wk 49–50",
        "Multi-agent orchestration v0",
        "AgentGraph types, Supervisor/Pipeline/Parallel patterns, executor with cycle detection, shared memory + cost rollup, integration test.",
        "S400-S410",
        "Not started",
    ),
    Sprint(
        "S17",
        "Wk 51–52",
        "TS SDK + CLI v0",
        "Auto-gen TS client, react hooks, full CLI surface (login/init/deploy/logs/eval/secrets), multi-arch release pipeline.",
        "S420-S433",
        "Not started",
    ),
    Sprint(
        "S18",
        "Wk 53–54",
        "Helm chart for self-host",
        "Per-service subcharts, dependencies (Postgres/Redis/Qdrant/NATS/ClickHouse/MinIO), ingress + cert-manager, kind smoke test.",
        "S440-S453",
        "Not started",
    ),
    Sprint(
        "S19",
        "Wk 55–56",
        "Studio flow editor v0",
        "Visual node-based editor with palette/config/edges/serialize/emulator/templates — Botpress's killer UX.",
        "S460-S472",
        "Not started",
    ),
    Sprint(
        "S20",
        "Wk 57–58",
        "Trace viewer + replay",
        "Frame recorder, deterministic replayer, side-by-side diff, prod-failure → eval-case auto-flow.",
        "S480-S487",
        "Not started",
    ),
    Sprint(
        "S21",
        "Wk 59–60",
        "Episodic memory + KB v1",
        "Auto-summarize on conv close, retrieval at turn-start, scheduled refresh, layout-aware chunking.",
        "S490-S497",
        "Not started",
    ),
    Sprint(
        "S22",
        "Wk 61–62",
        "SMS + RCS + Email + Telegram channels",
        "Twilio SMS w/ STOP compliance, RCS via Jibe/MaaP, SES inbound+outbound w/ DKIM, Telegram polling+webhook.",
        "S510-S519, S540-S545",
        "Not started",
    ),
    Sprint(
        "S23",
        "Wk 63–64",
        "Discord + Teams channels",
        "Bot SDK adapters; studio connect flows; cross-channel test fixture.",
        "S530-S536",
        "Not started",
    ),
    Sprint(
        "S24",
        "Wk 65–66",
        "MCP marketplace v0",
        "Registry table, signed-manifest verification, install flow, browse/install UI, first 4 first-party MCP servers.",
        "S550-S559",
        "Not started",
    ),
    Sprint(
        "S25",
        "Wk 67–70",
        "SOC2 Type 1 prep",
        "Vanta sync, control mapping, backups+DR, pen-test, SBOM, scanning gates, audit-trail review, attestation kickoff.",
        "S570-S582",
        "Not started",
    ),
    Sprint(
        "S26",
        "Wk 71–72",
        "EU region (data residency)",
        "Region pinning, EU stack, region-aware routing, cross-region export blocker, smoke test.",
        "S590-S597",
        "Not started",
    ),
    Sprint(
        "S27",
        "Wk 73–74",
        "Enterprise SSO/SAML",
        "PySAML2 SP, SCIM provisioning, Okta/Entra/Google recipes, JIT user provisioning, group→role mapping.",
        "S610-S618",
        "Not started",
    ),
    Sprint(
        "S28",
        "Wk 75–76",
        "Audit log UI + DPA + on-prem parity",
        "Audit events table+middleware, studio audit UI, SIEM webhook, DPA, GDPR Art-17, CMK, BYO Vault, dedicated single-tenant.",
        "S630-S639",
        "Not started",
    ),
    Sprint(
        "S29",
        "Wk 77–78",
        "Voice latency + GA polish",
        "Voice ≤700ms p50; design-system audit; a11y WCAG-AA; i18n; support runbook; docs.loop.example v1.",
        "S650-S659",
        "Not started",
    ),
    Sprint(
        "S30",
        "Wk 79–80",
        "1.0 launch + Series A",
        "Release notes, pricing page, design-partner conversion, HN/PH launch, Series A data room.",
        "S670-S674",
        "Not started",
    ),
    # ---- Audit-follow-up sprints (added after vision-coverage audit) ----
    # These five sprints close gaps the v1 plan missed: LLM gateway breadth,
    # MCP production hardening, marketplace scale, cloud-portability proof,
    # and production-security/ops acceptance gates. Plus a memory-providers
    # sprint and a hard performance-gates sprint. Run in parallel with the
    # main S2-S30 arc when capacity allows; serial-blocking points called out
    # below.
    Sprint(
        "S31",
        "Wk 23–28 (parallel w/ S3-S6)",
        "LLM gateway breadth",
        "Bedrock + Vertex/Gemini + Mistral + Cohere + Groq + vLLM + generic OpenAI-compat. Semantic cache, BYO keys, model aliases, routing engine, failover, rate-limiting, Decimal cost precision, 50-prompt provider eval.",
        "S700-S714",
        "Not started",
    ),
    Sprint(
        "S32",
        "Wk 29–34 (parallel w/ S7-S10)",
        "MCP production hardening",
        "Tool policy engine, egress allowlist, rate-limit, schema validation, secrets injection, sandbox controller, hot-restart, inbound MCP, version negotiation, resource quotas, signed-tool verification, hostile-tool kill-switch.",
        "S720-S735",
        "Not started",
    ),
    Sprint(
        "S33",
        "Wk 65–68 (after S24)",
        "MCP marketplace scale + community",
        "Quality scoring, community-publish PR flow, reviews/ratings, usage analytics, 12 first-party servers (Calendar, Gmail, GitHub, Linear, Jira, Notion, Asana, Stripe-write, Slack-write, HubSpot-write, web-search), 25-server MVP acceptance gate.",
        "S750-S765",
        "Not started",
    ),
    Sprint(
        "S34",
        "Wk 71–76 (parallel w/ S26-S28)",
        "Cloud-portability proof",
        "Terraform modules for AWS / Azure / GCP / Alibaba / OVH / Hetzner. Protocol parity tests for ObjectStore + KMS + SecretsBackend + EmailSender. Cross-cloud nightly smoke matrix. Live CLOUD_PROOF.md report.",
        "S770-S781",
        "Not started",
    ),
    Sprint(
        "S35",
        "Wk 67–72 (overlap w/ S25)",
        "Production security / ops acceptance gates",
        "Continuous fuzz testing, STRIDE PR-gate, SLSA-3 provenance, Falco runtime detection, chaos-eng harness, SLOs + error-budget alerts, incident-response game-days, data-retention enforcement, backup-restore verification, bug bounty.",
        "S800-S809",
        "Not started",
    ),
    Sprint(
        "S36",
        "Wk 59–62 (parallel w/ S21-S22)",
        "Memory providers + KB v2",
        "Mem0 + Zep adapters, hybrid summarization, per-user isolation tests, PII-redaction-on-write, memory dashboard, ColBERT late-interaction retrieval, structured-data (SQL-on-spreadsheet) retrieval.",
        "S820-S827",
        "Not started",
    ),
    Sprint(
        "S37",
        "Wk 77–80 (overlap w/ S29-S30)",
        "Latency + scale acceptance gates",
        "Hard performance gates: turn p95 <2s, gateway cache-hit >30%, KB p50 <200ms at 1M chunks, tool-host warm <300ms p95, 1000 concurrent turns/pod, cp-api 5000 RPS, perf-regression budget enforced in CI.",
        "S840-S846",
        "Not started",
    ),
    # ---- Production-readiness gap-close (filed after the post-S37 audit) ----
    # The post-S37 audit revealed that the cp-api / dp-runtime container
    # entrypoints just exit 0 (loop_data_plane.__main__ literally prints
    # version and exits; the cp-api Dockerfile CMD runs the healthz module
    # only). Every external integration was a Protocol seam with InMemory*
    # implementations — no httpx-backed gateway transport, no boto3, no
    # PySAML2, no real microVM. S38 closes that gap so the system actually
    # runs against real upstreams and real clouds.
    Sprint(
        "S38",
        "Wk 81+ (post-audit gap-close)",
        "Production-readiness wiring",
        "FastAPI app objects for cp-api + dp-runtime, real httpx gateway transport, real boto3 KMS+S3, real Deepgram/ElevenLabs WS clients, real RuncSandboxFactory, real PySAML2 signature verification, Vault transit BYO key path, Mintlify docs deploy, demo bundle. Closes the architectural-skeleton-vs-runnable-system gap.",
        "S900-S919",
        "Not started",
    ),
]
_LEGACY_SPRINTS_BELOW: list[Sprint] = [
    Sprint(
        "_LEGACY_S0",
        "Wk 1–6",
        "Bootstrap",
        "Local stack + first turn + first deploy + 3 design partners onboarded",
        "S001-S034",
        "In progress",
    ),
    Sprint(
        "S1",
        "Wk 7–8",
        "Episodic memory + Helm",
        "Episodic memory; helm chart; email + telegram; multi-agent v0",
        "S035-S038",
        "Not started",
    ),
    Sprint(
        "S2",
        "Wk 9–10",
        "TS SDK + Discord/Teams + replay",
        "TS SDK GA; Discord + Teams; replay debugging in Studio",
        "S039-S041",
        "Not started",
    ),
    Sprint(
        "S3",
        "Wk 11–12",
        "Multi-agent GA + eval registry + Series A",
        "Parallel + AgentGraph; public eval registry; Series A narrative",
        "S042-S044",
        "Not started",
    ),
    Sprint(
        "S4",
        "Wk 13–14",
        "EU region + SOC2 kickoff",
        "Deploy `eu-west` (cloud-agnostic); Vanta; Salesforce + Zendesk MCP",
        "S045-S047",
        "Not started",
    ),
    Sprint(
        "S5",
        "Wk 15–16",
        "Voice latency + phone provisioning",
        "Voice ≤700ms; phone number provisioning",
        "S048-S049",
        "Not started",
    ),
    Sprint(
        "S6",
        "Wk 17–18",
        "Enterprise GA",
        "SSO/SAML, audit UI, on-prem parity, SOC2 Type 1 done",
        "S050",
        "Not started",
    ),
]


HIRING: list[Hire] = [
    Hire(
        1,
        "Founding engineer — Runtime (Python core)",
        "Owns the agent loop. Senior, opinionated.",
        "M0",
        "Searching",
        "CTO",
        "Bar: shipped a high-throughput Python service before",
    ),
    Hire(
        2,
        "Founding engineer — Infra / Platform",
        "Postgres, Redis, NATS, k8s, Terraform. Builds data plane.",
        "M0",
        "Searching",
        "CTO",
        "Bar: production k8s, observability",
    ),
    Hire(
        3,
        "Founding engineer — Voice / Real-time",
        "WebRTC, STT/TTS, latency. The voice moat.",
        "M0",
        "Pipeline",
        "CTO",
        "Bar: ≤500ms voice in prod",
    ),
    Hire(
        4,
        "Founding engineer — Observability + Eval harness",
        "ClickHouse, OTel, eval scorers. The other moat.",
        "M1",
        "Pipeline",
        "CTO",
        "Bar: scaled tracing/eval system before",
    ),
    Hire(
        5,
        "Founding engineer — Full-stack / Studio",
        "Next.js, React, tRPC. Debugger UI.",
        "M1",
        "Pipeline",
        "CTO",
        "Bar: shipped a polished web app to GA",
    ),
    Hire(
        6,
        "DevRel / Docs engineer",
        "Examples, blog, docs, MCP server contributions. OSS adoption.",
        "M3",
        "Pipeline",
        "CEO",
        "Critical for community velocity",
    ),
    Hire(
        7,
        "Senior engineer — Channel integrations",
        "WhatsApp, Slack, Teams, email. Compounding work.",
        "M3",
        "Pipeline",
        "CTO",
        "Bar: 3+ external API integrations",
    ),
    Hire(
        8,
        "Security / Compliance engineer",
        "SOC2, HIPAA-readiness, audit logs, secrets. Unlocks enterprise.",
        "M5",
        "Searching",
        "CTO",
        "Bar: led SOC2 effort end-to-end",
    ),
]


RISKS: list[Risk] = [
    Risk(
        "R1",
        "Frontier-lab SDKs (OpenAI Agents, Claude Agent) eat the category",
        "Med",
        "High",
        "CEO",
        "Be the agnostic Switzerland. Run on every provider. Own observability + evals + voice as differentiators.",
        "Watching",
    ),
    Risk(
        "R2",
        "MCP standard fragments (OpenAI/Google compete)",
        "Low",
        "Med",
        "Eng #1",
        "MCP-first but adapter-flexible; can speak OpenAI tool format too.",
        "Watching",
    ),
    Risk(
        "R3",
        "Voice latency target (≤700ms p50) misses",
        "Med",
        "High",
        "Eng #3",
        "Schedule slip is acceptable; ship voice at M7 instead of MVP. Edge POPs + warm pool.",
        "Watching",
    ),
    Risk(
        "R4",
        "Hire #1 (runtime) takes >60 days to fill",
        "Med",
        "High",
        "CTO",
        "CTO writes first-draft TurnExecutor; new hire inherits. Multiple parallel candidates.",
        "Active",
    ),
    Risk(
        "R5",
        "Botpress closes the gap (voice + MCP + true OSS in 12mo)",
        "Low",
        "Med",
        "CEO",
        "Architecture mid-pivot makes this unlikely. We move faster on each axis.",
        "Watching",
    ),
    Risk(
        "R6",
        "Runtime engineering complexity (async + streaming + sandboxes)",
        "Med",
        "High",
        "Eng #1",
        "Hire bar #1 must be exceptional. Sprint 0 establishes a working baseline.",
        "Active",
    ),
    Risk(
        "R7",
        "Compliance burden (SOC2, HIPAA) blocks enterprise revenue",
        "Med",
        "High",
        "Sec eng",
        "Vanta day 1. Hire sec eng by M5. SOC2 Type 1 by M12.",
        "Watching",
    ),
    Risk(
        "R8",
        "OSS license arbitrage (hyperscaler offers managed Loop)",
        "Low",
        "Med",
        "CEO",
        "Apache 2.0 accepts the risk; brand + control plane + network effects are the moat.",
        "Watching",
    ),
    Risk(
        "R9",
        "Eval harness over-promises; teams don't adopt",
        "Med",
        "Med",
        "Eng #4",
        "`loop eval init` scaffolds from production replay automatically. Public registry seeds value.",
        "Watching",
    ),
    Risk(
        "R10",
        "Cost overruns on infra (LLM, ClickHouse, voice POPs)",
        "Med",
        "Med",
        "CTO",
        "Budget caps + monthly review. Negotiate annual commits with providers post-Series A.",
        "Watching",
    ),
    Risk(
        "R11",
        "Channel provider terms change (Meta WhatsApp policies)",
        "High",
        "Low",
        "Eng #7",
        "Multi-BSP support; document fallback path; surface channel cost on invoice.",
        "Watching",
    ),
    Risk(
        "R12",
        "Studio scope creep (users want a flow editor)",
        "Med",
        "Low",
        "Eng #5",
        "Politely decline. Code-first is the wedge. Optional read-only DAG view at M9.",
        "Active",
    ),
]


ROADMAP: list[Milestone] = [
    Milestone(
        "M0",
        "Hire + scope",
        "Hire engineers 1–4; tech-stack lock-in; runtime + SDK started",
        "Not started",
    ),
    Milestone(
        "M1",
        "Runtime alpha",
        "Python SDK skeleton; LLM gateway w/ OpenAI + Anthropic; Slack channel",
        "Not started",
    ),
    Milestone(
        "M2", "Tools + KB", "Tool/MCP layer; auto-MCP; KB ingestion v0; web widget", "Not started"
    ),
    Milestone(
        "M3",
        "Eval + cloud",
        "Eval harness v0 (6 scorers); CLI v0; cloud control plane (auth, deploy)",
        "Not started",
    ),
    Milestone(
        "M4",
        "Closed alpha",
        "10 design partners; WhatsApp; Studio v0 (conversations + traces)",
        "Not started",
    ),
    Milestone("M5", "Voice MVP", "Voice channel MVP; memory tiers; cost dashboard", "Not started"),
    Milestone(
        "M6",
        "Public beta",
        "OSS the runtime (Apache 2.0); Hub v0; free hobby tier; PUBLIC BETA",
        "Not started",
    ),
    Milestone(
        "M7",
        "Episodic + helm",
        "Episodic memory; Helm chart; email + Telegram; multi-agent primitives v0",
        "Not started",
    ),
    Milestone(
        "M8",
        "TS SDK + replay",
        "TS SDK GA; Discord + Teams; replay/time-travel debugging",
        "Not started",
    ),
    Milestone(
        "M9",
        "Multi-agent GA",
        "Multi-agent GA (Graph, Parallel, Blackboard); public eval registry; Series A",
        "Not started",
    ),
    Milestone(
        "M10",
        "EU + SOC2",
        "EU region (`eu-west`, cloud-agnostic); SOC2 Type 1 kickoff; Salesforce + Zendesk MCP",
        "Not started",
    ),
    Milestone(
        "M11", "Voice latency", "Voice ≤700ms p50; phone-number provisioning; RCS", "Not started"
    ),
    Milestone(
        "M12",
        "Enterprise GA",
        "SSO/SAML, audit logs, on-prem parity, SOC2 Type 1 done; ENTERPRISE GA",
        "Not started",
    ),
]


PERF_BUDGETS: list[Budget] = [
    Budget("Voice latency p50 (end-to-end)", "≤ 700 ms", "Eng #3"),
    Budget("Chat first-token p50", "≤ 600 ms", "Eng #1"),
    Budget("Chat p99", "≤ 2000 ms", "Eng #1"),
    Budget("API availability (Pro/Team)", "99.9%", "Eng #2"),
    Budget("API availability (Enterprise)", "99.95%", "Eng #2"),
    Budget("Trace ingestion lag", "≤ 5 s", "Eng #4"),
    Budget("Cold start (warm pool)", "0 (not user-visible)", "Eng #2"),
    Budget("Deploy time (push → live)", "≤ 60 s", "Eng #2"),
    Budget("Eval suite of 100 cases", "≤ 90 s", "Eng #4"),
]


UNIT_ECONOMICS: list[Budget] = [
    Budget("Gross margin", "75%", notes="LLM ~95% on 5%, compute ~70%, storage ~85%"),
    Budget("LTV : CAC", "≥ 3 : 1 by month 18", notes="Bottom-up PLG with sales-led at the top"),
    Budget("ARR per FTE (by M24)", "$300K", notes="Industry P75 for OSS/PLG infra"),
    Budget("LLM token markup", "5%, fully disclosed", notes="Trust commitment"),
    Budget("Hard-cap behavior", "Graceful degrade, never drop", notes="Trust commitment"),
]


# --------------------------------------------------------------------------- #
# Rollup status: epic / sprint / milestone derive from story status           #
# --------------------------------------------------------------------------- #
#
# The hand-written `status` on each Epic / Sprint / Milestone above is the
# *intent* — kept around so a maintainer can see at a glance what was
# originally targeted. We override it on every render with a value derived
# from the underlying STORIES so the tracker never lies about progress.
#
# Rule:
#   - no stories → "Not started"
#   - all stories Done → "Done"
#   - all stories Not started → "Not started"
#   - all stories Blocked → "Blocked"
#   - all stories Cancelled → "Cancelled"
#   - anything else → "In progress"
#
# Roadmap milestones don't reference stories directly. They reference the
# sprints whose deliverables together make up the milestone, and roll up the
# same way over those sprint statuses. The mapping below is taken from the
# milestone deliverables in ROADMAP and the sprint goals in SPRINTS — it is
# intentionally explicit so a reader can verify it by eye.

# Each milestone → the sprint IDs whose deliverables together satisfy it.
# A milestone is Done when every sprint it depends on is Done.
MILESTONE_SPRINTS: dict[str, list[str]] = {
    "M0": ["S0"],
    "M1": ["S0", "S1", "S31"],
    "M2": ["S2", "S3", "S5", "S6", "S32"],
    "M3": ["S4", "S7", "S8", "S9"],
    "M4": ["S4", "S5", "S11", "S13"],
    "M5": ["S10", "S12", "S14", "S15"],
    "M6": ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10",
           "S11", "S12", "S13", "S14", "S15", "S31", "S32"],
    "M7": ["S16", "S17", "S18", "S21", "S22"],
    "M8": ["S17", "S20", "S23"],
    "M9": ["S16", "S24", "S33"],
    "M10": ["S25", "S26", "S34"],
    "M11": ["S29", "S37"],
    "M12": ["S27", "S28", "S29", "S30", "S35", "S36"],
}


def _rollup_status(statuses: list[str]) -> str:
    """Roll a list of child statuses up to a single parent status."""
    if not statuses:
        return "Not started"
    counts: dict[str, int] = {}
    for s in statuses:
        counts[s] = counts.get(s, 0) + 1
    total = len(statuses)
    if counts.get("Done", 0) == total:
        return "Done"
    if counts.get("Not started", 0) == total:
        return "Not started"
    if counts.get("Blocked", 0) == total:
        return "Blocked"
    if counts.get("Cancelled", 0) == total:
        return "Cancelled"
    return "In progress"


def _align_rollups() -> None:
    """Override Epic / Sprint / Milestone status from underlying story status.

    Idempotent — safe to call repeatedly. Mutates EPICS, SPRINTS, ROADMAP in
    place so render_md / render_json / validate all see the aligned values.
    """
    # Epics: roll up the stories that point to each epic.
    stories_by_epic: dict[str, list[str]] = {e.id: [] for e in EPICS}
    for s in STORIES:
        if s.epic in stories_by_epic:
            stories_by_epic[s.epic].append(s.status)
    for e in EPICS:
        e.status = _rollup_status(stories_by_epic[e.id])

    # Sprints: roll up the stories assigned to each sprint via story.sprint.
    stories_by_sprint: dict[str, list[str]] = {sp.id: [] for sp in SPRINTS}
    for s in STORIES:
        if s.sprint in stories_by_sprint:
            stories_by_sprint[s.sprint].append(s.status)
    sprint_status: dict[str, str] = {}
    for sp in SPRINTS:
        sp.status = _rollup_status(stories_by_sprint[sp.id])
        sprint_status[sp.id] = sp.status

    # Roadmap: each milestone rolls up over its constituent sprints.
    for m in ROADMAP:
        sprint_ids = MILESTONE_SPRINTS.get(m.month, [])
        m.status = _rollup_status([sprint_status[sid] for sid in sprint_ids if sid in sprint_status])


_align_rollups()


# --------------------------------------------------------------------------- #
# Validation                                                                  #
# --------------------------------------------------------------------------- #


def validate() -> list[str]:
    errors: list[str] = []

    epic_ids = {e.id for e in EPICS}
    story_ids = [s.id for s in STORIES]

    if len(set(story_ids)) != len(story_ids):
        errors.append("duplicate story IDs detected")

    for s in STORIES:
        if s.status not in VALID_STATUSES:
            errors.append(f"{s.id}: invalid status '{s.status}'")
        if s.epic != "—" and s.epic not in epic_ids:
            errors.append(f"{s.id}: references unknown epic {s.epic}")
        # Structured-notes rule
        if s.status in {"In progress", "Blocked", "Handing off"}:
            required = (
                "Branch:",
                "Skill:",
                "Last step:",
                "Heartbeat:",
                "Open questions:",
                "Blockers:",
                "Commits:",
            )
            missing = [k for k in required if k not in s.notes]
            if missing:
                errors.append(
                    f"{s.id}: status={s.status} but Notes is missing fields: {missing}. "
                    "See skills/meta/update-tracker.md 'Canonical Notes-cell format'."
                )

    return errors


# --------------------------------------------------------------------------- #
# Renderers                                                                   #
# --------------------------------------------------------------------------- #


def _md_cell(text: str) -> str:
    """Render a multi-line value safely inside a Markdown table cell."""
    if "\n" in text:
        text = text.replace("\n", "<br>")
    if "|" in text:
        text = text.replace("|", "\\|")
    return text


def render_md() -> str:
    out: list[str] = []
    out.append("# Loop — Implementation Tracker (Markdown view)\n")
    out.append(
        "**Generated by** `tools/build_tracker.py` — do NOT edit this file directly.\n"
        "Source of truth: `tools/build_tracker.py`. xlsx companion regenerated separately.\n"
    )
    out.append("---\n")

    # Epics
    out.append("## Epics\n")
    out.append("| ID | Epic | Owner | Target milestone | Status | Notes |")
    out.append("|---|---|---|---|---|---|")
    for e in EPICS:
        out.append(
            f"| {e.id} | {_md_cell(e.name)} | {e.owner} | {e.target} | {e.status} | {_md_cell(e.notes)} |"
        )
    out.append("")

    # Stories
    out.append("## Stories\n")
    out.append(
        "| ID | Story | Owner | Sprint | Epic | Estimate (pts) | Priority | Status | Notes |"
    )
    out.append("|---|---|---|---|---|---|---|---|---|")
    for s in STORIES:
        out.append(
            f"| {s.id} | {_md_cell(s.title)} | {s.owner} | {s.sprint} | {s.epic} | "
            f"{s.points} | {s.priority} | {s.status} | {_md_cell(s.notes)} |"
        )
    out.append("")

    # Sprints
    out.append("## Sprints\n")
    out.append("| Sprint | Window | Theme | Goal | Stories | Status |")
    out.append("|---|---|---|---|---|---|")
    for sp in SPRINTS:
        out.append(
            f"| {sp.id} | {sp.window} | {_md_cell(sp.theme)} | {_md_cell(sp.goal)} | {sp.stories} | {sp.status} |"
        )
    out.append("")

    # Hiring
    out.append("## Hiring plan\n")
    out.append("| # | Role | Why first | Start month | Stage | Owner | Notes |")
    out.append("|---|---|---|---|---|---|---|")
    for h in HIRING:
        out.append(
            f"| {h.n} | {_md_cell(h.role)} | {_md_cell(h.why)} | {h.start_month} | {h.stage} | {h.owner} | {_md_cell(h.notes)} |"
        )
    out.append("")

    # Risks
    out.append("## Risks register\n")
    out.append("| ID | Risk | Likelihood | Severity | Owner | Mitigation | Status |")
    out.append("|---|---|---|---|---|---|---|")
    for r in RISKS:
        out.append(
            f"| {r.id} | {_md_cell(r.risk)} | {r.likelihood} | {r.severity} | {r.owner} | {_md_cell(r.mitigation)} | {r.status} |"
        )
    out.append("")

    # Roadmap
    out.append("## 12-month roadmap\n")
    out.append("| Month | Milestone | Key deliverables | Status |")
    out.append("|---|---|---|---|")
    for m in ROADMAP:
        out.append(
            f"| {m.month} | {_md_cell(m.milestone)} | {_md_cell(m.deliverables)} | {m.status} |"
        )
    out.append("")

    # Budgets
    out.append("## Budgets & metrics\n")
    out.append("**Performance budgets**\n")
    out.append("| Metric | Target | Owner |")
    out.append("|---|---|---|")
    for b in PERF_BUDGETS:
        out.append(f"| {_md_cell(b.metric)} | {b.target} | {b.owner} |")
    out.append("")
    out.append("**Unit-economics targets**\n")
    out.append("| Metric | Target | Notes |")
    out.append("|---|---|---|")
    for b in UNIT_ECONOMICS:
        out.append(f"| {_md_cell(b.metric)} | {b.target} | {_md_cell(b.notes)} |")
    out.append("")

    # Quick links
    out.append("## Quick links\n")
    out.append("- **Architecture** — `loop_implementation/architecture/ARCHITECTURE.md`")
    out.append("- **Data model** — `loop_implementation/data/SCHEMA.md`")
    out.append("- **API spec** — `loop_implementation/api/openapi.yaml`")
    out.append("- **ADRs** — `loop_implementation/adrs/README.md`")
    out.append("- **UX/UI** — `loop_implementation/ux/00_CANONICAL_TARGET_UX_STANDARD.md`")
    out.append("- **Engineering handbook** — `loop_implementation/engineering/HANDBOOK.md`")
    out.append("- **Security** — `loop_implementation/engineering/SECURITY.md`")
    out.append("- **Testing** — `loop_implementation/engineering/TESTING.md`")
    out.append("- **Sprint 0 plan** — `loop_implementation/tracker/SPRINT_0.md`")
    out.append("- **Master spec** — `botpress_competitor_spec.md`")
    out.append("")

    return "\n".join(out)


def render_json() -> dict[str, Any]:
    return {
        "_meta": {
            "source_file": "tools/build_tracker.py",
            "generated_by": "tools/build_tracker.py",
            "generated_at": datetime.now(UTC).isoformat(),
            "format_version": 2,
        },
        "epics": [asdict(e) for e in EPICS],
        "stories": [asdict(s) for s in STORIES],
        "sprints": [asdict(sp) for sp in SPRINTS],
        "hiring": [asdict(h) for h in HIRING],
        "risks": [asdict(r) for r in RISKS],
        "roadmap": [asdict(m) for m in ROADMAP],
        "perf_budgets": [asdict(b) for b in PERF_BUDGETS],
        "unit_economics": [asdict(b) for b in UNIT_ECONOMICS],
    }


def render_csvs() -> dict[str, list[list[str]]]:
    def stringify(v: Any) -> str:
        return "" if v is None else str(v)

    def rows_for(records: list[Any], fields: list[str]) -> list[list[str]]:
        out = [fields]
        for rec in records:
            d = asdict(rec)
            out.append([stringify(d[f]) for f in fields])
        return out

    return {
        "epics.csv": rows_for(EPICS, ["id", "name", "owner", "target", "status", "notes"]),
        "stories.csv": rows_for(
            STORIES,
            ["id", "title", "owner", "sprint", "epic", "points", "priority", "status", "notes"],
        ),
        "sprints.csv": rows_for(SPRINTS, ["id", "window", "theme", "goal", "stories", "status"]),
        "hiring.csv": rows_for(
            HIRING, ["n", "role", "why", "start_month", "stage", "owner", "notes"]
        ),
        "risks.csv": rows_for(
            RISKS, ["id", "risk", "likelihood", "severity", "owner", "mitigation", "status"]
        ),
        "roadmap.csv": rows_for(ROADMAP, ["month", "milestone", "deliverables", "status"]),
        "budgets.csv": rows_for(
            PERF_BUDGETS + UNIT_ECONOMICS, ["metric", "target", "owner", "notes"]
        ),
        "overview.csv": [
            ["key", "value"],
            ["title", "Loop — Implementation Tracker"],
            ["owner", "CTO"],
            ["sprint_length", "2 weeks (Sprint 0 is 6w bootstrap)"],
            ["epics_total", str(len(EPICS))],
            ["stories_total", str(len(STORIES))],
            ["stories_done", str(sum(1 for s in STORIES if s.status == "Done"))],
            ["stories_in_progress", str(sum(1 for s in STORIES if s.status == "In progress"))],
            ["stories_blocked", str(sum(1 for s in STORIES if s.status == "Blocked"))],
            ["sprints_total", str(len(SPRINTS))],
            ["risks_total", str(len(RISKS))],
        ],
    }


# --------------------------------------------------------------------------- #
# Output                                                                      #
# --------------------------------------------------------------------------- #


def write_outputs() -> None:
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    MD_PATH.write_text(render_md(), encoding="utf-8")
    JSON_PATH.write_text(
        json.dumps(render_json(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    for filename, rows in render_csvs().items():
        path = CSV_DIR / filename
        with path.open("w", encoding="utf-8", newline="") as fh:
            csv.writer(fh).writerows(rows)


def check_clean() -> int:
    """Return 0 if regenerating outputs would be a no-op; else 1."""
    expected_md = render_md()
    expected_json = json.dumps(render_json(), indent=2, ensure_ascii=False) + "\n"

    actual_md = MD_PATH.read_text(encoding="utf-8") if MD_PATH.exists() else ""
    actual_json = JSON_PATH.read_text(encoding="utf-8") if JSON_PATH.exists() else ""

    # Strip generated_at from both before comparing
    def _strip_ts(s: str) -> str:
        import re

        return re.sub(r'"generated_at":\s*"[^"]*"', '"generated_at": "<ts>"', s)

    drift: list[str] = []
    if actual_md != expected_md:
        drift.append("TRACKER.md")
    if _strip_ts(actual_json) != _strip_ts(expected_json):
        drift.append("tracker.json")
    if drift:
        print(f"tracker outputs are stale: {', '.join(drift)}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if outputs are stale")
    args = parser.parse_args()

    errors = validate()
    if errors:
        print("tracker validation errors:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 2

    if args.check:
        return check_clean()

    write_outputs()
    print(f"wrote {MD_PATH.relative_to(ROOT)}")
    print(f"wrote {JSON_PATH.relative_to(ROOT)}")
    for name in render_csvs():
        print(f"wrote {(CSV_DIR / name).relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
