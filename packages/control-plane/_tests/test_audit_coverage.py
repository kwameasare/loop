"""Audit trail completeness checks for S581."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest
import yaml
from loop_control_plane.api_keys import ApiKeyService
from loop_control_plane.api_keys_api import ApiKeyAPI
from loop_control_plane.audit import (
    AuditContext,
    AuditEventInput,
    AuditLogError,
    InMemoryAuditLog,
    audit_log_append,
)
from loop_control_plane.audit_coverage import (
    coverage_gaps,
    required_write_routes,
)
from loop_control_plane.inbox import InboxQueue
from loop_control_plane.inbox_api import InboxAPI
from loop_control_plane.workspace_api import WorkspaceAPI
from loop_control_plane.workspaces import Role, WorkspaceService

ROOT = Path(__file__).resolve().parents[3]
OPENAPI_PATH = ROOT / "loop_implementation" / "api" / "openapi.yaml"


def _ctx(actor: str = "owner", *, idempotency_key: str | None = None) -> AuditContext:
    return AuditContext(
        actor=actor,
        ip="203.0.113.10",
        user_agent="pytest",
        request_id="req-1",
        trace_id="trace-1",
        idempotency_key=idempotency_key,
    )


def test_audit_log_append_chains_and_deduplicates_idempotency() -> None:
    log = InMemoryAuditLog()
    workspace_id = uuid4()
    first = audit_log_append(
        log,
        AuditEventInput(
            context=_ctx(idempotency_key="idem-1"),
            workspace_id=workspace_id,
            action="workspace.create",
            resource_type="workspace",
            resource_id=workspace_id,
            before=None,
            after={"id": str(workspace_id)},
        ),
    )
    duplicate = audit_log_append(
        log,
        AuditEventInput(
            context=_ctx(idempotency_key="idem-1"),
            workspace_id=workspace_id,
            action="workspace.create",
            resource_type="workspace",
            resource_id=workspace_id,
            before=None,
            after={"id": str(workspace_id)},
        ),
    )
    second = audit_log_append(
        log,
        AuditEventInput(
            context=_ctx(),
            workspace_id=workspace_id,
            action="workspace.update",
            resource_type="workspace",
            resource_id=workspace_id,
            before={"name": "Old"},
            after={"name": "New"},
        ),
    )

    assert duplicate == first
    assert len(log.entries()) == 2
    assert second.previous_hash == first.entry_hash
    assert log.verify_chain()


def test_audit_log_rejects_missing_required_context() -> None:
    log = InMemoryAuditLog()
    with pytest.raises(AuditLogError):
        audit_log_append(
            log,
            AuditEventInput(
                context=AuditContext(
                    actor="",
                    ip="203.0.113.10",
                    user_agent="pytest",
                    request_id="req-1",
                    trace_id="trace-1",
                ),
                workspace_id=uuid4(),
                action="workspace.create",
                resource_type="workspace",
                resource_id=None,
                before=None,
                after={},
            ),
        )


def test_audit_coverage_matrix_has_no_openapi_write_gaps() -> None:
    openapi = yaml.safe_load(OPENAPI_PATH.read_text(encoding="utf-8"))
    assert coverage_gaps(required_write_routes(openapi)) == ()


def test_audit_coverage_reports_new_write_route_gap() -> None:
    required = frozenset({("POST", "/new-state-changing-route")})
    assert coverage_gaps(required) == (("POST", "/new-state-changing-route"),)


@pytest.mark.asyncio
async def test_workspace_api_emits_audit_events_for_mutations() -> None:
    log = InMemoryAuditLog()
    api = WorkspaceAPI(workspaces=WorkspaceService(), audit_log=log)

    created = await api.create(
        caller_sub="owner",
        body={"name": "Acme", "slug": "acme"},
        audit_context=_ctx(),
    )
    ws_id = UUID(created["id"])
    updated = await api.patch(
        caller_sub="owner",
        workspace_id=ws_id,
        body={"name": "Acme Inc"},
        audit_context=_ctx(),
    )
    added = await api.add_member(
        caller_sub="owner",
        workspace_id=ws_id,
        body={"user_sub": "alice", "role": "admin"},
        audit_context=_ctx(),
    )
    await api.update_member_role(
        caller_sub="owner",
        workspace_id=ws_id,
        user_sub="alice",
        body={"role": "member"},
        audit_context=_ctx(),
    )
    await api.remove_member(
        caller_sub="owner",
        workspace_id=ws_id,
        user_sub="alice",
        audit_context=_ctx(),
    )

    actions = [entry.action for entry in log.entries()]
    assert actions == [
        "workspace.create",
        "workspace.update",
        "member.invite",
        "member.role_update",
        "member.remove",
    ]
    assert log.entries()[1].before == created
    assert log.entries()[1].after == updated
    assert log.entries()[3].before == added
    assert log.verify_chain()


@pytest.mark.asyncio
async def test_api_key_audit_redacts_secret_material() -> None:
    workspaces = WorkspaceService()
    ws = await workspaces.create(name="Acme", slug="acme", owner_sub="owner")
    await workspaces.add_member(workspace_id=ws.id, user_sub="admin", role=Role.ADMIN)
    log = InMemoryAuditLog()
    api = ApiKeyAPI(api_keys=ApiKeyService(), workspaces=workspaces, audit_log=log)

    issued = await api.create(
        caller_sub="admin",
        workspace_id=ws.id,
        body={"name": "ci-key"},
        audit_context=_ctx("admin"),
    )

    [entry] = log.entries()
    assert entry.action == "api_key.create"
    assert entry.after is not None
    assert "plaintext" not in entry.after
    assert "hash" not in entry.after
    assert issued["plaintext"] not in str(entry.after)


def test_inbox_api_emits_before_after_audit_events() -> None:
    log = InMemoryAuditLog()
    api = InboxAPI(queue=InboxQueue(), audit_log=log)
    workspace_id = uuid4()
    created = api.escalate(
        workspace_id=workspace_id,
        body={
            "agent_id": str(uuid4()),
            "conversation_id": str(uuid4()),
            "user_id": "u-1",
            "reason": "user requested human",
            "now_ms": 1,
        },
        audit_context=_ctx("u-1"),
    )
    claimed = api.claim(
        item_id=UUID(created["id"]),
        body={"operator_id": "op-1", "now_ms": 2},
        audit_context=_ctx("op-1"),
    )
    api.resolve(
        item_id=UUID(created["id"]),
        body={"now_ms": 3},
        audit_context=_ctx("op-1"),
    )

    assert [entry.action for entry in log.entries()] == [
        "hitl.escalate",
        "hitl.claim",
        "hitl.resolve",
    ]
    assert log.entries()[1].before == created
    assert log.entries()[1].after == claimed
    assert log.verify_chain()
