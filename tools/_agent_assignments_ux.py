"""Agent partition for the canonical target UX/UI implementation cycle.

This file partitions ``tools/_stories_ux.py`` across the same four agents used
by ``tools/_agent_assignments.py``. The goal is parallel UI implementation with
minimal merge conflicts.

Start order
===========
1. ``codex-orion`` starts first and closes UX001-UX004.
2. Once UX001-UX004 are merged, all agents can begin their parallel queues.
3. UX005 and UX006 should land early, but they are not hard blockers for every
   feature surface if the shell/primitives/fixture contracts are already in.
4. Final integration stories wait for their listed dependencies.

Shared ownership rules
======================
* ``codex-orion`` owns the shared foundation plus Build surfaces: shell,
  tokens, target primitives, fixtures, state/copy kit, quality harness, agents,
  behavior, tools, memory, map, conductor, and build-to-test flow.
* ``codex-vega`` owns Test/Observe/data-heavy surfaces: simulator, traces,
  evals, replay/scenes, knowledge, voice, observatory, cost/latency.
* ``copilot-titan`` owns Migrate/Ship/Govern/HITL/collaboration/AI co-builder.
* ``copilot-thor`` owns horizontal experience layers after the foundation:
  command/search, onboarding, marketplace, responsive/a11y, polish, quality
  dashboard, scenario demos, and final stitching.

Agents should stay inside their story ``primary_paths`` unless a dependency
explicitly requires otherwise. If a shared primitive is missing, file the need
against UX003/UX005 or coordinate with ``codex-orion`` instead of adding a
local duplicate.
"""

from __future__ import annotations

from dataclasses import dataclass

from _stories_ux import UX_STORIES, blocking_foundation_ids


START_FIRST_AGENT = "codex-orion"
START_FIRST_STORIES: frozenset[str] = blocking_foundation_ids()


CODEX_ORION: frozenset[str] = frozenset(
    {
        "UX001",
        "UX002",
        "UX003",
        "UX004",
        "UX005",
        "UX006",
        "UX101",
        "UX102",
        "UX103",
        "UX104",
        "UX105",
        "UX106",
        "UX107",
    }
)


CODEX_VEGA: frozenset[str] = frozenset(
    {
        "UX201",
        "UX202",
        "UX203",
        "UX204",
        "UX205",
        "UX206",
        "UX207",
        "UX208",
        "UX209",
        "UX210",
    }
)


COPILOT_TITAN: frozenset[str] = frozenset(
    {
        "UX301",
        "UX302",
        "UX303",
        "UX304",
        "UX305",
        "UX306",
        "UX307",
        "UX308",
    }
)


COPILOT_THOR: frozenset[str] = frozenset(
    {
        "UX401",
        "UX402",
        "UX403",
        "UX404",
        "UX405",
        "UX406",
        "UX407",
        "UX408",
        "UX409",
    }
)


ASSIGNMENTS_UX: dict[str, frozenset[str]] = {
    "codex-orion": CODEX_ORION,
    "codex-vega": CODEX_VEGA,
    "copilot-thor": COPILOT_THOR,
    "copilot-titan": COPILOT_TITAN,
}


DEPENDENCY_GATES: dict[str, tuple[str, ...]] = {
    "Gate A - start first": tuple(sorted(START_FIRST_STORIES)),
    "Gate B - parallel surfaces": ("UX001", "UX002", "UX003", "UX004"),
    "Gate C - scenario demos": (
        "UX101",
        "UX202",
        "UX204",
        "UX301",
        "UX303",
        "UX305",
        "UX306",
    ),
    "Gate D - final stitching": ("UX408",),
}


@dataclass(frozen=True)
class AgentUXBrief:
    agent_id: str
    role: str
    start_instruction: str
    owns: tuple[str, ...]
    avoid: tuple[str, ...]


AGENT_BRIEFS: dict[str, AgentUXBrief] = {
    "codex-orion": AgentUXBrief(
        "codex-orion",
        "Foundation plus Build surfaces: shell, target primitives, fixtures, agents, behavior, map, tools, memory, conductor",
        "Start immediately with UX001-UX004. After those merge, close UX005-UX006 early and then work through UX101-UX107 in dependency order.",
        (
            "apps/studio/src/components/shell/**",
            "apps/studio/src/components/ui/**",
            "apps/studio/src/components/target/**",
            "apps/studio/src/lib/target-ux/**",
            "apps/studio/src/lib/fixtures/**",
            "apps/studio/src/components/agents/**",
            "apps/studio/src/components/behavior/**",
            "apps/studio/src/components/agent-map/**",
            "apps/studio/src/components/tools/**",
            "apps/studio/src/components/memory/**",
            "apps/studio/src/components/conductor/**",
            "apps/studio/src/app/agents/**",
        ),
        (
            "Trace/eval/replay internals owned by codex-vega.",
            "Migration/deploy/govern/HITL/collaboration surfaces owned by copilot-titan.",
            "Horizontal command/onboarding/marketplace/final-stitch surfaces owned by copilot-thor.",
        ),
    ),
    "copilot-thor": AgentUXBrief(
        "copilot-thor",
        "Horizontal UX after the shared foundation: command/search, onboarding, marketplace, responsive/a11y, polish, quality dashboard, scenario demos, final stitch",
        "Wait for codex-orion to merge UX001-UX004. Then work UX401-UX409 in dependency order; UX409 is the only broad final-stitch story.",
        (
            "apps/studio/src/components/command/**",
            "apps/studio/src/components/search/**",
            "apps/studio/src/components/sharing/**",
            "apps/studio/src/components/onboarding/**",
            "apps/studio/src/components/templates/**",
            "apps/studio/src/components/marketplace/**",
            "apps/studio/src/components/responsive/**",
            "apps/studio/src/components/polish/**",
            "apps/studio/src/components/quality/**",
            "apps/studio/e2e/**",
        ),
        (
            "Shared shell/tokens/primitives owned by codex-orion.",
            "Feature-domain components owned by other agents unless performing UX409 final stitching.",
        ),
    ),
    "codex-vega": AgentUXBrief(
        "codex-vega",
        "Test and observe surfaces: simulator, traces, evals, knowledge, voice, observatory, cost",
        "Wait for UX001-UX004, then prioritize UX202, UX204, UX206, UX210 before dependent advanced surfaces.",
        (
            "apps/studio/src/components/simulator/**",
            "apps/studio/src/components/trace/**",
            "apps/studio/src/components/evals/**",
            "apps/studio/src/components/replay/**",
            "apps/studio/src/components/scenes/**",
            "apps/studio/src/components/knowledge/**",
            "apps/studio/src/components/voice/**",
            "apps/studio/src/components/observatory/**",
            "apps/studio/src/components/cost/**",
        ),
        (
            "Deploy/migration/govern surfaces owned by copilot-titan.",
            "Shared shell/tokens/primitives owned by codex-orion.",
        ),
    ),
    "copilot-titan": AgentUXBrief(
        "copilot-titan",
        "Migrate, ship, govern, HITL, collaboration, AI co-builder",
        "Wait for UX001-UX004, then prioritize UX301, UX303, UX305, UX306 before dependent advanced surfaces.",
        (
            "apps/studio/src/components/migration/**",
            "apps/studio/src/components/deploy/**",
            "apps/studio/src/components/snapshots/**",
            "apps/studio/src/components/inbox/**",
            "apps/studio/src/components/enterprise/**",
            "apps/studio/src/components/workspaces/**",
            "apps/studio/src/components/collaboration/**",
            "apps/studio/src/components/comments/**",
            "apps/studio/src/components/ai-cobuilder/**",
        ),
        (
            "Shared shell/tokens/primitives owned by codex-orion.",
            "Trace/eval/replay internals owned by codex-vega; consume their public components.",
        ),
    ),
}


def for_agent(agent_id: str) -> frozenset[str]:
    return ASSIGNMENTS_UX.get(agent_id, frozenset())


def all_assigned_ids() -> frozenset[str]:
    out: frozenset[str] = frozenset()
    for story_ids in ASSIGNMENTS_UX.values():
        out = out | story_ids
    return out


def all_story_ids() -> frozenset[str]:
    return frozenset(story.id for story in UX_STORIES)


def unassigned_ids() -> frozenset[str]:
    return all_story_ids() - all_assigned_ids()


def duplicate_assignments() -> dict[str, tuple[str, ...]]:
    owners_by_story: dict[str, list[str]] = {}
    for agent, story_ids in ASSIGNMENTS_UX.items():
        for story_id in story_ids:
            owners_by_story.setdefault(story_id, []).append(agent)
    return {
        story_id: tuple(owners)
        for story_id, owners in owners_by_story.items()
        if len(owners) > 1
    }


def missing_dependency_ids() -> dict[str, tuple[str, ...]]:
    valid = all_story_ids()
    out: dict[str, tuple[str, ...]] = {}
    for story in UX_STORIES:
        missing = tuple(dep for dep in story.depends_on if dep not in valid)
        if missing:
            out[story.id] = missing
    return out


__all__ = [
    "AGENT_BRIEFS",
    "ASSIGNMENTS_UX",
    "CODEX_ORION",
    "CODEX_VEGA",
    "COPILOT_THOR",
    "COPILOT_TITAN",
    "DEPENDENCY_GATES",
    "START_FIRST_AGENT",
    "START_FIRST_STORIES",
    "AgentUXBrief",
    "all_assigned_ids",
    "all_story_ids",
    "duplicate_assignments",
    "for_agent",
    "missing_dependency_ids",
    "unassigned_ids",
]
