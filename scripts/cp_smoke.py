"""S122: end-to-end smoke for the cp-api domain surface.

The S122 acceptance criterion is *the smoke script exits 0 against a
freshly-deployed cp-api*. The cp-api HTTP transport (FastAPI + ASGI
runtime) is being landed in a separate slice; until that ships, the
"deployed" surface we can exercise is the in-process facade tier
(``WorkspaceAPI``, ``ApiKeyAPI``, ``MeAPI``) — the same code the HTTP
routers will call.

This script walks the canonical onboarding flow:

    1. Bootstrap fresh in-memory services.
    2. Provision a user profile via a small in-memory directory.
    3. The user creates a workspace through ``WorkspaceAPI``.
    4. The user issues an API key through ``ApiKeyAPI``.
    5. The plaintext key is verified by ``ApiKeyService.verify`` —
       modelling the "authed echo" round-trip a downstream service
       would do.
    6. ``MeAPI.to_dict`` returns the expected user + workspace list.

Each step asserts the response shape so a regression in any facade
contract trips the smoke. Exits 0 with a one-line ``OK`` summary on
success; non-zero on assertion failure.

Run via ``scripts/cp_smoke.sh`` (which CI invokes) or directly with
``uv run python scripts/cp_smoke.py``.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from uuid import UUID

from loop_control_plane.api_keys import ApiKeyService
from loop_control_plane.api_keys_api import ApiKeyAPI
from loop_control_plane.me_api import MeAPI, UserProfile
from loop_control_plane.workspace_api import WorkspaceAPI
from loop_control_plane.workspaces import WorkspaceService

USER_SUB = "user-smoke"
USER_EMAIL = "smoke@example.com"
USER_NAME = "Smoke User"


async def _run() -> None:
    workspaces = WorkspaceService()
    api_keys = ApiKeyService()

    profile = UserProfile(
        sub=USER_SUB,
        email=USER_EMAIL,
        name=USER_NAME,
        created_at=datetime.now(UTC),
    )

    async def directory(sub: str) -> UserProfile | None:
        return profile if sub == USER_SUB else None

    me = MeAPI(workspace_service=workspaces, user_directory=directory)
    ws_api = WorkspaceAPI(workspaces=workspaces)
    keys_api = ApiKeyAPI(api_keys=api_keys, workspaces=workspaces)

    # 1) workspace
    ws = await ws_api.create(
        caller_sub=USER_SUB,
        body={"name": "Smoke Inc", "slug": "smoke-inc"},
    )
    assert ws["slug"] == "smoke-inc", f"workspace slug mismatch: {ws}"
    workspace_id = UUID(str(ws["id"]))

    # 2) API key
    issued = await keys_api.create(
        caller_sub=USER_SUB,
        workspace_id=workspace_id,
        body={"name": "ci-smoke"},
    )
    plaintext = issued["plaintext"]
    assert plaintext, "expected plaintext key to be returned exactly once"

    # 3) authed echo: re-verify the key out-of-band
    verified = await api_keys.verify(plaintext)
    assert str(verified.workspace_id) == str(workspace_id), "verified key bound to wrong workspace"

    # 4) /me roundtrip
    me_payload = await me.to_dict(USER_SUB)
    assert me_payload["profile"]["email"] == USER_EMAIL, f"/me returned wrong email: {me_payload}"
    assert any(w["slug"] == "smoke-inc" for w in me_payload["workspaces"]), (
        "/me did not include the new workspace"
    )


def main() -> int:
    try:
        asyncio.run(_run())
    except AssertionError as exc:
        sys.stderr.write(f"cp_smoke: FAIL {exc}\n")
        return 1
    sys.stdout.write("cp_smoke: OK\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
