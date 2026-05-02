"""Audit-event coverage matrix for control-plane write endpoints."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

MUTATING_METHODS = frozenset({"delete", "patch", "post", "put"})


@dataclass(frozen=True)
class WriteEndpointAuditCoverage:
    method: str
    path: str
    action: str
    resource_type: str
    state_source: str
    before_after: str

    @property
    def route_key(self) -> tuple[str, str]:
        return (self.method.upper(), self.path)


AUDIT_COVERAGE: tuple[WriteEndpointAuditCoverage, ...] = (
    WriteEndpointAuditCoverage(
        "POST", "/workspaces", "workspace.create", "workspace", "WorkspaceAPI.create", "after"
    ),
    WriteEndpointAuditCoverage(
        "PATCH",
        "/workspaces/{workspace_id}",
        "workspace.update",
        "workspace",
        "WorkspaceAPI.patch",
        "before+after",
    ),
    WriteEndpointAuditCoverage(
        "POST",
        "/workspaces/{workspace_id}/members",
        "member.invite",
        "member",
        "WorkspaceAPI.add_member",
        "after",
    ),
    WriteEndpointAuditCoverage(
        "PATCH",
        "/workspaces/{workspace_id}/members/{user_sub}",
        "member.role_update",
        "member",
        "WorkspaceAPI.update_member_role",
        "before+after",
    ),
    WriteEndpointAuditCoverage(
        "DELETE",
        "/workspaces/{workspace_id}/members/{user_sub}",
        "member.remove",
        "member",
        "WorkspaceAPI.remove_member",
        "before",
    ),
    WriteEndpointAuditCoverage(
        "POST",
        "/workspaces/{workspace_id}/api-keys",
        "api_key.create",
        "api_key",
        "ApiKeyAPI.create",
        "after",
    ),
    WriteEndpointAuditCoverage(
        "DELETE",
        "/workspaces/{workspace_id}/api-keys/{key_id}",
        "api_key.revoke",
        "api_key",
        "ApiKeyAPI.revoke",
        "before+after",
    ),
    WriteEndpointAuditCoverage(
        "POST", "/agents", "agent.create", "agent", "OpenAPI router", "after"
    ),
    WriteEndpointAuditCoverage(
        "DELETE", "/agents/{agent_id}", "agent.archive", "agent", "OpenAPI router", "before+after"
    ),
    WriteEndpointAuditCoverage(
        "POST",
        "/agents/{agent_id}/versions",
        "agent.deploy",
        "agent_version",
        "DeployController",
        "after",
    ),
    WriteEndpointAuditCoverage(
        "POST",
        "/agents/{agent_id}/invoke",
        "agent.invoke",
        "conversation_turn",
        "runtime trace",
        "after",
    ),
    WriteEndpointAuditCoverage(
        "POST",
        "/conversations/{conversation_id}/takeover",
        "hitl.takeover",
        "conversation",
        "InboxAPI.claim",
        "before+after",
    ),
    WriteEndpointAuditCoverage(
        "POST",
        "/conversations/{conversation_id}/messages",
        "hitl.message",
        "conversation_message",
        "conversation store",
        "after",
    ),
    WriteEndpointAuditCoverage(
        "POST", "/kb", "kb.create", "knowledge_base", "OpenAPI router", "after"
    ),
    WriteEndpointAuditCoverage(
        "POST", "/kb/{kb_id}/ingest", "kb.ingest", "kb_document", "KB ingestion queue", "after"
    ),
    WriteEndpointAuditCoverage(
        "POST", "/mcp", "mcp.install", "mcp_server", "MarketplaceInstaller.install", "after"
    ),
    WriteEndpointAuditCoverage(
        "POST", "/eval-suites", "eval_suite.create", "eval_suite", "OpenAPI router", "after"
    ),
    WriteEndpointAuditCoverage(
        "POST",
        "/eval-suites/{suite_id}/runs",
        "eval_run.start",
        "eval_run",
        "eval harness queue",
        "after",
    ),
    WriteEndpointAuditCoverage(
        "POST", "/webhooks/incoming", "webhook.register", "webhook", "OpenAPI router", "after"
    ),
    WriteEndpointAuditCoverage(
        "POST", "/budgets", "budget.create", "budget", "OpenAPI router", "after"
    ),
    WriteEndpointAuditCoverage(
        "POST",
        "/eval-suites/{suite_id}/cases",
        "eval_case.create",
        "eval_case",
        "OpenAPI router",
        "after",
    ),
    WriteEndpointAuditCoverage(
        "DELETE",
        "/eval-suites/{suite_id}/cases",
        "eval_case.delete",
        "eval_case",
        "OpenAPI router",
        "before",
    ),
    WriteEndpointAuditCoverage(
        "POST",
        "/workspaces/{workspace_id}/inbox/escalate",
        "hitl.escalate",
        "inbox_item",
        "InboxAPI.escalate",
        "after",
    ),
    WriteEndpointAuditCoverage(
        "POST",
        "/inbox/{item_id}/claim",
        "hitl.claim",
        "inbox_item",
        "InboxAPI.claim",
        "before+after",
    ),
    WriteEndpointAuditCoverage(
        "POST",
        "/inbox/{item_id}/release",
        "hitl.release",
        "inbox_item",
        "InboxAPI.release",
        "before+after",
    ),
    WriteEndpointAuditCoverage(
        "POST",
        "/inbox/{item_id}/resolve",
        "hitl.resolve",
        "inbox_item",
        "InboxAPI.resolve",
        "before+after",
    ),
)


def required_write_routes(openapi: Mapping[str, Any]) -> frozenset[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for path, item in openapi["paths"].items():
        for method in item:
            if method in MUTATING_METHODS:
                routes.add((method.upper(), path))
    return frozenset(routes)


def coverage_gaps(
    required_routes: frozenset[tuple[str, str]],
    coverage: tuple[WriteEndpointAuditCoverage, ...] = AUDIT_COVERAGE,
) -> tuple[tuple[str, str], ...]:
    covered = {entry.route_key for entry in coverage}
    return tuple(sorted(required_routes - covered))


__all__ = [
    "AUDIT_COVERAGE",
    "MUTATING_METHODS",
    "WriteEndpointAuditCoverage",
    "coverage_gaps",
    "required_write_routes",
]
