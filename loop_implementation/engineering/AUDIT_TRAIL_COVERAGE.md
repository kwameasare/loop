# Audit Trail Coverage Matrix

Story: S581

This matrix maps every committed write endpoint to its canonical audit
event. Implemented control-plane facades append through
`loop_control_plane.audit.audit_log_append`; routes that only exist in
`openapi.yaml` use this matrix as the implementation contract for their
router story.

## Required Event Fields

Every emitted row must include:

- `actor`
- `action`
- `workspace_id`
- `resource_type` and `resource_id`
- `created_at`, `previous_hash`, and `entry_hash`
- `client_ip`, `user_agent`, `request_id`, and `trace_id`
- `before_state` and/or `after_state` for state changes

## Matrix

| Method | Endpoint | Audit action | Resource | State source | Snapshot |
| --- | --- | --- | --- | --- | --- |
| POST | `/workspaces` | `workspace.create` | workspace | `WorkspaceAPI.create` | after |
| PATCH | `/workspaces/{workspace_id}` | `workspace.update` | workspace | `WorkspaceAPI.patch` | before+after |
| POST | `/workspaces/{workspace_id}/members` | `member.invite` | member | `WorkspaceAPI.add_member` | after |
| PATCH | `/workspaces/{workspace_id}/members/{user_sub}` | `member.role_update` | member | `WorkspaceAPI.update_member_role` | before+after |
| DELETE | `/workspaces/{workspace_id}/members/{user_sub}` | `member.remove` | member | `WorkspaceAPI.remove_member` | before |
| POST | `/workspaces/{workspace_id}/api-keys` | `api_key.create` | api_key | `ApiKeyAPI.create` | after |
| DELETE | `/workspaces/{workspace_id}/api-keys/{key_id}` | `api_key.revoke` | api_key | `ApiKeyAPI.revoke` | before+after |
| POST | `/agents` | `agent.create` | agent | OpenAPI router | after |
| DELETE | `/agents/{agent_id}` | `agent.archive` | agent | OpenAPI router | before+after |
| POST | `/agents/{agent_id}/versions` | `agent.deploy` | agent_version | `DeployController` | after |
| POST | `/agents/{agent_id}/invoke` | `agent.invoke` | conversation_turn | runtime trace | after |
| POST | `/conversations/{conversation_id}/takeover` | `hitl.takeover` | conversation | `InboxAPI.claim` | before+after |
| POST | `/conversations/{conversation_id}/messages` | `hitl.message` | conversation_message | conversation store | after |
| POST | `/kb` | `kb.create` | knowledge_base | OpenAPI router | after |
| POST | `/kb/{kb_id}/ingest` | `kb.ingest` | kb_document | KB ingestion queue | after |
| POST | `/mcp` | `mcp.install` | mcp_server | `MarketplaceInstaller.install` | after |
| POST | `/eval-suites` | `eval_suite.create` | eval_suite | OpenAPI router | after |
| POST | `/eval-suites/{suite_id}/runs` | `eval_run.start` | eval_run | eval harness queue | after |
| POST | `/webhooks/incoming` | `webhook.register` | webhook | OpenAPI router | after |
| POST | `/budgets` | `budget.create` | budget | OpenAPI router | after |
| POST | `/eval-suites/{suite_id}/cases` | `eval_case.create` | eval_case | OpenAPI router | after |
| DELETE | `/eval-suites/{suite_id}/cases` | `eval_case.delete` | eval_case | OpenAPI router | before |
| POST | `/workspaces/{workspace_id}/inbox/escalate` | `hitl.escalate` | inbox_item | `InboxAPI.escalate` | after |
| POST | `/inbox/{item_id}/claim` | `hitl.claim` | inbox_item | `InboxAPI.claim` | before+after |
| POST | `/inbox/{item_id}/release` | `hitl.release` | inbox_item | `InboxAPI.release` | before+after |
| POST | `/inbox/{item_id}/resolve` | `hitl.resolve` | inbox_item | `InboxAPI.resolve` | before+after |

## Coverage Gate

`packages/control-plane/_tests/test_audit_coverage.py` parses
`loop_implementation/api/openapi.yaml` and fails whenever a committed
`POST`, `PUT`, `PATCH`, or `DELETE` route lacks a matrix entry. The
same test checks the failure mode by adding a synthetic write route and
confirming it is reported as a gap.
