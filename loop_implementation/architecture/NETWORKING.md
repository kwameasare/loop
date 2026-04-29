# Loop — Networking, DNS & Certificates

**Status:** v0.1  •  **Owner:** Founding Eng #2 (Infra)
**Companions:** `architecture/CLOUD_PORTABILITY.md`, `architecture/AUTH_FLOWS.md` §5 (mTLS), `engineering/SECURITY.md` §1 (trust boundaries).

This document specifies Loop's network topology, egress policies, private connectivity, DNS, and certificate management. Cloud-portable; same primitives on every cloud.

---

## 1. Network model

```
                                 ┌────────────────────────────┐
                                 │    Public Internet         │
                                 └─────────────┬──────────────┘
                                               │
                                  Cloudflare (CDN/WAF/DDoS)
                                               │
                          ┌───────────────────────────────────┐
                          │      Edge / ingress (Envoy)       │
                          │      mTLS terminates here         │
                          └───────────────────────────────────┘
                                               │
        ┌──────────────────┬─────────────┬─────┴───────┬─────────────────┐
        ▼                  ▼             ▼             ▼                 ▼
   cp-api           studio-web     dp-webhook    dp-channel-*       dp-runtime
   (control)        (Next.js)      ingester       (channels)        (multi-tenant)
                                                                          │
                                  Service mesh (mTLS / SPIFFE)            │
                                                                          ▼
                                                              ┌─────────────────────┐
                                                              │ dp-postgres / redis │
                                                              │ qdrant / nats / S3  │
                                                              │ ClickHouse / Vault  │
                                                              └─────────────────────┘
                                                                          │
                                                                          ▼
                                                              External (LLM providers,
                                                              channel APIs, MCP servers)
                                                              via egress-controlled
                                                              gateway
```

---

## 2. Cluster network policies (k8s)

Default: **deny all**. Allow rules:

| From | To | Ports |
|------|-----|------|
| `ingress` namespace | `cp-api`, `studio-web`, `dp-webhook-ingester`, `dp-channel-*` | 8080, 3000, varies |
| `dp-runtime` | `dp-gateway`, `dp-tool-host`, `dp-kb-engine` | service ports |
| `dp-runtime` | `dp-postgres` (PgBouncer), `dp-redis`, `dp-qdrant` | 5432, 6379, 6333 |
| `dp-gateway` | `egress-gw` | 8443 |
| `dp-tool-host` | `egress-gw` | 8443 |
| every pod | `dp-otel-collector` | 4317 |
| every pod | `vault` | 8200 |
| `dp-channel-voice` | `livekit` | 7881, UDP RTP range |
| nothing | nothing | (default deny) |

NetworkPolicy resources committed in `infra/helm/loop/templates/network-policies/`.

---

## 3. Egress control

All egress to the public internet routes through `egress-gw` (a hardened Envoy + Squid setup). This:

1. Enforces an **allow-list** of FQDNs per workspace (LLM providers, channel APIs, customer-declared MCP-server hosts).
2. Logs every egress request with workspace_id (correlated to traces).
3. Blocks egress to internal RFC1918 ranges (no SSRF).
4. Caches DNS at the gateway level (60 s TTL) to detect rebinding.

Per-workspace egress policy stored in `egress_policies` (Postgres). Updated via `cp-api` admin endpoint; propagated to `egress-gw` within 60 s.

---

## 4. Private connectivity (per cloud)

| Cloud | Private Loop ↔ customer link | Private Loop ↔ cloud-managed services |
|-------|------------------------------|-----------------------------------------|
| AWS | PrivateLink (Loop publishes a VPC Endpoint Service) | VPC Endpoints to RDS, S3, KMS |
| Azure | Private Link (Loop publishes a Private Link Service) | Private Endpoints to Azure DB, Blob, Key Vault |
| GCP | Private Service Connect | PSC for Cloud SQL, GCS, KMS |
| Alibaba | PrivateLink | VPC endpoints to ApsaraDB, OSS, KMS |
| Self-host | customer's choice (peering, IPsec, WireGuard) | n/a |

Hybrid customers (control plane = our Cloud, data plane = their VPC) connect via mutual private connectivity in both directions:
- Loop → customer: outbound mTLS via the Loop egress-gw, IP-restricted.
- Customer → Loop: inbound via private endpoint we publish.

Public endpoints are available for plans that don't need private connectivity, but Enterprise default is private-only.

---

## 5. DNS

### 5.1 Public

- `loop.example` and subdomains hosted on **Cloudflare DNS** by default (cloud-neutral; AAA security; fast TTL).
- Per-region public hostname pattern: `api-<region>.loop.example`, `studio-<region>.loop.example`.
- TTL: 60 s for record types we may need to flip during incidents (A, AAAA, CNAME for region endpoints). 1 h for static records (TXT, MX).
- `_dmarc`, `_domainkey`, SPF, DMARC TXT records present from day 1.
- CAA records pin Let's Encrypt and ZeroSSL only; other CAs blocked.

### 5.2 Private (in-cluster)

- CoreDNS as the cluster DNS (k8s default). Per-region zones.
- Service-to-service uses standard `svc.cluster.local` resolution.
- ExternalDNS optional for external-facing services.

### 5.3 Customer-supplied custom domains

Workspaces on Pro+ plans can map a custom domain (e.g., `support.acme.com`) to their agent. We provision Let's Encrypt certs via DNS-01 (with the customer creating a CNAME) or HTTP-01 (with the customer pointing A records).

---

## 6. TLS / certificates

### 6.1 Public TLS

- Cloudflare terminates TLS for public traffic.
- Behind Cloudflare, Envoy terminates a second TLS (Cloudflare Origin Certs or Loop-issued ACM-equivalent).
- Min: TLS 1.3. TLS 1.2 only when a customer pins it for compatibility.
- Cert renewal: ACME via cert-manager. 60-day rotation; 30-day buffer.

### 6.2 Internal mTLS

- SPIRE issues x509 with SPIFFE SAN.
- Cert lifetime: 24 h.
- Root CA rotation: yearly, with a 90-day overlap.

### 6.3 Customer-facing certs

- Workspaces with custom domains: Let's Encrypt or ZeroSSL via cert-manager + DNS-01.
- We never see the customer's private key for their own domain — the cert lives in our edge proxy only.

---

## 7. IPv6 readiness

- Public ingress (Cloudflare) is dual-stack from day 1.
- Per-region clusters dual-stack on launch where supported (AWS EKS, GKE — dual-stack-able; AKS — dual-stack supported in newer regions; Alibaba ACK — IPv6 supported).
- Outbound LLM-provider calls happen over whatever the provider supports (mostly v4, some v6).
- IPv6-only workloads acceptable at customer request (Enterprise) but not the default.

---

## 8. Firewalls / security groups

Codified per cloud as Terraform; no console-edited rules. Common rule set:

- Inbound 443/tcp from anywhere → ingress LB.
- Inbound 7881/tcp + UDP RTP range → voice ingress (only for voice-enabled regions).
- Inbound 4222/tcp from peering only → NATS (never from public internet).
- Inbound 5432/tcp, 6379/tcp, 6333/tcp → only from same-VPC subnets.
- Outbound 443/tcp → only to the egress-gw (other pods cannot egress directly).
- Outbound to RFC1918 → only to within-cluster ranges.

---

## 9. Voice-specific networking

Voice is the most latency-sensitive surface and gets a separate path:

- LiveKit SFU per voice region, sized for current p50 of 700 ms total.
- WebRTC ports: TCP 7881 + UDP 50000–60000 (ephemeral RTP).
- Ingress via Cloudflare Spectrum (TCP) and direct UDP (Cloudflare doesn't proxy UDP for voice).
- RTP encryption: SRTP/DTLS-SRTP.
- STT/TTS providers reached via the egress-gw with explicit allow-list.

Cross-region voice: caller routed to the nearest voice POP; agent runtime in the workspace's pinned region; cross-region link is mTLS via the service mesh. Adds ~50 ms but acceptable for the < 0.1% of cross-region calls.

---

## 10. Connectivity to customer-supplied MCP servers

A customer's MCP server can be:

1. **Public-internet HTTPS** with API-key auth. Egress-gw allow-list adds the customer's MCP host.
2. **Private** via PrivateLink / Private Service Connect / equivalent. Customer publishes; Loop's egress-gw consumes it.
3. **Co-located in the customer's VPC** (hybrid deployment). Loop runtime calls within the same VPC.

In all three cases, the runtime treats the MCP server as untrusted: timeouts, schema validation, retry budgets, sandbox if Loop runs the server.

---

## 11. DDoS posture

| Layer | Mitigation |
|-------|-----------|
| Edge | Cloudflare DDoS, WAF, bot management, Turnstile challenge |
| Per-IP | Rate limit (redis sliding window) at cp-api |
| Per-key | Rate limit per API key |
| Per-tenant | Cost cap + agent invocation cap |
| Internal | Pod-level connection limits via Envoy |

---

## 12. References

- `architecture/CLOUD_PORTABILITY.md` §3 (service mapping including DNS).
- `architecture/AUTH_FLOWS.md` §5 (mTLS).
- `engineering/SECURITY.md` §1 (trust boundaries).
- `engineering/RUNBOOKS.md` RB-005 (provider 5xx storm — egress impact).
