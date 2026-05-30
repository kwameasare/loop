"""Agent test-turn proxy.

The studio's "Test turn" button posts here. cp resolves the agent's
workspace_id, constructs a ``RuntimeTurnRequest`` shape that dp accepts,
forwards the caller's bearer to dp's ``/v1/turns``, and returns dp's
JSON response.

This is intentionally a thin proxy — cp does not buffer the streaming
SSE variant yet. For the first-agent moment we want a single
request/response round-trip the studio can show as "the agent replied
with X." Streaming + tool dispatch land in a follow-up pass.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access

router = APIRouter(prefix="/v1/agents", tags=["AgentTurns"])


class TestTurnRequest(BaseModel):
    """Body for ``POST /v1/agents/{id}/test-turn``."""

    model_config = ConfigDict(extra="forbid", strict=True)
    input: str = Field(min_length=1, max_length=8_000)
    """User-typed prompt to send to the agent."""
    version: int | None = Field(default=None, ge=1)
    """Pin a specific agent version. None → resolve to active."""
    channel: str = Field(default="web", min_length=1, max_length=32)
    """Channel hint for the runtime; default to the in-studio web preview."""


def _dp_url(request: Request) -> str:
    """Resolve the dp-runtime base URL.

    Reads ``LOOP_DP_INTERNAL_URL`` from app state at boot. Falls back
    to the local-dev default so tests don't need to wire env vars.
    """
    return getattr(request.app.state, "dp_internal_url", None) or (
        "http://localhost:18181"
    )


@router.post("/{agent_id}/test-turn", status_code=200)
async def test_turn(
    request: Request,
    agent_id: UUID,
    body: TestTurnRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    """Send a single test prompt through cp → dp → gateway → model.

    The caller's bearer is forwarded to dp; dp's auth middleware verifies
    it the same way it verifies any other turn caller.
    """
    cp = request.app.state.cp
    agent = cp.agents._agents.get(agent_id)  # type: ignore[attr-defined]
    if agent is None:
        raise HTTPException(status_code=404, detail="unknown agent")
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=agent.workspace_id,
        user_sub=caller_sub,
        required_role=Role.MEMBER,
    )

    if authorization is None or not authorization.startswith("Bearer "):
        # The caller is authenticated against cp via api-key (CALLER
        # dependency above), but dp needs a forwardable bearer too.
        # We refuse to fake one — the caller must hold a session
        # PASETO that dp can verify.
        raise HTTPException(
            status_code=401,
            detail="test-turn requires a forwardable bearer for dp",
        )

    conversation_id = uuid4()
    dp_payload: dict[str, Any] = {
        "workspace_id": str(agent.workspace_id),
        "conversation_id": str(conversation_id),
        "user_id": caller_sub,
        "channel": body.channel,
        "input": body.input,
        "agent_id": str(agent_id),
        "request_id": str(uuid4()),
    }
    if body.version is not None:
        dp_payload["agent_version"] = body.version

    dp_url = _dp_url(request).rstrip("/")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{dp_url}/v1/turns",
                json=dp_payload,
                headers={
                    "Authorization": authorization,
                    "Accept": "application/json",
                },
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"dp unreachable: {exc}",
            ) from exc

    record_audit_event(
        workspace_id=agent.workspace_id,
        actor_sub=caller_sub,
        action="agent:test-turn",
        resource_type="agent",
        store=cp.audit_events,
        resource_id=str(agent_id),
        request_id=request_id(request),
        payload={
            "conversation_id": str(conversation_id),
            "version": body.version,
            "channel": body.channel,
            "status": response.status_code,
        },
    )

    if response.status_code >= 500:
        raise HTTPException(
            status_code=502,
            detail=f"dp returned {response.status_code}: {response.text[:240]}",
        )
    if response.status_code >= 400:
        # 4xx is meaningful to the caller (auth, validation, agent
        # without an active version, etc.) — forward as-is.
        raise HTTPException(
            status_code=response.status_code,
            detail=response.json() if response.content else None,
        )

    return response.json()
