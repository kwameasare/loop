"""Tests for canonical UX wire-up routes."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

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
        json={"name": "Acme", "slug": f"acme-{uuid4().hex[:8]}", "region": "eu-west"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


@pytest.fixture
def agent_id(client: TestClient, workspace_id: UUID) -> UUID:
    response = client.post(
        "/v1/agents",
        headers={
            "authorization": _bearer_for("owner-1"),
            "x-loop-workspace-id": str(workspace_id),
        },
        json={"name": "Support Bot", "slug": f"support-{uuid4().hex[:8]}"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def _auth(sub: str = "owner-1") -> dict[str, str]:
    return {"authorization": _bearer_for(sub)}


def _add_trace(client: TestClient, workspace_id: UUID, agent_id: UUID, trace_id: str) -> None:
    cp = client.app.state.cp  # type: ignore[attr-defined]
    cp.trace_store.add(
        TraceSummary(
            workspace_id=workspace_id,
            trace_id=trace_id,
            turn_id=uuid4(),
            conversation_id=uuid4(),
            agent_id=agent_id,
            started_at=datetime(2026, 5, 7, 10, 0, tzinfo=UTC),
            duration_ms=180,
            span_count=8,
        )
    )


def test_presence_websocket_broadcasts_selection_updates(
    client: TestClient, workspace_id: UUID
) -> None:
    url = f"/v1/workspaces/{workspace_id}/presence?caller_sub=owner-1"
    with client.websocket_connect(url) as ws1:
        assert ws1.receive_json()["type"] == "presence.joined"
        with client.websocket_connect(url) as ws2:
            assert ws1.receive_json()["type"] == "presence.joined"
            assert ws2.receive_json()["type"] == "presence.joined"
            ws1.send_json({"type": "selection.update", "cursor": {"x": 42, "y": 8}})
            assert ws1.receive_json()["type"] == "selection.update"
            peer_event = ws2.receive_json()
            assert peer_event["type"] == "selection.update"
            assert peer_event["cursor"] == {"x": 42, "y": 8}


def test_replay_against_draft_and_version_diff_are_audited(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    trace_id = "trace-prod-1"
    response = client.post(
        f"/v1/agents/{agent_id}/replay/against-draft",
        headers=_auth(),
        json={"trace_ids": [trace_id], "draft_branch_ref": "draft/safer-refunds"},
    )
    assert response.status_code == 200, response.text
    row = response.json()["items"][0]
    assert row["trace_id"] == trace_id
    assert row["token_aligned_rows"][1]["status"] == "changed"

    diff = client.post(
        f"/v1/agents/{agent_id}/replay/diff",
        headers=_auth(),
        json={
            "trace_ids": [trace_id],
            "draft_branch_ref": "v23",
            "compare_version_ref": "v22",
        },
    )
    assert diff.status_code == 200, diff.text
    assert diff.json()["items"][0]["baseline_version_ref"] == "v22"

    audit = client.get(
        f"/v1/audit-events?workspace_id={workspace_id}",
        headers=_auth(),
    ).json()["items"]
    assert {event["action"] for event in audit} >= {
        "replay:against_draft",
        "replay:version_diff",
    }


def test_dashboard_pins_persist_and_homepage_pins_are_user_scoped(
    client: TestClient, workspace_id: UUID
) -> None:
    created = client.post(
        f"/v1/workspaces/{workspace_id}/dashboards",
        headers=_auth(),
        json={
            "name": "Production health",
            "layout": [{"metric_id": "p95_latency", "span": 4}],
            "shared_with": ["teammate@example.com"],
        },
    )
    assert created.status_code == 201, created.text
    listed = client.get(f"/v1/workspaces/{workspace_id}/dashboards", headers=_auth())
    assert listed.json()["items"][0]["layout"][0]["metric_id"] == "p95_latency"

    pin = client.post(
        f"/v1/workspaces/{workspace_id}/homepage/pins",
        headers=_auth(),
        json={
            "source_type": "trace",
            "source_id": "trace-prod-1",
            "title": "Worst trace",
            "href": "/traces/trace-prod-1",
        },
    )
    assert pin.status_code == 201, pin.text
    pins = client.get(f"/v1/workspaces/{workspace_id}/homepage/pins", headers=_auth())
    assert pins.json()["items"][0]["title"] == "Worst trace"


def test_comment_resolution_can_create_eval_case(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    response = client.post(
        f"/v1/agents/{agent_id}/comments/cmt_123/resolve",
        headers=_auth(),
        json={
            "expected_behavior": "Refund premium customers immediately.",
            "failure_reason": "Agent escalated instead of refunding.",
            "source_trace": "trace-prod-1",
            "also_create_eval_case": True,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["case_id"] == "eval_comment_cmt_123"


def test_approval_edit_invalidates_content_hash_bound_approval(
    client: TestClient, workspace_id: UUID
) -> None:
    changeset = client.post(
        f"/v1/workspaces/{workspace_id}/approval-changesets",
        headers=_auth(),
        json={"title": "Raise tool budget", "payload": {"budget_usd": 10}},
    ).json()
    approved = client.post(
        f"/v1/workspaces/{workspace_id}/approval-changesets/{changeset['id']}/approve",
        headers=_auth(),
    ).json()
    assert approved["approvals"][0]["state"] == "approved"

    edited = client.post(
        f"/v1/workspaces/{workspace_id}/approval-changesets/{changeset['id']}/edit",
        headers=_auth(),
        json={"title": "Raise tool budget", "payload": {"budget_usd": 20}},
    )
    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert body["approvals"] == []
    assert body["invalidated_approvals"][0]["state"] == "invalidated"


def test_byok_rotation_revocation_and_residency_block_are_audited(
    client: TestClient, workspace_id: UUID
) -> None:
    bind = client.post(
        f"/v1/workspaces/{workspace_id}/encryption/key",
        headers=_auth(),
        json={
            "provider": "aws-kms",
            "key_uri": "arn:aws:kms:eu-west-2:111:key/abc",
            "role_binding": "arn:aws:iam::111:role/loop",
        },
    )
    assert bind.status_code == 200, bind.text
    rotate = client.post(
        f"/v1/workspaces/{workspace_id}/encryption/key/rotate",
        headers=_auth(),
    ).json()
    assert rotate["version"] == 2
    revoke = client.post(
        f"/v1/workspaces/{workspace_id}/encryption/key/revoke",
        headers=_auth(),
    ).json()
    assert revoke["workspace_disabled"] is True
    assert revoke["status"] == "revoked"

    residency = client.post(
        f"/v1/workspaces/{workspace_id}/residency/check",
        headers=_auth(),
        json={"target_region": "na-east", "tool_name": "lookup_order"},
    )
    assert residency.status_code == 200, residency.text
    assert residency.json()["code"] == "LOOP-AC-602"
    assert residency.json()["trace_event"] == "cross_region_blocked"


def test_behavior_telemetry_inverse_retrieval_voice_and_scenes(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    trace_id = "2" * 32
    _add_trace(client, workspace_id, agent_id, trace_id)

    telemetry = client.get(
        f"/v1/agents/{agent_id}/behavior/sentence-telemetry",
        headers=_auth(),
    )
    assert telemetry.status_code == 200, telemetry.text
    assert telemetry.json()["items"][0]["representative_traces"] == [trace_id]

    inverse = client.post(
        f"/v1/agents/{agent_id}/kb/inverse-retrieval",
        headers=_auth(),
        json={"chunk_id": "chunk_refunds"},
    )
    assert inverse.status_code == 200, inverse.text
    assert inverse.json()["items"][0]["trace_id"] == trace_id

    number = client.post(
        f"/v1/workspaces/{workspace_id}/voice/numbers/provision",
        headers=_auth(),
        json={"country": "US", "area_code": "415", "capability": "voice", "provider": "twilio"},
    )
    assert number.status_code == 200, number.text
    assert number.json()["sip_route"].startswith("livekit://")

    scorers = client.get("/v1/eval-scorers/voice", headers=_auth()).json()["items"]
    assert {item["id"] for item in scorers} >= {"voice_wer", "voice_stage_latency"}

    scene = client.post(
        f"/v1/workspaces/{workspace_id}/scenes",
        headers=_auth(),
        json={
            "name": "Refund escalation",
            "category": "refund flow",
            "trace_ids": [trace_id],
            "expected_behavior": "Refund or explain policy.",
        },
    )
    assert scene.status_code == 201, scene.text
    replay = client.post(
        f"/v1/workspaces/{workspace_id}/scenes/{scene.json()['id']}/replay",
        headers=_auth(),
    )
    assert replay.json()["trace_ids"] == [trace_id]


def test_tool_import_persona_semantic_diff_style_bisect_and_shares(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    client.post(
        f"/v1/agents/{agent_id}/versions",
        headers=_auth(),
        json={"spec": {"prompt": "Keep answers under 100 words."}, "notes": "tightened copy"},
    )

    tool = client.post(
        f"/v1/agents/{agent_id}/tools/import",
        headers=_auth(),
        json={"source": "curl -X POST https://api.stripe.com/v1/customers", "source_kind": "curl"},
    )
    assert tool.status_code == 200, tool.text
    assert tool.json()["name"] == "stripe_request"
    assert tool.json()["safety_contract"]["approval_required"] is True

    persona = client.post(
        f"/v1/agents/{agent_id}/persona-test",
        headers=_auth(),
        json={"persona_set": "first-user"},
    )
    assert len(persona.json()["items"]) == 5

    semantic = client.post(
        f"/v1/agents/{agent_id}/semantic-diff",
        headers=_auth(),
        json={"before": "Keep under 100 words.", "after": "Refuse medical advice."},
    )
    summaries = [item["summary"] for item in semantic.json()["items"]]
    assert any("100 words" in summary for summary in summaries)
    assert any("medical advice" in summary for summary in summaries)

    style = client.post(
        f"/v1/agents/{agent_id}/style-transfer",
        headers=_auth(),
        json={"section": "Be clear."},
    )
    assert {item["voice"] for item in style.json()["items"]} == {
        "formal",
        "casual",
        "empathetic",
        "concise",
        "expert",
    }

    bisect = client.post(
        f"/v1/agents/{agent_id}/bisect",
        headers=_auth(),
        json={"failing_eval_case_id": "eval.refund.regressed"},
    )
    assert bisect.json()["status"] == "complete"

    share = client.post(
        f"/v1/workspaces/{workspace_id}/shares",
        headers=_auth(),
        json={
            "source_type": "trace",
            "source_id": "2" * 32,
            "redactions": ["pii", "secrets"],
        },
    )
    assert share.status_code == 201, share.text
    viewed = client.get(f"/v1/shares/{share.json()['id']}", headers=_auth())
    assert viewed.json()["redaction_banner"].startswith("2 redaction")


def test_telemetry_help_branding_voice_demo_and_activity(
    client: TestClient, workspace_id: UUID, agent_id: UUID
) -> None:
    consent = client.get(
        f"/v1/workspaces/{workspace_id}/telemetry-consent",
        headers=_auth(),
    )
    assert consent.json()["annual_review_due"] is True
    saved = client.post(
        f"/v1/workspaces/{workspace_id}/telemetry-consent",
        headers=_auth(),
        json={
            "product_analytics": False,
            "diagnostics": True,
            "ai_improvement": False,
            "crash_reports": False,
        },
    )
    assert saved.json()["product_analytics"] is False
    assert saved.json()["annual_review_due"] is False

    clips = client.get("/v1/help-clips?surface=pipeline", headers=_auth()).json()["items"]
    assert clips[0]["clip_id"] == "clip_canary_slider"

    branding = client.post(
        f"/v1/workspaces/{workspace_id}/branding/compile",
        headers=_auth(),
        json={
            "logo_url": "https://example.com/logo.png",
            "primary_color": "#123456",
            "custom_domain": "studio.acme.test",
        },
    )
    assert branding.json()["css_variables"]["--loop-brand-primary"] == "#123456"

    demo = client.post(
        f"/v1/workspaces/{workspace_id}/voice/demo-links",
        headers=_auth(),
        json={"snapshot_id": "snap_123", "expires_in_minutes": 5},
    )
    assert demo.status_code == 201, demo.text
    assert demo.json()["url"].startswith("/voice-demo/")

    _add_trace(client, workspace_id, agent_id, "3" * 32)
    activity = client.get(f"/v1/workspaces/{workspace_id}/activity", headers=_auth())
    assert activity.json()["turn_rate_per_minute"] == 1
