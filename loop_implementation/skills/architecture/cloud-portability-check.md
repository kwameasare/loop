---
name: cloud-portability-check
description: Use whenever a change touches cloud-native code (object storage, KMS, secrets, identity, DNS, edge, email, container registry).
when_to_use: |
  - Adding code that calls an SDK that ships per-cloud (boto3, azure-*, google-cloud-*, alicloud-*).
  - Adding infra Terraform.
  - Adding a Helm value that selects a cloud-specific backend.
  - Adding a runbook step that's cloud-specific.
required_reading:
  - architecture/CLOUD_PORTABILITY.md
  - adrs/README.md   # ADR-016
applies_to: architecture
owner: Founding Eng #2 (Infra)
last_reviewed: 2026-04-29
---

# Cloud portability check

## Trigger

Any cloud-touching code path.

## Required reading

`architecture/CLOUD_PORTABILITY.md` end-to-end; ADR-016.

## Steps

1. **Code constraint** — never import a cloud SDK in: `packages/runtime/`, `packages/gateway/`, `packages/sdk-py/`, `packages/channels/` (except channel-internal infra modules with explicit ADR).
   ```bash
   # static check this PR
   ! grep -rn "import boto3\|import azure\.\|from google\.cloud\|import alibabacloud" \
       packages/runtime packages/gateway packages/sdk-py packages/channels
   ```
2. **Allowed places:** `packages/observability/`, `apps/control-plane/` may use cloud SDKs, but only *behind* a `KMS`/`ObjectStore`/`SecretsBackend`/`EmailSender` interface from `architecture/CLOUD_PORTABILITY.md` §4.
3. **Two-cloud rule.** Every primitive has at least two implementations (one cloud-native, one OSS). Validate via the CI cloud matrix:
   ```yaml
   matrix:
     cloud: [aws, gcp, azure, self_host_minio]
   ```
4. **Forbidden services** — see ADR-016 §"Forbidden services". Adding any of: DynamoDB, Cosmos DB, Spanner, MNS, Step Functions, Lambda-as-primary-compute requires a successor ADR.
5. **Helm values:** every cloud-specific knob lives in `infra/helm/loop/values.yaml` under `global.cloud`, `global.kms`, `global.objectStore`, `global.secrets`, etc.
6. **Region naming:** abstract names only (`na-east`, `eu-west`) in code. Concrete regions live only in `infra/terraform/regions.yaml`.
7. **Tests:**
   - Unit: ensure the abstraction protocol is honored (no direct cloud-SDK call).
   - Integration: run on at least two backends (one cloud-native, one OSS).
8. **Docs:** if the change introduces a new cloud-touching primitive, update `architecture/CLOUD_PORTABILITY.md` §3 mapping table and §4 interface list.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] No cloud SDK imported in forbidden packages.
- [ ] Abstraction interface used.
- [ ] Two implementations exist + matrix-tested.
- [ ] Helm values added (if applicable).
- [ ] Abstract region naming preserved.
- [ ] CLOUD_PORTABILITY.md updated if new primitive.
- [ ] No forbidden services without successor ADR.

## Anti-patterns

- ❌ "Just for AWS first, we'll port later." It bakes lock-in.
- ❌ Hard-coded `us-east-1`.
- ❌ One implementation only.
- ❌ ARM/CloudFormation/Deployment-Manager templates (Terraform only).

## Related skills

- `architecture/propose-adr.md` (if you must add a forbidden service).
- `security/secrets-kms-check.md`.

## References

- `architecture/CLOUD_PORTABILITY.md`.
- ADR-016.
