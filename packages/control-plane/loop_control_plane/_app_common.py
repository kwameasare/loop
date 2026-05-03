"""Shared FastAPI dependencies for the cp-api app."""

from __future__ import annotations

import os
import time
import uuid
from importlib.metadata import PackageNotFoundError, version
from uuid import UUID

from fastapi import Body, Depends, Header, Request
from fastapi.responses import JSONResponse

from loop_control_plane.auth import AuthError
from loop_control_plane.auth_exchange import AuthExchangeError
from loop_control_plane.errors import map_to_loop_api_error
from loop_control_plane.paseto import PasetoError, decode_local
from loop_control_plane.workspaces import WorkspaceError


def package_version() -> str:
    try:
        return version("loop-control-plane")
    except PackageNotFoundError:
        return "0.1.0"


def env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def now_ms() -> int:
    return int(time.time() * 1000)


def paseto_key() -> bytes:
    key = os.environ.get("LOOP_CP_PASETO_LOCAL_KEY", "").encode("utf-8")
    if len(key) < 32:
        raise AuthError("LOOP_CP_PASETO_LOCAL_KEY must be at least 32 bytes")
    return key


def request_id(request: Request) -> str:
    header = env("LOOP_CP_REQUEST_ID_HEADER", "X-Request-Id")
    return request.headers.get(header) or str(uuid.uuid4())


async def domain_error(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, AuthExchangeError | PasetoError):
        exc = AuthError(str(exc))
    err = map_to_loop_api_error(exc, request_id=request_id(request))
    return JSONResponse(
        status_code=err.status,
        content=err.to_dict(),
        headers={"X-Request-Id": err.request_id},
    )


async def caller_sub(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> str:
    if authorization is None or not authorization.startswith("Bearer "):
        raise AuthError("missing bearer token")
    parsed = decode_local(
        authorization.removeprefix("Bearer ").strip(),
        key=paseto_key(),
        now_ms=now_ms(),
    )
    sub = parsed.claims.get("sub")
    if not isinstance(sub, str) or not sub:
        raise AuthError("token missing sub")
    request.state.loop_user_sub = sub
    return sub


async def workspace_id_header(
    x_loop_workspace_id: str | None = Header(default=None, alias="X-Loop-Workspace-Id"),
) -> UUID:
    if not x_loop_workspace_id:
        raise WorkspaceError("X-Loop-Workspace-Id header is required")
    try:
        return UUID(x_loop_workspace_id)
    except ValueError as exc:
        raise WorkspaceError("X-Loop-Workspace-Id must be a UUID") from exc


JSON_BODY = Body(...)
CALLER = Depends(caller_sub)
ACTIVE_WORKSPACE = Depends(workspace_id_header)
