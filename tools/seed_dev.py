"""Seed local-dev data so the studio has something to render.

Why this exists
===============

The Makefile target ``make seed`` references ``tools/seed_dev.py``, but
the file didn't exist (P0.6b in the prod-readiness audit). That meant
``make seed`` errored out and developers were left with an empty cp-api
on every fresh boot — studio's `/agents`, `/workspaces`, `/inbox` pages
all rendered "no data" or 401 because there was nothing to authorise
against.

What it does
============

1. Mints a short-lived HS256 JWT signed with ``LOOP_CP_LOCAL_JWT_SECRET``.
   The cp-api ``/v1/auth/exchange`` endpoint accepts this in dev mode
   (see ``packages/control-plane/loop_control_plane/_routes_auth.py``).
2. Exchanges that JWT for a PASETO access token.
3. Idempotently creates one workspace + one agent if they don't already
   exist. We GET first; only POST when missing. So re-running the script
   is safe (no duplicates).
4. Prints the resulting access token and workspace/agent IDs so the
   operator can paste them into ``apps/studio/.env.local`` (as
   ``LOOP_TOKEN``) for studio's server-side fetches to succeed.

Configuration
=============

Reads the same ``.env`` the rest of the local stack uses:

* ``LOOP_CP_API_URL``        — default ``http://localhost:8080``
* ``LOOP_CP_LOCAL_JWT_SECRET`` — REQUIRED. Operator must set this and
  cp-api must be started with the same value.
* ``LOOP_CP_AUTH_ISSUER``     — default ``https://loop.local/``
* ``LOOP_CP_AUTH_AUDIENCE``   — default ``loop-cp``
* ``LOOP_DEV_SEED_USER``      — default ``dev@loop.local``
* ``LOOP_DEV_SEED_WORKSPACE_NAME`` — default ``Dev Workspace``
* ``LOOP_DEV_SEED_AGENT_NAME``    — default ``demo-agent``

Exit codes
==========

* ``0`` on success or already-seeded.
* ``1`` if cp-api is unreachable, the JWT secret is missing, or the
  exchange fails.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import time
from typing import Any

import httpx


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def mint_local_jwt(
    *,
    secret: str,
    sub: str,
    issuer: str,
    audience: str,
    ttl_seconds: int = 300,
) -> str:
    """Hand-mint an HS256 JWT.

    Tiny implementation so we don't add ``pyjwt`` as a dev-only
    dependency. cp-api's ``HS256Verifier`` (``loop_control_plane.auth``)
    accepts the same wire format.
    """
    if not secret:
        raise ValueError("LOOP_CP_LOCAL_JWT_SECRET must be set to mint a local JWT")
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": sub,
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": now + ttl_seconds,
        "email": sub if "@" in sub else f"{sub}@loop.local",
    }
    header_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url(sig)}"


def exchange(client: httpx.Client, base_url: str, id_token: str) -> str:
    response = client.post(
        f"{base_url}/v1/auth/exchange",
        json={"id_token": id_token},
        timeout=5.0,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"auth exchange failed: HTTP {response.status_code} — {response.text[:300]}"
        )
    body = response.json()
    token = body.get("access_token") or body.get("session_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError(f"auth exchange returned no access_token: {body!r}")
    return token


def _bearer(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


def get_or_create_workspace(
    client: httpx.Client, base_url: str, token: str, name: str
) -> dict[str, Any]:
    headers = _bearer(token)
    listing = client.get(f"{base_url}/v1/workspaces", headers=headers, timeout=5.0)
    if listing.status_code == 200:
        for ws in listing.json().get("workspaces", []):
            if ws.get("name") == name:
                return ws  # type: ignore[no-any-return]
    response = client.post(
        f"{base_url}/v1/workspaces",
        headers=headers,
        json={"name": name},
        timeout=5.0,
    )
    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"create workspace failed: HTTP {response.status_code} — {response.text[:300]}"
        )
    return response.json()  # type: ignore[no-any-return]


def get_or_create_agent(
    client: httpx.Client,
    base_url: str,
    token: str,
    workspace_id: str,
    name: str,
) -> dict[str, Any]:
    headers = _bearer(token)
    listing = client.get(f"{base_url}/v1/agents", headers=headers, timeout=5.0)
    if listing.status_code == 200:
        for agent in listing.json().get("agents", []):
            if agent.get("name") == name and agent.get("workspace_id") == workspace_id:
                return agent  # type: ignore[no-any-return]
    response = client.post(
        f"{base_url}/v1/agents",
        headers=headers,
        json={"workspace_id": workspace_id, "name": name, "slug": name.lower().replace(" ", "-")},
        timeout=5.0,
    )
    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"create agent failed: HTTP {response.status_code} — {response.text[:300]}"
        )
    return response.json()  # type: ignore[no-any-return]


def main() -> int:
    base_url = os.environ.get("LOOP_CP_API_URL", "http://localhost:8080").rstrip("/")
    secret = os.environ.get("LOOP_CP_LOCAL_JWT_SECRET", "")
    if not secret:
        sys.stderr.write(
            "error: LOOP_CP_LOCAL_JWT_SECRET is not set.\n"
            "       Add it to .env (any string >=16 chars), restart the cp uvicorn,\n"
            "       and re-run `make seed`. The cp-api must boot with the same value.\n"
        )
        return 1

    issuer = os.environ.get("LOOP_CP_AUTH_ISSUER", "https://loop.local/")
    audience = os.environ.get("LOOP_CP_AUTH_AUDIENCE", "loop-cp")
    seed_user = os.environ.get("LOOP_DEV_SEED_USER", "dev@loop.local")
    workspace_name = os.environ.get("LOOP_DEV_SEED_WORKSPACE_NAME", "Dev Workspace")
    agent_name = os.environ.get("LOOP_DEV_SEED_AGENT_NAME", "demo-agent")

    sys.stdout.write(f"→ minting local JWT for sub={seed_user}\n")
    id_token = mint_local_jwt(
        secret=secret, sub=seed_user, issuer=issuer, audience=audience
    )

    with httpx.Client() as client:
        # Cheap reachability check first so the operator gets a clear error
        # if cp-api isn't running before we burn time on auth.
        try:
            health = client.get(f"{base_url}/healthz", timeout=2.0)
            health.raise_for_status()
        except httpx.HTTPError as exc:
            sys.stderr.write(
                f"error: cp-api at {base_url} is unreachable ({exc}).\n"
                "       Start it first: `set -a; . ./.env; set +a; "
                "uv run uvicorn loop_control_plane.app:app --port 8080`\n"
            )
            return 1

        sys.stdout.write(f"→ exchanging for PASETO at {base_url}/v1/auth/exchange\n")
        try:
            access_token = exchange(client, base_url, id_token)
        except RuntimeError as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 1

        sys.stdout.write(f"→ ensuring workspace {workspace_name!r} exists\n")
        workspace = get_or_create_workspace(client, base_url, access_token, workspace_name)
        sys.stdout.write(f"  workspace_id = {workspace.get('id')}\n")

        sys.stdout.write(f"→ ensuring agent {agent_name!r} exists\n")
        agent = get_or_create_agent(
            client, base_url, access_token, str(workspace["id"]), agent_name
        )
        sys.stdout.write(f"  agent_id     = {agent.get('id')}\n")

    sys.stdout.write("\n✓ seed complete. To use the studio against this data:\n\n")
    sys.stdout.write(f"  echo 'LOOP_TOKEN={access_token}' >> apps/studio/.env.local\n")
    sys.stdout.write("  pnpm -C apps/studio dev\n\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
