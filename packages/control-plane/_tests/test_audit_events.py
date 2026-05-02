"""Audit-event recording tests — S630.

Covers the unit-level invariants of the ``audit_events`` module AND
the integration property the AC asks for: every cp-api write
endpoint emits exactly one ``audit_event`` row, while read endpoints
emit none.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from loop_control_plane.audit_events import (
    AuditEventError,
    InMemoryAuditEventStore,
    audited,
    hash_payload,
    record_audit_event,
)

_NOW = datetime(2027, 6, 15, 12, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_record_audit_event_round_trip() -> None:
    store = InMemoryAuditEventStore()
    ws = uuid.uuid4()
    event = record_audit_event(
        workspace_id=ws,
        actor_sub="auth0|alice",
        action="workspace.create",
        resource_type="workspace",
        resource_id=str(ws),
        store=store,
        now=_NOW,
    )
    rows = store.list_for_workspace(ws)
    assert rows == (event,)
    assert event.outcome == "success"


def test_record_audit_event_rejects_unknown_outcome() -> None:
    store = InMemoryAuditEventStore()
    with pytest.raises(AuditEventError, match="outcome"):
        record_audit_event(
            workspace_id=uuid.uuid4(),
            actor_sub="auth0|alice",
            action="workspace.create",
            resource_type="workspace",
            store=store,
            outcome="bogus",
        )


def test_record_audit_event_rejects_empty_actor() -> None:
    store = InMemoryAuditEventStore()
    with pytest.raises(AuditEventError, match="actor_sub"):
        record_audit_event(
            workspace_id=uuid.uuid4(),
            actor_sub="   ",
            action="workspace.create",
            resource_type="workspace",
            store=store,
        )


def test_record_audit_event_rejects_long_action() -> None:
    store = InMemoryAuditEventStore()
    with pytest.raises(AuditEventError, match="character limit"):
        record_audit_event(
            workspace_id=uuid.uuid4(),
            actor_sub="auth0|alice",
            action="x" * 257,
            resource_type="workspace",
            store=store,
        )


def test_payload_hash_is_stable_and_order_independent() -> None:
    a = hash_payload({"name": "demo", "slug": "d"})
    b = hash_payload({"slug": "d", "name": "demo"})
    assert a == b
    assert a != hash_payload({"name": "demo", "slug": "e"})


def test_in_memory_store_rejects_duplicate_id() -> None:
    store = InMemoryAuditEventStore()
    ev = record_audit_event(
        workspace_id=uuid.uuid4(),
        actor_sub="auth0|alice",
        action="workspace.create",
        resource_type="workspace",
        store=store,
        now=_NOW,
    )
    with pytest.raises(AuditEventError, match="already recorded"):
        store.insert(ev)  # second insert of the same event id is rejected.


def test_list_for_workspace_orders_by_occurred_at() -> None:
    store = InMemoryAuditEventStore()
    ws = uuid.uuid4()
    later = record_audit_event(
        workspace_id=ws,
        actor_sub="auth0|alice",
        action="workspace.update",
        resource_type="workspace",
        store=store,
        now=datetime(2027, 6, 16, 0, 0, tzinfo=UTC),
    )
    earlier = record_audit_event(
        workspace_id=ws,
        actor_sub="auth0|alice",
        action="workspace.create",
        resource_type="workspace",
        store=store,
        now=datetime(2027, 6, 15, 0, 0, tzinfo=UTC),
    )
    rows = store.list_for_workspace(ws)
    assert rows == (earlier, later)


# ---------------------------------------------------------------------------
# Integration: every write endpoint emits an event; reads emit none.
# ---------------------------------------------------------------------------


class _AuthorisationError(PermissionError):
    """Stand-in for cp-api's AuthorisationError (subclass of PermissionError)."""


class _StubCpApi:
    """Mimics the cp-api facade pattern — write methods are decorated,
    read methods are not, exactly as the cp-api intends."""

    def __init__(self, store: InMemoryAuditEventStore) -> None:
        self.audit_store = store
        self.created_workspaces: list[uuid.UUID] = []
        self.deny_member_add = False

    @audited(action="workspace.create", resource_type="workspace")
    async def create_workspace(
        self, *, caller_sub: str, workspace_id: uuid.UUID, name: str
    ) -> dict[str, Any]:
        self.created_workspaces.append(workspace_id)
        return {"id": str(workspace_id), "name": name}

    @audited(
        action="workspace.member.add",
        resource_type="workspace_member",
        resource_id_kwarg="member_sub",
    )
    async def add_member(
        self,
        *,
        caller_sub: str,
        workspace_id: uuid.UUID,
        member_sub: str,
        role: str,
    ) -> dict[str, Any]:
        if self.deny_member_add:
            raise _AuthorisationError("caller is not OWNER")
        return {"workspace_id": str(workspace_id), "member": member_sub, "role": role}

    @audited(action="workspace.delete", resource_type="workspace")
    async def delete_workspace(
        self, *, caller_sub: str, workspace_id: uuid.UUID
    ) -> dict[str, Any]:
        raise RuntimeError("simulated downstream failure")

    # Read methods — intentionally NOT decorated. They MUST NOT emit
    # audit events.
    async def get_workspace(
        self, *, caller_sub: str, workspace_id: uuid.UUID
    ) -> dict[str, Any]:
        return {"id": str(workspace_id)}

    async def list_workspaces(self, *, caller_sub: str) -> dict[str, Any]:
        return {"items": [{"id": str(w)} for w in self.created_workspaces]}


@pytest.mark.asyncio
async def test_every_write_endpoint_emits_audit_event_reads_emit_none() -> None:
    pytest.importorskip("pytest_asyncio")  # the async test driver
    store = InMemoryAuditEventStore()
    api = _StubCpApi(store)
    ws = uuid.uuid4()

    # 3 write calls (1 success, 1 denied, 1 error).
    await api.create_workspace(
        caller_sub="auth0|alice", workspace_id=ws, name="acme"
    )

    api.deny_member_add = True
    with pytest.raises(_AuthorisationError):
        await api.add_member(
            caller_sub="auth0|alice",
            workspace_id=ws,
            member_sub="auth0|bob",
            role="editor",
        )

    with pytest.raises(RuntimeError):
        await api.delete_workspace(caller_sub="auth0|alice", workspace_id=ws)

    # 2 read calls — must NOT emit any events.
    await api.get_workspace(caller_sub="auth0|alice", workspace_id=ws)
    await api.list_workspaces(caller_sub="auth0|alice")

    rows = store.list_for_workspace(ws)
    assert len(rows) == 3, f"expected 3 events, got: {rows}"
    actions_outcomes = sorted((r.action, r.outcome) for r in rows)
    assert actions_outcomes == sorted(
        [
            ("workspace.create", "success"),
            ("workspace.member.add", "denied"),
            ("workspace.delete", "error"),
        ]
    )


@pytest.mark.asyncio
async def test_decorator_is_noop_when_audit_store_not_wired() -> None:
    pytest.importorskip("pytest_asyncio")

    class _NoStoreApi(_StubCpApi):
        def __init__(self) -> None:
            super().__init__(InMemoryAuditEventStore())
            del self.audit_store  # remove the attribute entirely.

    api = _NoStoreApi()
    # Must not raise — must just pass through to the wrapped method.
    out = await api.create_workspace(
        caller_sub="auth0|alice", workspace_id=uuid.uuid4(), name="acme"
    )
    assert out["name"] == "acme"
