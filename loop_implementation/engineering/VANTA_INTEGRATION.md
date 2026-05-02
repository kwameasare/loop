# Vanta integration — auth + organization sync (S570)

> Extends [SOC2.md](SOC2.md) (S046). This document specifies how Loop
> connects to Vanta as a downstream client of the Vanta API, distinct
> from the inverse "what does Vanta connect to inside Loop" checklist
> in `SOC2.md §Vanta integration checklist`.

## Scope

S570 lands the OAuth handshake and the per-workspace organization
linkage so that subsequent SOC2 stories (control evidence push, vendor
sync, CVE export) have a stable identity to write against.

Out of scope for S570:

- Pushing control evidence to Vanta (S571 control mapping does that).
- Pulling Vanta findings back into Studio dashboards.
- Multi-instance Vanta (we only support one Vanta tenant per Loop
  workspace today; multi-tenant fan-out is a future story).

## OAuth 2.0 authorization code flow

Vanta exposes an OAuth 2.0 authorization-code endpoint. We use the
standard three-leg flow with PKCE.

| Step | Endpoint                                 | Notes                                 |
| ---- | ---------------------------------------- | ------------------------------------- |
| 1    | `GET /oauth/authorize` on app.vanta.com  | We send `client_id`, `redirect_uri`, `state`, `code_challenge`, `scope`. |
| 2    | Vanta redirects to `redirect_uri?code=…` | Loop validates `state` + matches the originating workspace. |
| 3    | `POST /oauth/token`                      | Loop exchanges `code + code_verifier` for `access_token` + `refresh_token`. |

### Configuration

| Setting               | Value (production)                                  | Notes                                 |
| --------------------- | --------------------------------------------------- | ------------------------------------- |
| `client_id`           | Vanta-issued, per-environment                       | `VANTA_CLIENT_ID` env var.            |
| `client_secret`       | Vanta-issued, KMS-wrapped at rest                   | `VANTA_CLIENT_SECRET` env var.        |
| `redirect_uri`        | `https://app.loop.dev/integrations/vanta/callback`  | Per-region equivalents in `eu-west-1`, `ap-southeast-2`. |
| `scope`               | `org.read controls.write evidence.write vendors.read` | Minimum set for S570 + S571.           |
| `code_challenge_method` | `S256`                                            | PKCE required.                        |
| `state` lifetime      | 10 minutes                                          | TTL'd in Redis under `vanta:oauth:state:{state}`. |

### State payload

`state` is a base64url-encoded JSON envelope signed with the
control-plane HS256 key and stored in Redis for replay protection:

```json
{
  "workspace_id": "ws_…",
  "user_id": "usr_…",
  "issued_at": "2026-04-30T00:00:00Z",
  "nonce": "<32-byte random>"
}
```

The callback handler:

1. Looks up `state` in Redis; rejects if missing or already consumed.
2. Verifies the HS256 signature.
3. Asserts the calling user still has `vanta:link` permission on the
   workspace.
4. Marks the `state` row as consumed (single-use).

### Token storage

Both `access_token` and `refresh_token` are stored in
`workspace_integrations` with the `provider='vanta'` row, encrypted
with the workspace KMS key (per `data/SCHEMA.md`). Plaintext tokens
never leave the control-plane process.

| Column            | Type        | Notes                                 |
| ----------------- | ----------- | ------------------------------------- |
| `workspace_id`    | uuid PK     | FK to `workspaces`.                   |
| `provider`        | text PK     | Always `'vanta'` for this row.        |
| `vanta_org_id`    | text        | Returned by `GET /v1/organizations/me`. |
| `access_token_enc`| bytea       | KMS-wrapped.                          |
| `refresh_token_enc`| bytea      | KMS-wrapped.                          |
| `expires_at`      | timestamptz | Refresh window ends ~5 min before.    |
| `scopes`          | text[]      | Granted scopes from token response.   |
| `linked_by`       | uuid        | `users.id` who completed the handshake. |
| `linked_at`       | timestamptz | Audit trail.                          |

## Organization sync

Once the token is stored, the linker performs an immediate
`GET /v1/organizations/me` call and persists `vanta_org_id`. This id is
the cross-system anchor used by all downstream SOC2 stories.

### Linkage contract

A Loop workspace is "Vanta-linked" iff:

1. A `workspace_integrations` row exists with
   `provider='vanta' AND vanta_org_id IS NOT NULL`.
2. The most recent `GET /v1/organizations/me` succeeded within the
   freshness window (default: 24h).
3. The token has not been revoked (signalled by a `401` from any Vanta
   API call → row marked `revoked_at = now()` and the linkage drops).

### Refresh schedule

| Trigger                              | Action                                      |
| ------------------------------------ | ------------------------------------------- |
| `expires_at - 5m` (background)       | Refresh via `/oauth/token grant=refresh_token`. |
| Vanta returns `401` on any API call  | Mark row `revoked_at = now()`, surface `vanta.unlinked` event. |
| User clicks "Re-authorize" in Studio | Restart the OAuth flow; replace the row.    |
| Workspace deletion                   | Revoke at Vanta then delete the row.        |

## Failure modes

| Failure                              | Surface                                | Mitigation                                  |
| ------------------------------------ | -------------------------------------- | ------------------------------------------- |
| `state` mismatch / replay            | `400 invalid_state`                    | Single-use state in Redis; user retries.    |
| `code` expired                       | `400 invalid_grant`                    | Restart flow.                               |
| Vanta `5xx` on token exchange        | `502 upstream_error`, retried 3x       | Exponential backoff capped at 8s.           |
| Refresh-token revoked                | Linkage drops; `vanta.unlinked` event  | Studio surfaces re-authorize banner.        |
| Network partition during org fetch   | Linkage stays "pending"; retried 5x    | Token is preserved; org_id back-fills later.|

## Test plan

S570 ships with three layers of coverage:

1. **Unit** — state envelope sign/verify, PKCE challenge derivation,
   token-row encryption.
2. **Integration** — fakeoauth provider that mints `code` and validates
   PKCE; round-trips through the callback handler and asserts the
   `workspace_integrations` row lands with the encrypted tokens.
3. **Contract** — recorded HTTP fixtures of `/oauth/token` and
   `/v1/organizations/me`; verifies parsing of the org id and the
   refresh-grant response shape.

The contract layer is the AC ("OAuth complete; vanta-side organization
linked"): the test asserts that after a successful handshake, the
workspace row reports `linked = true` AND `vanta_org_id` matches the
fixture organization.

## Audit-trail events

Every state transition emits an event into `audit_log`:

| Event                       | Actor                         | Payload (selected fields)                |
| --------------------------- | ----------------------------- | ---------------------------------------- |
| `vanta.link.started`        | user                          | `workspace_id`, `requested_scopes`       |
| `vanta.link.completed`      | system (callback)             | `workspace_id`, `vanta_org_id`, `scopes` |
| `vanta.link.failed`         | system                        | `workspace_id`, `error_code`             |
| `vanta.token.refreshed`     | system (refresher)            | `workspace_id`, `expires_at`             |
| `vanta.unlinked`            | system or user                | `workspace_id`, `reason`                 |

## Related stories

- **S046** — SOC2 kickoff (this doc's parent context).
- **S571** — control mapping → push evidence using the linked org.
- **S572** — vendor sync into the Loop subprocessor inventory.

## Change log

| Date       | Author            | Change                                            |
| ---------- | ----------------- | ------------------------------------------------- |
| 2026-05-02 | GitHub Copilot (S570) | Initial OAuth + organization-sync spec.        |
