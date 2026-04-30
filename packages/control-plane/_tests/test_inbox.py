"""Tests for the operator inbox queue + HTTP-shape API (S030)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from loop_control_plane import (
    InboxAPI,
    InboxError,
    InboxQueue,
)


def _ids() -> dict[str, object]:
    return {
        "workspace_id": uuid4(),
        "agent_id": uuid4(),
        "conversation_id": uuid4(),
    }


def test_escalate_creates_pending_item() -> None:
    q = InboxQueue()
    ids = _ids()
    item = q.escalate(
        workspace_id=ids["workspace_id"],  # type: ignore[arg-type]
        agent_id=ids["agent_id"],  # type: ignore[arg-type]
        conversation_id=ids["conversation_id"],  # type: ignore[arg-type]
        user_id="u-1",
        reason="user requested human",
        now_ms=1_700_000_000_000,
    )
    assert item.status == "pending"
    assert item.operator_id is None
    assert q.list_pending(ids["workspace_id"]) == [item]  # type: ignore[arg-type]


def test_escalate_rejects_duplicate_open_item_per_conversation() -> None:
    q = InboxQueue()
    ids = _ids()
    q.escalate(
        workspace_id=ids["workspace_id"],  # type: ignore[arg-type]
        agent_id=ids["agent_id"],  # type: ignore[arg-type]
        conversation_id=ids["conversation_id"],  # type: ignore[arg-type]
        user_id="u-1",
        reason="r",
        now_ms=1,
    )
    with pytest.raises(InboxError):
        q.escalate(
            workspace_id=ids["workspace_id"],  # type: ignore[arg-type]
            agent_id=ids["agent_id"],  # type: ignore[arg-type]
            conversation_id=ids["conversation_id"],  # type: ignore[arg-type]
            user_id="u-1",
            reason="r2",
            now_ms=2,
        )


def test_claim_assigns_operator_and_blocks_second_claim() -> None:
    q = InboxQueue()
    ids = _ids()
    item = q.escalate(
        workspace_id=ids["workspace_id"],  # type: ignore[arg-type]
        agent_id=ids["agent_id"],  # type: ignore[arg-type]
        conversation_id=ids["conversation_id"],  # type: ignore[arg-type]
        user_id="u-1",
        reason="r",
        now_ms=1,
    )
    claimed = q.claim(item.id, operator_id="op-alice", now_ms=2)
    assert claimed.status == "claimed"
    assert claimed.operator_id == "op-alice"
    assert claimed.claimed_at_ms == 2
    with pytest.raises(InboxError):
        q.claim(item.id, operator_id="op-bob", now_ms=3)


def test_release_returns_to_pending_and_clears_operator() -> None:
    q = InboxQueue()
    ids = _ids()
    item = q.escalate(
        workspace_id=ids["workspace_id"],  # type: ignore[arg-type]
        agent_id=ids["agent_id"],  # type: ignore[arg-type]
        conversation_id=ids["conversation_id"],  # type: ignore[arg-type]
        user_id="u-1",
        reason="r",
        now_ms=1,
    )
    q.claim(item.id, operator_id="op-alice", now_ms=2)
    released = q.release(item.id)
    assert released.status == "pending"
    assert released.operator_id is None
    # Now another operator can claim.
    q.claim(item.id, operator_id="op-bob", now_ms=4)


def test_resolve_is_terminal_and_frees_conversation_slot() -> None:
    q = InboxQueue()
    ids = _ids()
    item = q.escalate(
        workspace_id=ids["workspace_id"],  # type: ignore[arg-type]
        agent_id=ids["agent_id"],  # type: ignore[arg-type]
        conversation_id=ids["conversation_id"],  # type: ignore[arg-type]
        user_id="u-1",
        reason="r",
        now_ms=1,
    )
    q.claim(item.id, operator_id="op-alice", now_ms=2)
    resolved = q.resolve(item.id, now_ms=3)
    assert resolved.status == "resolved"
    with pytest.raises(InboxError):
        q.resolve(item.id, now_ms=4)
    # Conversation slot is freed -- a fresh escalation succeeds.
    fresh = q.escalate(
        workspace_id=ids["workspace_id"],  # type: ignore[arg-type]
        agent_id=ids["agent_id"],  # type: ignore[arg-type]
        conversation_id=ids["conversation_id"],  # type: ignore[arg-type]
        user_id="u-1",
        reason="r2",
        now_ms=5,
    )
    assert fresh.status == "pending"


def test_release_only_valid_from_claimed() -> None:
    q = InboxQueue()
    ids = _ids()
    item = q.escalate(
        workspace_id=ids["workspace_id"],  # type: ignore[arg-type]
        agent_id=ids["agent_id"],  # type: ignore[arg-type]
        conversation_id=ids["conversation_id"],  # type: ignore[arg-type]
        user_id="u-1",
        reason="r",
        now_ms=1,
    )
    with pytest.raises(InboxError):
        q.release(item.id)


def test_list_pending_filters_by_workspace_and_orders_by_created() -> None:
    q = InboxQueue()
    ws = uuid4()
    other_ws = uuid4()
    a = q.escalate(
        workspace_id=ws,
        agent_id=uuid4(),
        conversation_id=uuid4(),
        user_id="u-1",
        reason="r",
        now_ms=10,
    )
    b = q.escalate(
        workspace_id=ws,
        agent_id=uuid4(),
        conversation_id=uuid4(),
        user_id="u-2",
        reason="r",
        now_ms=5,
    )
    q.escalate(
        workspace_id=other_ws,
        agent_id=uuid4(),
        conversation_id=uuid4(),
        user_id="u-3",
        reason="r",
        now_ms=1,
    )
    assert q.list_pending(ws) == [b, a]


def test_list_claimed_by_filters_by_operator() -> None:
    q = InboxQueue()
    ws = uuid4()
    a = q.escalate(
        workspace_id=ws,
        agent_id=uuid4(),
        conversation_id=uuid4(),
        user_id="u-1",
        reason="r",
        now_ms=1,
    )
    b = q.escalate(
        workspace_id=ws,
        agent_id=uuid4(),
        conversation_id=uuid4(),
        user_id="u-2",
        reason="r",
        now_ms=2,
    )
    q.claim(a.id, operator_id="alice", now_ms=10)
    q.claim(b.id, operator_id="bob", now_ms=11)
    [alice_item] = q.list_claimed_by("alice")
    assert alice_item.id == a.id


def test_inbox_api_escalate_then_claim_then_resolve_round_trip() -> None:
    api = InboxAPI(queue=InboxQueue())
    ws = uuid4()
    agent_id = uuid4()
    conv = uuid4()
    created = api.escalate(
        workspace_id=ws,
        body={
            "agent_id": str(agent_id),
            "conversation_id": str(conv),
            "user_id": "u-1",
            "reason": "user requested human",
            "now_ms": 1_700_000_000_000,
        },
    )
    assert created["status"] == "pending"
    pending = api.list_pending(workspace_id=ws)
    assert len(pending["items"]) == 1
    item_id = pending["items"][0]["id"]
    from uuid import UUID as _UUID

    claimed = api.claim(
        item_id=_UUID(item_id),
        body={"operator_id": "alice", "now_ms": 1_700_000_001_000},
    )
    assert claimed["status"] == "claimed"
    assert claimed["operator_id"] == "alice"
    resolved = api.resolve(
        item_id=_UUID(item_id), body={"now_ms": 1_700_000_002_000}
    )
    assert resolved["status"] == "resolved"


def test_inbox_api_validation_errors_raise_inbox_error() -> None:
    api = InboxAPI(queue=InboxQueue())
    ws = uuid4()
    with pytest.raises(InboxError):
        api.escalate(workspace_id=ws, body={"agent_id": "not-a-uuid"})
    with pytest.raises(InboxError):
        api.escalate(
            workspace_id=ws,
            body={
                "agent_id": str(uuid4()),
                "conversation_id": str(uuid4()),
                "user_id": "",
                "reason": "r",
                "now_ms": 1,
            },
        )
    with pytest.raises(InboxError):
        api.escalate(
            workspace_id=ws,
            body={
                "agent_id": str(uuid4()),
                "conversation_id": str(uuid4()),
                "user_id": "u",
                "reason": "r",
                "now_ms": -1,
            },
        )
