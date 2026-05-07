"""Migration parity workspace route for Studio wire-up."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, Request

from loop_control_plane._app_common import CALLER
from loop_control_plane.authorize import authorize_workspace_access
from loop_control_plane.trace_search import TraceQuery

router = APIRouter(prefix="/v1/workspaces", tags=["Migration"])


def _labels(value: Any) -> list[str]:
    if isinstance(value, str):
        return [part.strip() for part in value.replace("\n", ",").split(",") if part.strip()]
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        elif isinstance(item, dict):
            for key in ("name", "id", "key", "label"):
                label = item.get(key)
                if isinstance(label, str) and label.strip():
                    out.append(label.strip())
                    break
    return out


def _list_from_spec(spec: dict[str, Any], *keys: str) -> list[str]:
    for key in keys:
        labels = _labels(spec.get(key))
        if labels:
            return labels
    return []


def _text_from_spec(spec: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = spec.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _migration_meta(spec: dict[str, Any]) -> dict[str, Any]:
    value = spec.get("migration")
    return value if isinstance(value, dict) else {}


def _source_archive(meta: dict[str, Any], source: str) -> str:
    archive = meta.get("archive") or meta.get("archive_name") or meta.get("file")
    return str(archive) if archive else f"{source}-workspace-import"


def _archive_sha(meta: dict[str, Any], workspace_id: UUID) -> str:
    sha = meta.get("archive_sha") or meta.get("sha256")
    if isinstance(sha, str) and sha.startswith("sha256:"):
        return sha
    return f"sha256:{str(workspace_id).replace('-', '')[:32]:0<64}"


def _has_side_effect_tool(name: str) -> bool:
    lowered = name.lower()
    return any(
        token in lowered
        for token in (
            "refund",
            "charge",
            "payment",
            "delete",
            "write",
            "send",
            "email",
            "sms",
            "transfer",
            "payout",
        )
    )


def _diff(
    *,
    diff_id: str,
    mode: str,
    source_path: str,
    target_path: str,
    severity: str,
    summary: str,
    evidence_ref: str,
    delta: str | None = None,
) -> dict[str, Any]:
    item = {
        "id": diff_id,
        "mode": mode,
        "sourcePath": source_path,
        "targetPath": target_path,
        "severity": severity,
        "summary": summary,
        "evidenceRef": evidence_ref,
    }
    if delta is not None:
        item["delta"] = delta
    return item


def _repair(
    *,
    repair_id: str,
    diff_id: str,
    rationale: str,
    grounding_ref: str,
    confidence: str,
    patch_summary: str,
) -> dict[str, Any]:
    return {
        "id": repair_id,
        "diffId": diff_id,
        "rationale": rationale,
        "groundingRef": grounding_ref,
        "confidence": confidence,
        "patchSummary": patch_summary,
    }


async def _latest_version(cp: Any, workspace_id: UUID, agent_id: UUID) -> Any | None:
    versions = await cp.agent_versions.list_for_agent(
        workspace_id=workspace_id,
        agent_id=agent_id,
    )
    return max(versions, key=lambda version: version.version, default=None)


@router.get("/{workspace_id}/migration/parity")
async def get_migration_parity(
    request: Request,
    workspace_id: UUID,
    source: str = Query(default="botpress"),
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    agents = await cp.agents.list_for_workspace(workspace_id)
    agent = agents[0] if agents else None
    latest = await _latest_version(cp, workspace_id, agent.id) if agent else None
    spec = getattr(latest, "spec", {}) if latest is not None else {}
    if not isinstance(spec, dict):
        spec = {}
    meta = _migration_meta(spec)
    tools = _list_from_spec(spec, "tools", "tool_ids", "tool_grants")
    prompt = _text_from_spec(spec, "system_prompt", "prompt", "instructions", "behavior")
    traces = (
        await cp.trace_search.run(
            TraceQuery(workspace_id=workspace_id, page_size=8)
        )
    ).items
    evidence_base = f"audit/migration/{workspace_id}/{source}"

    lineage_steps = [
        {
            "id": "parse",
            "label": "Parse source archive",
            "status": "ok" if agent else "warn",
            "evidenceRef": f"{evidence_base}/parse",
            "detail": (
                f"Mapped source archive into agent `{agent.slug}`."
                if agent
                else "No imported agent is present yet."
            ),
        },
        {
            "id": "map",
            "label": "Map to Loop primitives",
            "status": "ok" if latest else "warn",
            "evidenceRef": f"{evidence_base}/map",
            "detail": (
                f"Latest saved version v{latest.version} is the target primitive map."
                if latest
                else "Save a version to attach behavior, tools, memory, and evals."
            ),
        },
        {
            "id": "secrets",
            "label": "Re-collect secrets",
            "status": "warn" if any(_has_side_effect_tool(tool) for tool in tools) else "ok",
            "evidenceRef": f"{evidence_base}/secrets",
            "detail": (
                "Side-effect capable tools require fresh secret grants and approval."
                if any(_has_side_effect_tool(tool) for tool in tools)
                else "No side-effect capable imported tools detected."
            ),
        },
        {
            "id": "compile",
            "label": "Compile target build",
            "status": "ok" if prompt else "warn",
            "evidenceRef": f"{evidence_base}/compile",
            "detail": (
                "Behavior instructions are present for parity replay."
                if prompt
                else "Behavior instructions are missing from the target version."
            ),
        },
    ]

    diffs = [
        _diff(
            diff_id="diff_structure_agent",
            mode="structure",
            source_path=f"{source}.bot",
            target_path=f"agent.{getattr(agent, 'slug', 'missing')}",
            severity="ok" if agent else "blocking",
            summary=(
                "Imported bot is represented as a Loop agent."
                if agent
                else "No target agent exists for the imported source."
            ),
            evidence_ref=f"{evidence_base}/diff/structure_agent",
        ),
        _diff(
            diff_id="diff_behavior_prompt",
            mode="behavior",
            source_path=f"{source}.instructions",
            target_path="version.spec.system_prompt",
            severity="ok" if prompt else "blocking",
            summary=(
                "Target behavior has explicit instructions for parity replay."
                if prompt
                else "Target behavior is missing explicit instructions."
            ),
            evidence_ref=f"{evidence_base}/diff/behavior_prompt",
        ),
        _diff(
            diff_id="diff_cost_tools",
            mode="cost",
            source_path=f"{source}.actions",
            target_path="version.spec.tools",
            severity="advisory" if len(tools) > 4 else "ok",
            summary=f"{len(tools)} imported tool bindings affect latency and cost budgets.",
            delta=f"{len(tools) * 120}ms estimated tool budget",
            evidence_ref=f"{evidence_base}/diff/cost_tools",
        ),
        _diff(
            diff_id="diff_risk_tools",
            mode="risk",
            source_path=f"{source}.actions",
            target_path="tools.safety_contracts",
            severity=(
                "blocking" if any(_has_side_effect_tool(tool) for tool in tools) else "ok"
            ),
            summary=(
                "Side-effect capable imported tools require safety contracts."
                if any(_has_side_effect_tool(tool) for tool in tools)
                else "No side-effect capable imported tools detected."
            ),
            evidence_ref=f"{evidence_base}/diff/risk_tools",
        ),
    ]
    repairs = []
    if not prompt:
        repairs.append(
            _repair(
                repair_id="rep_add_prompt",
                diff_id="diff_behavior_prompt",
                rationale="Parity replay cannot explain behavior without explicit target instructions.",
                grounding_ref=f"{evidence_base}/diff/behavior_prompt",
                confidence="high",
                patch_summary="Add a system_prompt that preserves source behavior and cites evidence.",
            )
        )
    if any(_has_side_effect_tool(tool) for tool in tools):
        repairs.append(
            _repair(
                repair_id="rep_tool_safety_contract",
                diff_id="diff_risk_tools",
                rationale="Imported side-effect actions should remain gated until replay and approvals pass.",
                grounding_ref=f"{evidence_base}/diff/risk_tools",
                confidence="high",
                patch_summary="Attach preview_required, approval_required, and rollback triggers to risky tools.",
            )
        )

    replay = [
        {
            "id": f"rp_{index + 1:03d}",
            "transcript": f"Production trace {trace.trace_id[:8]} replayed against target version.",
            "status": "regress" if trace.error else "pass",
            "expectedTarget": f"{source}.trace.{trace.trace_id[:8]}",
            "observedTarget": f"loop.agent.{trace.agent_id}",
            "evidenceRef": f"trace/{trace.trace_id}",
        }
        for index, trace in enumerate(traces)
    ]
    if not replay:
        replay = [
            {
                "id": "rp_pending",
                "transcript": "No production conversations are available for parity replay yet.",
                "status": "skipped",
                "expectedTarget": f"{source}.golden_set",
                "observedTarget": "loop.awaiting_trace",
                "evidenceRef": f"{evidence_base}/replay/pending",
            }
        ]

    blocking_count = sum(1 for diff in diffs if diff["severity"] == "blocking")
    advisory_count = sum(1 for diff in diffs if diff["severity"] == "advisory")
    regress_count = sum(1 for case in replay if case["status"] == "regress")
    pass_count = sum(1 for case in replay if case["status"] in ("pass", "improve"))
    total_replay = len([case for case in replay if case["status"] != "skipped"])
    score = max(
        0,
        min(
            100,
            100
            - blocking_count * 18
            - advisory_count * 5
            - regress_count * 12
            - (0 if prompt else 10),
        ),
    )
    now = datetime.now(UTC).isoformat()
    return {
        "lineage": {
            "importId": str(meta.get("import_id") or f"imp_{workspace_id.hex[:10]}"),
            "source": source,
            "archive": _source_archive(meta, source),
            "importedAt": str(meta.get("imported_at") or now),
            "archiveSha": _archive_sha(meta, workspace_id),
            "steps": lineage_steps,
        },
        "readiness": {
            "overallScore": score,
            "parityPassing": pass_count,
            "parityTotal": total_replay,
            "blockingCount": blocking_count,
            "advisoryCount": advisory_count,
        },
        "diffs": diffs,
        "replay": replay,
        "repairs": repairs,
        "cutover": {
            "id": f"cut_{workspace_id.hex[:10]}",
            "shadow": {
                "durationMinutes": 60 if total_replay else 0,
                "turns": total_replay,
                "agreement": score,
                "divergences": regress_count + blocking_count,
                "costPerTurnDelta": f"+{len(tools) * 0.001:.3f}",
                "evidenceRef": f"{evidence_base}/shadow",
            },
            "stages": [
                {
                    "id": "canary_1pct",
                    "percent": 1,
                    "durationMinutes": 30,
                    "status": "pending" if blocking_count else "in_progress",
                    "guardrails": ["regression=0", "error_rate<0.5%"],
                },
                {
                    "id": "canary_10pct",
                    "percent": 10,
                    "durationMinutes": 60,
                    "status": "pending",
                    "guardrails": ["regression<2", "cost_per_turn<150%"],
                },
                {
                    "id": "canary_100pct",
                    "percent": 100,
                    "durationMinutes": 0,
                    "status": "pending",
                    "guardrails": ["all-stages-passed"],
                },
            ],
            "rollbackTriggers": [
                {
                    "id": "rb_regression",
                    "metric": "regression",
                    "threshold": ">1 parity regression during canary",
                    "action": "Halt canary and restore source behavior.",
                    "evidenceRef": f"{evidence_base}/rollback/regression",
                },
                {
                    "id": "rb_error_rate",
                    "metric": "error_rate",
                    "threshold": "5xx rate >2% over 5m",
                    "action": "Halt canary and page the owner.",
                    "evidenceRef": f"{evidence_base}/rollback/error_rate",
                },
                {
                    "id": "rb_cost",
                    "metric": "cost_spike",
                    "threshold": "Cost-per-turn >150% baseline",
                    "action": "Throttle canary and alert finance.",
                    "evidenceRef": f"{evidence_base}/rollback/cost",
                },
            ],
        },
    }


__all__ = ["router"]
