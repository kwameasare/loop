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
