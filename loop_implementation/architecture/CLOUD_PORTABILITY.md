# Loop — Cloud Portability

**Status:** Draft v0.1
**Owner:** Founding Eng #2 (Infra)
**Companion:** `architecture/ARCHITECTURE.md`, `adrs/README.md` (ADR-016)

Loop runs on **any major cloud** (AWS, Azure, GCP, Alibaba Cloud, Oracle Cloud, OVHcloud, Hetzner) and **fully self-hosted** (k8s on bare metal or hypervisor) with the same code. This document spells out the abstractions and the mapping table the team uses to keep that promise.

---

## 1. Why this matters

Customers pick their cloud for reasons that have nothing to do with us — data residency, existing committed spend, regulatory requirements, regional preference (China-domestic must run on Alibaba; some EU public-sector must run on OVHcloud or Sovereign Cloud). Loop must not become an "AWS shop" the way Botpress did. The wedge is portability; the implementation discipline is to never let cloud-specific primitives leak into our own code.

---

## 2. Principles

1. **Code targets abstractions, not vendors.** Every cloud-touching line of code goes through a small set of internal interfaces (`ObjectStore`, `KMS`, `SecretsBackend`, `EmailSender`, `ManagedPostgres`, `ManagedRedis`, `ManagedQdrant`).
2. **Kubernetes is the lowest common denominator.** Anything that can be a k8s workload, is. We use managed k8s on each cloud (EKS, AKS, GKE, ACK) — not the cloud's proprietary container service.
3. **Open standards over proprietary APIs.** S3-compatible object storage. Postgres-wire-compatible Postgres. OTLP for telemetry. OIDC for auth. PostgreSQL `pgvector` or Qdrant for vectors — both runnable anywhere.
4. **Terraform/Pulumi for everything.** No CloudFormation, no ARM templates, no Deployment Manager, no ROS. Same `infra/terraform/` works on every cloud with provider swap.
5. **Two-cloud rule.** Every primitive in our code has at least two implementations validated in CI: one cloud-native and one open-source. If only one exists, we have a vendor lock — fix before merging.

---

## 3. Service mapping table

| Loop need | Internal interface | AWS | Azure | GCP | Alibaba Cloud | Self-host (OSS) |
|-----------|--------------------|-----|-------|-----|---------------|------------------|
| **Container orchestration** | k8s | EKS | AKS | GKE | Container Service for Kubernetes (ACK) | k3s, kubeadm |
| **Managed Postgres** | `ManagedPostgres` | RDS for PostgreSQL / Aurora PostgreSQL | Azure Database for PostgreSQL Flexible | Cloud SQL for PostgreSQL / AlloyDB | ApsaraDB RDS for PostgreSQL / PolarDB | Postgres on k8s (CloudNativePG) |
| **Managed Redis** | `ManagedRedis` | ElastiCache for Redis | Azure Cache for Redis | Memorystore for Redis | Tair / ApsaraDB for Redis | Redis on k8s (Redis Operator) |
| **Vector store** | `VectorBackend` | Qdrant Cloud / pgvector via RDS | Qdrant on AKS / pgvector | Qdrant on GKE / pgvector | Qdrant on ACK / pgvector | Qdrant Helm |
| **Object storage (S3-compatible)** | `ObjectStore` | S3 | Blob Storage (use S3 protocol via [Blob's S3 endpoint](https://learn.microsoft.com/azure/storage/blobs/blob-storage-overview) **or** MinIO Gateway) | Cloud Storage (S3-compatible via Interoperability) | OSS (S3-compatible via interop endpoint) | MinIO |
| **Cloud KMS** | `KMS` | AWS KMS | Azure Key Vault | Cloud KMS | KMS / Cloud KMS | HashiCorp Vault Transit |
| **Secrets** | `SecretsBackend` | Secrets Manager | Key Vault Secrets | Secret Manager | KMS Secret | HashiCorp Vault |
| **Identity (workforce)** | OIDC | Cognito + Auth0 | Entra ID + Auth0 | Cloud Identity + Auth0 | RAM + Auth0 | Ory Kratos |
| **Pub/sub (event bus)** | `EventBus` (NATS-API) | NATS on EKS | NATS on AKS | NATS on GKE | NATS on ACK | NATS Helm |
| **Trace storage** | OTLP | Managed Service for Prometheus / X-Ray + Altinity ClickHouse on EKS | Azure Monitor + ClickHouse on AKS | Cloud Trace + ClickHouse on GKE | Log Service + ClickHouse on ACK | ClickHouse Helm |
| **Edge / CDN / WAF** | `EdgeRouter` | CloudFront + WAF | Front Door + WAF | Cloud CDN + Cloud Armor | DCDN + WAF | Cloudflare (multi-cloud) or self-host Envoy |
| **Email transactional** | `EmailSender` | SES | Communication Services | Cloud Email (via partners) | DirectMail | SMTP relay (Postmark, Resend, Mailgun) |
| **CI/CD** | — | GitHub Actions | GitHub Actions | GitHub Actions | GitHub Actions | GitHub Actions or Forgejo Actions |
| **Container registry** | OCI | ECR | ACR | Artifact Registry | Container Registry | Harbor |
| **DNS** | — | Route 53 | Azure DNS | Cloud DNS | Alibaba DNS | PowerDNS |

**Cloudflare is the recommended default for CDN, WAF, DDoS, DNS, and Spectrum (voice).** It is itself cloud-agnostic; using it everywhere reduces per-cloud variance for our most user-visible perf surface.

---

## 4. Internal interfaces (Python)

All cloud-touching code goes through these. Each interface ships at least two implementations: one native to the active cloud, one OSS fallback for self-host. Adding a fifth cloud means adding implementations, not editing call sites.

### 4.1 ObjectStore

```python
from typing import Protocol, AsyncIterator

class ObjectStore(Protocol):
    async def put(self, key: str, body: bytes, *, content_type: str | None = None,
                  encryption_key_ref: str | None = None) -> None: ...
    async def get(self, key: str) -> bytes: ...
    async def stream(self, key: str) -> AsyncIterator[bytes]: ...
    async def delete(self, key: str) -> None: ...
    async def presigned_url(self, key: str, *, ttl_seconds: int) -> str: ...
```

Implementations:
- `S3CompatibleObjectStore` (works for AWS S3, GCS-via-interop, Alibaba OSS, MinIO).
- `AzureBlobObjectStore` (native; falls back to S3 gateway when configured).

### 4.2 KMS

```python
class KMS(Protocol):
    async def generate_data_key(self, *, key_ref: str) -> tuple[bytes, bytes]:
        """Returns (plaintext_key, encrypted_key)."""
    async def decrypt(self, *, key_ref: str, ciphertext: bytes) -> bytes: ...
    async def encrypt(self, *, key_ref: str, plaintext: bytes) -> bytes: ...
    async def rotate(self, *, key_ref: str) -> None: ...
```

Implementations:
- `AwsKmsBackend`, `AzureKeyVaultBackend`, `GcpKmsBackend`, `AlicloudKmsBackend`, `VaultTransitBackend`.

### 4.3 SecretsBackend

```python
class SecretsBackend(Protocol):
    async def read(self, ref: str) -> str: ...
    async def write(self, ref: str, value: str, *, ttl: int | None = None) -> None: ...
    async def delete(self, ref: str) -> None: ...
    async def rotate(self, ref: str, new_value: str) -> None: ...
```

Implementations: `VaultBackend` (default for self-host AND multi-cloud), `AwsSecretsManagerBackend`, `AzureKeyVaultSecretsBackend`, `GcpSecretManagerBackend`, `AlicloudKmsSecretsBackend`.

**Default in cloud:** Vault deployed as a service in our own cluster. We do not depend on the cloud's secrets product unless a customer requires it for compliance.

### 4.4 ManagedPostgres / ManagedRedis / ManagedQdrant

These are *configuration*, not code. The runtime connects to them via standard wire protocols. Choosing the backend is a Helm value (`postgres.host`, `postgres.cert`, `redis.host`, `qdrant.url`). The runtime does not know which cloud is hosting them.

### 4.5 EventBus

NATS JetStream is our event bus. Identical Helm chart on every cloud. We do not use Kinesis / Event Hubs / Pub/Sub / MNS. Fewer abstractions = simpler operations = portability for free.

### 4.6 IdentityProvider

OIDC. Cloud-agnostic. Auth0 (cloud) or Ory Kratos (self-host). No cloud-specific identity dependencies.

### 4.7 EmailSender

```python
class EmailSender(Protocol):
    async def send(self, *, to: list[str], subject: str, html: str, text: str) -> None: ...
```

`SesBackend`, `AzureCommunicationBackend`, `MailgunBackend`, `ResendBackend`, `SmtpBackend`. Default in cloud = Resend or Mailgun (cloud-neutral SaaS).

---

## 5. Region & data-residency model

We do not encode region constants in code. Workspace records carry a `region` field; the data plane is selected by region; the control plane proxies cross-region admin.

Default region pairs offered at launch:

| Geography | Recommended cloud(s) | Region examples |
|-----------|----------------------|------------------|
| North America | AWS / GCP / Azure | `na-east`, `na-west` |
| Europe | AWS / Azure / GCP / OVHcloud | `eu-central`, `eu-west` |
| China (mainland) | Alibaba Cloud (data sovereignty) | `cn-shanghai`, `cn-hangzhou` |
| APAC ex-China | AWS / GCP | `apac-sg`, `apac-tokyo` |
| Sovereign / regulated | OVHcloud, Sovereign Cloud, on-prem | per customer |

Region names are abstract (`na-east` not `us-east-1`); the deployment manifests map them onto each cloud's actual region naming. New regions are added via the `infra/terraform/regions.yaml` file, not via code changes.

---

## 6. Infrastructure as code

We use **Terraform** (with the `terraform-provider-loop` umbrella module) and **Pulumi** for the application layer.

`infra/terraform/` structure:

```
infra/terraform/
├── regions.yaml           # abstract Loop region registry + concrete cloud mapping
├── modules/
│   ├── data-plane/        # cloud-agnostic; takes provider creds + region
│   ├── control-plane/
│   ├── kubernetes/        # wraps EKS / AKS / GKE / ACK behind one interface
│   ├── postgres/          # wraps RDS / Azure DB / Cloud SQL / ApsaraDB
│   ├── redis/
│   ├── object-store/
│   ├── kms/
│   ├── networking/
│   └── observability/
├── envs/
│   ├── dev-aws/
│   ├── dev-gcp/
│   ├── staging-aws/
│   ├── prod-aws-na-east/
│   ├── prod-azure-eu-west/
│   ├── prod-alibaba-cn-shanghai/
│   └── prod-self-host-example/
└── providers.tf           # all four cloud providers + helm + kubernetes
```

Every customer-facing region directory under `envs/` invokes the same module set with different provider config. Adding a new region/cloud = a new directory + provider config — never a code change in `modules/`.

Pulumi is used in `apps/control-plane/` for higher-level k8s manifests where TypeScript ergonomics matter; but the Pulumi layer also takes the cloud provider as a constructor argument.

---

## 7. IPv6 & networking neutrality

Loop is **dual-stack IPv6/IPv4 ready** at the platform level:

- All managed Postgres, Redis, and Qdrant services must support IPv6 connectivity (cloud-native offerings do; self-host via k8s DNS names resolve to both).
- NATS cluster uses IPv4 internally (peer-to-peer within a region) but accepts IPv6 client connections.
- Kubernetes services use dual-stack (`.spec.ipFamilies: [IPv4, IPv6]`).
- LLM provider and channel provider calls are dual-stack capable (no preference, let the client resolve).
- WAF (Cloudflare) is IPv6-native and forwards both stacks to the origin.

**Status:** IPv6 is not required in MVP (month 6) but must be non-breaking. All services must *accept* IPv6 connections; prefer IPv6 on capable networks. Revisit for mandatory IPv6-primary at month 12.

---

## 8. DNS & certificate rotation cadence

**DNS resolution:**
- Abstract region names (`api.na-east.loop.example`) → Cloudflare DNS → concrete cloud region endpoints.
- TTL = 60s for resilience during regional failover.
- Per-cloud region endpoints registered in Terraform: `aws-us-east-1.na-east.loop.example`, `azure-eastus.na-east.loop.example`, etc.; Cloudflare load-balances traffic via geolocation + health checks.
- CAA records: only Let's Encrypt + Digicert permitted issuers.

**Certificate lifecycle:**
- TLS handshake certs (api.loop.example, *.loop.example) issued by Let's Encrypt, auto-renewed 30 days before expiry via cert-manager in k8s.
- Per-workspace mTLS certs (runtime ↔ control plane) issued via SPIRE every 24h; old cert honored for 1h grace period.
- Per-agent secrets (LLM keys, channel tokens) rotated via the `SecretsBackend` interface; policy is per-workspace (recommended ≤ 90 days, warning at 90d, auto-revoke at 180d for leaked keys).

---

## 9. Data residency & regulatory proof

**Region pinning:**
- Workspace `region` field (set at creation) determines:
  - Which data-plane cluster processes the agent.
  - Where Postgres, Redis, Qdrant, object storage live.
  - Control plane is multi-region (active-active per ADR-013); data plane is single-region per workspace.
- cp-api dispatch resolves the workspace region through `infra/terraform/regions.yaml`
  and forwards data-plane calls to that region's `data_plane_url`, recording
  per-call latency for routing SLOs.
- Data export loaders are deny-by-default across regions: cp-api checks the
  requested export region against the workspace pin before any export store is
  allowed to load metadata or bytes.

**EU / GDPR:**
- Workspaces created in `eu-west` abstract region map to a concrete cloud region in Europe (e.g., `eu-central-1` on AWS, `westeurope` on Azure).
- Audit log: every read/write of sensitive data (conversations, memory) includes the region and logs to the local ClickHouse + forwarded to control-plane ClickHouse via HTTPS + mTLS.
- DSAR compliance: `/v1/workspaces/{id}/export` returns all customer data as encrypted tar.gz, signed with customer's public key (if provided). No cross-border transfer; export lives in the data-plane region's object storage.

**China / Alibaba:**
- Mainland-China workspaces must run on Alibaba Cloud (legal requirement).
- Abstract region `cn-shanghai` deploys exclusively to Alibaba Cloud ACK + ApsaraDB.
- No cross-border egress allowed; LLM calls are routed through a local LLM provider (TBD at month 9).

**Sovereign cloud / on-prem:**
- Customer runs k8s in their own VPC / data center.
- Loop control plane (cloud) communicates to data plane via outbound HTTPS + mTLS only.
- No inbound firewall rules required on customer side; data plane initiates.

---

## 10. Helm chart for self-host

`infra/helm/loop/` is the single source of truth for self-host. It wraps every Loop service plus optional bundled deps (Postgres, Redis, Qdrant, NATS, MinIO, ClickHouse) that customers can disable to point at their own.

`values.yaml` exposes every cloud-specific knob:

```yaml
global:
  cloud: aws            # aws | azure | gcp | alibaba | self_host
  region: us-east-1     # cloud-specific name; resolves into our abstract region
  kms:
    backend: vault       # aws_kms | azure_key_vault | gcp_kms | alicloud_kms | vault
    keyRef: ${LOOP_KMS_KEY_REF}
  objectStore:
    backend: s3
    endpoint: ""        # blank = aws default; set for GCS-interop, OSS, MinIO
    bucket: loop-prod
  secrets:
    backend: vault       # default; cloud-native via cloud == ...
    address: https://vault.example
  postgres:
    host: ${LOOP_DB_HOST}
    sslMode: verify-full
  redis:
    host: ${LOOP_REDIS_HOST}
    tls: true
  email:
    backend: resend
    apiKeyRef: vault://secret/data/email
  edge:
    cdn: cloudflare
    wafZoneId: ${CF_ZONE_ID}
```

A team running on Alibaba Cloud sets `global.cloud: alibaba`, points at ApsaraDB and OSS, and the chart picks the right configurations.

---

## 11. CI matrix

To keep the two-cloud rule honest, CI runs the integration suite in matrix:

```yaml
matrix:
  cloud:
    - aws
    - gcp
    - azure
    - self_host_minio
```

Self-hosted Linux runners with Docker + LocalStack / Azurite / fake-gcs-server stand in for the actual clouds in PR CI. A nightly job runs the same matrix against real cloud accounts (one minimal env per cloud) to catch drift.

---

## 12. What we explicitly do NOT use

These would tie us to a single cloud and are forbidden:

- AWS-only: Aurora-specific extensions beyond standard Postgres, DynamoDB, Lambda, Step Functions, AppSync, EventBridge Pipes, IAM-based service-to-service auth.
- Azure-only: Cosmos DB, Logic Apps, Service Bus, Functions, AAD-Only auth flows.
- GCP-only: Spanner, BigQuery as a primary store (analytics export OK), Pub/Sub as primary bus, Firestore.
- Alibaba-only: MaxCompute, Function Compute, MNS as primary bus.

Anything in this list requires an ADR with explicit justification before introduction.

---

## 13. Migration playbook (mid-customer)

If a customer wants to migrate clouds (e.g., AWS → Azure), the playbook is:

1. Spin up the target environment via `infra/terraform/envs/prod-azure-<region>/`.
2. Replicate Postgres via logical replication.
3. Sync Qdrant via snapshot + restore.
4. Replicate object storage via [rclone](https://rclone.org/) (S3 ↔ Azure Blob ↔ GCS ↔ OSS — all supported).
5. Cut the workspace's `region` field over.
6. Decommission the old environment after a soak window.

This is documented as a runbook owned by Eng #2.

---

## 14. Open questions

1. **Cross-cloud single-pane-of-glass.** Customers running multi-cloud will expect the Loop control plane to see all their data planes. Plan: control plane aggregates via the same outbound-mTLS pattern documented in `architecture/ARCHITECTURE.md` §6.3.
2. **Cloud-specific SLOs.** Each cloud's underlying primitives have different SLOs. We publish per-cloud SLOs in our SLA, not a single uniform number.
3. **Cost model variance.** Per-token, per-GB, per-instance costs differ across clouds; pricing must accommodate per-region cost-of-goods variance. Track via the costs sheet in the implementation tracker.
