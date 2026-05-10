from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.channel_bindings import (
    ChannelBindingRecord,
    ChannelType,
    channel_readiness_state,
)
from loop_control_plane.deployments import (
    DeploymentRecord,
    DeploymentStart,
    deployment_payload,
    evidence_pack_payload,
)
from loop_control_plane.trace_search import TraceQuery
from loop_control_plane.workspaces import WorkspaceError

router = APIRouter(prefix="/v1/agents", tags=["Deployments"])


class DeploymentActionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["manual", "auto"] = "manual"
    trigger: str = Field(default="", max_length=500)
    reason: str = Field(default="", max_length=1200)


class DeploymentThresholdEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str = Field(min_length=1, max_length=120)
    observed: float
    threshold: float | None = None
    policy: Literal["pause", "rollback"] = "rollback"
    window: str = Field(default="5m", min_length=1, max_length=80)
    reason: str = Field(default="", max_length=1200)


class DeploymentRampBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    traffic_percent: int = Field(ge=1, le=99)


class EvidencePackExportBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["pdf", "json", "csv", "grc_integration", "api"] = "json"
    purpose: str = Field(default="review", max_length=240)
    redactions: list[str] = Field(
        default_factory=lambda: ["secrets", "pii", "credentials"],
        max_length=20,
    )


async def _agent(
    request: Request,
    *,
    agent_id: UUID,
    caller_sub: str,
    workspace_id: UUID | None = None,
    required_role: Role | None = None,
) -> Any:
    cp = request.app.state.cp
    if workspace_id is None:
        agent = cp.agents._agents.get(agent_id)  # type: ignore[attr-defined]
        if agent is None:
            raise HTTPException(status_code=404, detail="unknown agent")
        workspace_id = agent.workspace_id
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=required_role,
    )
    return await cp.agents.get(
        workspace_id=workspace_id,
        agent_id=agent_id,
    )


async def _change_package(request: Request, *, agent: Any, package_id: str) -> Any:
    packages = await request.app.state.cp.change_packages.list_for_agent(agent=agent)
    for package in packages:
        if package.id == package_id:
            return package
    raise WorkspaceError(f"unknown change package: {package_id}")


async def _deployment(request: Request, *, agent: Any, deployment_id: str) -> DeploymentRecord:
    deployments = await request.app.state.cp.deployments.list_for_agent(agent=agent)
    for deployment in deployments:
        if deployment.id == deployment_id:
            return deployment
    raise WorkspaceError(f"unknown deployment: {deployment_id}")


async def _evidence_pack(
    request: Request,
    *,
    agent: Any,
    evidence_pack_id: str,
) -> Any:
    packs = await request.app.state.cp.deployments.list_evidence_packs(agent=agent)
    for pack in packs:
        if pack.id == evidence_pack_id:
            return pack
    raise WorkspaceError(f"unknown evidence pack: {evidence_pack_id}")


def _evidence_export_bucket(request: Request) -> dict[str, dict[str, Any]]:
    return request.app.state.cp.ux_wireup.setdefault("evidence_pack_exports", {})


async def _notification_targets(request: Request, *, agent: Any, fallback: str) -> list[str]:
    commitment = await request.app.state.cp.agent_commitments.current(agent=agent)
    return list(
        dict.fromkeys(
            target
            for target in (
                commitment.body.owner_user_id.strip(),
                commitment.body.backup_owner_user_id.strip(),
                fallback,
            )
            if target
        )
    )


def _audit(
    request: Request,
    *,
    workspace_id: UUID,
    caller_sub: str,
    action: str,
    resource_id: str,
    payload: object | None = None,
) -> None:
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action=action,
        resource_type="deployment",
        resource_id=resource_id,
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload=payload,
    )


def _channel_blocking_checks(binding: ChannelBindingRecord) -> list[dict[str, Any]]:
    checks = [
        {
            "id": str(check.get("id", "")),
            "label": str(check.get("label", "")),
            "status": str(check.get("status", "")),
            "evidence_ref": check.get("evidence_ref"),
        }
        for check in binding.readiness
        if check.get("status") in {"pending", "failed"}
    ]
    if checks:
        return checks
    return [
        {
            "id": f"{binding.channel_type}_not_ready",
            "label": f"{binding.display_name} is not ready",
            "status": channel_readiness_state(binding),
            "evidence_ref": None,
        }
    ]


def _ready_channel_scope(
    *,
    bindings: list[ChannelBindingRecord],
    requested_scope: list[ChannelType],
) -> tuple[list[ChannelType], list[dict[str, Any]]]:
    by_type = {binding.channel_type: binding for binding in bindings}
    scope = requested_scope or [
        binding.channel_type for binding in bindings if channel_readiness_state(binding) == "ready"
    ]
    blockers: list[dict[str, Any]] = []
    if not scope:
        blockers.append(
            {
                "channel_type": "none",
                "readiness_state": "no_ready_channels",
                "display_name": "No ready channel bindings",
                "blocking_checks": [
                    {
                        "id": "channel_scope_empty",
                        "label": "At least one requested channel must be ready",
                        "status": "failed",
                        "evidence_ref": None,
                    }
                ],
            }
        )
        return scope, blockers

    for channel_type in scope:
        binding = by_type[channel_type]
        state = channel_readiness_state(binding)
        if state == "ready":
            continue
        blockers.append(
            {
                "channel_type": binding.channel_type,
                "readiness_state": state,
                "display_name": binding.display_name,
                "blocking_checks": _channel_blocking_checks(binding),
            }
        )
    return scope, blockers


def _channel_blocker_message(blockers: list[dict[str, Any]]) -> str:
    summary = ", ".join(
        f"{blocker['channel_type']} {blocker['readiness_state']}" for blocker in blockers
    )
    return f"channel readiness blocks rollout: {summary}"


def _numeric_threshold(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    if isinstance(value, dict):
        for key in ("threshold", "max", "value"):
            numeric = _numeric_threshold(value.get(key))
            if numeric is not None:
                return numeric
    return None


@router.get("/{agent_id}/deployments")
async def list_deployments(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
    )
    deployments = await request.app.state.cp.deployments.list_for_agent(agent=agent)
    return {"items": [deployment_payload(deployment) for deployment in deployments]}


@router.post("/{agent_id}/deployments/start", status_code=201)
async def start_deployment(
    request: Request,
    agent_id: UUID,
    body: DeploymentStart,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    workspace_id = agent.workspace_id
    change_package = await _change_package(
        request,
        agent=agent,
        package_id=body.change_package_id,
    )
    bindings = await request.app.state.cp.channel_bindings.list_for_agent(agent=agent)
    channel_scope, channel_blockers = _ready_channel_scope(
        bindings=bindings,
        requested_scope=body.channel_scope,
    )
    if channel_blockers:
        _audit(
            request,
            workspace_id=workspace_id,
            caller_sub=caller_sub,
            action="deployment:start_blocked",
            resource_id=change_package.id,
            payload={
                "agent_id": str(agent_id),
                "change_package_id": change_package.id,
                "stage": body.stage,
                "requested_channel_scope": body.channel_scope,
                "channel_blockers": channel_blockers,
            },
        )
        raise WorkspaceError(_channel_blocker_message(channel_blockers))
    body = body.model_copy(update={"channel_scope": channel_scope})
    deployment, evidence_pack = await request.app.state.cp.deployments.start(
        agent=agent,
        change_package=change_package,
        body=body,
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="deployment:start",
        resource_id=deployment.id,
        payload={
            "agent_id": str(agent_id),
            "change_package_id": change_package.id,
            "evidence_pack_id": evidence_pack.id,
            "stage": deployment.stage,
            "traffic_percent": deployment.traffic_percent,
            "channel_scope": deployment.channel_scope,
        },
    )
    return {
        "deployment": deployment_payload(deployment),
        "evidence_pack": evidence_pack_payload(evidence_pack),
    }


async def _deployment_action(
    request: Request,
    *,
    agent_id: UUID,
    deployment_id: str,
    action: str,
    body: DeploymentActionBody | None,
    caller_sub: str,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    workspace_id = agent.workspace_id
    deployment = await request.app.state.cp.deployments.action(
        agent=agent,
        deployment_id=deployment_id,
        action=action,
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action=f"deployment:{action}",
        resource_id=deployment.id,
        payload={"agent_id": str(agent_id), "status": deployment.status},
    )
    if action == "rollback":
        details = body or DeploymentActionBody()
        traces = await request.app.state.cp.trace_search.run(
            TraceQuery(workspace_id=workspace_id, agent_id=agent.id, page_size=25)
        )
        affected_trace_ids = [trace.trace_id for trace in traces.items]
        notification_targets = await _notification_targets(
            request,
            agent=agent,
            fallback=caller_sub,
        )
        incident = await request.app.state.cp.incidents.create_for_rollback(
            agent=agent,
            deployment_id=deployment.id,
            version_id=deployment.version_id,
            actor_sub=caller_sub,
            mode=details.mode,
            trigger=details.trigger,
            reason=details.reason,
            affected_trace_ids=affected_trace_ids,
            notification_targets=notification_targets,
        )
        record_audit_event(
            workspace_id=workspace_id,
            actor_sub=caller_sub,
            action="incident:create_auto_rollback"
            if details.mode == "auto"
            else "incident:create_from_rollback",
            resource_type="incident",
            resource_id=incident.id,
            store=request.app.state.cp.audit_events,
            request_id=request_id(request),
            payload={
                "agent_id": str(agent_id),
                "deployment_id": deployment.id,
                "rollback_action_ref": incident.rollback_action_ref,
                "affected_trace_count": len(affected_trace_ids),
                "notification_targets": notification_targets,
                "trigger": incident.trigger,
            },
        )
    return deployment_payload(deployment)


@router.post("/{agent_id}/deployments/{deployment_id}/thresholds/evaluate")
async def evaluate_deployment_threshold(
    request: Request,
    agent_id: UUID,
    deployment_id: str,
    body: DeploymentThresholdEvaluation,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    workspace_id = agent.workspace_id
    deployment = await _deployment(request, agent=agent, deployment_id=deployment_id)
    threshold = body.threshold
    if threshold is None:
        threshold = _numeric_threshold(deployment.auto_rollback_thresholds.get(body.metric))
    if threshold is None:
        raise WorkspaceError(f"no numeric threshold configured for metric: {body.metric}")

    trigger = f"{body.metric} breached {body.observed:g} > {threshold:g} over {body.window}"
    audit_payload = {
        "agent_id": str(agent_id),
        "deployment_id": deployment.id,
        "metric": body.metric,
        "observed": body.observed,
        "threshold": threshold,
        "policy": body.policy,
        "window": body.window,
        "trigger": trigger,
    }
    if body.observed <= threshold:
        _audit(
            request,
            workspace_id=workspace_id,
            caller_sub=caller_sub,
            action="deployment:threshold_evaluate",
            resource_id=deployment.id,
            payload={**audit_payload, "decision": "no_action", "breached": False},
        )
        return {
            "decision": "no_action",
            "breached": False,
            "metric": body.metric,
            "observed": body.observed,
            "threshold": threshold,
            "policy": body.policy,
            "deployment": deployment_payload(deployment),
        }

    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="deployment:threshold_breach",
        resource_id=deployment.id,
        payload={**audit_payload, "decision": body.policy, "breached": True},
    )
    if body.policy == "pause":
        updated = await _deployment_action(
            request,
            agent_id=agent_id,
            deployment_id=deployment_id,
            action="pause",
            body=None,
            caller_sub=caller_sub,
            workspace_id=workspace_id,
        )
        return {
            "decision": "paused",
            "breached": True,
            "metric": body.metric,
            "observed": body.observed,
            "threshold": threshold,
            "policy": body.policy,
            "deployment": updated,
        }

    updated = await _deployment_action(
        request,
        agent_id=agent_id,
        deployment_id=deployment_id,
        action="rollback",
        body=DeploymentActionBody(
            mode="auto",
            trigger=trigger,
            reason=body.reason or f"{body.metric} exceeded the configured rollout threshold.",
        ),
        caller_sub=caller_sub,
        workspace_id=workspace_id,
    )
    return {
        "decision": "rolled_back",
        "breached": True,
        "metric": body.metric,
        "observed": body.observed,
        "threshold": threshold,
        "policy": body.policy,
        "deployment": updated,
    }


@router.post("/{agent_id}/deployments/{deployment_id}/promote")
async def promote_deployment(
    request: Request,
    agent_id: UUID,
    deployment_id: str,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    return await _deployment_action(
        request,
        agent_id=agent_id,
        deployment_id=deployment_id,
        action="promote",
        body=None,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
    )


@router.post("/{agent_id}/deployments/{deployment_id}/ramp")
async def ramp_deployment(
    request: Request,
    agent_id: UUID,
    deployment_id: str,
    body: DeploymentRampBody,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    workspace_id = agent.workspace_id
    deployment = await request.app.state.cp.deployments.ramp(
        agent=agent,
        deployment_id=deployment_id,
        traffic_percent=body.traffic_percent,
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="deployment:ramp",
        resource_id=deployment.id,
        payload={
            "agent_id": str(agent_id),
            "stage": deployment.stage,
            "status": deployment.status,
            "traffic_percent": deployment.traffic_percent,
        },
    )
    return deployment_payload(deployment)


@router.post("/{agent_id}/deployments/{deployment_id}/pause")
async def pause_deployment(
    request: Request,
    agent_id: UUID,
    deployment_id: str,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    return await _deployment_action(
        request,
        agent_id=agent_id,
        deployment_id=deployment_id,
        action="pause",
        body=None,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
    )


@router.post("/{agent_id}/deployments/{deployment_id}/rollback")
async def rollback_deployment(
    request: Request,
    agent_id: UUID,
    deployment_id: str,
    body: DeploymentActionBody | None = None,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    return await _deployment_action(
        request,
        agent_id=agent_id,
        deployment_id=deployment_id,
        action="rollback",
        body=body,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
    )


@router.get("/{agent_id}/evidence-packs")
async def list_evidence_packs(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
    )
    packs = await request.app.state.cp.deployments.list_evidence_packs(agent=agent)
    return {"items": [evidence_pack_payload(pack) for pack in packs]}


@router.post("/{agent_id}/evidence-packs/{evidence_pack_id}/exports", status_code=201)
async def export_evidence_pack(
    request: Request,
    agent_id: UUID,
    evidence_pack_id: str,
    body: EvidencePackExportBody,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    workspace_id = agent.workspace_id
    pack = await _evidence_pack(request, agent=agent, evidence_pack_id=evidence_pack_id)
    if body.format not in pack.export_formats:
        raise WorkspaceError(
            f"evidence pack {evidence_pack_id} cannot export format: {body.format}"
        )

    now = datetime.now(UTC)
    export_id = f"epex_{uuid4().hex[:12]}"
    redactions = sorted(
        set(body.redactions)
        | {"secrets", "credentials", "raw_secret_values", "raw_tool_credentials"}
    )
    sections = [
        "commitment",
        "change_package",
        "version_manifest",
        "behavior_diff",
        "tool_permissions",
        "knowledge_diff",
        "memory_policy",
        "channel_deployment_plan",
        "eval_results",
        "approvals",
        "canary_results",
        "rollback_plan",
        "audit_log",
    ]
    artifact_refs = [
        f"evidence-pack/{pack.id}",
        f"agent/{pack.agent_id}",
        f"deployment/{pack.deployment_id}",
        f"change-package/{pack.change_package_id}",
        pack.behavior_diff_ref,
        pack.tool_permission_diff_ref,
        pack.knowledge_diff_ref,
        pack.memory_policy_ref,
        pack.channel_deployment_plan_ref,
        pack.eval_results_ref,
        pack.approval_records_ref,
        pack.canary_results_ref,
        pack.rollback_plan_ref,
        pack.audit_log_ref,
    ]
    payload = {
        "id": export_id,
        "status": "ready",
        "format": body.format,
        "purpose": body.purpose,
        "workspace_id": str(pack.workspace_id),
        "agent_id": str(pack.agent_id),
        "evidence_pack_id": pack.id,
        "deployment_id": pack.deployment_id,
        "change_package_id": pack.change_package_id,
        "sections": sections,
        "artifact_refs": artifact_refs,
        "redactions": redactions,
        "download_url": (
            f"/v1/agents/{agent_id}/evidence-packs/{pack.id}/exports/{export_id}"
        ),
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(days=7)).isoformat(),
    }
    _evidence_export_bucket(request)[export_id] = payload
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="evidence_pack:export",
        resource_type="evidence_pack",
        resource_id=pack.id,
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload={
            "agent_id": str(agent_id),
            "evidence_pack_id": pack.id,
            "export_id": export_id,
            "format": body.format,
            "redactions": redactions,
        },
    )
    return payload


@router.get("/{agent_id}/evidence-packs/{evidence_pack_id}/exports/{export_id}")
async def download_evidence_pack_export(
    request: Request,
    agent_id: UUID,
    evidence_pack_id: str,
    export_id: str,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
    )
    workspace_id = agent.workspace_id
    pack = await _evidence_pack(request, agent=agent, evidence_pack_id=evidence_pack_id)
    export = _evidence_export_bucket(request).get(export_id)
    if export is None or export.get("evidence_pack_id") != pack.id:
        raise HTTPException(status_code=404, detail="evidence pack export not found")
    if datetime.fromisoformat(str(export["expires_at"])) <= datetime.now(UTC):
        raise HTTPException(status_code=410, detail="evidence pack export expired")
    redactions = list(export["redactions"])
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="evidence_pack:export_download",
        resource_type="evidence_pack",
        resource_id=pack.id,
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload={
            "agent_id": str(agent_id),
            "evidence_pack_id": pack.id,
            "export_id": export_id,
            "redactions": redactions,
        },
    )
    return {
        "id": export_id,
        "status": "ready",
        "format": export["format"],
        "purpose": export["purpose"],
        "evidence_pack_id": pack.id,
        "deployment_id": pack.deployment_id,
        "change_package_id": pack.change_package_id,
        "sections": export["sections"],
        "artifact_refs": export["artifact_refs"],
        "redactions": redactions,
        "secret_policy": "Raw secrets and tool credentials are never included in evidence exports.",
        "evidence_pack": evidence_pack_payload(pack),
        "created_at": export["created_at"],
        "expires_at": export["expires_at"],
    }
