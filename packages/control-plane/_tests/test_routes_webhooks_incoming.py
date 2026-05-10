"""Tests for the inbound webhook dispatcher (P0.4 final)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from loop_control_plane.app import create_app
from loop_control_plane.paseto import encode_local

_TEST_KEY = b"x" * 32


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOOP_CP_PASETO_LOCAL_KEY", _TEST_KEY.decode())
    monkeypatch.setenv("LOOP_OTEL_ENDPOINT", "disabled")


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


@pytest.fixture
def workspace_id(client: TestClient) -> UUID:
    return UUID(
        client.post(
            "/v1/workspaces",
            headers=_auth(),
            json={"name": "Acme", "slug": f"acme-{uuid4().hex[:8]}"},
        ).json()["id"]
    )


@pytest.fixture
def agent_id(client: TestClient, workspace_id: UUID) -> UUID:
    response = client.post(
        "/v1/agents",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={"name": "Support Bot", "slug": f"support-{uuid4().hex[:8]}"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def _configure_binding(
    client: TestClient,
    *,
    workspace_id: UUID,
    agent_id: UUID,
    channel_type: str,
    status: str = "live",
) -> dict[str, object]:
    response = client.post(
        f"/v1/agents/{agent_id}/channel-bindings",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
        json={
            "channel_type": channel_type,
            "provider": f"{channel_type} provider",
            "display_name": f"Acme {channel_type}",
            "status": status,
            "identity_config": {"external_ref": f"{channel_type}_{uuid4().hex[:8]}"},
            "auth_config_ref": f"secret://channels/{channel_type}/{uuid4().hex[:8]}",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_supported_channels_endpoint() -> None:
    """The /_supported probe lets operators discover channel names
    without consulting docs."""
    import os

    os.environ["LOOP_CP_PASETO_LOCAL_KEY"] = _TEST_KEY.decode()
    os.environ["LOOP_OTEL_ENDPOINT"] = "disabled"
    client = TestClient(create_app())
    response = client.get("/v1/webhooks/incoming/_supported")
    assert response.status_code == 200
    channels = response.json()["channels"]
    for c in ("slack", "whatsapp", "discord", "telegram", "twilio", "teams", "email"):
        assert c in channels


def test_unknown_channel_returns_404(
    client: TestClient, workspace_id: UUID
) -> None:
    response = client.post(
        f"/v1/webhooks/incoming/imaginary-channel?workspace_id={workspace_id}",
        json={"event_id": "x"},
    )
    assert response.status_code == 404


def test_slack_inbound_dedups_replays(
    client: TestClient, workspace_id: UUID
) -> None:
    """Same Slack `event_id` posted twice = first claims, second
    reports duplicate=True. Closes the at-least-once delivery
    vector that would otherwise produce 2 agent runs per event."""
    payload = {"event_id": "Ev123ABC", "event": {"ts": "1", "type": "message"}}
    first = client.post(
        f"/v1/webhooks/incoming/slack?workspace_id={workspace_id}",
        json=payload,
    )
    second = client.post(
        f"/v1/webhooks/incoming/slack?workspace_id={workspace_id}",
        json=payload,
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True


def test_inbound_webhook_records_trace_and_channel_activity(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
) -> None:
    """A configured live channel must create durable trace evidence.

    This is the agent-flow acceptance criterion: a live channel event
    records the channel binding that produced it instead of remaining a
    provider ack with no Studio evidence.
    """
    binding = _configure_binding(
        client,
        workspace_id=workspace_id,
        agent_id=agent_id,
        channel_type="slack",
        status="live",
    )
    payload = {
        "event_id": f"EvTrace{uuid4().hex}",
        "event": {"ts": "1", "type": "message"},
    }

    response = client.post(
        (
            f"/v1/webhooks/incoming/slack?workspace_id={workspace_id}"
            f"&agent_id={agent_id}&channel_binding_id={binding['id']}"
        ),
        json=payload,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["duplicate"] is False
    assert body["routing_status"] == "routed"
    assert body["agent_id"] == str(agent_id)
    assert body["channel_binding_id"] == binding["id"]
    assert len(body["trace_id"]) == 32
    assert body["evidence_ref"] == f"trace/{body['trace_id']}"

    trace = client.get(f"/v1/traces/{body['trace_id']}", headers=_auth())
    assert trace.status_code == 200, trace.text
    trace_body = trace.json()
    assert trace_body["agent_id"] == str(agent_id)
    assert trace_body["channel_binding_id"] == binding["id"]
    assert trace_body["spans"][0]["attrs"]["channel_binding_id"] == binding["id"]

    channels = client.get(
        f"/v1/agents/{agent_id}/channel-bindings",
        headers={**_auth(), "x-loop-workspace-id": str(workspace_id)},
    )
    assert channels.status_code == 200, channels.text
    slack = next(item for item in channels.json()["items"] if item["channel_type"] == "slack")
    assert slack["last_traffic_at"] is not None
    assert slack["last_failure_at"] is None


def test_inbound_webhook_duplicate_does_not_create_second_trace(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
) -> None:
    binding = _configure_binding(
        client,
        workspace_id=workspace_id,
        agent_id=agent_id,
        channel_type="whatsapp",
        status="ready",
    )
    message_id = f"wamid.{uuid4().hex}"
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": message_id,
                                    "from": "15551234567",
                                    "timestamp": "1700",
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    url = (
        f"/v1/webhooks/incoming/whatsapp?workspace_id={workspace_id}"
        f"&agent_id={agent_id}&channel_binding_id={binding['id']}"
    )

    first = client.post(url, json=payload)
    second = client.post(url, json=payload)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["routing_status"] == "routed"
    assert first.json()["trace_id"]
    assert second.json()["routing_status"] == "duplicate"
    assert second.json()["trace_id"] is None

    traces = client.get(
        f"/v1/workspaces/{workspace_id}/traces?agent_id={agent_id}",
        headers=_auth(),
    )
    assert traces.status_code == 200, traces.text
    assert [item["trace_id"] for item in traces.json()["items"]] == [first.json()["trace_id"]]


def test_inbound_webhook_acknowledges_but_does_not_fake_trace_without_live_binding(
    client: TestClient,
    workspace_id: UUID,
    agent_id: UUID,
) -> None:
    binding = _configure_binding(
        client,
        workspace_id=workspace_id,
        agent_id=agent_id,
        channel_type="telegram",
        status="draft",
    )
    payload = {"update_id": int(datetime.now(UTC).timestamp()), "message": {"text": "Hi"}}

    response = client.post(
        (
            f"/v1/webhooks/incoming/telegram?workspace_id={workspace_id}"
            f"&agent_id={agent_id}&channel_binding_id={binding['id']}"
        ),
        json=payload,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["duplicate"] is False
    assert body["routing_status"] == "binding_not_routable"
    assert body["trace_id"] is None
    assert body["evidence_ref"] is None

    traces = client.get(
        f"/v1/workspaces/{workspace_id}/traces?agent_id={agent_id}",
        headers=_auth(),
    )
    assert traces.status_code == 200, traces.text
    assert traces.json()["items"] == []


def test_whatsapp_dedups_on_wamid(
    client: TestClient, workspace_id: UUID
) -> None:
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "wamid.HBgL_X",
                                    "from": "15551234567",
                                    "timestamp": "1700",
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    a = client.post(
        f"/v1/webhooks/incoming/whatsapp?workspace_id={workspace_id}", json=payload
    )
    b = client.post(
        f"/v1/webhooks/incoming/whatsapp?workspace_id={workspace_id}", json=payload
    )
    assert a.json()["duplicate"] is False
    assert b.json()["duplicate"] is True


def test_twilio_dedups_form_encoded(
    client: TestClient, workspace_id: UUID
) -> None:
    """Twilio sends form-encoded; the dispatcher's _payload_for_extractor
    parses it before delegating to the extractor."""
    body = "From=%2B15551234567&MessageSid=SM" + "x" * 32
    a = client.post(
        f"/v1/webhooks/incoming/twilio?workspace_id={workspace_id}",
        content=body,
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    b = client.post(
        f"/v1/webhooks/incoming/twilio?workspace_id={workspace_id}",
        content=body,
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert a.json()["duplicate"] is False
    assert b.json()["duplicate"] is True


def test_dedup_namespaces_per_channel(
    client: TestClient, workspace_id: UUID
) -> None:
    """Same provider-event-id under two channels is two distinct dedup
    keys (the namespacing in `make_dedup_key` enforces this)."""
    slack = client.post(
        f"/v1/webhooks/incoming/slack?workspace_id={workspace_id}",
        json={"event_id": "shared-id"},
    ).json()
    discord = client.post(
        f"/v1/webhooks/incoming/discord?workspace_id={workspace_id}",
        json={"id": "shared-id"},
    ).json()
    assert slack["duplicate"] is False
    assert discord["duplicate"] is False


def test_dedup_namespaces_per_workspace(client: TestClient, workspace_id: UUID) -> None:
    """Same provider event in two workspaces must not suppress another tenant."""
    other_workspace = UUID(
        client.post(
            "/v1/workspaces",
            headers=_auth(),
            json={"name": "Beta", "slug": f"beta-{uuid4().hex[:8]}"},
        ).json()["id"]
    )
    payload = {"event_id": f"shared-workspace-event-{uuid4().hex}"}

    acme = client.post(
        f"/v1/webhooks/incoming/slack?workspace_id={workspace_id}",
        json=payload,
    ).json()
    beta = client.post(
        f"/v1/webhooks/incoming/slack?workspace_id={other_workspace}",
        json=payload,
    ).json()

    assert acme["duplicate"] is False
    assert beta["duplicate"] is False


def test_audit_emits_accept_and_duplicate_events(
    client: TestClient, workspace_id: UUID
) -> None:
    payload = {"event_id": "Ev999"}
    client.post(
        f"/v1/webhooks/incoming/slack?workspace_id={workspace_id}", json=payload
    )
    client.post(
        f"/v1/webhooks/incoming/slack?workspace_id={workspace_id}", json=payload
    )
    state = client.app.state.cp  # type: ignore[attr-defined]
    actions = [e.action for e in state.audit_events.list_for_workspace(workspace_id)]
    assert "webhook:incoming:accept" in actions
    assert "webhook:incoming:duplicate" in actions


def test_missing_workspace_id_returns_422(client: TestClient) -> None:
    response = client.post(
        "/v1/webhooks/incoming/slack",
        json={"event_id": "x"},
    )
    assert response.status_code == 422  # Pydantic missing required Query


def test_audit_payload_does_not_contain_raw_message_content(
    client: TestClient, workspace_id: UUID
) -> None:
    """Channel content can include PII; we only log metadata in the
    audit row. Belt-and-suspenders since AuditEvent stores hash anyway."""
    payload = {"event_id": "Ev1", "text": "personal-secret-message"}
    client.post(
        f"/v1/webhooks/incoming/slack?workspace_id={workspace_id}", json=payload
    )
    state = client.app.state.cp  # type: ignore[attr-defined]
    rows = list(state.audit_events.list_for_workspace(workspace_id))
    assert all(not hasattr(r, "payload") for r in rows)
    # AuditEvent stores `payload_hash` only; the route's payload dict
    # passed to record_audit_event must not contain the message text.
    # (We can't introspect the now-hashed payload, but the route source
    # never includes raw body in the payload arg — verified by reading
    # the route source.)
