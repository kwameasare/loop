# On-Prem Parity Matrix (S639)

This matrix compares Loop's managed cloud offer with the customer-run
Helm install. The checked-in evidence is
`loop_implementation/engineering/parity_evidence.tsv`; CI asserts that
every parity row references real Helm feature gates and every gap has an
explicit accepted disposition.

## Policy

No silent gaps: a capability is either `parity` with repo evidence, or
`accepted_gap` with a named follow-up/customer-owned disposition. S639
does not claim unfinished S28 stories as shipped; it records them as
accepted gaps until their owning stories land.

## Matrix

| ID | Capability | Cloud gate | On-prem gate | Status | Disposition |
| --- | --- | --- | --- | --- | --- |
| `runtime-turns` | Agent runtime and `/v1/turns` | Managed runtime deployment | Helm `runtime.*` deployment and service | parity | Same container contract and service port |
| `control-plane-api` | Control-plane API | Managed CP deployment | Helm `controlPlane.*` deployment and service | parity | Same API surface behind configurable release |
| `llm-gateway` | LLM gateway | Managed provider gateway | Helm `gateway.*` deployment and service | parity | Customer supplies provider credentials |
| `kb-search` | KB ingest and vector search | Managed KB services | `kbEngine`, Qdrant, and object-store gates | parity | Customer may use bundled or external stores |
| `tool-sandbox` | Tool execution sandbox | Managed sandbox tier | `toolHost` plus Kata preflight gates | parity | Fails install when sandbox runtime is missing |
| `data-stores` | Runtime data plane stores | Managed Postgres/Redis/NATS/ClickHouse | Helm subchart or external URI gates | parity | Same logical dependencies, customer-operated |
| `ingress-tls` | Public ingress and TLS | Managed edge | Ingress and cert-manager gates | parity | Customer controls DNS and issuer |
| `observability` | Telemetry export | Managed telemetry backend | OTLP endpoint gate | parity | Customer supplies collector endpoint |
| `ha-resilience` | HPA/PDB rollout safety | Managed autoscaling | Helm HPA/PDB feature gates | parity | Disabled by default, available per values |
| `audit-compliance` | Audit UI/export/DPA/GDPR | Managed compliance stack | Pending S28 audit stories | accepted_gap | Accepted: S630-S635 own shipment |
| `customer-managed-keys` | CMK and BYO Vault | Managed KMS controls | Pending CMK/Vault stories | accepted_gap | Accepted: S636-S637 own shipment |
| `single-tenant-mode` | Dedicated tenant isolation | Cloud tenant isolation | Pending enterprise values mode | accepted_gap | Accepted: S638 owns isolated stack |
| `multi-tenant-cluster` | Multi-tenant control plane | Managed shared cloud | Single tenant per Helm release | accepted_gap | Accepted: S082 tracks in-cluster tenancy |
| `cross-region-failover` | Provider-backed failover | Managed regional topology | Customer topology/runbook | accepted_gap | Accepted: customer-owned cluster design |
| `airgap-bundle` | Air-gapped private build | Cloud release channel | Pending bundle story | accepted_gap | Accepted: S080 owns bundle packaging |

## Evidence contract

`parity_evidence.tsv` columns:

- `id`: matrix row id.
- `cloud_gate`: the managed-cloud control the row is compared against.
- `feature_gates`: semicolon-separated Helm values for `parity` rows,
  or `accepted:<story-or-owner>` markers for accepted gaps.
- `status`: `parity` or `accepted_gap`.
- `evidence_paths`: semicolon-separated repo files that prove the row.
- `accepted_gap`: empty for parity rows; starts with `Accepted:` for gaps.
