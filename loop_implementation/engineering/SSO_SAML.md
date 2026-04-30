# SSO/SAML configuration (S050)

Companion to [ENTERPRISE_GA.md](ENTERPRISE_GA.md). This file gives
Enterprise admins the click-by-click setup recipe for each
supported IdP, plus the troubleshooting matrix on-call uses when an
incoming P1 names "SSO is broken".

## Tenant-level SSO record

Every tenant has at most one active SSO config of one of these
shapes:

```yaml
# stored as `tenant_sso.config` (JSONB), validated by pydantic
kind: saml | oidc
issuer: <IdP entity id / OIDC issuer URL>
metadata_url: <IdP federation metadata URL>      # SAML only
client_id: <OIDC client id>                       # OIDC only
client_secret_ref: <kms://...>                    # OIDC only
acs_url: https://app.loop.dev/auth/saml/acs/{tenant_id}
sp_entity_id: https://app.loop.dev/auth/saml/sp/{tenant_id}
default_role: viewer | editor | admin
group_role_map:
  - {group: "Loop-Admins", role: admin}
  - {group: "Loop-Editors", role: editor}
session:
  ttl_minutes: 720
  absolute_max_minutes: 1440
  force_reauth_on:
    - billing.update
    - tenant.export
    - role.update
```

The on-prem chart writes the equivalent record into the cluster's
control-plane DB at install time (values key:
`enterprise.sso.config`).

## Okta — SAML

1. Okta Admin → Applications → "Create App Integration" → SAML 2.0.
2. Single Sign-On URL: `https://app.loop.dev/auth/saml/acs/{tenant_id}`
3. Audience URI: `https://app.loop.dev/auth/saml/sp/{tenant_id}`
4. Name ID format: `EmailAddress`. Application username: Okta username.
5. Attribute statements: `email`, `firstName`, `lastName`,
   `groups` (filter: regex `^Loop-.*`).
6. Download the IdP metadata XML; paste the URL into the Loop
   tenant SSO settings page.
7. (Optional) Enable SCIM 2.0 — base URL
   `https://app.loop.dev/v1/scim/v2/{tenant_id}`, bearer token
   minted from Studio → Settings → SSO → "Generate SCIM token".

## Entra ID — SAML

1. Entra ID → Enterprise applications → New application → "Create
   your own application".
2. Single sign-on → SAML.
3. Identifier: `https://app.loop.dev/auth/saml/sp/{tenant_id}`.
4. Reply URL: `https://app.loop.dev/auth/saml/acs/{tenant_id}`.
5. User attributes: ensure `groups` claim is emitted as
   "sAMAccountName" (or display name) — pure object IDs cannot be
   mapped without manual import.
6. Download Federation Metadata XML, paste URL into Loop.
7. SCIM: same base URL pattern as Okta.

## Google Workspace — OIDC

1. Admin Console → Security → Authentication → SSO with Google as
   IdP. (Note: Workspace prefers OIDC over SAML for new apps.)
2. Web application: redirect URI
   `https://app.loop.dev/auth/oidc/callback/{tenant_id}`.
3. Scopes: `openid email profile groups`.
4. Loop side: paste client_id + client_secret; secret is stored at
   `kms://loop/sso/{tenant_id}/oidc-client-secret`.

## Generic SAML / OIDC

Any IdP that ships SAML 2.0 metadata or implements OIDC discovery
works. Loop reads everything from `metadata_url` (SAML) or
`issuer/.well-known/openid-configuration` (OIDC). Two requirements:

- **Signed assertions / signed ID tokens are required.** Unsigned
  assertions are rejected with `auth.sso.signature_invalid`.
- **Clock skew tolerance is ±5 minutes.** Larger skew rejects with
  `auth.sso.clock_skew`; the tenant admin must NTP-correct the IdP
  side.

## Troubleshooting matrix

| Symptom                                  | Likely cause                                  | Remediation                                                    |
| ---------------------------------------- | --------------------------------------------- | -------------------------------------------------------------- |
| 401 immediately after IdP redirect       | ACS URL mismatch                              | Check the SP-side `acs_url` exactly matches the IdP setting    |
| 403 "no role assigned"                   | Group claim missing or unmappable             | Add the user's group to `group_role_map` or set `default_role` |
| Loops between IdP and Loop endlessly     | Cookie domain misconfigured (on-prem)         | Set `enterprise.sso.cookieDomain` in values.yaml               |
| SCIM provisioning paused                 | SCIM bearer token expired / revoked           | Regenerate token in Studio; reconfigure on the IdP side        |
| User can log in but Studio is read-only  | JIT created user with `viewer` default role   | Map their group, or have an admin promote                      |

## Audit events emitted

All SSO-relevant audit events live under the `auth.sso.*` namespace
and are visible in the Audit log UI (S050 Pillar 2):

- `auth.sso.login.succeeded`
- `auth.sso.login.denied`
- `auth.sso.signature_invalid`
- `auth.sso.clock_skew`
- `auth.sso.scim.user_created`
- `auth.sso.scim.user_deactivated`
- `auth.sso.scim.token_minted`
- `auth.sso.scim.token_revoked`
- `auth.sso.config.updated`

See [SECURITY.md § Audit Events](SECURITY.md) for the full schema
each row carries.
