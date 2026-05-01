# Enterprise GA (S050)

This document is the **definition of done** for shipping Loop's
Enterprise tier publicly. Three pillars must be GA-ready in the same
release:

1. **SSO / SAML** — IdP-initiated and SP-initiated flows for Okta,
   Entra ID, Google Workspace, plus generic SAML 2.0 + OIDC.
2. **Audit log UI** — Studio screen exposing every event from
   [SECURITY.md § Audit Events](SECURITY.md) with filter / export /
   retention controls.
3. **On-prem parity** — feature matrix where the Helm-installed
   private build matches the multi-tenant cloud, with documented
   deltas and timelines. The authoritative checked matrix is
   [PARITY.md](PARITY.md).

## Pillar 1 — SSO / SAML

### Supported flows

| IdP                  | SP-init | IdP-init | SCIM 2.0 | JIT  |
| -------------------- | :-----: | :------: | :------: | :--: |
| Okta                 |   ✅    |    ✅    |    ✅    |  ✅  |
| Entra ID             |   ✅    |    ✅    |    ✅    |  ✅  |
| Google Workspace     |   ✅    |    ✅    |    ✅    |  ✅  |
| Generic SAML 2.0     |   ✅    |    ✅    |    ❌    |  ✅  |
| Generic OIDC         |   ✅    |    ✅    |    ❌    |  ✅  |
| Auth0                |   ✅    |    ✅    |    ❌    |  ✅  |

- **JIT** (just-in-time) provisioning creates the user on first
  login if the IdP asserts a known tenant claim.
- **SCIM 2.0** is required for Okta and Entra ID to drive group
  → role mapping; the SCIM endpoint lives at
  `/v1/scim/v2/{tenant_id}` behind a tenant-scoped bearer token.

### Role mapping

The IdP asserts groups via the `groups` SAML attribute or `groups`
OIDC claim. Loop maps groups to one of four built-in roles:

| Role       | Permissions                                      |
| ---------- | ------------------------------------------------ |
| `owner`    | All actions, including billing                   |
| `admin`    | All except billing + tenant deletion             |
| `editor`   | Create/modify agents, KBs, channels              |
| `viewer`   | Read-only across the tenant                      |

Custom RBAC is **out of scope for GA**; tracked under S067.

### Session policy

- Default session lifetime: 12h sliding, 24h absolute.
- Force re-auth for: billing changes, tenant export, role
  modifications, deletion of any agent version.
- IdP-initiated logout (SAML SLO / OIDC end-session) is honoured.

### Failure modes

| Failure                                | Behaviour                                                       |
| -------------------------------------- | --------------------------------------------------------------- |
| IdP signature verification failure     | 401, audit `auth.sso.signature_invalid`, no session granted     |
| Clock skew > 5 min                     | 401, audit `auth.sso.clock_skew`, surface remediation in UI     |
| Group claim missing / unmappable       | Login allowed if `viewer` is the configured default; else 403   |
| SCIM token revoked                     | Provisioning paused, banner in Studio, on-call paged after 4h   |

## Pillar 2 — Audit log UI

### Surface

A new top-level Studio screen at `/studio/audit`. The screen is
gated by the `audit:read` permission (granted to `owner` + `admin`
by default, opt-in for `editor`).

### Capabilities

- Time range picker (last 24h / 7d / 30d / custom up to retention
  cap).
- Filters: actor (user / api-key / system), tenant, agent, action
  family (auth, agent, kb, billing, security, channel), severity,
  IP, region.
- Per-row drill-down to the full structured event JSON (matches
  the schema in [SECURITY.md § Audit Events](SECURITY.md)).
- CSV / JSON-Lines export, capped at 1M rows per export.
- Saved views per user; "alert me when ≥ N events match this view
  in 1h" lands in S068 (deferred).

### Retention

- **Hot** (queryable from UI): 90 days standard, 365 days for
  Enterprise.
- **Cold** (S3 / GCS / Azure Blob, replay-only): 7 years for
  Enterprise (matches SOC 2 + HIPAA expectations).
- Both knobs are per-tenant, settable by `owner` only, with a
  `audit.retention.changed` audit row.

### Performance

- Hot store target p95 query latency: 1.5 s for any 7-day
  filter window with ≤ 5 active filters.
- Index on `(tenant_id, ts DESC, action)` covers the default view;
  see [data/SCHEMA.md § audit_events](../data/SCHEMA.md).

## Pillar 3 — On-prem parity

The **on-prem private build** is a Helm chart customers install
into their own Kubernetes (any of EKS / GKE / AKS / OpenShift).
Parity matrix vs. multi-tenant cloud as of GA:

| Capability                       | Cloud | On-prem GA | Notes                                                     |
| -------------------------------- | :---: | :--------: | --------------------------------------------------------- |
| Agent runtime                    |  ✅   |    ✅      | Identical container images, identical image digests       |
| KB ingest + search               |  ✅   |    ✅      | Customer brings own object store + vector DB              |
| Voice (WebRTC + PSTN)            |  ✅   |    ✅      | Customer brings carrier; LiveKit in-cluster               |
| Channels (web, slack, msteams)   |  ✅   |    ✅      | All channels are stateless adapters                       |
| LLM gateway                      |  ✅   |    ✅      | Customer plugs in their preferred providers               |
| Audit log UI                     |  ✅   |    ✅      | Same chart, same screen                                   |
| SSO/SAML/OIDC                    |  ✅   |    ✅      | Identical config; on-prem exposes one SP per cluster      |
| SCIM provisioning                |  ✅   |    ✅      | —                                                         |
| Eval harness                     |  ✅   |    ✅      | Runs against in-cluster judges                            |
| Observability (OTEL traces)      |  ✅   |    ✅      | Customer-supplied OTEL collector endpoint                 |
| **Hosted control-plane updates** |  ✅   |    🟡      | Customer-driven `helm upgrade`; release cadence quarterly |
| **Multi-tenant within cluster**  |  ✅   |    🟡      | Single-tenant only; multi-tenant in S082                  |
| **Cross-region failover**        |  ✅   |    ❌      | Customer's cluster topology problem; runbook only         |
| **Auto-scaling control plane**   |  ✅   |    🟡      | Manual replica counts via values; HPA in S081             |

🟡 = ships with a documented workaround / manual procedure.
❌ = explicitly customer-owned, not a Loop deliverable.

### Install footprint

- Minimum: 6 vCPU / 16 GB RAM / 200 GB SSD (single-replica, dev).
- Production: 24 vCPU / 96 GB RAM / 1 TB SSD across ≥ 3 nodes.
- External dependencies: Postgres 15+, Redis 7+, S3-compatible
  object store, Kafka or Redpanda, KMS-equivalent key store. See
  [REGIONAL_DEPLOYS.md](REGIONAL_DEPLOYS.md) for the per-cloud
  mapping.

### Air-gapped variant

The `helm-loop-airgap` bundle (lands in S080) ships every container
image, the Studio JS bundle, and the documentation site as a single
tarball + index. **Out of scope for S050 GA**; tracked separately.

## GA gates

A release of Loop is allowed to claim "Enterprise GA" only if all
of the following are green for two consecutive release trains:

1. SOC 2 Type 1 report issued (S046 milestone) **or** Type 1
   walkthrough complete and report scheduled within 60 days.
2. SSO + SCIM end-to-end tested against Okta and Entra ID staging
   tenants (Layer-3 integration test under
   [TESTING.md](TESTING.md)).
3. Audit log UI passes Studio visual-regression suite + a11y
   contract (see [ux/UX_DESIGN.md](../ux/UX_DESIGN.md)).
4. [PARITY.md](PARITY.md) is published in the docs site for the exact
   release tag, with evidence committed beside it.
5. p50 voice latency ≤ 700 ms on the synthetic harness
   (S048 budget).

## Out of scope for S050

- Custom RBAC roles (S067).
- Audit alert subscriptions (S068).
- HPA + cross-region for on-prem (S081, S083).
- Air-gapped install bundle (S080).
- Multi-tenant on-prem (S082).
- HIPAA / FedRAMP / PCI attestations.
