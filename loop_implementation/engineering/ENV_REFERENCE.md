# Loop — Environment Variable Reference

**Status:** v0.1  •  **Owner:** Founding Eng #2 (Infra)
**Companion:** `engineering/HANDBOOK.md` §1.

Single source of truth for every environment variable used by Loop. Every service reads only its own subset via `pydantic_settings.BaseSettings`. PRs that add an env var must update this file in the same change.

Naming convention: `LOOP_<DOMAIN>_<NAME>` (e.g. `LOOP_RUNTIME_PORT`). Avoid `_` ambiguity by prefixing every var; never use bare `DEBUG`.

---

## 0. As-shipped — env vars actually present in the codebase today

> The sections below describe the **target** env-var surface. This section is
> the live truth as of the Sprint-0 cut-off (S001–S014). The
> `docs-with-code` CI gate (`tools/check_docs_with_code.py`) requires this
> section to be updated when any `LOOP_*` literal is added or changed in code.

| Variable | Where it's read | Story |
|----------|------------------|-------|
| `LOOP_ENV` | `packages/observability/loop_observability/config.py` (deployment label) | S009 |
| `LOOP_SERVICE_NAME` | observability `Settings` — OTel `service.name` resource attribute (no default; required) | S009 |
| `LOOP_SERVICE_VERSION` | observability `Settings` — OTel `service.version` resource attribute (default `"0.0.0"`) | S009 |
| `LOOP_OTEL_ENDPOINT` | observability `Settings` — OTLP HTTP endpoint when `LOOP_OTEL_EXPORTER=otlp`; ClickHouse HTTP base URL when `LOOP_OTEL_EXPORTER=clickhouse` | S009, S286 |
| `LOOP_OTEL_EXPORTER` | observability `Settings` — exporter selector (`"otlp"` / `"clickhouse"` / `"inmemory"` / `"memory"` / `"none"`); prod defaults to ClickHouse, tests use in-memory | S009, S286 |
| `LOOP_CP_DB_URL` | `packages/control-plane` Alembic `env.py` and `cp-api` settings | S006, S019 |
| `LOOP_RUNTIME_DB_URL` | `packages/data-plane` Alembic `env.py` and runtime settings | S006, S008 |
| `LOOP_GATEWAY_REQUEST_ID_TTL_SECONDS` | `packages/gateway` idempotency cache | S007 |
| `LOOP_DEV_BIND` | `infra/docker-compose.yml` — host bind address for service ports (default `127.0.0.1`) | S003 |
| `LOOP_EGRESS_ALLOWLIST` | `infra/k8s/sandbox/pod-template.yaml` — comma-separated CIDR list mounted into Firecracker pods | S014 |
| `LOOP_CP_API_BASE_URL` | `apps/studio/src/lib/cp-api.ts` — runtime CP API URL (server-side; complements `NEXT_PUBLIC_LOOP_API_URL` for browser-side fetches) | S010 |
| `LOOP_DEMO_URL` | `scripts/e2e_web_smoke.py` / `.github/workflows/e2e-web-smoke.yml` — published demo base URL for nightly first-chat smoke | S181 |
| `LOOP_DEMO_CHAT_ENDPOINT` | `scripts/e2e_web_smoke.py` — optional absolute chat endpoint override; defaults to `${LOOP_DEMO_URL}/api/chat` | S181 |
| `LOOP_DEMO_QUESTION` | `scripts/e2e_web_smoke.py` — visitor question posted by the nightly demo smoke (default `"What is Loop?"`) | S181 |
| `LOOP_DEMO_EXPECTED_ANSWER` | `scripts/e2e_web_smoke.py` — required golden answer fragment asserted in the demo response | S181 |
| `LOOP_DEMO_TIMEOUT_SECONDS` | `scripts/e2e_web_smoke.py` — HTTP timeout for the published demo smoke (default `20`) | S181 |
| `LOOP_DEMO_TOKEN` | `scripts/e2e_web_smoke.py` — optional bearer token for protected demo environments | S181 |
| `LOOP_CLOUD` | `.github/workflows/cross-cloud-smoke.yml` — cloud label injected into Helm smoke pods for the AWS/Azure/GCP nightly matrix | S780 |
| `LOOP_ONCALL_WEBHOOK_URL` | `.github/workflows/cross-cloud-smoke.yml`, `.github/workflows/turn-latency-k6.yml` — GitHub Actions secret receiving JSON page payloads when smoke or performance gates fail | S780, S840 |
| `LOOP_TURN_LATENCY_BASE_URL` | `scripts/k6_turn_latency.js` / `.github/workflows/turn-latency-k6.yml` — base URL for the S840 text-turn k6 latency gate | S840 |

> Note — **`LOOP_WORKSPACE_ID` is not an env var.** It is a Postgres
> session-scoped setting (`SET LOCAL loop.workspace_id = '<uuid>'`) used by
> the row-level-security policy in cp_0001 / dp_0001. Don't expose it as an
> environment variable in any service config — that would defeat tenant
> isolation.

### 0.1 Adding a new `LOOP_*` variable

The flow in §13 still applies. Additionally, the `docs-with-code` CI gate
greps for new `LOOP_[A-Z][A-Z0-9_]+` literals introduced under `packages/`,
`apps/`, `cli/`, `infra/`, `tools/` and **fails the PR** if this file is not
also touched. Update this section (table 0) at the same time, even if you also
update §1–§11.

---

## 1. Common (every service)

| Variable | Default | Type | Description |
|----------|---------|------|-------------|
| `LOOP_ENV` | `dev` | enum: `dev`, `staging`, `prod`, `test` | Deployment environment. Affects defaults for logging, telemetry, allowed origins. |
| `LOOP_VERSION` | (build-time) | string | Service version, set at build time from git tag. |
| `LOOP_REGION` | `na-east` | abstract region | Used for region-pinning workspace data; resolves via `regions.yaml`. |
| `LOOP_LOG_LEVEL` | `INFO` | enum: `DEBUG`, `INFO`, `WARN`, `ERROR`, `CRITICAL` | structlog level. `DEBUG` only in dev/test. |
| `LOOP_LOG_FORMAT` | `json` | enum: `json`, `console` | `console` only in dev. |
| `LOOP_OTEL_ENDPOINT` | `http://otel-collector:4317` | URL | OTLP gRPC endpoint. |
| `LOOP_OTEL_SAMPLING_RATE` | `1.0` | float 0–1 | Trace sampling. Drop to 0.1 in prod for cost. |
| `LOOP_SENTRY_DSN` | (none) | URL | If set, errors go to Sentry. Optional in dev. |
| `LOOP_OBSERVABILITY_ENABLED` | `true` | bool | Master switch — disable in tight unit tests only. |
| `LOOP_REQUEST_TIMEOUT_SECONDS` | `60` | int | Default outbound HTTP timeout. |

## 2. Runtime (`dp-runtime`)

| Variable | Default | Type | Description |
|----------|---------|------|-------------|
| `LOOP_RUNTIME_PORT` | `8000` | int | HTTP listen port. |
| `LOOP_RUNTIME_WORKERS` | `2` | int | Uvicorn worker count per pod. |
| `LOOP_RUNTIME_DB_URL` | (required) | postgres URL | Data-plane Postgres. |
| `LOOP_RUNTIME_REDIS_URL` | (required) | redis URL | Session memory + LLM cache. |
| `LOOP_RUNTIME_QDRANT_URL` | (required) | URL | Vector store. |
| `LOOP_RUNTIME_NATS_URL` | (required) | NATS URL | Event bus. |
| `LOOP_RUNTIME_GATEWAY_URL` | `http://dp-gateway:8001` | URL | LLM gateway. |
| `LOOP_RUNTIME_TOOL_HOST_URL` | `http://dp-tool-host:8002` | URL | MCP tool dispatcher. |
| `LOOP_RUNTIME_KB_URL` | `http://dp-kb-engine:8003` | URL | KB retrieval service. |
| `LOOP_RUNTIME_OBJECT_STORE_BUCKET` | `loop-runtime` | string | Code artifact bucket. |
| `LOOP_RUNTIME_MAX_ITERATIONS` | `10` | int | Hard cap on reasoning loop iterations per turn. |
| `LOOP_RUNTIME_MAX_COST_USD` | `0.50` | decimal | Hard cap on per-turn LLM+tool cost. |
| `LOOP_RUNTIME_MAX_RUNTIME_SECONDS` | `300` | int | Hard cap on per-turn wall time. |
| `LOOP_RUNTIME_MAX_TOOL_CALLS_PER_TURN` | `20` | int | Hard cap. |
| `LOOP_RUNTIME_MAX_MESSAGE_BYTES` | `16777216` | int | 16 MB; reject above. |
| `LOOP_RUNTIME_MEMORY_TTL_SESSION_SECONDS` | `86400` | int | 24h default; per-agent override possible. |
| `LOOP_RUNTIME_WARM_POOL_SIZE` | `5` | int | Pre-spawned agent contexts per pod. |
| `LOOP_TOOL_HOST_RUNC_LIVE` | `0` | bool (`0`/`1`) | Opt-in flag for `RuncSandbox` integration tests; live tests skip unless set to `1` and `runc` is on PATH (S916). |
| `LOOP_TOOL_HOST_TEST_ROOTFS` | (none) | path | Pre-staged OCI rootfs used by the `RuncSandbox` live integration tests (S916). |

## 3. Gateway (`dp-gateway`)

| Variable | Default | Type | Description |
|----------|---------|------|-------------|
| `LOOP_GATEWAY_PORT` | `8001` | int | HTTP listen port. |
| `LOOP_GATEWAY_OPENAI_API_KEY` | (per workspace via Vault) | string | Default key if no workspace key set. |
| `LOOP_GATEWAY_ANTHROPIC_API_KEY` | (per workspace via Vault) | string | Same. |
| `LOOP_GATEWAY_HTTP_TIMEOUT_SECONDS` | `30` | float | S906 real provider stream timeout for OpenAI/Anthropic `httpx` calls. |
| `LOOP_GATEWAY_HTTP_MAX_RETRIES` | `2` | int | S906 retry count for provider 429/5xx/timeout failures. |
| `LOOP_GATEWAY_LIVE_TESTS` | (unset) | bool | Set to `1` to run live OpenAI/Anthropic smoke tests instead of cassette replay. |
| `LOOP_GATEWAY_BEDROCK_PROFILE` | (none) | string | If using AWS Bedrock. |
| `LOOP_GATEWAY_VLLM_URL` | (none) | URL | Self-hosted vLLM endpoint. |
| `LOOP_GATEWAY_CACHE_TTL_SECONDS` | `604800` | int | 7 days for semantic cache. |
| `LOOP_GATEWAY_CACHE_SIM_THRESHOLD` | `0.97` | float | Cosine sim threshold for cache hit. |
| `LOOP_GATEWAY_TOKEN_MARKUP` | `0.05` | float | Disclosed margin (5%). |
| `LOOP_GATEWAY_REQUEST_ID_TTL_SECONDS` | `600` | int | 10 min idempotency window. |
| `LOOP_GATEWAY_FALLBACK_MODEL` | `claude-haiku-4-5` | string | Used by graceful-degrade. |

## 4. Channel adapters

Each channel adapter has its own subset; common shape:

```
LOOP_CHANNEL_<NAME>_PORT
LOOP_CHANNEL_<NAME>_WEBHOOK_SECRET   # HMAC for incoming
LOOP_CHANNEL_<NAME>_ALLOWED_ORIGINS
LOOP_CHANNEL_<NAME>_RATE_LIMIT_RPS
```

WhatsApp:
- `LOOP_CHANNEL_WA_VERIFY_TOKEN`, `LOOP_CHANNEL_WA_APP_SECRET`, `LOOP_CHANNEL_WA_PHONE_ID`.

Slack:
- `LOOP_CHANNEL_SLACK_SIGNING_SECRET`, `LOOP_CHANNEL_SLACK_BOT_TOKEN`.

Twilio (SMS / voice):
- `LOOP_CHANNEL_TWILIO_AUTH_TOKEN`, `LOOP_CHANNEL_TWILIO_ACCOUNT_SID`, `LOOP_CHANNEL_TWILIO_VOICE_API_KEY`, `LOOP_CHANNEL_TWILIO_VOICE_API_SECRET`.

LiveKit (voice):
- `LOOP_CHANNEL_VOICE_LIVEKIT_URL`, `LOOP_CHANNEL_VOICE_LIVEKIT_API_KEY`, `LOOP_CHANNEL_VOICE_LIVEKIT_API_SECRET`, `LOOP_CHANNEL_VOICE_DEEPGRAM_API_KEY`, `LOOP_CHANNEL_VOICE_TTS_PROVIDER` (`elevenlabs|cartesia|piper`), `LOOP_CHANNEL_VOICE_ELEVENLABS_API_KEY`.

Voice provider clients:
- `LOOP_VOICE_WS_OPEN_TIMEOUT_SECONDS` (default `10`) caps Deepgram / ElevenLabs websocket handshakes.
- `LOOP_VOICE_LIVE_TESTS=1` enables live Deepgram + ElevenLabs quota-spending tests.
- `LOOP_VOICE_DEEPGRAM_API_KEY`, `LOOP_VOICE_ELEVENLABS_API_KEY`, `LOOP_VOICE_ELEVENLABS_VOICE_ID` are used by the opt-in live voice test. Production may continue to source provider keys from the channel-scoped `LOOP_CHANNEL_VOICE_*` variables or Vault-backed config.

## 5. Control plane (`cp-api`, `cp-billing`, `cp-deploy-controller`)

| Variable | Default | Description |
|----------|---------|-------------|
| `LOOP_CP_DB_URL` | (required) | Control-plane Postgres. |
| `LOOP_CP_REDIS_URL` | (required) | Sessions + rate limits. |
| `LOOP_CP_CLICKHOUSE_URL` | (required) | Trace + cost analytics. |
| `LOOP_CP_AUTH_PROVIDER` | `auth0` | enum: `auth0`, `kratos`. |
| `LOOP_CP_AUTH0_DOMAIN` | (Auth0) | required if `auth_provider=auth0`. |
| `LOOP_CP_AUTH0_AUDIENCE` | (Auth0) | required if `auth_provider=auth0`. |
| `LOOP_CP_KRATOS_URL` | (Kratos) | required if `auth_provider=kratos`. |
| `LOOP_CP_PASETO_PRIVATE_KEY_PATH` | `/secrets/paseto/key.pem` | path | Token signing key. |
| `LOOP_CP_STRIPE_SECRET_KEY` | (required for billing) | string | |
| `LOOP_CP_STRIPE_WEBHOOK_SECRET` | (required) | string | |
| `LOOP_CP_DEPLOY_K8S_KUBECONFIG_PATH` | `/secrets/kubeconfig` | path | Per-region cluster config. |
| `LOOP_CP_DEPLOY_IMAGE_REGISTRY` | (required) | OCI registry URL | |

## 6. KB engine (`dp-kb-engine`)

| Variable | Default | Description |
|----------|---------|-------------|
| `LOOP_KB_PORT` | `8003` | |
| `LOOP_KB_QDRANT_URL` | (inherits) | |
| `LOOP_KB_EMBEDDING_PROVIDER` | `openai` | enum: `openai`, `voyage`, `cohere`, `bge`, `nv-embed`. |
| `LOOP_KB_EMBEDDING_MODEL` | `text-embedding-3-large` | string | |
| `LOOP_KB_VECTOR_DIM` | `3072` | int | Must match the embedding model. |
| `LOOP_KB_FIRECRAWL_API_KEY` | (none) | Optional; for web crawl. |
| `LOOP_KB_CHUNK_DEFAULT` | `semantic_boundary` | enum | Per-bot override possible. |

## 7. Eval harness (`dp-eval-runner`, `cp-eval-orchestrator`)

| Variable | Default | Description |
|----------|---------|-------------|
| `LOOP_EVAL_HARNESS_ENABLED` | `true` | Master switch. |
| `LOOP_EVAL_CASSETTE_DIR` | `/var/loop/cassettes` | path | Read-only mount in prod. |
| `LOOP_EVAL_CASSETTE_REFRESH_DAYS` | `30` | int | Warning at this age; 90 days = error. |
| `LOOP_EVAL_LLM_JUDGE_MODEL` | `claude-sonnet-4-7` | string | |
| `LOOP_EVAL_LLM_JUDGE_RUNS` | `3` | int | Average across N. |
| `LOOP_EVAL_REGRESSION_THRESHOLD` | `0.05` | float | Block deploy if score regresses by > this fraction. |

## 8. Object store (cloud-agnostic)

| Variable | Default | Description |
|----------|---------|-------------|
| `LOOP_OBJSTORE_BACKEND` | `s3` | enum: `s3`, `azure_blob`, `gcs`, `oss`, `minio`. |
| `LOOP_OBJSTORE_ENDPOINT` | (none) | Override S3 endpoint for non-AWS. |
| `LOOP_OBJSTORE_BUCKET` | (required) | Bucket name. |
| `LOOP_OBJSTORE_REGION` | `auto` | Cloud-specific region. |
| `LOOP_OBJSTORE_ACCESS_KEY_ID` | (vault) | |
| `LOOP_OBJSTORE_SECRET_ACCESS_KEY` | (vault) | |

## 9. KMS / Secrets

| Variable | Default | Description |
|----------|---------|-------------|
| `LOOP_KMS_BACKEND` | `vault` | enum: `vault`, `aws_kms`, `azure_key_vault`, `gcp_kms`, `alicloud_kms`. |
| `LOOP_KMS_KEY_REF` | (per workspace) | Resolved at runtime from workspace. |
| `LOOP_VAULT_ADDR` | `https://vault.svc:8200` | URL | Always set even if backend is cloud. |
| `LOOP_VAULT_ROLE` | `loop-runtime` | string | Workload identity. |
| `LOOP_VAULT_NAMESPACE` | (none) | Vault Enterprise only. |
| `LOOP_SECRETS_BACKEND` | `vault` | Mirror of KMS_BACKEND for secrets-mgr usage. |

## 10. Studio (`apps/studio`)

| Variable | Default | Description |
|----------|---------|-------------|
| `LOOP_STUDIO_PORT` | `3000` | Next.js port. |
| `NEXT_PUBLIC_LOOP_API_URL` | `http://localhost:8080` | cp-api URL exposed to browser. |
| `NEXT_PUBLIC_LOOP_OAUTH_CLIENT_ID` | (Auth0) | Public OIDC client ID. |
| `NEXT_PUBLIC_LOOP_DEFAULT_REGION` | `na-east` | |
| `LOOP_STUDIO_SESSION_SECRET` | (required, ≥32B) | Cookie signing. |

### 10.1 Published demo smoke (`scripts/e2e_web_smoke.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `LOOP_DEMO_URL` | (required) | Published demo base URL hit by the nightly first-chat smoke. |
| `LOOP_DEMO_CHAT_ENDPOINT` | `${LOOP_DEMO_URL}/api/chat` | Absolute endpoint override if the demo chat route differs. |
| `LOOP_DEMO_QUESTION` | `What is Loop?` | Visitor question sent to the demo chat endpoint. |
| `LOOP_DEMO_EXPECTED_ANSWER` | (required) | Case-insensitive answer fragment the response must include. |
| `LOOP_DEMO_TIMEOUT_SECONDS` | `20` | HTTP timeout for the smoke request. |
| `LOOP_DEMO_TOKEN` | (none) | Optional bearer token when the published demo is protected. |

### 10.2 Cross-cloud smoke (`.github/workflows/cross-cloud-smoke.yml`)

| Variable | Default | Description |
|----------|---------|-------------|
| `LOOP_CLOUD` | matrix value | Cloud label injected into the Helm smoke deployment (`aws`, `azure`, `gcp`). |
| `LOOP_ONCALL_WEBHOOK_URL` | (required GitHub Actions secret) | Webhook that pages the primary on-call with the failed cloud/region and Actions run URL. |

### 10.3 Turn-latency k6 gate (`scripts/k6_turn_latency.js`)

| Variable | Default | Description |
|----------|---------|-------------|
| `LOOP_TURN_LATENCY_BASE_URL` | `http://127.0.0.1:18081` | Runtime base URL used by the nightly text-turn k6 latency gate. |
| `LOOP_ONCALL_WEBHOOK_URL` | (required GitHub Actions secret) | Webhook that pages the primary on-call when the k6 p95 latency threshold fails. |

## 11. CLI (`loop`)

| Variable | Default | Description |
|----------|---------|-------------|
| `LOOP_API_URL` | `https://api.loop.example/v1` | Override for self-host. |
| `LOOP_TOKEN` | (none) | API token; alternative to interactive login. |
| `LOOP_PROFILE` | `default` | Named profile in `~/.loop/profiles.yaml`. |
| `LOOP_NO_TELEMETRY` | `false` | Set to `true` to disable anonymous CLI telemetry. |

---

## 12. Loading & precedence

1. CLI flag (highest).
2. Environment variable.
3. `.env.<env>` file (gitignored, dev only).
4. Helm values / Kustomize patch (cluster).
5. Pydantic Settings default (lowest).

In production, every value comes from Helm + Vault. `.env.*` files are dev-only and never deployed.

---

## 13. Adding a new env var (process)

1. Add to the appropriate Pydantic `Settings` class with a typed default.
2. Add a row to this file.
3. Add the var to `scaffolding/.env.example` if it has a sensible dev default.
4. If it's a secret, add a Vault path mapping in `infra/helm/loop/values.yaml`.
5. Mention it in the PR description and update `engineering/HANDBOOK.md` if conventions change.

---

## 14. Forbidden

- `DEBUG=1`-style truthy strings — always `LOOP_LOG_LEVEL=DEBUG`.
- Service-specific env vars without the `LOOP_<SERVICE>_` prefix.
- Reading `os.environ.get(...)` ad-hoc — always go through Pydantic Settings.
- Secrets in env vars in containers — use Vault sidecar / projected files.
