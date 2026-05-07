"""FastAPI routes for Studio voice configuration wire-up."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from loop_control_plane.app import create_app
from loop_control_plane.paseto import encode_local
from loop_control_plane.trace_search import TraceSummary

_TEST_KEY = b"x" * 32


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOOP_CP_PASETO_LOCAL_KEY", _TEST_KEY.decode())
    monkeypatch.setenv("LOOP_OTEL_ENDPOINT", "disabled")


def _bearer_for(sub: str) -> str:
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    token = encode_local(
        claims={"sub": sub}, key=_TEST_KEY, now_ms=now_ms, expires_in_ms=3600 * 1000
    )
    return f"Bearer {token}"


@pytest.fixture
def client(env: None) -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def workspace_id(client: TestClient) -> UUID:
    response = client.post(
        "/v1/workspaces",
        headers={"authorization": _bearer_for("owner-1")},
        json={"name": "Acme", "slug": "acme"},
    )
    return UUID(response.json()["id"])


def test_voice_config_get_patch_round_trip(client: TestClient, workspace_id: UUID) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    initial = client.get(f"/v1/workspaces/{workspace_id}/voice/config", headers=headers)
    assert initial.status_code == 200, initial.text
    assert initial.json()["asr_provider"] == "deepgram"
    assert initial.json()["tts_provider"] == "elevenlabs"

    patched = client.patch(
        f"/v1/workspaces/{workspace_id}/voice/config",
        headers=headers,
        json={"asr_provider": "google", "tts_provider": "polly"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["asr_provider"] == "google"
    assert patched.json()["tts_provider"] == "polly"

    fetched = client.get(f"/v1/workspaces/{workspace_id}/voice/config", headers=headers)
    assert fetched.json()["asr_provider"] == "google"


def test_voice_config_requires_workspace_membership(
    client: TestClient, workspace_id: UUID
) -> None:
    response = client.get(
        f"/v1/workspaces/{workspace_id}/voice/config",
        headers={"authorization": _bearer_for("stranger")},
    )
    assert response.status_code in (401, 403)


def test_voice_stage_composes_config_agent_and_trace(
    client: TestClient, workspace_id: UUID
) -> None:
    headers = {"authorization": _bearer_for("owner-1")}
    agent_id = UUID(
        client.post(
            "/v1/agents",
            headers={**headers, "x-loop-workspace-id": str(workspace_id)},
            json={"name": "Voice Concierge", "slug": "voice-concierge"},
        ).json()["id"]
    )
    client.patch(
        f"/v1/workspaces/{workspace_id}/voice/config",
        headers=headers,
        json={"asr_provider": "google", "tts_provider": "polly"},
    )
    cp = client.app.state.cp  # type: ignore[attr-defined]
    cp.trace_store.add(
        TraceSummary(
            workspace_id=workspace_id,
            trace_id="e" * 32,
            turn_id=UUID("11111111-1111-1111-1111-111111111111"),
            conversation_id=UUID("22222222-2222-2222-2222-222222222222"),
            agent_id=agent_id,
            started_at=datetime(2026, 5, 4, 12, 0, tzinfo=UTC),
            duration_ms=900,
            span_count=4,
        )
    )

    response = client.get(
        f"/v1/workspaces/{workspace_id}/voice/stage",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["agentName"] == "Voice Concierge"
    assert body["config"]["asr"] == "Google Speech-to-Text v2"
    assert body["config"]["tts"] == "Amazon Polly Neural"
    assert body["transcript"][0]["id"] == "trace_eeeeeeee"
    assert body["demoLinks"][0]["audited"] is True
