# Loop — Authentication & Authorization Flows

**Status:** v0.1  •  **Owners:** Founding Eng #2 (Infra), Sec eng
**Companions:** `engineering/SECURITY.md` §5–§6, `architecture/ARCHITECTURE.md` §7.1, `adrs/README.md` ADR-011 + ADR-017.

This doc enumerates every authentication and authorization flow in Loop with a sequence diagram, the tokens involved, and the failure paths.

---

## 1. Actor overview

Five actors authenticate to Loop:

| Actor | How they authenticate | Token format |
|-------|----------------------|---------------|
| **Builder** (engineer) | OIDC interactive login | Browser session cookie (HttpOnly + Secure + SameSite=Lax) |
| **Operator** (HITL) | OIDC interactive login | Same as builder |
| **CLI** | Device-flow OAuth or long-lived API key | PASETO v4 |
| **Programmatic** (CI, customer integrations) | Long-lived API key | PASETO v4 |
| **Service-to-service** (internal) | Mutual TLS via SPIFFE IDs | x509 certs, rotated 24h |
| **End user** (channel) | Delegated to channel | Channel-native (Slack OAuth, WhatsApp BSP token, web widget JWT) |

Plus three webhook senders (channel providers, MCP servers, Stripe) authenticate via signed webhooks.

---

## 2. Builder OIDC login (Studio)

```
Browser           Studio (Next.js)        cp-api          Auth0/Kratos
   │                   │                    │                  │
   │  GET /studio      │                    │                  │
   ├──────────────────►│                    │                  │
   │ <- HTML +redirect │                    │                  │
   │  to /authorize    │                    │                  │
   │                                                            │
   │   GET /authorize?response_type=code&client_id=...&         │
   │       redirect_uri=...&state=&code_challenge=&             │
   │       code_challenge_method=S256                           │
   ├───────────────────────────────────────────────────────────►│
   │                                                            │ <- login UI
   ◄───────────────────────────────────────────────────────────┤
   │   user authenticates + MFA                                 │
   ├───────────────────────────────────────────────────────────►│
   │   GET /callback?code=…&state=…                             │
   ◄───────────────────────────────────────────────────────────┤
   │                                                            │
   │   GET /callback?code=…       ┌─────────────────────────────┘
   ├──────────────────►│          ▼
   │                   │   POST /oauth/token
   │                   ├─────────────────────►│ (verify code+verifier)
   │                   │   id_token,access    │
   │                   ◄─────────────────────┤
   │                   │
   │                   │   verify id_token JWS (JWKS)
   │                   │   look up user, create session
   │                   │   set HttpOnly cookie
   ◄──────────────────┤
   │   subsequent requests carry cookie; cp-api validates session
```

**Key invariants:**
- PKCE (S256) is required.
- `state` is HMAC-bound to the user agent; replay protection.
- `id_token` lifetime ≤ 1 h; refresh-token rotation server-side every 12 h.
- Session cookie: HttpOnly + Secure + SameSite=Lax + Path=/. 12 h sliding TTL, max 30 d absolute.

**Failure paths:**
- Invalid `state` → 400 with `LOOP-API-002`.
- Token signature fails JWKS verification → 401 with `LOOP-API-101`.
- MFA missing on a role that requires it → step-up flow re-issued.

---

## 3. CLI authentication

### 3.1 Device-flow (preferred for interactive)

```
CLI                 cp-api              Auth0/Kratos      Browser
 │                    │                    │                │
 │ loop login         │                    │                │
 │ POST /v1/oauth/    │                    │                │
 │   device           │                    │                │
 ├───────────────────►│                    │                │
 │                    │ POST /oauth/device │                │
 │                    ├───────────────────►│                │
 │ ◄──── { device_code, user_code, verification_uri, expires_in: 600 } ┘
 │                                                          │
 │ "Open https://loop.example/activate?user_code=ABCD-1234" │
 │                                                          │
 │ poll POST /v1/oauth/token (every 5s)                     │
 │ {grant_type: device_code}                                │
 ├───────────────────►│                                     │
 │ ◄──── 428 (pending), 5xx loop                            │
 │                                                          │
 │                            user opens URL in browser, authenticates
 │                            ───────────────────────────────►│
 │                                                          │
 │ poll again                                               │
 │ ◄──── 200 { access_token: paseto_v4..., expires_in: 3600,│
 │          refresh_token: paseto_v4..., scope: ... }       │
 │                                                          │
 │ writes ~/.loop/credentials                               │
```

### 3.2 API key (preferred for CI / non-interactive)

User generates a key via Studio → Settings → API Keys (with scopes). Key is shown **once**, hashed with Argon2id at rest. CLI uses it via:

```
$ export LOOP_TOKEN=lpk_v1.aBcDeF...
$ loop deploy
```

Server-side: `cp-api` middleware verifies the key prefix → looks up `api_keys.hashed_key` → Argon2id verify → loads scopes → sets request context.

---

## 4. Programmatic API key

Same as §3.2. Long-lived; revocable by setting `revoked_at`. Propagates within 60 s via Vault watcher invalidating the in-memory cache.

Each call carries `Authorization: Bearer lpk_v1.<key>` and is scoped to a single workspace. Cross-workspace keys are not supported by design.

---

## 5. Service-to-service (mTLS via SPIFFE)

```
dp-runtime              dp-gateway
  │                       │
  │ TLS handshake         │
  │  (client_hello, SNI)  │
  ├──────────────────────►│
  │                       │
  │  presents x509 cert   │
  │  with SPIFFE SAN:     │
  │  spiffe://loop/dp-runtime/<region>/<pod>
  ├──────────────────────►│
  │                       │
  │  gateway validates:   │
  │  - cert chain (SPIRE root)
  │  - SAN matches expected runtime identity
  │  - cert not expired (24h max)
  ◄───────────────────────┤
  │                       │
  │  encrypted application traffic
```

**Issuance:** SPIRE Server runs in cp-clusters and dp-clusters. Each pod has a SPIRE Agent sidecar (or in-cluster daemon) that requests workload certs via the Workload API. Identity bound to k8s ServiceAccount + namespace + cluster.

**Rotation:** every 24 h automatically. No human in the loop. Old cert revoked immediately.

**Invariants:**
- Client cert REQUIRED for every internal call. No anonymous internal traffic.
- Pinning policy: gateway only accepts certs whose SAN matches the expected service ABI.
- SPIRE root rotates yearly via a documented cutover.

---

## 6. End-user channel auth (delegated)

End-user identity is the channel's responsibility:

| Channel | End-user identity source |
|---------|--------------------------|
| Web widget | JWT signed by the customer's backend (`exp`, `sub`, `iat`, `aud`); Loop validates via per-workspace public key |
| WhatsApp | Meta's `from` phone number; Loop hashes for storage |
| Slack | Slack `user_id`; OAuth scope `users:read` |
| Teams | AAD object ID via Bot Framework token |
| Telegram | Telegram user ID + `init_data` HMAC for web app |
| SMS | Phone number; no separate auth |
| Email | From address; SPF/DKIM verified by inbound gateway |
| Voice | Caller ID; optional PIN entry per workspace policy |

The channel adapter mints a short-lived `EndUserSession` token bound to `(workspace_id, channel, user_id, conversation_id)` for the duration of the turn. The runtime trusts the channel adapter; the channel adapter is responsible for end-user authentication.

---

## 7. Inbound webhook authentication

Channel webhooks → `dp-webhook-ingester`:

```
Channel provider (e.g. Twilio)
  │
  │ POST /webhooks/twilio
  │  X-Twilio-Signature: <HMAC-SHA1(request_body, account_secret)>
  ▼
dp-webhook-ingester
  │
  │ 1. Look up workspace+agent from URL path.
  │ 2. Pull verification secret from Vault.
  │ 3. Compute HMAC; constant-time compare.
  │ 4. Reject if mismatch (401 + LOOP-CH-001).
  │ 5. Check Idempotency-Key (or provider's message_id) against
  │    Redis SET (24 h TTL). Reject duplicates (409 + LOOP-CH-002).
  │ 6. Publish to NATS subject EVENTS.inbound.<workspace>.<agent>.<channel>.
  │ 7. Return 202.
```

Per-provider signature schemes:

| Provider | Algorithm | Header |
|----------|-----------|--------|
| Meta WhatsApp | HMAC-SHA256 | `X-Hub-Signature-256` |
| Twilio | HMAC-SHA1 | `X-Twilio-Signature` |
| Slack | HMAC-SHA256 | `X-Slack-Signature` + `X-Slack-Request-Timestamp` (5-min window) |
| Stripe | HMAC-SHA256 | `Stripe-Signature` |
| Microsoft Bot | OAuth2 token in `Authorization` | n/a |
| Custom HTTP | HMAC-SHA256 (Loop default) | `X-Loop-Signature` |

---

## 8. Authorization (post-auth)

Every authenticated request carries:
- `workspace_id` (from token).
- `subject` (user ID or API-key ID).
- `scopes` (from PASETO claims).

Authorization happens at the API gateway middleware, **before** the handler runs:

```python
def require(*needed_scopes):
    def deco(handler):
        async def wrapped(req, *a, **k):
            ctx = req.state.auth
            if not set(needed_scopes).issubset(ctx.scopes):
                raise InsufficientScope(needed=needed_scopes, got=ctx.scopes)
            if ctx.role not in REQUIRED_MIN_ROLE.get(handler.__name__, ()):
                raise InsufficientRole(...)
            return await handler(req, *a, **k)
        return wrapped
    return deco

@require("agents:deploy")
async def deploy_agent(...):
    ...
```

**Scope catalog** (canonical list in `engineering/SECURITY.md` §6):

| Scope | Allows | Min role |
|-------|--------|----------|
| `workspace:read` | View workspace metadata | viewer |
| `agents:read` | List + view agents | viewer |
| `agents:write` | Create + edit | editor |
| `agents:deploy` | Deploy a new version | editor (non-prod) / admin (prod) |
| `agents:rollback` | Roll back versions | admin |
| `conversations:read` | View conversations + traces | operator |
| `conversations:takeover` | Take over a conversation | operator |
| `kb:read` | Search KBs | viewer |
| `kb:write` | Ingest sources | editor |
| `secrets:read` | List secret refs (not values) | admin |
| `secrets:write` | Create/rotate secrets | admin |
| `members:invite` | Invite members | admin |
| `audit:read` | Read audit log | admin (compliance) |
| `billing:read` | View bills | admin |
| `billing:write` | Change plans | owner |
| `workspace:delete` | Delete workspace | owner |

**Tenant isolation** is enforced separately via Postgres RLS (every connection sets `loop.workspace_id` from the auth context). Even if a scope check were bypassed, RLS prevents cross-tenant reads.

---

## 9. Step-up auth (high-risk actions)

Some actions require a fresh MFA challenge even within an existing session:

- Deleting a workspace.
- Changing the billing plan.
- Bulk deleting > 1000 conversations.
- Rotating a customer-supplied KMS key.
- Any action that originates from a user who hasn't MFA'd in > 1 h.

Flow: handler returns 401 + `LOOP-API-103`; Studio invokes a step-up dialog; user MFA's; resulting access token has a `mfa_at` claim; handler retries.

---

## 10. Token formats

### 10.1 PASETO v4 (preferred)

```
v4.public.<base64url payload>.<base64url signature>
```

Payload (JSON):

```json
{
  "iss": "loop-cp-api",
  "sub": "api_key_018f...",
  "aud": ["loop-runtime","loop-cp-api"],
  "exp": 1735689600,
  "iat": 1735603200,
  "jti": "01HW...",
  "workspace_id": "ws_018f...",
  "scopes": ["agents:deploy","traces:read"],
  "mfa_at": 1735603100
}
```

Signed with Ed25519. Public key published at `/.well-known/loop-keys`.

### 10.2 Session cookies (browser)

Opaque random 256-bit token; lookup table in Redis with same payload structure as the PASETO. We do not put PASETOs in cookies.

### 10.3 Internal mTLS

x509 certs with SPIFFE SAN. No claims; identity is the SAN.

---

## 11. Failure modes & alerts

| Condition | Alert | Severity |
|-----------|-------|----------|
| > 1% of /authorize requests returning errors | `auth_oidc_failure_rate` | SEV2 |
| JWKS endpoint unreachable | `auth_jwks_down` | SEV1 (Auth0 outage) |
| API key brute-force pattern (> 100 failed key checks/min from one IP) | `auth_brute_force` | SEV2 → IP block |
| MFA bypass attempt (claim mismatch) | `auth_mfa_bypass` | SEV1 — security review |
| Cross-workspace token use detected | `auth_workspace_drift` | SEV1 — kill the key |
| SPIRE down | `auth_spire_down` | SEV1 (S2S broken) |
| Audit log chain mismatch | `audit_chain_break` | SEV1 (RB-014) |

---

## 12. References

- `engineering/SECURITY.md` §5–§6 — controls.
- `adrs/README.md` ADR-011 — Auth0 cloud / Kratos self-host.
- `adrs/README.md` ADR-017 — Authorization model.
- `architecture/ARCHITECTURE.md` §7.1 — high-level summary.
