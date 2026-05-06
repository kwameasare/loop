"""Canonical target UX/UI implementation backlog.

Why this file exists
====================
The canonical target standard at
``loop_implementation/ux/00_CANONICAL_TARGET_UX_STANDARD.md`` is intentionally
large: it defines the full north-star Studio experience, not a small patch.
This file breaks that target into implementable, conflict-aware stories for a
single high-intensity UI/UX implementation cycle.

This is deliberately separate from ``tools/_stories_v2.py``. The existing V2
backlog is the production tracker source used by ``agent_lifecycle.py`` today.
The UX cycle should be reviewed and activated intentionally before those
stories are copied into the live tracker. Until then, this module is the
canonical planning source for the UX/UI overhaul.

How this links to the agent workflow
====================================
Every story below references:

* canonical standard sections from ``00_CANONICAL_TARGET_UX_STANDARD.md``
* required UX/coding skills from ``loop_implementation/skills``
* primary file ownership paths to reduce merge conflicts
* explicit dependencies via ``depends_on``

The companion ``tools/_agent_assignments_ux.py`` partitions every story across
the four agents from ``tools/_agent_assignments.py``:

* codex-orion
* codex-vega
* copilot-thor
* copilot-titan

Activation rule
===============
Start with the blocking foundation stories owned by ``codex-orion``. No other
agent should start feature-surface work until UX001-UX004 are merged. UX005 and
UX006 are strong early follow-ups but do not need to block every parallel
surface if UX001-UX004 already provide the shell, primitives, and fixture
contracts.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UXStory:
    """One target-UX implementation slice.

    ``acceptance`` is intentionally concrete enough for an AI agent to turn into
    a PR checklist. ``primary_paths`` is the merge-conflict boundary: the owning
    agent should stay inside those paths unless the story explicitly says
    otherwise.
    """

    id: str
    title: str
    phase: str
    area: str
    points: int
    priority: str
    canonical_sections: tuple[str, ...]
    skills: tuple[str, ...]
    primary_paths: tuple[str, ...]
    depends_on: tuple[str, ...]
    acceptance: str
    notes: str = ""


CYCLE_ID = "UX-CANONICAL-ONE-CYCLE"
DEFAULT_STATUS = "Not started"


UX_STORIES: list[UXStory] = [
    # ------------------------------------------------------------------
    # Gate A: shared foundation. Start these first with codex-orion.
    # ------------------------------------------------------------------
    UXStory(
        "UX001",
        "Studio shell: canonical six-verb IA and five-region layout",
        "Gate A - blocking foundation",
        "foundation/shell",
        3,
        "P0",
        ("5", "6", "23", "31"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/components/shell/**",
            "apps/studio/src/app/layout.tsx",
            "apps/studio/src/app/page.tsx",
            "apps/studio/src/lib/navigation*",
        ),
        (),
        (
            "AC: Studio exposes Build/Test/Ship/Observe/Migrate/Govern as the "
            "primary IA, not as decorative copy. The shell has named regions "
            "for asset rail, topbar/context bar, work surface, live "
            "preview/inspector, activity timeline, and system status. The "
            "topbar shows workspace, agent, environment, branch/state, command "
            "entry, and user controls. The shell is mounted from the root app "
            "layout so every feature surface inherits it; auth-only layouts "
            "must not create a second shell. Navigation items use icons, "
            "active state, keyboard focus, route-safe links, and concise "
            "builder-facing summaries. Mobile/tablet fallbacks stack regions "
            "without hiding core status or leaving orphan pages outside the IA."
        ),
        (
            "Blocks all feature-surface work because every surface mounts into "
            "this shell. A PR is not acceptable if it only adds a sidebar; it "
            "must make the canonical workbench frame real and reusable."
        ),
    ),
    UXStory(
        "UX002",
        "Target visual system: tokens, density, motion, status grammar",
        "Gate A - blocking foundation",
        "foundation/design-system",
        3,
        "P0",
        ("28", "29", "30", "31", "32"),
        ("ux/add-design-token.md", "ux/add-studio-component.md"),
        (
            "apps/studio/src/app/globals.css",
            "apps/studio/src/lib/design-tokens.ts",
            "apps/studio/src/components/ui/**",
        ),
        (),
        (
            "AC: design tokens cover the canonical palette, card/surface "
            "layers, semantic success/warning/info/destructive colors, "
            "object states, trust states, confidence levels, trace span "
            "shapes, density modes, focus rings, motion durations/easing, "
            "reduced-motion behavior, and dark/light contrast. Tailwind and "
            "CSS variables stay in sync. New target components must consume "
            "semantic tokens/classes instead of raw color literals, and the "
            "hardcoded-color audit must keep passing."
        ),
        (
            "No other agent should add new shared tokens until this lands. If "
            "a feature needs an additional color/status/motion token, it should "
            "extend this shared grammar instead of inventing a local one."
        ),
    ),
    UXStory(
        "UX003",
        "Target primitive kit: evidence, confidence, risk, diff, live, stage, snapshot",
        "Gate A - blocking foundation",
        "foundation/primitives",
        3,
        "P0",
        ("23", "28", "29", "32", "37"),
        ("ux/add-studio-component.md", "ux/write-ui-copy.md"),
        (
            "apps/studio/src/components/target/**",
            "apps/studio/src/components/ui/**",
        ),
        ("UX002",),
        (
            "AC: shared primitives exist and are exported from a stable target "
            "component barrel: EvidenceCallout, ConfidenceMeter, RiskHalo, "
            "DiffRibbon, LiveBadge, StageStepper, MetricCountUp, SnapshotCard, "
            "SceneCard, PermissionBoundary, and StatePanel. Each primitive "
            "must render accessible text, non-color status affordances where "
            "status is shown, stable sizing that will not jump under dynamic "
            "content, and friendly precision copy. Tests must cover evidence "
            "with source/confidence, risk/object-state rendering, gated "
            "permissions, snapshot/scene cards, and semantic diff display."
        ),
        (
            "Feature agents consume these primitives instead of creating local "
            "duplicates. Fake implementations that only render plain divs with "
            "names matching the components do not satisfy this story."
        ),
    ),
    UXStory(
        "UX004",
        "Target UX fixture and view-model contracts",
        "Gate A - blocking foundation",
        "foundation/data-contracts",
        3,
        "P0",
        ("1", "23", "36", "39"),
        ("coding/implement-studio-screen.md", "ux/design-studio-surface.md"),
        (
            "apps/studio/src/lib/target-ux/**",
            "apps/studio/src/lib/fixtures/**",
            "apps/studio/src/lib/*.test.ts",
        ),
        (),
        (
            "AC: typed view models and fixture builders cover agents, traces, "
            "tools, memory, evals, migration, deploys, costs, inbox, "
            "enterprise controls, snapshots, scenes, and command/search. "
            "Fixtures must be coherent across domains: traces point at real "
            "snapshots, deploys point at real agents, migration lineage has a "
            "snapshot, and commands map to canonical domains. The contract "
            "must live outside generated cp-api output and provide tests that "
            "prove every canonical domain has at least one fixture."
        ),
        (
            "Prevents merge conflicts on apps/studio/src/lib/cp-api/generated.ts "
            "during the UX cycle. Feature surfaces should consume these "
            "view-models for mock-first UI while backend contracts catch up."
        ),
    ),
    UXStory(
        "UX005",
        "State, copy, and localization kit for target surfaces",
        "Gate A - early foundation",
        "foundation/states-copy",
        2,
        "P0",
        ("30", "32", "Appendix C"),
        ("ux/write-ui-copy.md", "ux/add-studio-component.md"),
        (
            "apps/studio/src/components/target/state/**",
            "apps/studio/src/components/section-states.tsx",
            "apps/studio/src/app/**/loading.tsx",
            "apps/studio/src/app/**/error.tsx",
            "apps/studio/src/locales/**",
        ),
        ("UX002", "UX003"),
        "AC: reusable loading, empty, error, degraded, stale, and permission-blocked states exist with friendly precision copy and i18n keys.",
    ),
    UXStory(
        "UX006",
        "Canonical shell visual/a11y smoke harness",
        "Gate A - early foundation",
        "foundation/quality",
        2,
        "P0",
        ("30", "37", "39"),
        ("ux/review-studio-ux.md", "testing/write-e2e-test.md"),
        (
            "apps/studio/e2e/canonical-ux.spec.ts",
            "apps/studio/src/components/__a11y__/**",
            "apps/studio/a11y/**",
        ),
        ("UX001", "UX002", "UX003"),
        "AC: Playwright/a11y smoke checks cover shell layout, keyboard navigation, reduced motion, focus visibility, and non-color status on desktop and mobile.",
    ),

    # ------------------------------------------------------------------
    # codex-orion: Build surfaces and agent control primitives.
    # ------------------------------------------------------------------
    UXStory(
        "UX101",
        "Agent Workbench: profile, outline, object state, and live preview",
        "Parallel feature surface",
        "build/agent-workbench",
        3,
        "P0",
        ("7", "23", "31", "32"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/app/agents/**",
            "apps/studio/src/components/agents/**",
        ),
        ("UX001", "UX003", "UX004"),
        "AC: agent detail shows canonical profile, outline, tools/knowledge/memory/evals/deploy state, environment, branch, diff-from-production, and safe next actions.",
    ),
    UXStory(
        "UX102",
        "Behavior Editor: three levels, risk flags, semantic diff, sentence telemetry",
        "Parallel feature surface",
        "build/behavior-editor",
        3,
        "P0",
        ("11", "23", "26", "32"),
        ("ux/design-studio-surface.md", "ux/write-ui-copy.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/app/agents/[agent_id]/behavior/**",
            "apps/studio/src/components/behavior/**",
            "apps/studio/src/lib/behavior*",
        ),
        ("UX001", "UX003", "UX004"),
        "AC: behavior surface supports plain-language, structured-policy, and code/config modes with inline risk flags, sentence telemetry, semantic diff, eval coverage, and preview-before-apply.",
    ),
    UXStory(
        "UX103",
        "Agent Map: comprehension-first map, inspector, hazards, fork from here",
        "Parallel feature surface",
        "build/agent-map",
        3,
        "P1",
        ("8", "23", "30"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/app/agents/[agent_id]/map/**",
            "apps/studio/src/components/agent-map/**",
            "apps/studio/src/components/flow/**",
        ),
        ("UX001", "UX003", "UX004"),
        "AC: map is instrumentation/comprehension-first, exposes dependency/tool/memory/eval coverage, opens inspectors, rejects invalid edits, and never becomes the only place logic is understood.",
    ),
    UXStory(
        "UX104",
        "Tools Room: catalog, detail, safety contract, mock/live, instant tool from curl",
        "Parallel feature surface",
        "build/tools-room",
        3,
        "P0",
        ("12", "23", "24", "32"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md", "security/secrets-kms-check.md"),
        (
            "apps/studio/src/app/agents/[agent_id]/tools/**",
            "apps/studio/src/components/tools/**",
            "apps/studio/src/lib/agent-tools*",
        ),
        ("UX001", "UX003", "UX004"),
        "AC: tool UI shows schema, auth, side-effect class, owner, usage, failure, cost, eval coverage, mock/live status, production grant boundaries, and curl/OpenAPI/Postman-to-draft flow.",
    ),
    UXStory(
        "UX105",
        "Memory Studio: explorer, memory diff, safety flags, replay controls",
        "Parallel feature surface",
        "build/memory-studio",
        3,
        "P0",
        ("14", "23", "30", "32"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/app/agents/[agent_id]/memory/**",
            "apps/studio/src/components/memory/**",
            "apps/studio/src/lib/memory*",
        ),
        ("UX001", "UX003", "UX004"),
        "AC: memory surface shows session/user/episodic/scratch memory, before/after diffs, source traces, retention policy, PII/secret/conflict flags, deletion, and replay with/without memory.",
    ),
    UXStory(
        "UX106",
        "Multi-Agent Conductor: sub-agent assets, handoff contracts, conductor view",
        "Parallel feature surface",
        "build/multi-agent",
        2,
        "P1",
        ("17", "23", "25"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/app/agents/[agent_id]/conductor/**",
            "apps/studio/src/components/conductor/**",
            "apps/studio/src/lib/conductor*",
        ),
        ("UX001", "UX003", "UX004"),
        "AC: conductor view exposes sub-agent purpose, tools, budgets, handoff contracts, current ownership, failure paths, and traceable delegation without hidden orchestration.",
    ),
    UXStory(
        "UX107",
        "Build-to-test flow: fork, preview, save-as-eval, and branch state",
        "Parallel integration surface",
        "build/workflow-integration",
        2,
        "P0",
        ("8.5", "9", "15", "23"),
        ("coding/implement-studio-screen.md", "ux/review-studio-ux.md"),
        (
            "apps/studio/src/components/agents/**",
            "apps/studio/src/components/behavior/**",
            "apps/studio/src/lib/target-ux/build-flow*",
        ),
        ("UX101", "UX102", "UX201", "UX204"),
        "AC: from an agent or behavior edit, builder can preview, fork from a turn, save a run as eval, and see Draft/Saved/Staged state without contaminating production.",
    ),

    # ------------------------------------------------------------------
    # codex-vega: Test, observe, knowledge, voice, and cost surfaces.
    # ------------------------------------------------------------------
    UXStory(
        "UX201",
        "Simulator and Conversation Lab: multi-channel preview and ChatOps",
        "Parallel feature surface",
        "test/simulator",
        3,
        "P0",
        ("9", "27.6", "31", "32"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/components/simulator/**",
            "apps/studio/src/components/agents/emulator-panel*",
            "apps/studio/src/lib/emulator*",
        ),
        ("UX001", "UX003", "UX004"),
        "AC: simulator supports web/Slack/WhatsApp/SMS/email/voice shells, seeded context, memory modes, tool disable, model swap, persona user, replay command, and side-by-side version diff.",
    ),
    UXStory(
        "UX202",
        "Trace Theater: summary, waterfall, span inspector, explain-without-inventing",
        "Parallel feature surface",
        "observe/trace-theater",
        3,
        "P0",
        ("10.1", "10.2", "10.3", "10.4", "30"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md", "ux/write-ui-copy.md"),
        (
            "apps/studio/src/app/traces/**",
            "apps/studio/src/components/trace/**",
            "apps/studio/src/lib/traces*",
        ),
        ("UX001", "UX003", "UX004"),
        "AC: trace detail shows outcome, latency, cost, model, tools, retrieval, memory, eval/deploy metadata, accessible waterfall, span inspector, redaction view, and evidence-grounded explanations.",
    ),
    UXStory(
        "UX203",
        "Trace Scrubber and Agent X-Ray",
        "Parallel feature surface",
        "observe/trace-time-travel",
        3,
        "P0",
        ("10.5", "10.6", "10.7", "10.8"),
        ("ux/add-studio-component.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/components/trace/scrubber/**",
            "apps/studio/src/components/trace/xray/**",
            "apps/studio/src/lib/trace-scrubber*",
            "apps/studio/src/lib/agent-xray*",
        ),
        ("UX202",),
        "AC: builder can scrub a trace playhead, inspect context/tool/retrieval/memory state per frame, fork from frame, and view X-Ray claims with representative trace evidence.",
    ),
    UXStory(
        "UX204",
        "Eval Foundry: creation, suite builder, result view",
        "Parallel feature surface",
        "test/eval-foundry",
        3,
        "P0",
        ("15.1", "15.2", "15.3", "23", "32"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/app/evals/**",
            "apps/studio/src/components/evals/**",
            "apps/studio/src/lib/evals*",
        ),
        ("UX001", "UX003", "UX004"),
        "AC: eval UI creates cases from simulator/production/operator/migration/KB, builds suites with scorers/fixtures/thresholds, and shows before/after output, trace/tool/retrieval/memory/cost/latency diffs.",
    ),
    UXStory(
        "UX205",
        "Production replay, persona simulator, property tester, scenes",
        "Parallel feature surface",
        "test/replay-scenes",
        3,
        "P0",
        ("15.4", "15.5", "15.6", "15.8", "36"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/app/replay/**",
            "apps/studio/src/components/replay/**",
            "apps/studio/src/components/scenes/**",
            "apps/studio/src/lib/replay*",
            "apps/studio/src/lib/scenes*",
        ),
        ("UX202", "UX204"),
        "AC: production conversation can replay against draft, run persona/property variations, cluster failures, convert to evals, and save canonical scenes with provenance.",
    ),
    UXStory(
        "UX206",
        "Knowledge Atelier: sources, chunks, retrieval lab, Why panel, readiness",
        "Parallel feature surface",
        "build/knowledge-atelier",
        3,
        "P0",
        ("13.1", "13.2", "13.3", "13.4", "13.5"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/app/agents/[agent_id]/kb/**",
            "apps/studio/src/components/knowledge/**",
            "apps/studio/src/components/agents/kb-*",
            "apps/studio/src/lib/knowledge*",
        ),
        ("UX001", "UX003", "UX004"),
        "AC: knowledge surface shows source freshness/owner/access/sync/errors/chunks/eval coverage, visible chunking, retrieval lab score breakdown, Why panel, and readiness report.",
    ),
    UXStory(
        "UX207",
        "Inverse Retrieval Lab and Embeddings Explorer",
        "Parallel feature surface",
        "build/knowledge-diagnostics",
        3,
        "P1",
        ("13.6", "13.7", "30"),
        ("ux/add-studio-component.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/components/knowledge/inverse-retrieval/**",
            "apps/studio/src/components/knowledge/embeddings-explorer/**",
            "apps/studio/src/lib/knowledge-diagnostics*",
        ),
        ("UX206",),
        "AC: for any chunk, builder sees production queries that should have retrieved it, miss reasons, one-click repairs, and an accessible cluster/outlier/duplicate/citation explorer with table fallback.",
    ),
    UXStory(
        "UX208",
        "Voice Stage: voice preview, config, evals, queued speech, demo links",
        "Parallel feature surface",
        "test/voice-stage",
        3,
        "P0",
        ("16", "31", "32"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/app/voice/**",
            "apps/studio/src/components/voice/**",
            "apps/studio/src/lib/voice*",
        ),
        ("UX001", "UX003", "UX004"),
        "AC: voice surface shows waveform, ASR/TTS spans, barge-in, latency markers, config, voice evals, queued speech preview in dev/staging, and audited expiring demo links.",
    ),
    UXStory(
        "UX209",
        "Observatory: dashboards, anomalies, production tail, ambient health",
        "Parallel feature surface",
        "observe/observatory",
        3,
        "P0",
        ("20", "29.6", "31.4", "37"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/app/observe/**",
            "apps/studio/src/components/observatory/**",
            "apps/studio/src/lib/observatory*",
        ),
        ("UX001", "UX003", "UX004", "UX202"),
        "AC: observatory shows health/quality/latency/cost/knowledge/tools/channels/deploy/eval dashboards, anomaly cards with next action, pause-able production tail, and clickable ambient health arcs.",
    ),
    UXStory(
        "UX210",
        "Cost and latency: cost surfaces, decisions, line items, latency budget visualizer",
        "Parallel feature surface",
        "observe/cost-capacity",
        3,
        "P0",
        ("22", "23", "32"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md", "ux/write-ui-copy.md"),
        (
            "apps/studio/src/app/costs/**",
            "apps/studio/src/components/cost/**",
            "apps/studio/src/lib/cost*",
            "apps/studio/src/lib/latency*",
        ),
        ("UX001", "UX003", "UX004"),
        "AC: cost UI shows per-turn/agent/channel/model/tool/retrieval/environment/customer segment and projected month-end, plus line-item math and latency budget suggestions with quality/cost impact.",
    ),

    # ------------------------------------------------------------------
    # copilot-titan: Migrate, ship, govern, HITL, collaboration.
    # ------------------------------------------------------------------
    UXStory(
        "UX301",
        "Migration Atelier: entry, supported sources, import wizard, three-pane review",
        "Parallel feature surface",
        "migrate/import",
        3,
        "P0",
        ("18.1", "18.2", "18.3", "18.4", "40"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/app/migrate/**",
            "apps/studio/src/components/migration/**",
            "apps/studio/src/lib/migration*",
        ),
        ("UX001", "UX003", "UX004"),
        "AC: migration entry treats import as first-class, labels sources verified/planned/aspirational, guides source upload/connect/analyze/inventory/map/gap/parity/stage, and shows source/middle/Loop panes.",
    ),
    UXStory(
        "UX302",
        "Botpress parity harness, migration diff modes, assisted repair, cutover",
        "Parallel feature surface",
        "migrate/parity-cutover",
        3,
        "P0",
        ("18.5", "18.6", "18.7", "18.8", "18.9", "18.10", "18.11", "18.12", "18.13"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md", "ux/write-ui-copy.md"),
        (
            "apps/studio/src/components/migration/**",
            "apps/studio/src/lib/migration-parity*",
            "apps/studio/src/lib/botpress-import*",
        ),
        ("UX301",),
        "AC: Botpress flow preserves lineage, shows readiness, structure/behavior/cost/risk diff modes, parity replay, grounded repair suggestions, migration workspace, shadow traffic, canary cutover, and rollback.",
    ),
    UXStory(
        "UX303",
        "Deployment Flight Deck: environments, preflight, promotion, canary, rollback",
        "Parallel feature surface",
        "ship/deployment",
        3,
        "P0",
        ("19.1", "19.2", "19.3", "19.4", "19.5", "19.6", "23"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md", "security/add-audit-event.md"),
        (
            "apps/studio/src/app/agents/[agent_id]/deploys/**",
            "apps/studio/src/app/deploys/**",
            "apps/studio/src/components/deploy/**",
            "apps/studio/src/components/agents/deploy-*",
            "apps/studio/src/lib/deploys*",
        ),
        ("UX001", "UX003", "UX004", "UX204"),
        "AC: deploy surface shows environment-specific config, behavior/tool/knowledge/memory/channel/budget diffs, eval gates, approval requirements, canary slider, auto-rollback triggers, and audited rollback.",
    ),
    UXStory(
        "UX304",
        "What Could Break, regression bisect, snapshots",
        "Parallel feature surface",
        "ship/time-travel-safety",
        3,
        "P0",
        ("19.7", "19.8", "19.9", "23.5"),
        ("ux/add-studio-component.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/components/deploy/what-could-break/**",
            "apps/studio/src/components/deploy/regression-bisect/**",
            "apps/studio/src/components/snapshots/**",
            "apps/studio/src/lib/snapshots*",
        ),
        ("UX303", "UX202", "UX205"),
        "AC: pre-promote shows top likely behavior changes from production, old/new replay diffs, bisect result with confidence, and signed branchable snapshots for incident/demo/audit use.",
    ),
    UXStory(
        "UX305",
        "Inbox and HITL: queue, takeover, resolution to eval",
        "Parallel feature surface",
        "observe/hitl",
        3,
        "P0",
        ("21", "15.1", "25.4", "32"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md", "ux/write-ui-copy.md"),
        (
            "apps/studio/src/app/inbox/**",
            "apps/studio/src/components/inbox/**",
            "apps/studio/src/lib/conversation*",
            "apps/studio/src/lib/inbox*",
        ),
        ("UX001", "UX003", "UX004"),
        "AC: inbox shows queue filters, SLA/owner/reason, trace/memory/tool/retrieval evidence, takeover silence, suggested draft, handback/resolve, and one-click eval creation from operator resolution.",
    ),
    UXStory(
        "UX306",
        "Enterprise Govern: identity, RBAC, approvals, audit, residency, BYOK, procurement",
        "Parallel feature surface",
        "govern/enterprise",
        3,
        "P0",
        ("24", "23", "32"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md", "security/update-threat-model.md"),
        (
            "apps/studio/src/app/enterprise/**",
            "apps/studio/src/app/workspaces/**",
            "apps/studio/src/components/enterprise/**",
            "apps/studio/src/components/workspaces/**",
            "apps/studio/src/lib/enterprise*",
            "apps/studio/src/lib/audit*",
        ),
        ("UX001", "UX003", "UX004"),
        "AC: govern surfaces show SSO/SCIM, RBAC matrix, approvals, audit explorer, data residency, BYOK, whitelabel, procurement evidence, private skill library, and policy/audit consequences.",
    ),
    UXStory(
        "UX307",
        "Collaboration: presence, comments, changesets, comments-as-specs, pair debugging",
        "Parallel feature surface",
        "collaboration/review",
        3,
        "P1",
        ("25", "23.5", "30"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/components/collaboration/**",
            "apps/studio/src/components/comments/**",
            "apps/studio/src/lib/collaboration*",
            "apps/studio/src/lib/comments*",
        ),
        ("UX001", "UX003", "UX004", "UX204"),
        "AC: comments attach to stable object IDs, survive versions, resolve into eval specs, changesets show behavior/eval/cost/latency approvals, and pair debugging supports shared trace playhead.",
    ),
    UXStory(
        "UX308",
        "AI Co-Builder: consent grammar, provenance, Rubber Duck, Second Pair Of Eyes",
        "Parallel feature surface",
        "collaboration/ai-cobuilder",
        3,
        "P1",
        ("26", "23", "32"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md", "ux/write-ui-copy.md"),
        (
            "apps/studio/src/components/ai-cobuilder/**",
            "apps/studio/src/lib/ai-cobuilder*",
        ),
        ("UX001", "UX003", "UX004", "UX102", "UX204"),
        "AC: co-builder shows current selection context, Suggest/Edit/Drive modes, exact diffs, provenance, budget/permission constraints, diagnostic Rubber Duck fixes, and adversarial five-bullet review with evidence.",
    ),

    # ------------------------------------------------------------------
    # copilot-thor: horizontal surfaces after foundation.
    # ------------------------------------------------------------------
    UXStory(
        "UX401",
        "Command, search, saved searches, sharing, redaction, quick branch links",
        "Parallel horizontal surface",
        "horizontal/command-sharing",
        3,
        "P0",
        ("27", "23.4", "24.4", "30"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md", "ux/write-ui-copy.md"),
        (
            "apps/studio/src/components/command/**",
            "apps/studio/src/components/search/**",
            "apps/studio/src/components/sharing/**",
            "apps/studio/src/lib/command*",
            "apps/studio/src/lib/search*",
            "apps/studio/src/lib/sharing*",
        ),
        ("UX001", "UX003", "UX004"),
        "AC: global command palette, contextual find, saved searches, permissioned sharing, redaction preview, access log, revoke, inline ChatOps autocomplete, and quick branch review links work across target surfaces.",
    ),
    UXStory(
        "UX402",
        "Onboarding: three doors, templates, guided spotlight, first-week/month/quarter, concierge",
        "Parallel horizontal surface",
        "horizontal/onboarding",
        3,
        "P0",
        ("4.8", "4.9", "4.10", "33", "36"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md", "ux/write-ui-copy.md"),
        (
            "apps/studio/src/app/onboarding/**",
            "apps/studio/src/components/onboarding/**",
            "apps/studio/src/components/templates/**",
            "apps/studio/src/lib/onboarding*",
        ),
        ("UX001", "UX003", "UX004", "UX301"),
        "AC: first-run offers Import/Template/Blank only, templates are working agents with KB/tools/evals/traces/cost, spotlight has three hints, and concierge can learn from recent conversations with explicit consent.",
    ),
    UXStory(
        "UX403",
        "Marketplace and private skill library",
        "Parallel horizontal surface",
        "horizontal/marketplace",
        2,
        "P1",
        ("24.9", "34"),
        ("ux/design-studio-surface.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/app/marketplace/**",
            "apps/studio/src/components/marketplace/**",
            "apps/studio/src/lib/marketplace*",
        ),
        ("UX001", "UX003", "UX004"),
        "AC: marketplace supports tools, templates, skills, eval packs, KB connectors, channel packs, private workspace publishing, versioning, deprecation, review, usage, and trust metadata.",
    ),
    UXStory(
        "UX404",
        "Responsive modes: mobile urgent actions, tablet review, second-monitor, large display",
        "Parallel horizontal surface",
        "horizontal/responsive",
        3,
        "P0",
        ("31", "20.4", "21", "19"),
        ("ux/review-studio-ux.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/components/shell/**",
            "apps/studio/src/components/responsive/**",
            "apps/studio/e2e/responsive-ux.spec.ts",
        ),
        ("UX001", "UX003", "UX202", "UX303", "UX305"),
        "AC: desktop retains full power; tablet supports review/approval/parity; mobile supports incident/deploy/approval/rollback/takeover summaries only; second-monitor mode shows timeline, production tail, inbox, and deploy health.",
    ),
    UXStory(
        "UX405",
        "Accessibility, i18n, color-blind safety, keyboard sweep",
        "Parallel horizontal quality",
        "horizontal/accessibility",
        3,
        "P0",
        ("30", "37", "39"),
        ("ux/review-studio-ux.md", "testing/write-e2e-test.md"),
        (
            "apps/studio/src/components/__a11y__/**",
            "apps/studio/e2e/a11y-*.spec.ts",
            "apps/studio/src/locales/**",
            "apps/studio/a11y/**",
        ),
        ("UX005", "UX101", "UX202", "UX301", "UX303", "UX305"),
        "AC: target top surfaces pass keyboard, focus, reduced-motion, screen-reader, color-independent status, text-fit, and localization smoke checks.",
    ),
    UXStory(
        "UX406",
        "Creative polish: ambient life, earned moments, sound/tactility, skeletons",
        "Parallel horizontal polish",
        "horizontal/polish",
        2,
        "P1",
        ("29", "37.7", "41"),
        ("ux/add-studio-component.md", "ux/review-studio-ux.md"),
        (
            "apps/studio/src/components/polish/**",
            "apps/studio/src/components/target/**",
            "apps/studio/src/lib/polish*",
        ),
        ("UX002", "UX003", "UX101", "UX202", "UX303", "UX301"),
        "AC: earned moments and ambient state treatments are rare, opt-out, reduced-motion safe, tied to proof, and never use forbidden motion or fake liveness.",
    ),
    UXStory(
        "UX407",
        "Target UX quality bar dashboard and review checklist",
        "Parallel horizontal quality",
        "horizontal/quality-bar",
        2,
        "P1",
        ("37", "39", "42"),
        ("ux/review-studio-ux.md", "coding/implement-studio-screen.md"),
        (
            "apps/studio/src/app/quality/**",
            "apps/studio/src/components/quality/**",
            "apps/studio/src/lib/quality*",
        ),
        ("UX001", "UX003"),
        "AC: internal quality screen/checklist tracks Clarity, Control, Precision, Friendliness, Enterprise Readiness, Craft, Delight, and links each failing category to target-standard evidence.",
    ),
    UXStory(
        "UX408",
        "North-star scenario demo harness",
        "Final integration",
        "horizontal/scenario-demos",
        3,
        "P0",
        ("36", "38", "39"),
        ("testing/write-e2e-test.md", "ux/review-studio-ux.md"),
        (
            "apps/studio/e2e/north-star-scenarios.spec.ts",
            "scripts/demo/ux/**",
            "docs/ux-scenarios/**",
        ),
        ("UX101", "UX202", "UX204", "UX301", "UX303", "UX305", "UX306"),
        "AC: e2e/demo harness covers migration from Botpress, voice agent ship, wrong-tool investigation, four-eyes deploy, operator escalation, KB gap, replay before shipping, and X-Ray dead-context cleanup.",
    ),
    UXStory(
        "UX409",
        "Final UX stitching: route audit, copy pass, visual consistency, no orphan surfaces",
        "Final integration",
        "horizontal/final-stitch",
        3,
        "P0",
        ("5", "37", "41", "42"),
        ("ux/review-studio-ux.md", "ux/write-ui-copy.md", "testing/write-e2e-test.md"),
        (
            "apps/studio/src/app/**",
            "apps/studio/src/components/**",
            "apps/studio/e2e/**",
            "loop_implementation/ux/00_CANONICAL_TARGET_UX_STANDARD.md",
        ),
        ("UX408",),
        "AC: all target routes are reachable from canonical IA, old flow-first language is removed, copy is friendly-precise, quality bar passes, and no screen points users to superseded UX docs.",
        "This is the only story intentionally allowed to touch broad Studio paths.",
    ),
]


def by_id() -> dict[str, UXStory]:
    return {story.id: story for story in UX_STORIES}


def blocking_foundation_ids() -> frozenset[str]:
    return frozenset(
        story.id for story in UX_STORIES if story.phase == "Gate A - blocking foundation"
    )


__all__ = [
    "CYCLE_ID",
    "DEFAULT_STATUS",
    "UXStory",
    "UX_STORIES",
    "blocking_foundation_ids",
    "by_id",
]
