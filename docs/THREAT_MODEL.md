# Threat Model — Loop Platform

This document is the canonical STRIDE threat model for security-sensitive code paths in the Loop platform. It is kept in lock-step with the code: any PR that touches an auth, RLS, or secrets path **must** update this file (or explicitly mark the change as out-of-scope in the relevant table). The `threat-model-gate` GitHub Action enforces this.

See [`loop_implementation/engineering/SECURITY.md`](../loop_implementation/engineering/SECURITY.md) for the full security architecture (encryption, key management, incident response, etc.). This file is the *change-by-change* ledger.

## STRIDE checklist (per touched code path)

For every PR that lands in a `STRIDE-protected path` (see table below), the author must answer the six STRIDE questions in this file's update log. The reviewer must confirm the answers before approval.

| Letter | Threat | Required answer |
|---|---|---|
| **S** | Spoofing of identity | Who can call this code path? Which authn token is required (PASETO `v4.local.` / SAML / SCIM)? |
| **T** | Tampering with data | What integrity controls protect the data this code reads/writes (HMAC, signed tokens, RLS, append-only audit)? |
| **R** | Repudiation | Is an audit event recorded for state-changing actions? Cite the `audit_events.action` value. |
| **I** | Information disclosure | What data classification does this code touch (P0 secrets / P1 PII / P2 internal)? Does the change widen access? |
| **D** | Denial of service | Are there rate limits, quotas, or resource caps protecting this code? |
| **E** | Elevation of privilege | Does the change introduce a new role / scope / permission boundary? Is the principle of least privilege preserved? |

## STRIDE-protected paths

Any change to a file matching the patterns below is gated. The patterns are also encoded in [`tools/check_threat_model.py`](../tools/check_threat_model.py) and must stay in sync.

| Area | Glob patterns |
|---|---|
| Auth (PASETO / SAML / OIDC / API keys) | `**/paseto*.py`, `**/saml*.py`, `**/auth*.py`, `**/api_keys*.py`, `**/jwks*.py`, `**/scim*.py` |
| Authorization & RLS | `**/authorize*.py`, `**/rate_limit*.py`, `**/migrations/*rls*.py`, `**/migrations/*audit*.py` |
| Secrets handling | `**/byo_vault*.py`, `**/kms*.py`, `**/secrets*.py`, `**/workspace_encryption*.py` |
| Audit / repudiation | `**/audit_events*.py`, `**/audit_export*.py` |

## Update log

The gate refuses PRs that touch a protected path without appending a STRIDE entry below. Entries are append-only; do not edit prior rows except to add a `see also` cross-link.

### 2025-09-15 — Initial threat model snapshot (epic E16 spike)
- **S** All cp-api endpoints require a PASETO `v4.local.` session token or a workspace-scoped API key. SAML JIT provisioning verifies signed assertions only.
- **T** PASETO body is HMAC-SHA256 over header+body+footer; mismatch raises `TokenInvalid`. `audit_events` is append-only with payload SHA-256.
- **R** `record_audit_event` emits one row per state-changing call; outcome ∈ {success, denied, error}.
- **I** P0 secrets stay in BYO Vault or workspace KMS; never logged. P1 PII redacted in trace exporter.
- **D** Token-bucket rate limit per workspace + global; quota enforcement in `plan_limits`.
- **E** Roles: `owner`, `admin`, `developer`, `viewer`. New scopes require an ADR.

### 2025-09-22 — S617 SAML group-rules JIT provisioning (cp_0005 originally; superseded)
- **S** Reuses SAML signed-assertion path; no new authn surface.
- **T** Group rules table protected by RLS; rule expressions parsed by allow-list grammar.
- **R** New audit action `saml.group_rules.upsert`.
- **I** No new PII surfaced; rule body is workspace-scoped admin metadata.
- **D** Rule list capped at 256 per workspace.
- **E** Provisioning runs as system principal; cannot escalate beyond requested role mapping.
- *Note*: the cp_0005 migration was lost during a prior close-only flow; the audit-events migration in S630 took its slot. See `loop_implementation/tracker/`.

### 2025-09-30 — S630 cp_0005 audit_events table
- **S** Inserts performed by service principal only.
- **T** Append-only; payload_hash for tamper-evidence; RLS by workspace_id.
- **R** Emits the audit row itself.
- **I** Payload hashed not stored; no PII at rest.
- **D** Indexed by (workspace_id, occurred_at) for bounded scans.
- **E** No role changes.

### 2025-10-02 — S800 continuous fuzzing of auth/secrets surfaces
- **S** No production auth change; harness runs in CI sandbox.
- **T** Adds RLIMIT_AS=512 MiB so allocator regressions surface as MemoryError; oracle classifies expected vs unexpected exceptions.
- **R** Crashes auto-file GitHub issues with stable signatures.
- **I** Synthetic inputs only; no production data.
- **D** Nightly cap of 30-minute job; iterations bounded.
- **E** None.

### 2025-10-02 — S801 STRIDE checklist gate (this PR)
- **S** Gate runs as GitHub Actions; uses default `GITHUB_TOKEN` with read-only contents + pull-requests scopes.
- **T** Gate output is logged to the PR check; cannot mutate the PR.
- **R** PR check status is the audit trail.
- **I** Reads only the diff metadata (file names) and PR body — no source content extracted.
- **D** Single python invocation; bounded by GitHub's job timeout (5 min default).
- **E** None.

### 2026-05-03 — S900 cp_0006 audit migration-head merge
- **S** No request path or caller changes; this is an Alembic merge revision applied by the deploy migrator's existing database principal.
- **T** `cp_0006_merge_audit_heads` is DDL-only and preserves both existing append-only audit migrations (`audit_log` and `audit_events`) without altering table contents or integrity rules.
- **R** The migration itself is tracked in Alembic's version table; runtime repudiation controls remain the two audit tables created by the merged heads.
- **I** No new data is stored or exposed; the revision has no table or column DDL of its own.
- **D** The merge revision performs no table scan or data backfill, so it adds no runtime DoS surface beyond normal Alembic version-row updates.
- **E** No new roles, grants, scopes, or permission boundaries are introduced.

### 2026-05-03 — S901 cp-api FastAPI ASGI app
- **S** `/v1/auth/exchange` accepts a locally verified HS256 IdP token and returns a Loop PASETO-shaped bearer token; protected workspace, agent, and audit routes require that bearer token.
- **T** Loop bearer tokens are HMAC-authenticated by `decode_local`; audit rows include payload hashes for write requests.
- **R** State-changing app routes emit `workspace:create`, `workspace:update`, `agent:create`, and `agent:delete` audit events with the request id.
- **I** Responses expose workspace and agent metadata only to callers that are workspace members; no token secrets are written to audit payloads.
- **D** S901 does not add rate limiting; existing deployment ingress limits remain the DoS control until the cp-api rate-limit router lands.
- **E** No new roles are introduced; agent and audit routes reuse existing workspace membership checks.

### 2026-05-03 — S917 PySAML2Validator with xmlsec1 signature verification
Touches: `packages/control-plane/loop_control_plane/saml_pysaml2.py` (new), `_app_state.py` (selector). Replaces the `StubSamlValidator` in production paths when `LOOP_SAML_USE_PYSAML2=1`; the stub remains the default and is the only validator wired for sandbox tenants.
- **S** Real signature verification at the SAML SP boundary closes a spoofing gap: prior to this change the production trust path could be fooled by a hand-crafted base64-JSON envelope. `_PySAML2SignatureVerifier` now validates the XML Digital Signature against the active certs in the existing `CertificateBundle` (S610) using `pysaml2.sigver` + `xmlsec1`. Issuer match against `SamlSpConfig.issuer` is enforced after signature verification so a valid signature from a trusted-but-wrong IdP is still rejected.
- **T** Audience MUST contain the SP entity ID per OASIS SAML2 §2.5.1.4. `Conditions/NotBefore` and `NotOnOrAfter` are enforced with `SamlSpConfig.clock_skew` tolerance (default 2 min). Naive datetimes are coerced to UTC. The signature seam is a `Protocol` so production cannot accidentally degrade to the stub at runtime — selection happens once at app construction and is logged.
- **R** No new audit event from this module directly; the existing SAML JIT provisioning event chain (`saml.group_rules.upsert`, `saml.user.provisioned`) emits as before once the validator hands off a `SamlAssertion`. A bad-signature failure raises `SamlError` which the cp-api error handler converts to a 401 with structured `error.code` so the access denial is visible in the request log.
- **I** No new data classification. Decoded SAML XML is held in memory only for the duration of the request; no payload is logged. SAML assertions can carry PII (email, group memberships) — those reach the existing assertion-handling pipeline unchanged.
- **D** SAML responses are POSTed to the ACS endpoint; pysaml2 parses bounded XML and rejects anything beyond `xmlsec1`'s default size guard (1 MiB). The validator does not perform external network calls (no metadata refresh, no CRL lookup). pysaml2 is lazy-imported so workloads not using it pay no startup cost.
- **E** No new roles. Group → role mapping continues to flow through `saml_group_rules.py` (S617) which is itself STRIDE-gated. The validator only converts a verified XML response to the existing `SamlAssertion` shape; it cannot grant a role the rules table doesn't already authorise.

### 2026-05-03 — S918 Vault transit KMS backend (hvac)
Touches: `packages/control-plane/loop_control_plane/vault_transit.py` (new), `kms.py` (factory dispatch). Adds the `vault_transit` backend to the `KMS_BACKENDS` enum; selection is a runtime decision via `LOOP_KMS_BACKEND` and an explicit `VaultTransitConfig` passed by the app bootstrap.
- **S** The Vault token (`LOOP_VAULT_TOKEN`) is a per-deployment credential; tokens have a Vault policy that grants only `transit.encrypt`/`decrypt`/`datakey`/`rotate`/`hmac` on the configured mount. The BYO Vault path (S637) can substitute an AppRole-acquired token at runtime via response wrapping. The validator constructor accepts a pre-built `hvac.Client` so credential acquisition is the caller's responsibility — there is no embedded credential parsing in the KMS module.
- **T** Every KMS call round-trips to Vault; we never cache plaintext keys locally. Ciphertexts are returned with Vault's `vault:vN:<base64>` envelope so the key version is evident on read; key versions auto-increment on rotate, and old ciphertexts continue to decrypt because Vault retains prior versions. Errors from Vault are wrapped in `KMSError` with the upstream message — we never return a fabricated ciphertext on failure.
- **R** No direct audit emission; the existing KMS-using callers (envelope encryption in workspaces, secrets store, audit row signing via S630) emit their own audit events. Vault itself logs every call to its own audit device — that's the upstream audit trail.
- **I** No data classification change. Plaintexts pass through Vault round-trips; the module never logs or persists them. Key references are workspace-scoped strings (`workspace-{id}`); the validator rejects path-separator characters so a poisoned `key_ref` cannot escape the workspace's transit namespace.
- **D** `timeout_seconds` (default 5s) caps each Vault request. `hvac` is lazy-imported so workloads on other backends don't pay the install cost. No retry logic in the module itself — callers handle transient Vault outages via the existing degrade-and-page path used by the InMemoryKMS.
- **E** No new roles. The Vault policy bound to `LOOP_VAULT_TOKEN` is exactly the transit operations enumerated above; nothing in this module can mint a token with broader scope. `key_ref` validation prevents traversal-style escalation between workspaces.

### 2026-05-03 — S905 AWS KMS + S3 boto3 backends
Touches: `packages/control-plane/loop_control_plane/aws_backends.py` (new), `kms.py` (factory dispatch), `object_store.py` (factory dispatch). Adds the `aws_kms` and `s3` backends to the existing enums; both are selected explicitly via `AwsKmsConfig` / `S3Config` passed at app bootstrap.
- **S** AWS authentication is via the standard boto3 chain (IAM role on EKS pod, environment, instance profile). The KMS backend cannot read or modify a key that the bound IAM role does not have policy access to — least-privilege is enforced by the AWS-side policy, not by Loop code. KMS calls inherit the AWS request signature (SigV4); a tampered request is rejected by AWS before it reaches our code.
- **T** Envelope keys never leave KMS in plaintext (data keys are returned wrapped in their CMK ciphertext envelope and re-supplied to KMS on read). Object-store SSE-KMS, bucket versioning, and the `block_public_acls`/`restrict_public_buckets` posture are encoded in the matching terraform module (S904) so resources are tamper-resistant by default. The boto3 module wraps every upstream exception in `KMSError`/`ObjectStoreError`; we never return a fabricated value.
- **R** No direct audit emission; AWS KMS / S3 themselves log every call to CloudTrail, which is the upstream audit trail. The Loop callers continue to emit application-level audit events on the surrounding state changes (workspace create, secret rotate, object upload).
- **I** P0 (envelope keys) never persisted anywhere outside KMS or the wrapped ciphertext. P2 (object store keys) are workspace-scoped paths; signed-URL TTLs are caller-controlled and validated to be positive. No object content is logged. The factory rejects unknown methods (anything other than GET/PUT/DELETE) on `signed_url` to prevent abuse via boto3's broader API surface.
- **D** boto3 client `timeout_seconds` (default 5s) on KMS; S3 inherits the same. boto3 is lazy-imported so workloads on other backends pay no install cost. Multipart-upload `_parts` tracking is per-instance in-memory; `complete_multipart_upload` rejects unknown upload IDs so a forged ID cannot exhaust memory.
- **E** No new roles. The AWS policies bound to the runtime IAM role bound the operations available; nothing in this module can call AWS APIs outside KMS / S3.

### 2026-05-04 — Backfill mutating-route STRIDE coverage (#182, #185-195)
Touches: `packages/control-plane/loop_control_plane/_routes_*.py` mutating endpoints. This entry backfills STRIDE coverage so every mutating route namespace used by the cp-api routers is represented before the mutating-route gate became blocking.

Audit-action namespaces covered by this entry:
- `agent:create`, `agent:delete`, `agent:version`
- `workspace:create`, `workspace:delete`, `workspace:update`, `workspace:member`, `workspace:api_key`, `workspace:budget`, `workspace:secret`, `workspace:data_deletion`
- `kb:document`, `kb:refresh_all`
- `webhook:incoming`
- `eval:suite`, `eval:run`
- `conversation:takeover`

- **S** All mutating routes remain authenticated with workspace-scoped bearer credentials (or channel webhook secrets for `webhook:incoming`); no anonymous mutating path is introduced.
- **T** Every namespace above keeps integrity controls in place: write paths execute through validated Pydantic models and either RLS-protected SQL writes or idempotent channel/webhook guards.
- **R** Each namespace emits explicit `record_audit_event` actions, preserving repudiation evidence for state changes (`workspace:*`, `agent:*`, `kb:*`, `eval:*`, `webhook:*`, `conversation:*`).
- **I** No namespace broadens data exposure: mutating handlers remain workspace-scoped, redact secret material, and keep export/deletion controls constrained to authorized actors.
- **D** Existing quotas and rate-limit controls continue to apply to mutating paths; webhook and eval/start paths preserve idempotency and bounded retry behavior.
- **E** No additional privilege boundary is introduced. Role checks used by mutating handlers remain owner/admin scoped and do not grant cross-workspace authority.

### 2026-05-07 — UX wire-up perf gate rate-limit overrides (#266)
Touches: `packages/control-plane/loop_control_plane/rate_limit_middleware.py`, perf workflows. Adds environment-configurable HTTP token-bucket capacity/refill values so synthetic CI perf jobs can exercise real `cp-api` / `dp-runtime` images without being throttled by the public-boundary guard.
- **S** No caller identity change. Requests still resolve the same principal (`workspace_id`, forwarded IP, client IP, or anonymous); the env knobs only resize the bucket attached to that principal.
- **T** No request or state payload integrity change. Invalid or non-positive env values are ignored and the default limiter values remain in force.
- **R** The limiter remains a request-admission control, not a state-changing endpoint, so it emits no audit row directly. CI override usage is visible in the workflow definition and GitHub check logs.
- **I** No data exposure change. The configuration contains numeric budgets only and does not touch PII, secrets, traces, memory, or customer payloads.
- **D** Production defaults remain `capacity=60` and `refill_per_sec=30`; the high values are set only in perf workflow Helm overrides. This prevents false perf failures from the guard itself while preserving the default DoS protection for normal deployments.
- **E** No new role, scope, or permission boundary. Operators who can already set deployment environment variables could tune the limiter before this change via chart edits; this makes the intended knob explicit and bounded to positive numeric values.
