"""Agent → story-set assignments.

Why this file exists
====================
We run four autonomous coding agents in parallel against the Loop backlog:

    codex-orion   — Backend services & control plane
                    (cp-api, dp-runtime, gateway, memory, helm self-host)
    codex-vega    — Data, ML, voice, observability
                    (KB/RAG, voice ASR/TTS, perf gates, MCP servers)
    copilot-thor  — Frontend & UX
                    (Studio, flow editor, TS SDK, CLI, docs site)
    copilot-titan — Channels, security, enterprise, ops
                    (channel adapters, SOC2, SSO/SAML, audit, HITL)

Without an explicit partition the picker keeps suggesting overlapping work
to every agent — two agents claim adjacent Studio screens, the close-time
merges fight over `apps/studio/src/lib/cp-api/generated.ts`, and parallel
execution corrupts. With an explicit partition each agent has a private
queue and the only synchronization point is `[extends Sxxx]` cross-deps,
which the picker already enforces.

How it's used
=============
``tools/pick_next_story.py --assigned-to <agent-id>`` filters its eligible
set down to ``ASSIGNMENTS[<agent-id>]`` before ranking. ``tools/agent_-
lifecycle.py pick`` forwards ``--assigned-to`` automatically using
``$LOOP_AGENT_ID`` so the agent never has to think about it.

How to update
=============
The four sets below MUST partition every "agent-doable" Not-started story.
"Agent-doable" excludes anything in ``HUMAN_ONLY`` (cloud-account
provisioning, auditor kickoff, sales conversion plans, etc.).

When you add a new StoryV2 to ``tools/_stories_v2.py``:

    1. If a human action is required (vendor signup, auditor signature,
       founder/CTO provisioning), add the SID to ``HUMAN_ONLY``.
    2. Otherwise, add it to whichever agent's set matches the file paths
       it'll touch. If a story spans domains, assign it to the agent
       whose code is the *primary* edit, and set ``[extends Sxxx]`` in
       its AC if it depends on another agent's work first.
    3. Run ``python tools/build_tracker.py`` and
       ``python -m pytest tests/test_agent_assignments.py`` (the latter
       enforces full coverage + zero overlap).
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Partition                                                                   #
# --------------------------------------------------------------------------- #


# Backend services & control plane: cp-api, dp-runtime, gateway, memory,
# tool-host, helm chart, terraform modules.
CODEX_ORION: frozenset[str] = frozenset(
    {
        # --- runtime / perf gates ---
        "S142",  # k6 baseline 100 turns/min for 5min, p95 latency report
        "S844",  # 1000 concurrent turns held by single dp-runtime pod
        # --- gateway ---
        "S841",  # gateway-cache hit ratio > 30% on fixed eval workload
        # --- tool-host (MCP runtime) ---
        "S843",  # tool-host warm-start < 300ms p95
        # --- memory adapters ---
        "S821",  # Zep adapter (drop-in)
        "S822",  # LangMem-style summarization variant
        # --- control plane ---
        "S263",  # deploy: image push w/ cosign signature
        "S845",  # cp-api 5000 RPS sustained
        "S636",  # ent: customer-managed KMS key (CMK) per workspace
        # --- terraform modules (currently Blocked — code can be written
        # offline; cloud-account validation is the blocker) ---
        "S770",  # AWS  (EKS+RDS+ElastiCache+S3+KMS+CloudFront)
        "S771",  # Azure (AKS+Postgres+Redis+Blob+Key Vault+Front Door)
        "S772",  # GCP  (GKE+CloudSQL+Memorystore+GCS+KMS+Cloud CDN)
        "S773",  # Alibaba (ACK+RDS+Redis+OSS+KMS+DCDN)
        "S774",  # OVHcloud (managed K8s+Postgres+Redis+S3-compat+KMS)
        "S775",  # Hetzner (HCloud K8s+Postgres+S3-compat+KMS)
        # --- helm self-host ---
        "S638",  # ent: dedicated single-tenant deploy mode
        # --- proof report (depends on the modules above) ---
        "S781",  # docs: cloud-portability proof report
    }
)


# Data / ML / voice / observability: KB engine, voice subsystem,
# observability + perf-gate harness, MCP servers.
CODEX_VEGA: frozenset[str] = frozenset(
    {
        # --- KB v1 productionisation ---
        "S494",  # kb-v1: scheduled refresh (cron + on-demand)
        "S495",  # kb-v1: incremental URL crawler (sitemap-aware)
        "S496",  # kb-v1: layout-aware chunking (tables, code, math)
        # --- KB v2 ---
        "S826",  # late-interaction retrieval (ColBERT-style)
        "S827",  # structured-data retrieval (CSV/Excel/JSON SQL-on-fly)
        # --- KB perf gate ---
        "S842",  # KB retrieval p50 < 200ms at 1M chunks per agent
        # --- voice latency budget (gates M11) ---
        "S651",  # TTS pre-warm + sentence-boundary streaming
        "S652",  # ASR/TTS model warm-up + connection pooling
        "S653",  # regional ASR/TTS endpoints (eu-west, ap-south)
        "S654",  # voice ≤700 ms p50 acceptance gate
        # --- voice e2e (currently Blocked — needs Twilio sandbox; agent
        # should attempt with mocked SIP, escalate if AC requires real) ---
        "S387",  # voice integration test phone call → agent → response
        # --- observability + perf gates ---
        "S805",  # SLO definitions per service + error-budget burn alerts
        "S846",  # 5%+ p95 regression blocks PR (CI gate)
        "S596",  # region: metadata-only telemetry (no PII) leaving region
    }
)


# Frontend & UX: Studio (Next.js), flow editor, TS SDK, CLI, docs site.
COPILOT_THOR: frozenset[str] = frozenset(
    {
        # --- Studio MVP stragglers ---
        "S155",  # studio: settings drawer (profile, region, theme)
        "S159",  # studio: agent overview tab
        # --- Studio cost / billing ---
        "S285",  # studio: cost filters (agent, channel, model, date)
        "S328",  # studio: billing — invoice list + download PDF
        # --- Studio flow editor ---
        "S469",  # flow: undo/redo with capped history
        "S471",  # flow: 3 starter templates (FAQ, support-triage, lead-qual)
        # --- Studio KB / region / SSO / audit (depend on backend stories
        # via [extends Sxxx]) ---
        "S497",  # studio: KB freshness indicators + manual refresh
        "S594",  # region: studio region selector at workspace creation
        "S615",  # sso: studio enterprise tab → connect IdP + upload metadata
        "S631",  # audit: studio audit log page (filterable, paginated)
        "S825",  # memory: memory-usage dashboard
        # --- GA polish ---
        "S655",  # design-system audit + component refactor
        "S656",  # a11y audit (WCAG 2.1 AA) on top 10 studio pages
        "S657",  # i18n scaffolding (en, es, de, fr, ja)
        # --- docs / launch material ---
        "S658",  # support runbook + ticketing integration (Front)
        "S659",  # docs.loop.example v1 (Mintlify) — getting started + 3 tutorials
        "S670",  # 1.0 release-notes draft + changelog automation
        "S671",  # pricing page + plan-comparison matrix
    }
)


# Channels, security, enterprise, ops: channel adapters, SOC2 controls,
# SSO/SAML, audit log + DPA, security gates, runbooks.
COPILOT_TITAN: frozenset[str] = frozenset(
    {
        # --- channels ---
        "S178",  # web-channel-js: typing indicator + sessionStorage history
        # --- SOC2 prep work that doesn't need the auditor ---
        "S576",  # soc2: pen-test prep (scope + RoE doc; coordination
        # with vendor is the human step, but the doc is doable)
        "S581",  # soc2: audit-trail completeness review
        "S635",  # audit: GDPR Art-17 data-deletion request endpoint
        # --- SSO / SAML ---
        "S610",  # sso: SAML SP impl via PySAML2
        "S611",  # sso: SCIM provisioning endpoint (RFC 7644)
        "S612",  # sso: Okta integration recipe + sandbox tenant test
        "S613",  # sso: Entra ID recipe + sandbox tenant test
        "S614",  # sso: Google Workspace recipe + sandbox test
        "S616",  # sso: just-in-time user provisioning at first login
        "S617",  # sso: SAML group → workspace role mapping rules
        "S618",  # sso: integration test full Okta SP-initiated login
        # --- audit log ---
        "S630",  # audit: audit_events table cp_0004 + write-only middleware
        "S632",  # audit: audit log export CSV
        "S633",  # audit: SIEM webhook (Datadog/Splunk/generic)
        "S634",  # audit: DPA template + redlines workflow
        # --- enterprise (BYO Vault — single-tenant deploy is codex-orion) ---
        "S637",  # ent: BYO Vault integration
        # --- security gates ---
        "S800",  # security: continuous fuzz testing (atheris/restler)
        "S801",  # security: STRIDE checklist gate per security-touching PR
        "S802",  # security: SLSA Level 3 build provenance (in-toto)
        "S803",  # security: runtime detection (Falco rules)
        "S804",  # security: chaos-engineering harness
        # --- ops ---
        "S806",  # ops: incident-response runbook + monthly game-day cadence
        "S807",  # ops: data-retention policy enforced by scheduled jobs
        "S808",  # ops: encrypted backup verification (restore-then-diff weekly)
    }
)


# Stories that genuinely require human action and should NOT be claimed by
# any agent. The picker excludes these regardless of --assigned-to.
HUMAN_ONLY: frozenset[str] = frozenset(
    {
        "S002",  # cloud accounts, Auth0, Stripe tenants — founder/CTO
        "S577",  # pen-test fix queue — depends on actual pen-test results
        "S582",  # SOC2 Type 1 attestation kickoff with auditor — auditor
        "S672",  # design partners → 10 paid customers conversion plan — sales
        "S673",  # HN / Product Hunt launch playbook executed — humans launch
        "S809",  # bug-bounty program launch (HackerOne / YesWeHack) — vendor signup
    }
)


# --------------------------------------------------------------------------- #
# Public API                                                                  #
# --------------------------------------------------------------------------- #

ASSIGNMENTS: dict[str, frozenset[str]] = {
    "codex-orion": CODEX_ORION,
    "codex-vega": CODEX_VEGA,
    "copilot-thor": COPILOT_THOR,
    "copilot-titan": COPILOT_TITAN,
}


def for_agent(agent_id: str) -> frozenset[str]:
    """Return the story-id set assigned to ``agent_id`` (frozenset, possibly empty).

    Unknown ids return an empty set so the picker simply finds nothing
    eligible — which is the safe failure mode (better than picking from
    every agent's queue and racing).
    """
    return ASSIGNMENTS.get(agent_id, frozenset())


def all_assigned_ids() -> frozenset[str]:
    """Union of every story id in any agent's queue."""
    out: frozenset[str] = frozenset()
    for s in ASSIGNMENTS.values():
        out = out | s
    return out
