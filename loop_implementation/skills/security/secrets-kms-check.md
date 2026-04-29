---
name: secrets-kms-check
description: Use whenever code touches secrets, encryption keys, or KMS — reading channel credentials, encrypting customer data, rotating keys.
when_to_use: |
  - Adding code that reads a secret from Vault.
  - Adding code that encrypts/decrypts payload using a workspace KMS data key.
  - Adding a customer-supplied secret (channel token, BYO LLM key).
  - Touching the BYOK (customer-supplied KMS) flow.
required_reading:
  - engineering/SECURITY.md            # §3 secrets, §4 encryption
  - architecture/CLOUD_PORTABILITY.md  # §4.2 KMS interface, §4.3 SecretsBackend
  - engineering/ENV_REFERENCE.md       # §9 KMS / Secrets
applies_to: security
owner: Sec/Compliance Eng
last_reviewed: 2026-04-29
---

# Secrets & KMS check

## Trigger

Any code path that reads a secret, calls a KMS, or stores customer-encrypted data.

## Required reading

1. `engineering/SECURITY.md` §3 (inventory + storage rules) and §4 (encryption).
2. `architecture/CLOUD_PORTABILITY.md` §4.2 (`KMS` Protocol) and §4.3 (`SecretsBackend` Protocol).

## Steps

1. **Never** reference a cloud SDK directly (`boto3.client('kms', ...)`). Always go through the abstractions:
   ```python
   kms: KMS = ctx.kms                     # injected
   ciphertext = await kms.encrypt(key_ref=ws.tenant_kms_key_id, plaintext=...)
   ```
2. **Never** put a secret in: env vars in containers, application logs, source code, IaC committed to git, Postgres (except hashed API keys), or Redis. Vault only.
3. **Per-bot scoping** for customer credentials: secret stored at `vault/data/workspace/{ws_id}/agent/{agent_id}/{name}`, referenced by `agent_secrets.vault_path` (`data/SCHEMA.md` §2.1).
4. **Envelope encryption** for customer data:
   - Data key encrypts the payload.
   - Workspace KMS key encrypts the data key.
   - Both stored alongside the ciphertext.
   - Destroying the workspace KMS key cryptographically invalidates all encrypted data — feature, not bug.
5. **Rotation:**
   - Infra secrets: automatic ≤ 90 days.
   - Customer secrets: warn at 90 days, never auto-rotate without consent.
   - Master KMS keys: yearly with 90-day overlap.
6. **Logs / errors:** secrets never appear. Pre-commit detect-secrets scans must pass. Structured logger redacts via patterns from `engineering/SECURITY.md` §7.3.
7. **Tests:**
   - Unit: secret read/write goes through the right interface; cloud SDK direct import is forbidden by a static check.
   - Integration: round-trip via Vault dev mode in docker-compose.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] No cloud SDK imported in `packages/runtime/`, `packages/gateway/`, `packages/sdk-py/`, or `packages/channels/`.
- [ ] Secret access via `SecretsBackend`.
- [ ] Encryption via `KMS` interface with per-workspace data key.
- [ ] Per-bot scoping (not workspace-wide).
- [ ] Pre-commit detect-secrets passes.
- [ ] No secrets in tests/fixtures (use Vault dev tokens or mock).
- [ ] Rotation policy followed.

## Anti-patterns

- ❌ Reading credentials from environment variables in production containers.
- ❌ Using `boto3` / `azure-keyvault` / `google-cloud-kms` directly in the runtime.
- ❌ Logging raw API keys or secret values.
- ❌ Workspace-wide channel credentials (use per-bot).
- ❌ Storing secrets in Postgres.

## Related skills

- `security/update-threat-model.md`, `coding/implement-channel-adapter.md`, `architecture/cloud-portability-check.md`.

## References

- `engineering/SECURITY.md` §3–§4.
- `architecture/CLOUD_PORTABILITY.md` §4.2–§4.3.
- `engineering/ENV_REFERENCE.md` §9.
