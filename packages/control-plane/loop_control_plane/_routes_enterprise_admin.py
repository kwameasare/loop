"""Enterprise signup, workspace onboarding, and system-admin routes."""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr, Field

from loop_control_plane._app_common import CALLER, JSON_BODY, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import (
    AuthorisationError,
    authorize_workspace_access,
)
from loop_control_plane.auth_exchange import map_idp_sub_to_internal_user_id
from loop_control_plane.enterprise_admin import (
    EnterpriseSignup,
    WorkspaceInvite,
)
from loop_control_plane.workspaces import Role, WorkspaceError

router_public = APIRouter(prefix="/v1/enterprise", tags=["Enterprise Signup"])
router_workspaces = APIRouter(prefix="/v1/workspaces", tags=["Enterprise Admin"])
router_system = APIRouter(prefix="/v1/system/admin", tags=["System Admin"])


class EnterpriseSignupRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=120)
    workspace_slug: str | None = Field(default=None, max_length=64)
    admin_name: str = Field(min_length=2, max_length=120)
    admin_email: EmailStr
    company_size: str = Field(min_length=1, max_length=80)
    region: str = Field(default="na-east", min_length=1, max_length=64)
    primary_use_case: str = Field(min_length=8, max_length=400)
    channel_priorities: list[str] = Field(default_factory=list, max_length=12)
    compliance_needs: list[str] = Field(default_factory=list, max_length=12)
    sso_required: bool = False


class WorkspaceInviteRequest(BaseModel):
    email: EmailStr
    role: Role = Role.MEMBER
    full_name: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)


class ApproveSignupRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def _now() -> datetime:
    return datetime.now(UTC)


def _serialise_dt(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _slugify(value: str) -> str:
    slug = _SLUG_RE.sub("-", value.lower().strip()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return (slug or "workspace")[:64].strip("-") or "workspace"


def _signup_payload(record: EnterpriseSignup) -> dict[str, Any]:
    return {
        "id": record.id,
        "organization_name": record.organization_name,
        "workspace_slug": record.workspace_slug,
        "admin_name": record.admin_name,
        "admin_email": record.admin_email,
        "company_size": record.company_size,
        "region": record.region,
        "primary_use_case": record.primary_use_case,
        "channel_priorities": list(record.channel_priorities),
        "compliance_needs": list(record.compliance_needs),
        "sso_required": record.sso_required,
        "status": record.status,
        "created_at": _serialise_dt(record.created_at),
        "updated_at": _serialise_dt(record.updated_at),
        "approved_workspace_id": record.approved_workspace_id,
        "approved_by": record.approved_by,
        "admin_invite_id": record.admin_invite_id,
    }


def _invite_payload(record: WorkspaceInvite) -> dict[str, Any]:
    return {
        "id": record.id,
        "workspace_id": str(record.workspace_id),
        "email": record.email,
        "role": record.role,
        "full_name": record.full_name,
        "note": record.note,
        "status": record.status,
        "created_at": _serialise_dt(record.created_at),
        "expires_at": _serialise_dt(record.expires_at),
        "created_by": record.created_by,
        "invite_url": record.invite_url,
    }


def _system_admin_context(caller_sub: str) -> dict[str, str]:
    raw_configured = {
        item.strip()
        for item in os.environ.get("LOOP_SYSTEM_ADMIN_SUBS", "").split(",")
        if item.strip()
    }
    if raw_configured:
        # Operators paste their IdP sub (e.g. ``google-oauth2|123…`` or
        # ``auth0|abc``) — but the PASETO carries the UUID5 internal
        # user-id minted by /v1/auth/exchange. Match against both
        # forms so the env var stays readable while the runtime check
        # is still done against the internal id.
        allow = raw_configured | {
            map_idp_sub_to_internal_user_id(sub) for sub in raw_configured
        }
        if caller_sub not in allow:
            raise AuthorisationError("system admin role required")
        return {"mode": "configured", "actor_sub": caller_sub}
    if os.environ.get("LOOP_ENV", "dev").lower() == "production":
        raise AuthorisationError("LOOP_SYSTEM_ADMIN_SUBS must be configured")
    return {"mode": "dev_unrestricted", "actor_sub": caller_sub}


async def _create_invite(
    *,
    request: Request,
    workspace_id: UUID,
    body: WorkspaceInviteRequest,
    actor_sub: str,
) -> WorkspaceInvite:
    runtime = request.app.state.cp
    await authorize_workspace_access(
        workspaces=runtime.workspaces,
        workspace_id=workspace_id,
        user_sub=actor_sub,
        required_role=Role.ADMIN,
    )
    now = _now()
    invite_id = f"inv_{uuid4().hex[:12]}"
    invite = WorkspaceInvite(
        id=invite_id,
        workspace_id=workspace_id,
        email=str(body.email).lower(),
        role=body.role.value,
        full_name=body.full_name,
        note=body.note,
        status="pending",
        created_at=now,
        expires_at=now + timedelta(days=14),
        created_by=actor_sub,
        invite_url=f"/signup?invite={invite_id}",
    )
    await runtime.workspace_invites.create(invite)
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=actor_sub,
        action="workspace:invite:create",
        resource_type="workspace_invite",
        store=runtime.audit_events,
        resource_id=invite_id,
        request_id=request_id(request),
        payload={
            "email": invite.email,
            "role": invite.role,
            "full_name": invite.full_name,
        },
    )
    return invite


@router_public.post("/signups", status_code=201)
async def create_enterprise_signup(
    request: Request,
    body: EnterpriseSignupRequest = JSON_BODY,
) -> dict[str, Any]:
    """Capture enterprise signup intent without pretending auth is complete."""
    now = _now()
    requested_slug = body.workspace_slug or body.organization_name
    signup = EnterpriseSignup(
        id=f"ens_{uuid4().hex[:12]}",
        organization_name=body.organization_name.strip(),
        workspace_slug=_slugify(requested_slug),
        admin_name=body.admin_name.strip(),
        admin_email=str(body.admin_email).lower(),
        company_size=body.company_size.strip(),
        region=body.region.strip(),
        primary_use_case=body.primary_use_case.strip(),
        channel_priorities=tuple(
            item.strip() for item in body.channel_priorities if item.strip()
        ),
        compliance_needs=tuple(
            item.strip() for item in body.compliance_needs if item.strip()
        ),
        sso_required=body.sso_required,
        status="pending_review",
        created_at=now,
        updated_at=now,
    )
    await request.app.state.cp.enterprise_signups.create(signup)
    return {
        "signup": _signup_payload(signup),
        "next_step": {
            "label": "Review queued",
            "detail": (
                "A system admin can approve the tenant, provision the workspace, "
                "and send the first owner invite."
            ),
            "href": "/login?returnTo=/system/admin",
        },
    }


@router_workspaces.get("/{workspace_id}/invites")
async def list_workspace_invites(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    runtime = request.app.state.cp
    await authorize_workspace_access(
        workspaces=runtime.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    invites = await runtime.workspace_invites.list_for_workspace(workspace_id)
    return {
        "items": [
            _invite_payload(record)
            for record in sorted(invites, key=lambda item: item.created_at)
        ]
    }


@router_workspaces.post("/{workspace_id}/invites", status_code=201)
async def create_workspace_invite(
    request: Request,
    workspace_id: UUID,
    body: WorkspaceInviteRequest = JSON_BODY,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    record = await _create_invite(
        request=request,
        workspace_id=workspace_id,
        body=body,
        actor_sub=caller_sub,
    )
    return _invite_payload(record)


async def _workspace_rollup(runtime: Any) -> dict[str, Any]:
    workspaces = await runtime.workspaces.list_all()
    members = []
    agents = []
    degraded: list[str] = []
    for workspace in workspaces:
        try:
            members.extend(await runtime.workspaces.list_members(workspace.id))
        except Exception as exc:  # pragma: no cover - defensive rollup
            degraded.append(f"members unavailable for {workspace.id}: {exc}")
        try:
            agents.extend(await runtime.agents.list_for_workspace(workspace.id))
        except Exception as exc:  # pragma: no cover - defensive rollup
            degraded.append(f"agents unavailable for {workspace.id}: {exc}")
    return {
        "workspaces": workspaces,
        "members": members,
        "agents": agents,
        "degraded": degraded,
    }


@router_system.get("/overview")
async def get_system_admin_overview(
    request: Request,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    context = _system_admin_context(caller_sub)
    runtime = request.app.state.cp
    rollup = await _workspace_rollup(runtime)
    all_signups = await runtime.enterprise_signups.list_all()
    signups = [
        _signup_payload(record)
        for record in sorted(
            all_signups, key=lambda item: item.created_at, reverse=True
        )
    ]
    all_invites = await runtime.workspace_invites.list_all()
    invites = [_invite_payload(invite) for invite in all_invites]
    return {
        "access": context,
        "metrics": {
            "workspaces": len(rollup["workspaces"]),
            "members": len(rollup["members"]),
            "agents": len(rollup["agents"]),
            "pending_signups": sum(1 for item in signups if item["status"] == "pending_review"),
            "pending_invites": sum(1 for item in invites if item["status"] == "pending"),
        },
        "enterprise_signups": signups,
        "recent_invites": sorted(invites, key=lambda item: item["created_at"], reverse=True)[:20],
        "degraded_reasons": rollup["degraded"],
    }


async def _create_workspace_for_signup(
    *,
    runtime: Any,
    signup: EnterpriseSignup,
    owner_sub: str,
) -> Any:
    base_slug = _slugify(signup.workspace_slug)
    last_error: Exception | None = None
    for index in range(0, 10):
        slug = base_slug if index == 0 else f"{base_slug}-{index + 1}"
        try:
            return await runtime.workspaces.create(
                name=signup.organization_name,
                slug=slug[:64].strip("-"),
                owner_sub=owner_sub,
                region=signup.region,
            )
        except WorkspaceError as exc:
            if "slug already taken" not in str(exc):
                raise
            last_error = exc
    raise WorkspaceError(f"could not allocate workspace slug: {last_error}")


@router_system.post("/signups/{signup_id}/approve")
async def approve_enterprise_signup(
    request: Request,
    signup_id: str,
    body: ApproveSignupRequest = JSON_BODY,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    _system_admin_context(caller_sub)
    runtime = request.app.state.cp
    signup = await runtime.enterprise_signups.get(signup_id)
    if signup is None:
        raise WorkspaceError(f"unknown enterprise signup: {signup_id}")
    if signup.status not in {"pending_review", "approved"}:
        raise WorkspaceError(f"signup is not approvable: {signup.status}")
    if signup.status == "approved" and signup.approved_workspace_id:
        workspace_id = UUID(str(signup.approved_workspace_id))
        admin_invite = (
            await runtime.workspace_invites.get(signup.admin_invite_id)
            if signup.admin_invite_id
            else None
        )
        return {
            "signup": _signup_payload(signup),
            "workspace_id": str(workspace_id),
            "admin_invite": _invite_payload(admin_invite) if admin_invite else None,
        }

    workspace = await _create_workspace_for_signup(
        runtime=runtime,
        signup=signup,
        owner_sub=caller_sub,
    )
    record_audit_event(
        workspace_id=workspace.id,
        actor_sub=caller_sub,
        action="workspace:create_from_enterprise_signup",
        resource_type="workspace",
        store=runtime.audit_events,
        resource_id=str(workspace.id),
        request_id=request_id(request),
        payload={"signup_id": signup_id, "admin_email": signup.admin_email},
    )
    invite = await _create_invite(
        request=request,
        workspace_id=workspace.id,
        body=WorkspaceInviteRequest(
            email=signup.admin_email,
            role=Role.OWNER,
            full_name=signup.admin_name,
            note=body.note or "Initial enterprise owner invite.",
        ),
        actor_sub=caller_sub,
    )
    now = _now()
    updated_signup = await runtime.enterprise_signups.update_approval(
        signup_id=signup_id,
        status="approved",
        approved_workspace_id=str(workspace.id),
        approved_by=caller_sub,
        admin_invite_id=invite.id,
        updated_at=now,
    )
    return {
        "signup": _signup_payload(updated_signup),
        "workspace_id": str(workspace.id),
        "admin_invite": _invite_payload(invite),
    }


__all__ = [
    "router_public",
    "router_system",
    "router_workspaces",
]
