"""Workspace-scoped enterprise SAML configuration routes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID
from xml.etree import ElementTree

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access

router = APIRouter(prefix="/v1/workspaces", tags=["Enterprise"])

_APP_BASE_URL = "https://app.loop.dev"


class SamlConfigBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metadata_url: str | None = Field(default=None, max_length=2048)
    metadata_xml: str | None = Field(default=None, max_length=200_000)

    @model_validator(mode="after")
    def exactly_one_metadata_source(self) -> SamlConfigBody:
        has_url = bool(self.metadata_url and self.metadata_url.strip())
        has_xml = bool(self.metadata_xml and self.metadata_xml.strip())
        if has_url == has_xml:
            raise ValueError("provide exactly one of metadata_url or metadata_xml")
        return self


def _acs_url(workspace_id: UUID) -> str:
    return f"{_APP_BASE_URL}/auth/saml/acs/{workspace_id}"


def _default_config(workspace_id: UUID) -> dict[str, Any]:
    return {
        "status": "not_configured",
        "entity_id": None,
        "acs_url": _acs_url(workspace_id),
        "connected_at": None,
    }


def _entity_id_from_xml(metadata_xml: str) -> str:
    try:
        # Bounded SAML metadata intake; this route reads only the root entityID.
        root = ElementTree.fromstring(metadata_xml)  # noqa: S314
    except ElementTree.ParseError as exc:
        raise HTTPException(status_code=400, detail="metadata_xml is not valid XML") from exc
    entity_id = root.attrib.get("entityID") or root.attrib.get("entityId")
    if not entity_id:
        raise HTTPException(
            status_code=400,
            detail="metadata_xml must include EntityDescriptor entityID",
        )
    return entity_id.strip()


def _entity_id_from_url(metadata_url: str) -> str:
    value = metadata_url.strip()
    if not (value.startswith("https://") or value.startswith("http://")):
        raise HTTPException(status_code=400, detail="metadata_url must be absolute")
    return value


def _config_from_body(workspace_id: UUID, body: SamlConfigBody) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    if body.metadata_xml and body.metadata_xml.strip():
        entity_id = _entity_id_from_xml(body.metadata_xml)
        source = "metadata_xml"
    else:
        entity_id = _entity_id_from_url(body.metadata_url or "")
        source = "metadata_url"
    return {
        "status": "pending_verification",
        "entity_id": entity_id,
        "acs_url": _acs_url(workspace_id),
        "connected_at": None,
        "metadata_source": source,
        "updated_at": now,
    }


@router.get("/{workspace_id}/enterprise/saml")
async def get_enterprise_saml_config(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    return cp.saml_configs.get(workspace_id, _default_config(workspace_id))


@router.post("/{workspace_id}/enterprise/saml")
async def post_enterprise_saml_config(
    request: Request,
    workspace_id: UUID,
    body: SamlConfigBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    config = _config_from_body(workspace_id, body)
    cp.saml_configs[workspace_id] = config
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="enterprise_saml:update",
        resource_type="enterprise_saml_config",
        store=cp.audit_events,
        resource_id=str(workspace_id),
        request_id=request_id(request),
        payload={
            "status": config["status"],
            "entity_id": config["entity_id"],
            "metadata_source": config["metadata_source"],
            "acs_url": config["acs_url"],
        },
    )
    return config


__all__ = ["router"]
