"""BYOC channel credentials route tests.

Verifies the upload → status → reveal → delete cycle and confirms
that the studio (read-only on credentials) can never round-trip the
plaintext back. Plaintext only flows out via
``cp.byoc_secrets.reveal_for_adapter`` (the channel adapter path).
"""

from __future__ import annotations

import base64
import os
from datetime import UTC, datetime
from uuid import UUID

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from loop_control_plane.app import create_app
from loop_control_plane.paseto import encode_local

_TEST_KEY = b"x" * 32
_BYOC_KEY = Fernet.generate_key()


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOOP_CP_PASETO_LOCAL_KEY", _TEST_KEY.decode())
    monkeypatch.setenv("LOOP_OTEL_ENDPOINT", "disabled")
    monkeypatch.setenv("LOOP_CP_BYOC_KEY", _BYOC_KEY.decode("ascii"))


@pytest.fixture
def client(env: None) -> TestClient:
    return TestClient(create_app())


def _bearer_for(sub: str) -> str:
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    token = encode_local(
        claims={"sub": sub},
        key=_TEST_KEY,
        now_ms=now_ms,
        expires_in_ms=3600 * 1000,
    )
    return f"Bearer {token}"


def _auth(sub: str = "owner-1") -> dict[str, str]:
    return {"authorization": _bearer_for(sub)}


def _workspace(client: TestClient) -> UUID:
    response = client.post(
        "/v1/workspaces",
        headers=_auth(),
        json={"name": "Acme", "slug": "acme"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def _agent(client: TestClient, workspace_id: UUID) -> UUID:
    response = client.post(
        "/v1/agents",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"name": "Support Bot", "slug": "support-bot"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def test_byoc_upload_status_and_reveal(client: TestClient) -> None:
    """Operator uploads Twilio creds; studio sees presence; only the
    runtime adapter resolves plaintext."""
    workspace_id = _workspace(client)
    agent_id = _agent(client, workspace_id)

    # Status before upload: empty.
    before = client.get(
        f"/v1/agents/{agent_id}/channels/sms/credentials",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert before.status_code == 200, before.text
    assert before.json() == {
        "agent_id": str(agent_id),
        "channel_type": "sms",
        "has_value": False,
    }

    # Upload Twilio account SID + auth token.
    creds = {
        "account_sid": "ACtestsid0123456789",
        "auth_token": "f0o-shhh-supersecret",
        "from_number": "+15551234567",
    }
    put = client.put(
        f"/v1/agents/{agent_id}/channels/sms/credentials",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"provider": "twilio", "values": creds},
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["has_value"] is True
    assert body["provider"] == "twilio"
    assert body["rotated_at"] is None  # first upload — no rotation yet.
    # The route NEVER echoes back the plaintext or the ciphertext.
    assert "values" not in body
    assert "ciphertext" not in body
    assert "account_sid" not in put.text
    assert "auth_token" not in put.text

    # Rotate: upload again, rotated_at flips.
    put_again = client.put(
        f"/v1/agents/{agent_id}/channels/sms/credentials",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "provider": "twilio",
            "values": {**creds, "auth_token": "rotated-token"},
        },
    )
    assert put_again.status_code == 200, put_again.text
    assert put_again.json()["rotated_at"] is not None

    # The runtime adapter path can resolve plaintext via the in-process
    # service. The HTTP surface cannot.
    app_state = client.app.state.cp
    revealed = client.app.state.cp.byoc_secrets
    # awaited via the registered event loop
    import asyncio

    plaintext = asyncio.run(
        revealed.reveal_for_adapter(agent_id=agent_id, channel_type="sms")
    )
    assert plaintext["account_sid"] == "ACtestsid0123456789"
    assert plaintext["auth_token"] == "rotated-token"

    # Delete wipes the value cleanly.
    deleted = client.delete(
        f"/v1/agents/{agent_id}/channels/sms/credentials",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert deleted.status_code == 204, deleted.text
    after = client.get(
        f"/v1/agents/{agent_id}/channels/sms/credentials",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert after.json()["has_value"] is False


def test_byoc_unknown_channel_400(client: TestClient) -> None:
    workspace_id = _workspace(client)
    agent_id = _agent(client, workspace_id)
    response = client.put(
        f"/v1/agents/{agent_id}/channels/fax/credentials",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"provider": "twilio", "values": {}},
    )
    assert response.status_code == 400, response.text
    assert "fax" in response.text


def test_byoc_unknown_agent_404(client: TestClient) -> None:
    response = client.put(
        "/v1/agents/00000000-0000-0000-0000-000000000001/channels/sms/credentials",
        headers=_auth(),
        json={"provider": "twilio", "values": {}},
    )
    assert response.status_code == 404, response.text


def test_byoc_key_at_rest_is_real_ciphertext(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Direct white-box check: the in-memory record stores Fernet
    ciphertext, not plaintext. A grep for the auth token in the
    serialised bytes must miss."""
    from loop_control_plane._byoc_secrets import build_byoc_secret_service

    key = base64.urlsafe_b64encode(os.urandom(32))
    service = build_byoc_secret_service(key=key)

    import asyncio

    async def _round_trip() -> tuple[bytes, dict[str, object]]:
        record = await service.put(
            workspace_id=UUID("00000000-0000-0000-0000-000000000aaa"),
            agent_id=UUID("00000000-0000-0000-0000-000000000bbb"),
            channel_type="sms",
            provider="twilio",
            values={"auth_token": "DO-NOT-LOG-ME"},
        )
        revealed = await service.reveal_for_adapter(
            agent_id=record.agent_id, channel_type="sms"
        )
        return record.ciphertext, revealed

    ciphertext, revealed = asyncio.run(_round_trip())
    assert b"DO-NOT-LOG-ME" not in ciphertext
    assert revealed["auth_token"] == "DO-NOT-LOG-ME"
