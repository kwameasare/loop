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
        "Not started",
        "Week 1",
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
        "In progress",
        (
            "**Active.** "
            "Branch: copilot/s006-pg-migrations. "
            "Skill: skills/data/add-postgres-migration.md. "
            "Last step: 1/5 (claim). "
            "Heartbeat: 2026-04-30T02:00Z (GitHub Copilot). "
            "Open questions: none — using Alembic with two trees (control_plane, data_plane). "
            "Blockers: none. "
            "Commits: claim."
        ),
    ),
    Story(
        "S007",
        "LLM Gateway client: streaming OpenAI + Anthropic",
        "Eng #1",
        "S0",
        "E2",
        8,
        "P0",
        "Not started",
        "Week 2",
    ),
    Story(
        "S008",
        "TurnExecutor reasoning loop v0 (no tools yet)",
        "Eng #1",
        "S0",
        "E1",
        8,
        "P0",
        "Not started",
        "Week 2",
    ),
    Story(
        "S009",
        "OTel collector wired; first span exported to ClickHouse",
        "Eng #4",
        "S0",
        "E9",
        5,
        "P0",
        "Not started",
        "Week 2",
    ),
    Story(
        "S010",
        "Studio agents-list page (read from cp-api)",
        "Eng #5",
        "S0",
        "E10",
        3,
        "P1",
        "Not started",
        "Week 2",
    ),
    Story(
        "S011",
        "MCP client; auto-MCP decorator for Python functions",
        "Eng #1",
        "S0",
        "E3",
        8,
        "P0",
        "Not started",
        "Week 3",
    ),
    Story(
        "S012",
        "Multi-iteration reasoning loop with parallel tool dispatch",
        "Eng #1",
        "S0",
        "E1",
        5,
        "P0",
        "Not started",
        "Week 3",
    ),
    Story(
        "S013",
        "Memory loader/persister (user + session)",
        "Eng #1",
        "S0",
        "E4",
        5,
        "P0",
        "Not started",
        "Week 3",
    ),
    Story(
        "S014",
        "Firecracker via Kata k8s runtime class + prewarmed pool",
        "Eng #2",
        "S0",
        "E3",
        8,
        "P0",
        "Not started",
        "Week 3",
    ),
    Story(
        "S015",
        "KB engine v0: PDF ingest, Qdrant write, hybrid retrieval",
        "Eng #4",
        "S0",
        "E5",
        8,
        "P0",
        "Not started",
        "Week 3",
    ),
    Story(
        "S016",
        "Voice pipeline PoC (LiveKit + Deepgram + ElevenLabs)",
        "Eng #3",
        "S0",
        "E7",
        5,
        "P1",
        "Not started",
        "Week 3",
    ),
    Story(
        "S017",
        "Channel layer abstraction; web channel adapter (REST + SSE)",
        "Eng #1",
        "S0",
        "E6",
        5,
        "P0",
        "Not started",
        "Week 4",
    ),
    Story(
        "S018",
        "Slack channel adapter (Block Kit, slash command, threaded)",
        "Eng #1",
        "S0",
        "E6",
        5,
        "P0",
        "Not started",
        "Week 4",
    ),
    Story(
        "S019",
        "cp-api: Auth0 OIDC, workspace mgmt, API keys",
        "Eng #2",
        "S0",
        "E12",
        8,
        "P0",
        "Not started",
        "Week 4",
    ),
    Story(
        "S020",
        "Deploy controller v0: artifact → image → k8s",
        "Eng #2",
        "S0",
        "E12",
        8,
        "P0",
        "Not started",
        "Week 4",
    ),
    Story(
        "S021",
        "Eval harness skeleton: 6 scorers + `loop eval run`",
        "Eng #4",
        "S0",
        "E8",
        8,
        "P0",
        "Not started",
        "Week 4",
    ),
    Story(
        "S022",
        "Studio: trace waterfall + span detail tabs",
        "Eng #5",
        "S0",
        "E10",
        8,
        "P0",
        "Not started",
        "Week 4",
    ),
    Story(
        "S023",
        "WhatsApp channel adapter (Cloud API direct)",
        "Eng #1",
        "S0",
        "E6",
        8,
        "P0",
        "Not started",
        "Week 5",
    ),
    Story(
        "S024",
        "Streaming SSE: tool_call_start/end events on the wire",
        "Eng #1",
        "S0",
        "E1",
        3,
        "P1",
        "Not started",
        "Week 5",
    ),
    Story(
        "S025",
        "Stripe billing wire-up (test); usage rollup nightly job",
        "Eng #2",
        "S0",
        "E19",
        5,
        "P0",
        "Not started",
        "Week 5",
    ),
    Story(
        "S026",
        "Eval harness: production-replay capture (failed turns)",
        "Eng #4",
        "S0",
        "E8",
        5,
        "P1",
        "Not started",
        "Week 5",
    ),
    Story(
        "S027",
        "Studio: cost dashboard v0 (workspace MTD + per-agent)",
        "Eng #5",
        "S0",
        "E10",
        5,
        "P0",
        "Not started",
        "Week 5",
    ),
    Story(
        "S028",
        "Examples repo: support_agent + docs site v0",
        "Eng #6",
        "S0",
        "E17",
        5,
        "P0",
        "Not started",
        "Week 5",
    ),
    Story(
        "S029",
        "Hard caps + graceful degrade; budget pre-flight at gateway",
        "Eng #1",
        "S0",
        "E2",
        5,
        "P0",
        "Not started",
        "Week 6",
    ),
    Story(
        "S030",
        "HITL takeover endpoint + operator inbox queue",
        "Eng #1",
        "S0",
        "E15",
        5,
        "P1",
        "Not started",
        "Week 6",
    ),
    Story(
        "S031",
        "Eval-gated deploy: block prod promotion on regression",
        "Eng #4",
        "S0",
        "E8",
        5,
        "P0",
        "Not started",
        "Week 6",
    ),
    Story(
        "S032",
        "Studio: operator inbox MVP (queue + takeover + composer)",
        "Eng #5",
        "S0",
        "E15",
        8,
        "P1",
        "Not started",
        "Week 6",
    ),
    Story(
        "S033",
        "Voice MVP: web-RTC echo agent end-to-end",
        "Eng #3",
        "S0",
        "E7",
        8,
        "P0",
        "Not started",
        "Week 6",
    ),
    Story(
        "S034",
        "First 3 design partners onboarded; weekly office hour",
        "CEO",
        "S0",
        "E17",
        3,
        "P0",
        "Not started",
        "Week 6",
    ),
    Story(
        "S035",
        "Episodic memory (Qdrant collection + auto-summarize)",
        "Eng #1",
        "S1",
        "E4",
        8,
        "P1",
        "Not started",
        "M7",
    ),
    Story(
        "S036",
        "Helm chart for self-host with feature parity goal",
        "Eng #2",
        "S1",
        "E13",
        13,
        "P0",
        "Not started",
        "M7",
    ),
    Story(
        "S037",
        "Email channel via SES; Telegram channel",
        "Eng #7",
        "S1",
        "E6",
        8,
        "P1",
        "Not started",
        "M7",
    ),
    Story(
        "S038",
        "Multi-agent v0: Supervisor + Pipeline patterns",
        "Eng #1",
        "S1",
        "E14",
        13,
        "P1",
        "Not started",
        "M7",
    ),
    Story(
        "S039",
        "TS SDK auto-gen from Pydantic types",
        "Eng #5",
        "S1",
        "E11",
        8,
        "P1",
        "Not started",
        "M8",
    ),
    Story("S040", "Discord + Teams channels", "Eng #7", "S1", "E6", 8, "P2", "Not started", "M8"),
    Story(
        "S041",
        "Replay/time-travel debugging in Studio",
        "Eng #5",
        "S1",
        "E10",
        8,
        "P1",
        "Not started",
        "M8",
    ),
    Story(
        "S042",
        "Multi-agent GA: Parallel + AgentGraph (cyclic)",
        "Eng #1",
        "S1",
        "E14",
        13,
        "P0",
        "Not started",
        "M9",
    ),
    Story(
        "S043",
        "Public eval registry (community suites)",
        "Eng #4",
        "S1",
        "E8",
        8,
        "P1",
        "Not started",
        "M9",
    ),
    Story(
        "S044",
        "Series A fundraise narrative + data room",
        "CEO",
        "S1",
        "—",
        5,
        "P0",
        "Not started",
        "M9",
    ),
    Story(
        "S045",
        "EU region (`eu-west`) deploy on chosen cloud (cloud-agnostic)",
        "Eng #2",
        "S1",
        "E12",
        13,
        "P0",
        "Not started",
        "M10",
    ),
    Story(
        "S046",
        "SOC2 Type 1 kickoff with Vanta",
        "Sec eng",
        "S1",
        "E16",
        13,
        "P0",
        "Not started",
        "M10",
    ),
    Story(
        "S047",
        "Salesforce + Zendesk first-party MCP servers",
        "Eng #6",
        "S1",
        "E18",
        13,
        "P1",
        "Not started",
        "M10",
    ),
    Story(
        "S048",
        "Voice latency push to ≤700ms p50",
        "Eng #3",
        "S1",
        "E7",
        13,
        "P0",
        "Not started",
        "M11",
    ),
    Story(
        "S049",
        "Phone number provisioning at the Loop layer",
        "Eng #3",
        "S1",
        "E7",
        8,
        "P1",
        "Not started",
        "M11",
    ),
    Story(
        "S050",
        "Enterprise GA: SSO/SAML, audit log UI, on-prem parity",
        "Eng #2",
        "S1",
        "E20",
        13,
        "P0",
        "Not started",
        "M12",
    ),
]


SPRINTS: list[Sprint] = [
    Sprint(
        "S0",
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
    out.append("- **UX/UI** — `loop_implementation/ux/UX_DESIGN.md`")
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
