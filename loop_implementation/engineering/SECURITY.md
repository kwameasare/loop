# Loop — Security & Threat Model

**Status:** Draft v0.1
**Owner:** Security/Compliance Engineer (hire #8)
**Companion:** `engineering/HANDBOOK.md`, `architecture/ARCHITECTURE.md`

This document defines (a) our threat model, (b) the controls we implement, (c) the SOC2 / HIPAA / GDPR posture, and (d) the secrets-management policy. It is the source of truth for any security questionnaire response.

---

## 1. Trust boundaries

```
                ┌──────────────────────────────────────────┐
                │  Untrusted: end users, attackers,        │
                │  hostile or buggy MCP servers            │
                └────────────────────┬─────────────────────┘
                                     │ TLS 1.3, WAF, rate limit
                                     ▼
                ┌──────────────────────────────────────────┐
                │  Channel adapters (DMZ-equivalent)       │
                └────────────────────┬─────────────────────┘
                                     │ mTLS in mesh
                                     ▼
                ┌──────────────────────────────────────────┐
                │  Runtime + gateway + storage             │
                │  (per-tenant RLS, KMS encryption)        │
                └────────────────────┬─────────────────────┘
                                     │ outbound mTLS / OIDC
                                     ▼
                ┌──────────────────────────────────────────┐
                │  External: LLM providers, customer       │
                │  webhooks, cloud KMS, observability      │
                └──────────────────────────────────────────┘
```

Trust boundaries:
1. End user ↔ channel adapter
2. Channel adapter ↔ runtime (within data plane)
3. Runtime ↔ tool sandbox
4. Data plane ↔ control plane
5. Service ↔ external SaaS

Each boundary has its own auth, authn, and audit story.

---

## 2. STRIDE threat model

### 2.1 Runtime

| Threat | Vector | Mitigation |
|--------|--------|------------|
| **S** poofing — fake AgentEvent | Forged channel webhook | Signed webhooks per provider (HMAC-SHA256, Ed25519); replay window 24h; idempotency-key dedup |
| **T** ampering — modified turn data | DB writes from another tenant | Postgres RLS by `workspace_id` (default deny); per-connection `SET LOCAL loop.workspace_id` enforced at pool layer |
| **R** epudiation — operator denies action | HITL takeover claim | Audit log append-only with SHA-256 chain; each entry hashes previous entry; tamper-detection via chain validation |
| **I** nfo disclosure — cross-tenant leak | Bug routes Tenant A's data to Tenant B | RLS + per-workspace KMS data keys (envelope encryption) + per-workspace Qdrant collections; network policies in k8s |
| **D** oS — runaway agent loop | Infinite tool-call recursion, fork bomb | Hard cap: `max_iterations=10` (configurable), `max_cost_usd` soft+hard, `max_runtime_seconds=300`, per-turn budget counter; runtime watchdog kills over-budget turns |
| **E** levation — RCE in agent code | Hostile customer code in agent class | Agent code runs in its own workspace's runtime process; no cross-workspace code execution. For external tools: Firecracker microVM with cgroup limits (CPU, RAM, fd), strict egress allowlist, 300s kill timeout |
| **Information leakage** | Model outputs contain PII / secrets | Output filter regex (same patterns as §7.3) applied to LLM responses before returning to channel; configurable per workspace |
| **Prompt injection** | Attacker embeds instructions in tool result / user input | Runtime does not execute user-controlled tool outputs as code; tool results are treated as data only. System prompt is immutable at runtime (no prompt editing mid-turn). Input validation: max length per message (16 MB), max turns per conversation (10K) |

### 2.2 Tool sandbox

| Threat | Vector | Mitigation |
|--------|--------|------------|
| RCE escapes sandbox | Kernel exploit | Firecracker microVM with hardened minimal kernel; weekly CVE rotation |
| Egress to disallowed host | Tool tries to reach internal IPs | Strict egress allowlist per tool manifest; default deny |
| Resource exhaustion | Forkbomb, OOM, fdleak | cgroup CPU/RAM/fd caps; 300s hard kill |
| Persistence across invocations | Tool writes to disk hoping for next call | Sandbox is ephemeral; rootfs reset per invocation |
| Side-channel data extraction | Timing / cache attacks | Per-tenant pool partitioning; no shared sandbox between tenants |

### 2.3 Channel adapters

| Threat | Vector | Mitigation |
|--------|--------|------------|
| Webhook spoofing | Attacker pretends to be Twilio | Verify provider signatures; reject unsigned in prod |
| Credential theft | Stolen channel token | Per-bot secret scoping (not workspace-wide); secret rotation |
| Replay | Attacker resends old webhook | Idempotency-key window of 24h |
| WhatsApp template abuse | Sending non-approved templates | Pre-flight template validation in adapter |

### 2.4 Auth & API

| Threat | Vector | Mitigation |
|--------|--------|------------|
| Stolen API key | Leaked in logs / GitHub | Argon2id-hashed at rest; key prefix shown in audit log; auto-revoke on detected leak |
| Session hijack | Cookie theft | HttpOnly + Secure + SameSite cookies; short TTL; refresh tokens server-side |
| Privilege escalation | Editor → admin via API bug | Permission checks on every endpoint; deny-by-default; integration tests on every endpoint enforce role matrix |
| Token replay | Old PASETO reused | PASETO with `exp` ≤ 1h for ephemeral tokens; long-lived API keys are stateful and revocable |

### 2.5 Data exfiltration

| Threat | Vector | Mitigation |
|--------|--------|------------|
| Mass export | Compromised admin account | MFA required; just-in-time access for export endpoints; alert on >1 GB export |
| Trace export bypass | Customer downloads other customer's traces | RLS on every query path including ClickHouse |
| Backup theft | Object-store bucket misconfig | Bucket policies deny public access; per-workspace KMS data keys (envelope); object-store audit log alerts on read-permission changes (CloudTrail / Activity Log / Audit Logs / ActionTrail) |

---

## 3. Secrets management

### 3.1 Inventory

We classify every secret.

| Category | Examples | Storage |
|----------|----------|---------|
| **Workspace API keys** | Customer-issued PASETO keys | Postgres (Argon2id hash) |
| **Channel credentials** | WhatsApp tokens, Slack bot tokens, Twilio creds | Vault / Secrets Manager, scoped per agent |
| **LLM provider keys** | OpenAI/Anthropic keys (BYO) | Vault, encrypted with workspace KMS data key |
| **Internal infra** | DB passwords, internal mTLS certs | Vault, rotated automatically |
| **Eng dev credentials** | Personal cloud SSO, GitHub PATs | 1Password (humans), never in repos |
| **Customer-uploaded secrets** | Connection strings in agent code | Vault, scoped to agent version |

### 3.2 Storage rules

- **Never** in Postgres (except hashed API keys).
- **Never** in environment variables in containers (use Vault sidecar / Secrets Manager-injected files).
- **Never** in source code or IaC (pre-commit detect-secrets scan;
  CI-side gate via `gitleaks` in the required `security` job — see
  `.gitleaks.toml` and `.github/workflows/ci.yml`. S580.).
- **Never** in logs (structured logging redaction; secret patterns auto-masked).

### 3.3 Lifecycle

- Creation: only via authenticated UI/API; logged.
- Access: short-lived, audited.
- Rotation: automatic for infra (≤ 90d); customer-initiated for theirs (recommended ≤ 90d, warning at 90d).
- Revocation: immediate, propagated within 60s via Vault watcher.

---

## 4. Encryption

### 4.1 At rest

- **Postgres:** AES-256 at the storage layer (cloud-managed encrypted volume on whichever provider hosts it; LUKS for self-host). Per-row sensitive fields additionally encrypted with workspace KMS data keys via envelope encryption.
- **Redis:** AES-256 in transit and at rest (managed Redis encryption + TLS, or `--tls-cert-file` for self-hosted).
- **Qdrant:** at-rest encryption on the underlying EBS volume; payload-level encryption for fields tagged `pii`.
- **S3:** SSE-KMS with per-workspace data keys.
- **Backups:** WAL-G to S3 with the same KMS keys; backups inherit encryption.

### 4.2 In transit

- All external traffic: TLS 1.3 (TLS 1.2 minimum if customer infra demands).
- Internal service-to-service: mTLS via SPIFFE/SPIRE.
- LLM provider calls: TLS 1.3 + provider-published cert pin where available.

### 4.3 Key management & rotation schedule

- **Primary KMS:** HashiCorp Vault Transit by default (works on every cloud and self-host). Cloud-native KMS (AWS KMS, Azure Key Vault, GCP KMS, Alibaba KMS) supported per workspace via the `KMS` interface (set at workspace creation, immutable).
- **Key hierarchy:**
  - **Master key:** Stored in Vault (cloud) or cloud-native KMS (hybrid/self-host). Rotated annually on Q1 31st (Jan 31, Apr 30, Jul 31, Oct 31) with zero-downtime re-wrap.
  - **Per-workspace data key:** Generated via `KMS.generate_data_key()`, plaintext returned to runtime once (cached in-memory), ciphertext stored in Postgres (`workspaces.tenant_kms_key_id`). Rotated every 90 days.
  - **Per-agent secret key:** Derived from workspace key, used to encrypt agent-scoped secrets in Vault.
- **Rotation schedule:**
  - Master key: annual, coordinated window (e.g., 2nd Sunday of Q1), with rollback plan.
  - Data keys: 90 days, automatic background job (`loop-cryptoctl rotate-workspace-keys`) runs weekly; keys older than 90d are marked for rotation but still decryptable.
  - All rotations are rewraps (re-encrypt in-place); no key destruction except on workspace deletion.
- **Key destruction:** Only via `DELETE /workspaces/{id}` (Owner-only, audit-logged). Destruction is **immediate** and **irreversible** — all data becomes unreadable within 60s (Vault revokes the key, KMS disables the key).
- **BYOK (Bring Your Own Key) / HYOK (Hold Your Own Key):** Enterprise feature (planned month 12).
  - BYOK: customer provides an AWS KMS key ARN; Loop uses it as the master key.
  - HYOK: customer hosts Vault in their own VPC; Loop calls out via mTLS.
  - Requires a signed DPA amendment + contract term `byok_available_at_plan_tier`.

---

## 5. Authentication

### 5.1 Builder/operator (humans)

- OIDC via Auth0 (cloud) or Ory Kratos (self-host).
- MFA **required** for all admin roles; recommended for all roles.
- SSO/SAML for enterprise plans.
- Session: HttpOnly + Secure cookie, 12h sliding expiry.

### 5.2 API tokens

- PASETO v4 (preferred over JWT for safer defaults).
- Workspace-scoped, with explicit scopes (`agents:deploy`, `traces:read`, etc.).
- Stored as Argon2id hash; the plaintext is shown once.
- Revocation propagates within 60s.

### 5.3 Service-to-service (internal)

- mTLS with SPIFFE IDs.
- No shared secrets between services.
- Cert rotation every 24h via SPIRE.

---

## 6. Authorization

### 6.1 Roles

| Role | Capabilities |
|------|--------------|
| **Owner** | Everything, including delete workspace + billing |
| **Admin** | Everything except billing + delete workspace |
| **Editor** | Create/edit agents, KBs, deploys (non-prod tags only) |
| **Operator** | Read conversations, take over (HITL), comment |
| **Viewer** | Read-only |

Custom roles: enterprise only; defined as scope sets.

### 6.2 Per-resource permissions & scope catalog

Every API endpoint maps to one or more required scopes. Authorization is computed at the API gateway layer; no per-handler ad-hoc checks. Denials are logged with `action=authorization_denied, actor=..., resource_type=..., required_scopes=[...]` in audit log.

**API scope catalog** (non-exhaustive; see `api/openapi.yaml` §security for the full matrix):

| Scope | Operations | Role minimum |
|-------|-----------|--------------|
| `agents:read` | GET agents, versions, deployments | Viewer |
| `agents:deploy` | POST/PATCH agent versions; promote tags | Editor+ |
| `agents:delete` | Archive agents | Admin+ |
| `conversations:read` | GET conversations, turns, traces, cost | Operator+ |
| `conversations:export` | POST data export requests (DSAR) | Admin+ |
| `tools:install` | Add MCP servers to workspace | Admin+ |
| `kb:read` | GET knowledge bases, documents | Viewer+ |
| `kb:ingest` | POST documents, refresh embeddings | Editor+ |
| `evals:read` | GET eval suites, runs, results | Viewer+ |
| `evals:execute` | POST eval runs (manually) | Editor+ |
| `workspace:settings` | PATCH workspace config, regions, budgets | Admin+ |
| `workspace:members` | Invite, role-change, remove members | Admin+ |
| `workspace:keys` | Create/revoke API keys | Admin+ |
| `workspace:billing` | View costs, set hard caps | Owner+ |
| `workspace:delete` | Delete workspace (soft-delete, then cryptographic erase) | Owner only |

Custom scopes for Enterprise: customers can define role-scope tuples via a scope matrix in the dashboard; applied at the gateway via a `ScopeResolver` hook.

### 6.3 Tenant isolation

Three layers:

1. **Postgres RLS** on every tenanted table. Default: `SELECT ... WHERE workspace_id = current_setting('loop.workspace_id')::UUID`. Set at connection init via `SET LOCAL loop.workspace_id = $1`. Enforced in tests: every query without workspace context must be explicitly scoped to a test tenant.
2. **Qdrant per-workspace collections** — no shared collections, ever. Collections named `kb_<workspace_id>_<kb_id>`, `episodic_<workspace_id>`. Queries filter by `workspace_id` in metadata.
3. **Network policies** in k8s: pods in `workspace-X` namespace can only reach pods in their own namespace + control plane + external (egress ACL per agent). Tested in chaos week.

S823 adds a runtime-level `UserMemoryStore` isolation guard for the
`memory_user` tuple `(workspace_id, agent_id, user_id, key)`. Reads and
writes are audit-recorded without storing values in the audit trail, and
the red-team harness runs 100k same-user/cross-user cases with zero
leaks and zero false positives before memory code can be marked done.

**RLS enforcement examples:**

```python
# Every tenanted table must have this pattern
async with db.transaction():
    db.execute("SET LOCAL loop.workspace_id = %s", workspace_id)
    result = await db.fetch("SELECT * FROM conversations")  # implicitly filtered to workspace_id
    # If RLS policy is missing, Postgres returns 0 rows; CI test will fail

# For agents table (control plane): no RLS (agents are global), but scoped in code
agents = await db.fetch(
    "SELECT * FROM agents WHERE workspace_id = %s", workspace_id
)

# For conversations (data plane): RLS enforced at row level
conversations = await db.fetch("SELECT * FROM conversations")  # RLS ensures only this workspace
```

---

## 7. Logging & audit

### 7.1 Audit log

Append-only log of admin events; cryptographic chain (each entry includes hash of the previous).

**Completeness:** Every write endpoint (POST/PATCH/DELETE) must emit an audit event. See [`AUDIT_COMPLETENESS.md`](AUDIT_COMPLETENESS.md) for the master coverage matrix, gap analysis, and remediation tracking.

Events tracked:
- Workspace lifecycle (create / delete / plan change).
- Member invite / role change / removal.
- API key create / revoke / use (sample).
- Secret create / rotate / access.
- Agent deploy / promote / rollback.
- Eval gating override.
- Budget changes.
- HITL takeover.
- Data export.

Each entry: actor, action, target, timestamp, IP, user-agent, request_id, before/after diff (if applicable).

### 7.2 Application logs

- Structured JSON.
- Per-request correlation IDs propagated end-to-end.
- Retention: 30 days hot, 1 year cold.

### 7.3 PII redaction

Default regex patterns auto-redacted at the structured-log handler before persisting to Loki:

```python
PII_PATTERNS = {
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}",
    "phone": r"(?:\+?1)?[\s.-]?\(?([2-9]\d{2})\)?[\s.-]?([2-9]\d{2})[\s.-]?(\d{4})",
    "credit_card": r"[0-9]{13,19}(?:\s|$)",  # non-validated; must pass luhn for DB writes
    "ssn": r"(?!000|666)[0-9]{3}-[0-9]{2}-[0-9]{4}",
    "passport": r"(?:passport|passport_number)[:\s]+[A-Z]{1,2}[0-9]{6,9}",
    "jwt": r"eyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}",
    "api_key": r"(?:sk|pk)_[A-Za-z0-9_]{20,}",  # OpenAI, Stripe, Anthropic common patterns
    "oauth_token": r"ya29\.[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9_]{36,}",  # Google OAuth, GitHub PAT
}
```

Customers can configure additional patterns per workspace via `PATCH /workspaces/{id}/settings` with a `custom_pii_patterns` array (regex strings, validated for performance). Redaction happens at the log handler layer, never in code paths.

Memory writes have an additional runtime filter. S824 adds
`loop_runtime.memory_redaction.MemoryPIIRedactor`, configurable per
agent at write time with `off`, `regex`, `presidio`, or `llm_classifier`
modes. Regex mode uses the built-in email/phone/payment-card patterns,
Presidio mode accepts a Presidio-compatible analyzer, and
LLM-classifier mode accepts classifier-produced spans. Memory audit
events record only action/scope/key metadata, never pre-redaction
values.

#### 7.3.1 Cross-region telemetry filter (S596)

Loop pins each workspace to a single region (S/D/P-plane). The OTel
trace pipeline, however, carries spans into a global aggregation
cluster so SRE has one pane of glass. That seam is enforced by
`loop.observability.PIIScrubber` and the `cross_region=True` flag on
`ClickHouseSpanExporter`:

* known PII attribute keys (`user.email`, `user.phone`, `msisdn`,
  `prompt`, `completion`, `request_body`, `response_body`,
  `user_input`, `user_text`, `message_text`, `address`, `ssn`,
  `credit_card`, …) are replaced with `<redacted-pii>` rather than
  forwarded;
* free-form attribute values that match the canonical email / phone /
  SSN / PAN regexes are redacted by value scan — even on attribute
  keys we have not enumerated;
* a structural keep-list (`workspace_id`, `conversation_id`,
  `turn_id`, `trace_id`, `span_id`, `span_kind`, `name`, timing,
  `cost_usd`, `status`, `region`, `tenant_id`) survives so receiving
  regions can still alert on shape;
* constructing a cross-region exporter without a scrubber **raises at
  boot** rather than silently exfiltrating — a misconfigured deploy
  fails closed.

Tested with synthetic PII in
`packages/sdk-py/_tests/test_region_pii_filter.py`.

---

## 8. Compliance

### 8.1 SOC2 Type 1 (target: month 12)

Control families and where they live:

| Family | Control | Evidence |
|--------|---------|----------|
| Security | Access reviews quarterly | Audit log + reviewer attestations in Vanta |
| Availability | Uptime SLO 99.9%, post-incident reviews | Pager + status page + PIRs |
| Confidentiality | Data classification + encryption | This doc + KMS reports |
| Processing integrity | Eval-gated deploys, audit log | CI logs, audit trail |
| Privacy | DSAR procedure, data deletion | DSAR runbook, object-store lifecycle policies |

Tooling: Vanta or Drata. Auditor selection by month 9.

### 8.2 HIPAA-readiness (target: month 14)

For enterprise customers in healthcare:

- BAA available on Enterprise plan.
- ePHI only stored in customer-designated encrypted regions.
- Audit logs retained 6 years.
- Workforce training on PHI handling.
- Breach notification SLA per HIPAA.

### 8.3 GDPR

- **Lawful basis:** contract (B2B SaaS). Data Processing Agreement (DPA) signed *before* the workspace is created; non-acceptance blocks activation.
- **DPA template & customer flow:**
  1. Customer onboards (sign-up → workspace creation).
  2. If region is EU, system issues DPA document (auto-generated from template with Loop's details + customer's details).
  3. Customer must sign DPA before first conversation is stored (gated by a flag `dpa_signed_at`).
  4. DPA is stored in `workspaces.dpa_signed_at` (audit-logged with actor, timestamp, document hash).
  5. For non-EU regions, DPA is optional but available on request.
- **Subprocessor list (public, on docs.loop.example):** Updated *at least 30 days before any change*. List includes:
  - **LLM providers** (OpenAI, Anthropic, Bedrock, Ollama, vLLM, …) — categorized by workspace API key ownership.
  - **Observability** (Honeycomb, Datadog optional; ClickHouse in-house, no third party for Loop Cloud).
  - **Billing** (Stripe).
  - **Email** (Resend or Mailgun).
  - **Communication** (Twilio, Meta WhatsApp, Slack, LiveKit).
  - Table format: processor name, data category (conversations, metadata, logs, etc.), location, DPA status.
- **Data residency:** EU customers default to `eu-west` abstract region → concrete cloud region selected per customer (e.g., AWS eu-central-1, Azure West Europe, GCP europe-west1). Data stays in region: Postgres, Redis, Qdrant, ClickHouse, object store backups all in the same region.
- **DSAR process:** Completed within 30 days; request tracked in `data_export_requests` table.
  - **Trigger:** `POST /workspaces/{id}/exports?type=dsar&end_user_id=...` (Admin+ only).
  - **What's included:** All conversations, turns, memory, KB chunks used by the user, tool call logs, traces, metadata. Format: `tar.zst` (tarball + Zstandard compression).
  - **Exclusions:** Operator notes (HITL), internal logs, cost ledgers (not end-user data).
  - **Access:** 7-day signed S3 URL; expires automatically.
- **Right to erasure:** `DELETE /workspaces/{id}/end-users/{user_id}` removes all that user's data (conversations, memory, episodic embeddings). Logged to audit. Backups inherit the workspace's KMS key destruction, so backups are invalidated by workspace deletion (PITR window ≤ 30d standard).

### 8.4 Other

- **CCPA/CPRA:** treated as a subset of GDPR for our purposes.
- **PCI:** out of scope; we do not store card data (Stripe-hosted).
- **FedRAMP:** out of scope for v1.

---

## 9. Vulnerability management & dependency provenance

### 9.1 Code

- **Dependency scanning:** Dependabot on every repo, daily. PRs opened for minor + patch; majors require manual review.
- **In-CI gates:**
  - `pip-audit` (Python), `npm audit` (Node), `govulncheck` (Go): PR fails on High/Critical.
  - Snyk (or osv.dev for open-source) for SCA + copyleft license detection.
    Wired in the required `security` job via `snyk/actions/python` with
    `--severity-threshold=high`, gated on `SNYK_TOKEN` presence so
    fork PRs / cold-clone CI skip cleanly. Production CI runs the
    repo with the token set, so the gate is hard. See
    `.github/workflows/ci.yml` (S579).
  - Trivy filesystem scan (HIGH+CRITICAL, blocking) on every PR.
  - Static analysis: `bandit` (Python), `gosec` (Go), CodeQL (all languages).
- **SBOM (Software Bill of Materials) + attestation:**
  - Every CI run on a PR or push to `main` generates a CycloneDX 1.5
    JSON SBOM via `anchore/sbom-action` (which wraps `syft`) inside the
    required `security` job and uploads it as a `sbom-cyclonedx`
    workflow artifact. The SOC2 evidence collector pulls the artifact
    from each green run. See `.github/workflows/ci.yml` (S578).
  - Every release additionally re-generates an SBOM at tag time.
  - Every binary + container signed with Sigstore (cosign); attestations include SLSA provenance.
  - Signatures verified at deployment via policy (Kyverno in k8s).
- **In-toto link attestations:** Each CI step (build, test, scan, sign) generates a link; chains are verified pre-deployment.
- **Pre-commit hook:** `detect-secrets` + pattern scan for API keys, PII in code. Blocks commit if secrets detected.

### 9.2 Infra

- Cloud-native VM/image scanner where available (AWS Inspector / Microsoft Defender for Cloud / GCP Container Analysis / Alicloud Security Center) plus Trivy on every image in CI as the cloud-neutral baseline.
- Trivy on container images in CI.
- Quarterly penetration test by an external firm — see [`PEN_TEST.md`](PEN_TEST.md) for vendor selection, scope, RoE, staging setup, credential management, and remediation tracking.
- Infrastructure-as-code linting: `tflint`, `kube-linter`.

### 9.3 Disclosure

- security@loop.example monitored.
- 90-day coordinated disclosure window; safe harbor for good-faith research.
- Hall of fame on the docs site.

---

## 10. Incident response

### 10.1 Roles

- **Incident commander** (rotating; primary on-call).
- **Comms lead** (CEO or designate for SEV1).
- **Scribe** (records timeline).
- **Tech lead** (drives the fix).

### 10.2 Process & severity mapping

Severity levels mapped to concrete scenarios:

| Severity | Example scenarios | Response SLA | Customer notif SLA |
|----------|------------------|--------------|-------------------|
| **SEV1** | Data loss confirmed; cross-tenant data leak (verified); >50% of customers unable to access agents; LLM provider compromised; RCE in runtime | Ack ≤5 min | Within 1h; call enterprise |
| **SEV2** | One enterprise customer unable to deploy; eval gates fully offline; auth service 99% error rate; tool sandbox DoS; billing system down | Ack ≤15 min | Within 4h; email |
| **SEV3** | Single-tenant bug; UI glitch; audit log delay; non-blocking API endpoint timeout; voice latency spike ≤10% | Ack ≤1h | None (status page only) |

**Process:**

1. Detect → page on-call → ack within SLA (or escalate if no ack in 50% of window).
2. Open `#inc-YYYYMMDD-shortname` Slack channel.
3. Assign incident commander (primary on-call) + comms lead (CEO for SEV1) + scribe (takes timeline).
4. Status page update within 15 min (SEV1), 30 min (SEV2), 2h (SEV3).
5. Customer comms within 1h for SEV1 (email + phone for Enterprise), 4h for SEV2 (email).
6. Mitigate → resolve → verify (confirm fix doesn't break anything else).
7. Post-incident review *within 48h*, blameless; action items owned + dated in Linear; track closure.
8. Root-cause doc + preventive measures drafted within 1 week.

### 10.3 Customer notification

For data-breach SEV1 affecting customer data:
- Notification within 72h per GDPR / state laws.
- Direct email to admin + status page entry + (for enterprise) phone call.

---

## 11. Data lifecycle

### 11.1 Retention

| Data | Default retention | Customer-configurable |
|------|-------------------|------------------------|
| Conversation content | 365 days | yes (1d–7y) |
| Traces | 90 days | yes (7d–1y) |
| Recordings (voice) | opt-in only, then 30 days | yes |
| KB documents | until customer deletes | always retained |
| Audit log | 7 years | no |
| Backups | 14 days PITR | extendable on Enterprise |

### 11.2 Deletion

- API: `DELETE /v1/workspaces/{id}` triggers a 30-day soft-delete window, then cryptographic erase via KMS key destruction.
- End-user erasure: `DELETE /v1/users/{user_id}` removes conversation, memory, episodic embeddings; logged in audit.
- Backups: customer-deletion is not retroactive over backups, but backup retention is bounded (≤ 30d standard, 90d enterprise) and backups are themselves KMS-encrypted with the workspace key, so destroying the key invalidates all backups too.

---

## 12. Security testing in CI

| Check | Tool | Gate |
|-------|------|------|
| Lint | ruff / biome / golangci-lint | block on error |
| Type | pyright / tsc / go vet | block on error |
| Secret scan | detect-secrets (pre-commit + CI) | block on detection |
| Dependency vuln | pip-audit / npm audit / govulncheck | block on High/Critical |
| Static analysis | bandit / CodeQL / gosec | block on High |
| Container scan | Trivy | block on Critical |
| Infra lint | tflint / kube-linter / checkov | block on High |
| License | scancode-toolkit | block on copyleft incompat |

---

## 13. Open security questions

1. **Tenant DB isolation on data plane.** Single Postgres with RLS vs schema-per-tenant vs DB-per-tenant. Currently single Postgres + RLS; revisit at 100 enterprise customers.
2. **End-user MFA for high-stakes agents.** When the agent triggers a money-moving action, do we require step-up auth from the end user? Likely yes via channel-side OTP.
3. **BYO encryption keys (BYOK)** for enterprise — month 12 deliverable, design TBD.
4. **Federated tenant identity** (customer's IdP for end-users, not just builders) — month 14 evaluation.
