# Audit-trail coverage matrix (S581)

**Owner:** Sec/Compliance Eng · **Last reviewed:** 2026-05-02 (copilot-titan, S581)

This matrix is the canonical source of truth for SOC2 CC4.1 / CC6.1 /
CC6.3 evidence: every write endpoint in the control-plane that mutates
tenant-visible state must emit at least one row to `audit_log` (see
`data/SCHEMA.md` §2.2a). The matrix is reviewed every audit cycle and
gates added work via `tests/test_audit_coverage_matrix.py`, which
structurally verifies that every write method enumerated below is
actually present in the codebase. Gaps trigger a follow-up StoryV2.

The skill that governs new audit emitters is
`loop_implementation/skills/security/add-audit-event.md`.

## Action vocabulary

Canonical verb-noun pairs (the `audit_log.action` column):

| Domain      | Action                          | Resource type    |
|-------------|---------------------------------|------------------|
| workspace   | `workspace.create`              | `workspace`      |
| workspace   | `workspace.update`              | `workspace`      |
| workspace   | `workspace.delete`              | `workspace`      |
| workspace   | `workspace.member.role.update`  | `workspace`      |
| api_key     | `api_key.create`                | `api_key`        |
| api_key     | `api_key.revoke`                | `api_key`        |
| secret      | `secret.create`                 | `secret`         |
| secret      | `secret.rotate`                 | `secret`         |
| secret      | `secret.delete`                 | `secret`         |
| deploy      | `agent.deploy`                  | `agent`          |
| deploy      | `agent.rollback`                | `agent`          |
| billing     | `billing.plan.change`           | `workspace`      |
| billing     | `billing.suspend`               | `workspace`      |
| mcp         | `mcp.publish`                   | `mcp_server`     |
| data_export | `data_export.request`           | `workspace`      |

New verbs MUST be added here in the same PR as the emitter and
referenced from `engineering/SECURITY.md` §7.1.

## Coverage matrix

Status legend: `covered` = emitter wired today; `gap` = endpoint
exists but no audit emit (follow-up StoryV2 cited); `n/a` = read-only
or service-internal, no audit required.

| Module (`packages/control-plane/loop_control_plane/...`) | Write method            | Action expected                  | Status | Evidence / gap-story |
|-----------------------------------------------------------|-------------------------|----------------------------------|--------|----------------------|
| `workspace_api.py`                                        | `WorkspaceApi.create`   | `workspace.create`               | gap    | S630 (audit emitter wiring) |
| `workspace_api.py`                                        | `WorkspaceApi.update_member_role` | `workspace.member.role.update` | gap    | S630 |
| `api_keys_api.py`                                         | `ApiKeysApi.create`     | `api_key.create`                 | gap    | S630 |
| `api_keys_api.py`                                         | `ApiKeysApi.revoke`     | `api_key.revoke`                 | gap    | S630 |
| `secrets.py`                                              | `SecretsStore.rotate`   | `secret.rotate`                  | gap    | S630 |
| `secrets.py`                                              | `SecretsStore.delete`   | `secret.delete`                  | gap    | S630 |
| `deploy.py`                                               | `DeployService.rollback`| `agent.rollback`                 | gap    | S630 |
| `suspension.py`                                           | `SuspensionService.suspend` | `billing.suspend`            | gap    | S630 |
| `mcp_marketplace.py`                                      | `McpMarketplace.publish`| `mcp.publish`                    | gap    | S630 |
| `subscription_plans.py`                                   | plan-change handlers    | `billing.plan.change`            | gap    | S630 |

Read-only / service-internal modules (no audit required):
`healthz.py`, `region_routing.py`, `regions.py` (read-only), `jwks.py`,
`rate_limit.py`, `cost_rollup.py`, `usage.py`, `trace_search.py`,
`logging.py`, `errors.py`, `config.py`, `paseto.py`, `auth_exchange.py`
(token issuance only — issuance is logged via `api_key.create`),
`api_key_middleware.py`, `auth.py`, `authorize.py`, `kms.py`,
`object_store.py`.

## Gap-fix queue

Every `gap` row above is owned by **S630** ("audit-event emitters for
control-plane write endpoints") which fans out one ≤90-line feat
commit per emitter. S631 lands `audit_log_append(event)` per the
add-audit-event skill (immutable, hash-chained per
`SCHEMA.md` §2.2a) plus per-module wiring. This story (S581) ships
the matrix + structural test that S631 will progressively flip from
`gap` → `covered`.

## Process

1. Adding a new write endpoint? Add a row to the matrix in the same
   PR, even if `status=gap` and the emitter is filed as a follow-up
   StoryV2.
2. Removing or renaming a write method? Update the matrix in the same
   PR — the structural test will fail until you do.
3. Annual SOC2 review walks this matrix top-to-bottom; gaps become
   the year's CC4.1 remediation queue.
