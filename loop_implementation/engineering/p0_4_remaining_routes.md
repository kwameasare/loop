# P0.4 — remaining routes blocked on missing service layer

The prod-readiness audit listed 25 cp-api routes documented in
`loop_implementation/api/openapi.yaml` but missing from `_routes_*.py`.
This file tracks the subset that **cannot be wired in a "shim only" PR**
because the service-layer Python class doesn't exist yet — wiring a
FastAPI handler would require simultaneously inventing the data model,
the persistence, the validation rules, and the audit-emission contract.
That's outside the scope of P0.4 ("wire missing routes") and belongs in
a separate per-feature story.

## What's already shipped (PRs #182 / #184 / #185 / #186 / and the
trace-usage PR introducing this file)

| Route group | Status | PR |
|---|---|---|
| GDPR data-deletion (`/v1/workspaces/{id}/data-deletion`) | ✅ shipped | #182 |
| Auth refresh (`POST /v1/auth/refresh`) | ✅ shipped | #184 |
| Workspace member CRUD | ✅ shipped | #185 |
| API keys + secrets | ✅ shipped | #186 |
| Traces search + usage list | ✅ shipped | this PR |

## Blocked on missing service layer

These routes appear in the OpenAPI spec but have no Python class
implementing the underlying behaviour. Each item below names the file
that *would* host the service class so the next iteration can land it
without re-discovering the gap.

### Agent versions

* `GET   /v1/agents/{id}/versions`
* `POST  /v1/agents/{id}/versions`
* `POST  /v1/agents/{id}/versions/{vid}/promote`

`AgentRegistry` (`_app_agents.py`) only models the agent itself
(create / list / get / archive). The `agent_versions` table exists
in `cp_0001_initial.py`, but no `AgentVersionService` reads or writes
it. New file needed: `loop_control_plane/agent_versions.py` with
`AgentVersionService` exposing `list_for_agent`, `create`, and
`promote_active(version_id)`.

### Conversations + takeover

* `GET   /v1/agents/{id}/conversations`
* `GET   /v1/conversations/{id}`
* `POST  /v1/conversations/{id}/takeover`

The data plane (`packages/data-plane`) owns conversation rows; cp-api
needs a thin read/takeover façade that proxies via
`forward_data_plane_call` (already exists on `WorkspaceAPI`). New file
needed: `loop_control_plane/conversations_facade.py`.

### KB documents

* `GET    /v1/workspaces/{id}/kb/documents`
* `POST   /v1/workspaces/{id}/kb/documents`
* `DELETE /v1/workspaces/{id}/kb/documents/{kid}`
* `POST   /v1/workspaces/{id}/kb/refresh`

KB ingestion lives in `packages/kb-engine`; cp-api needs an HTTP
façade. The kb-engine already exposes a Python API, so cp's new
`kb_facade.py` would be a thin authorisation + proxy layer.

### Eval suites

* `GET   /v1/workspaces/{id}/eval-suites`
* `POST  /v1/workspaces/{id}/eval-suites`
* `POST  /v1/eval-suites/{id}/runs`

`packages/eval-harness/loop_eval/registry.py` has the registry but
only ships toy fixtures (audit P1: "only 5 toy samples across two
suites"). Wiring these routes also unblocks P3-tier "real eval
datasets" work.

### Budgets

* `GET    /v1/workspaces/{id}/budgets`
* `PATCH  /v1/workspaces/{id}/budgets`

Budget primitives exist in `loop_gateway.preflight` but cp-api has no
`BudgetService` to surface them. The `gateway` package's
`preflight_budget` is a function, not a service.

### Incoming webhooks

* `POST /v1/webhooks/incoming/{channel}`

The cp must accept webhook POSTs from each channel provider, route to
the matching channel adapter's verifier (P0.5a-g already shipped),
then enqueue an `InboundEvent` for the runtime. New file needed:
`loop_control_plane/webhooks_inbound.py` plus per-channel signing-key
lookup against `secrets_backend`.

## Workspace deletion

* `DELETE /v1/workspaces/{id}`

`WorkspaceService` has no `delete` method (audit P0.4 specifically
called this out). Deleting a workspace touches every tenanted table
and is therefore the right place to wire `data_deletion.enqueue` —
both routes ship together as part of the GDPR / lifecycle workflow.
The DSR enqueue route already shipped (#182); the wrapping
`DELETE /v1/workspaces/{id}` belongs to the GDPR follow-up.

## Recommended sequencing

Each blocked group is its own story (~1-3 days). Recommend:

1. **Conversations + takeover** — unblocks the studio's `/inbox` page
   (currently fixture-driven). 1-2 days.
2. **Agent versions + promote** — unblocks deploys; modest scope. 1 day.
3. **Webhooks-incoming router** — unblocks every channel provider in
   prod. 2-3 days because of per-channel verifier wiring.
4. **KB document CRUD** — unblocks studio KB tab. 1-2 days.
5. **Eval suites** — depends on real dataset content; ~2 days.
6. **Budgets** — extracts existing `preflight_budget` into a service. 1 day.
7. **Workspace delete** — wraps `data_deletion.enqueue`; small once it
   has a place to live. 1 day.

Total: ~2 weeks of feature work.
