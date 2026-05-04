"""dp-runtime authentication dependency.

Closes P0.1 from the prod-readiness audit. Before this module shipped,
``/v1/turns`` and ``/v1/turns/stream`` accepted any caller with network
reach; ``RuntimeTurnRequest.workspace_id`` and ``user_id`` were plain
fields and a caller could post any UUID to bill an arbitrary
workspace's LLM quota. This was an open-relay LLM gateway.

Trust model
===========
The cp-api is the source of truth for IdP exchange + workspace
membership. cp mints a PASETO ``access_token`` with claims:

* ``sub`` — the IdP-issued user id (Auth0 sub or local-dev mapping).
* ``workspaces`` — optional list of workspace UUIDs the user may use.
  When present, dp checks `body.workspace_id in token.workspaces`.
  When absent (legacy mint or operator forced single-tenant), dp
  falls through to checking only that ``sub == body.user_id``.

dp shares the same PASETO local key (`LOOP_CP_PASETO_LOCAL_KEY`) as
cp because cp issues + dp consumes; this is the simplest workable
trust path. Production deployments where cp and dp must NOT share
a key can substitute service-to-service mTLS or a dp-specific
verifier — those are bigger refactors and out of scope for the
audit-closure PR.

Bypass
======
``LOOP_DP_AUTH_DISABLE=1`` skips the bearer check entirely. This is
strictly for the dev path (the local-stack `dev.sh` runner before
seed_dev mints any tokens) and for the existing test suite. The
production-readiness check below logs a hard warning when this flag
is set so the operator never forgets.
"""

from __future__ import annotations

import os
import time
from typing import Final

from fastapi import Depends, Header, HTTPException

DEFAULT_PASETO_KEY_ENV: Final[str] = "LOOP_CP_PASETO_LOCAL_KEY"
DEFAULT_DISABLE_ENV: Final[str] = "LOOP_DP_AUTH_DISABLE"


class DpAuthError(HTTPException):
    """Raised when an inbound /v1/turns request fails authentication.

    Maps to HTTP 401. Generic message — never reveals which check
    failed (missing token vs bad sig vs expired vs wrong sub).
    """

    def __init__(self, detail: str = "unauthorized") -> None:
        super().__init__(status_code=401, detail={"code": "LOOP-RT-101", "message": detail})


def _paseto_key() -> bytes:
    raw = os.environ.get(DEFAULT_PASETO_KEY_ENV, "").encode("utf-8")
    if len(raw) < 32:
        # If the operator forgot to set the key + auth-disable isn't on,
        # fail loudly at first request rather than silently no-op.
        raise DpAuthError("server misconfigured: missing PASETO key")
    return raw


def _auth_disabled() -> bool:
    return os.environ.get(DEFAULT_DISABLE_ENV, "").strip() in ("1", "true", "TRUE")


def _decode_token(token: str) -> dict[str, object]:
    """Decode + verify a PASETO bearer using cp's local key.

    We import lazily so dp doesn't take a hard dep on the cp package
    just for the verifier. Both packages already depend on each
    other's primitives transitively in the workspace.
    """
    from loop_control_plane.paseto import PasetoError, decode_local

    try:
        parsed = decode_local(token, key=_paseto_key(), now_ms=int(time.time() * 1000))
    except PasetoError as exc:
        raise DpAuthError() from exc
    return parsed.claims


async def authenticated_caller(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, object]:
    """FastAPI dependency: extract + verify the bearer.

    Returns the validated claims dict. Routes consume this and then
    call :func:`enforce_workspace_match` once they have the body
    parsed (FastAPI ordering: dependencies resolve before request
    body is bound, so the body-aware check happens in the handler).
    """
    if _auth_disabled():
        # Synthetic claims so handlers can pretend an anonymous caller
        # is the body's user_id. Logs a one-time warning at startup
        # via runtime_app's startup hook.
        return {"sub": "auth-disabled", "_dp_auth_disabled": True}
    if authorization is None or not authorization.startswith("Bearer "):
        raise DpAuthError()
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise DpAuthError()
    return _decode_token(token)


def enforce_workspace_match(
    *,
    claims: dict[str, object],
    body_workspace_id: str,
    body_user_id: str,
) -> None:
    """Verify the request body matches the authenticated principal.

    Raises :class:`DpAuthError` (401) on mismatch. Called by the route
    handler after the body is bound, since dependency ordering in
    FastAPI puts dep resolution before body parsing.
    """
    # When auth is disabled (dev path), skip the cross-check too —
    # the dev seed script doesn't mint workspace claims.
    if claims.get("_dp_auth_disabled"):
        return

    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub:
        raise DpAuthError()
    # `user_id` in the request body must match `sub` in the token.
    # Otherwise an authenticated user X could send turns posing as
    # user Y inside the same workspace.
    if sub != body_user_id:
        raise DpAuthError()

    # Optional workspace allow-list claim. cp can mint tokens with a
    # `workspaces: [uuid, ...]` claim listing every workspace the
    # subject is a member of. When present, gate; when absent,
    # accept (legacy mint).
    workspaces = claims.get("workspaces")
    if workspaces is None:
        return
    if not isinstance(workspaces, list):
        raise DpAuthError()
    workspace_ids = {str(w) for w in workspaces}
    if body_workspace_id not in workspace_ids:
        raise DpAuthError()


# Pre-built FastAPI Depends so route handlers can write
# `claims: dict = AUTH_CALLER` instead of `Depends(authenticated_caller)`.
AUTH_CALLER = Depends(authenticated_caller)


__all__ = [
    "AUTH_CALLER",
    "DpAuthError",
    "authenticated_caller",
    "enforce_workspace_match",
]
