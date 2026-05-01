# Loop — Data Model & Schema Reference

**Status:** Draft v0.1
**Owner:** Founding Eng #2 (Infra)
**Companion:** `architecture/ARCHITECTURE.md`

This is the canonical data model for Loop. Every table, collection, and key namespace is defined here. Engineers must update this doc *in the same PR* as any migration.

---

## 0. As-shipped — what actually lives in the database today

> This section is the single source of truth for the **live** schema. Everything
> else in this document is design intent — some of it is shipped, some of it is
> deferred to later migrations. **If sections 0 and 2/3 disagree, section 0 is
> right.** The `docs-with-code` CI gate requires this section to be updated in
> the same PR as any new migration.

### 0.1 Migrations shipped

| Migration | Plane | Story | Tables created |
|-----------|-------|-------|----------------|
| `cp_0001_initial` (`packages/control-plane/.../202604300215_cp_0001_initial.py`) | Control plane | S006 | `workspaces`, `users`, `workspace_members`, `api_keys`, `agent_secrets`, `agents`, `agent_versions` |
| `cp_0003_operator_assignments` (`packages/control-plane/.../202605260400_cp_0003_operator_assignments.py`) | Control plane | S300 | `operator_assignments` |
| `cp_0004_mcp_marketplace` (`packages/control-plane/.../202605010930_cp_0004_mcp_marketplace.py`) | Control plane | S550-S559, S750-S765 | `mcp_servers`, `mcp_server_versions`, `mcp_agent_installs`, `mcp_server_reviews`, `mcp_server_usage` |
| `dp_0001_initial` (`packages/data-plane/.../202604300220_dp_0001_initial.py`) | Data plane | S006 | `conversations`, `turns`, `memory_user`, `memory_bot`, `tool_calls` |

Every customer-data table from these migrations has **row-level security
enabled** under a tenant-isolation policy gated by
`current_setting('loop.workspace_id')::uuid` (ADR-020). Data-plane tables
additionally use `FORCE ROW LEVEL SECURITY` so even the table owner is bound
by the policy. The MCP marketplace global registry tables (`mcp_servers`,
`mcp_server_versions`) are shared catalog tables; tenant-scoped marketplace
state (`mcp_agent_installs`, `mcp_server_reviews`, `mcp_server_usage`) has RLS.

### 0.2 Divergences between as-shipped and the design draft below

The cp_0001/dp_0001 migrations intentionally ship a leaner initial cut. The
following fields described in sections 2/3 are **deferred** — they will be
added in cp_0002 / dp_0002. Until those land, these names do not exist:

| Table | Deferred fields | Tracking story |
|-------|-----------------|----------------|
| `agents` | `name`, `description` (cp_0001 ships `display_name` instead — no separate description column) | cp_0002 |
| `agent_versions` | `version` is `TEXT` (not `INTEGER`); `config_json`, `eval_status`, `eval_run_id`, `deployed_at`, `version_tag` not yet present; deploy state is `promoted_to` with values `'dev','staging','prod','rolled_back'` (not `deploy_state` with `inactive/canary/active/rolled_back`) | cp_0002 |
| `agent_versions` | Artifact location is `artifact_uri` + `artifact_sha256` (not `code_artifact_url` + `code_hash`) | doc-only; will be reconciled in cp_0002 |
| `agent_secrets` | FK is `agent_id` (nullable; secrets can be workspace-wide) — not `agent_version_id`. Field names are `name` / `secret_ref` (not `secret_name` / `vault_path`). Adds `tenant_kms_key TEXT NOT NULL` not in design draft. | cp_0002 |
| `api_keys` | Field is `prefix` (not `key_prefix`); adds `hash BYTEA`, `scopes TEXT[]`, `created_by` not present in the design-draft snippet. | doc-only |
| `deployment_events`, `channel_configs`, `voice_calls`, `eval_runs`, `usage_counters` | Not yet created. | cp_0002+ |
| Data-plane: `kb_documents`, `kb_chunks` (Qdrant-mirror metadata), `feedback`, `escalations` | Not yet created. | dp_0002+ |

### 0.3 Read-this-first when adding a migration

1. Author the migration under `packages/{control,data}-plane/.../migrations/versions/<utc_ts>_<rev>_<slug>.py`.
2. In the **same PR**, update section 0.1 above with the new revision id + tables, and update section 0.2 to remove any divergence the migration closes (or to add new ones).
3. The `docs-with-code` CI gate (`tools/check_docs_with_code.py`) will fail the PR if a `migrations/versions/*.py` file is touched without a `loop_implementation/data/SCHEMA.md` change in the same diff.

---

## 1. Storage map at a glance

| Backend | What lives here | Why |
|---------|-----------------|-----|
| Postgres (control plane) | Workspaces, users, deploys, eval runs, billing | Strong consistency, relational |
| Postgres (data plane) | Conversations, turns, memory, KB metadata | Same as above, per-region |
| Redis | Session memory, cache, rate-limit counters | Fast TTL, ephemeral |
| Qdrant | Vector embeddings (KB chunks, episodic memory) | Purpose-built vector store |
| ClickHouse | Traces, costs, eval results | Columnar analytics at scale |
| S3 (or compat) | Code artifacts, voice recordings, doc originals | Cheap durable blob |
| NATS JetStream | Event log (deliverable streams) | Async + replayable |

---

## 2. Postgres — control plane

### 2.1 Identity & secrets

```sql
CREATE TABLE workspaces (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL UNIQUE,
    plan            TEXT NOT NULL DEFAULT 'hobby'
                      CHECK (plan IN ('hobby','pro','team','enterprise')),
    region          TEXT NOT NULL DEFAULT 'na-east',  -- abstract region; mapped to concrete cloud region by the deploy controller
    tenant_kms_key_id TEXT,                            -- workspace-specific KMS data key ID (Vault path or cloud-native)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX idx_workspaces_slug ON workspaces(slug) WHERE deleted_at IS NULL;

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           CITEXT NOT NULL UNIQUE,
    full_name       TEXT,
    auth_provider   TEXT NOT NULL,           -- 'auth0', 'kratos', 'github'
    auth_subject    TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(auth_provider, auth_subject)
);

CREATE TABLE workspace_members (
    workspace_id    UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('owner','admin','editor','operator','viewer')),
    invited_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, user_id)
);

CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    hashed_key      TEXT NOT NULL,            -- argon2id of the key material
    key_prefix      TEXT NOT NULL,            -- first 8 chars for audit log visibility
    scopes          TEXT[] NOT NULL,          -- ['agents:deploy','traces:read',...]
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at    TIMESTAMPTZ,
    revoked_at      TIMESTAMPTZ
);
CREATE INDEX idx_api_keys_workspace ON api_keys(workspace_id) WHERE revoked_at IS NULL;

CREATE TABLE agent_secrets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_version_id UUID NOT NULL REFERENCES agent_versions(id) ON DELETE CASCADE,
    secret_name     TEXT NOT NULL,             -- 'stripe_key', 'anthropic_api_key', etc.
    vault_path      TEXT NOT NULL,             -- vault/data/workspace/{ws_id}/agent/{agent_id}/{secret_name}
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    rotated_at      TIMESTAMPTZ,
    UNIQUE(agent_version_id, secret_name)
);
CREATE INDEX idx_agent_secrets_version ON agent_secrets(agent_version_id);
```

### 2.2 Agents (registration metadata; runtime data lives in the data plane)

```sql
CREATE TABLE agents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL,
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived_at     TIMESTAMPTZ,
    UNIQUE(workspace_id, slug)
);

CREATE TABLE agent_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    version         INTEGER NOT NULL,
    code_artifact_url   TEXT NOT NULL,            -- s3://...
    code_hash       TEXT NOT NULL,                -- sha256
    config_json     JSONB NOT NULL,               -- {model, max_iterations, ...}
    eval_status     TEXT NOT NULL DEFAULT 'pending'
                      CHECK (eval_status IN ('pending','running','passed','failed','skipped')),
    eval_run_id     UUID,
    deployed_at     TIMESTAMPTZ,
    deploy_state    TEXT NOT NULL DEFAULT 'inactive'
                      CHECK (deploy_state IN ('inactive','canary','active','rolled_back')),
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    version_tag     INTEGER NOT NULL DEFAULT 0,  -- for optimistic locking
    UNIQUE(agent_id, version)
);
CREATE INDEX idx_agent_versions_active ON agent_versions(agent_id) WHERE deploy_state = 'active';

CREATE TABLE deployment_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    agent_version_id UUID NOT NULL REFERENCES agent_versions(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL CHECK (event_type IN ('canary_started','canary_progressed','promoted','rolled_back')),
    canary_percent  INTEGER,
    previous_state  TEXT,                       -- state before this event
    new_state       TEXT,                       -- state after this event
    triggered_by    TEXT,                       -- 'automated' or reason
    metadata_json   JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_deployment_events_version ON deployment_events(agent_version_id, created_at DESC);

CREATE TABLE channel_configs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    channel_type    TEXT NOT NULL,
    config_json     JSONB NOT NULL,
    secrets_ref     TEXT NOT NULL,                -- vault / secrets-mgr ref
    enabled         BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(agent_id, channel_type)
);

CREATE TABLE voice_calls (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    call_id         TEXT NOT NULL UNIQUE,          -- livkit/twilio call ID
    participant_id  TEXT,                          -- remote participant ID
    duration_seconds INTEGER,
    audio_url       TEXT,                          -- s3://... path if recording enabled
    recording_consent BOOLEAN,
    vad_events      JSONB,                         -- [{ts, type:'speech'|'silence'}]
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at        TIMESTAMPTZ
);
CREATE INDEX idx_voice_calls_conv ON voice_calls(conversation_id);

CREATE TABLE feature_flags (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID REFERENCES workspaces(id) ON DELETE CASCADE,  -- NULL = global flag
    agent_id        UUID REFERENCES agents(id) ON DELETE CASCADE,      -- NULL = workspace-wide
    flag_name       TEXT NOT NULL,
    flag_value      TEXT NOT NULL,                 -- 'on','off','50','true', etc.
    effective_date  TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ,
    metadata_json   JSONB NOT NULL DEFAULT '{}',  -- {canary_percent, rollback_trigger, ...}
    UNIQUE(workspace_id, agent_id, flag_name, effective_date)
);
CREATE INDEX idx_flags_agent ON feature_flags(agent_id, flag_name) WHERE expires_at IS NULL;
```

### 2.2a Audit & compliance

```sql
CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    actor_user_id   UUID REFERENCES users(id),
    action          TEXT NOT NULL,             -- 'api_key:create', 'agent:deploy', 'hitl:takeover', 'dsar:request'
    resource_type   TEXT NOT NULL,             -- 'agent', 'workspace', 'api_key', 'secret', etc.
    resource_id     UUID,
    before_state    JSONB,                     -- snapshot before change
    after_state     JSONB,                     -- snapshot after change
    client_ip       INET,
    user_agent      TEXT,
    request_id      TEXT,
    previous_hash   TEXT,                      -- SHA-256 hash of previous entry for chain validation
    entry_hash      TEXT,                      -- SHA-256 hash of this entry (for immutability audit)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_workspace_action ON audit_log(workspace_id, action, created_at DESC);
CREATE INDEX idx_audit_resource ON audit_log(workspace_id, resource_type, resource_id);
CREATE INDEX idx_audit_actor ON audit_log(actor_user_id, created_at DESC);

CREATE TABLE data_export_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    requester_user_id UUID NOT NULL REFERENCES users(id),
    request_type    TEXT NOT NULL CHECK (request_type IN ('dsar','backup','full_export')),
    end_user_id     TEXT,                      -- scoped to one end-user if DSAR, NULL for full export
    status          TEXT NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending','processing','ready','expired','cancelled')),
    output_s3_path  TEXT,                      -- s3://loop-{region}-prod/exports/{ws_id}/{export_id}.tar.zst
    size_bytes      BIGINT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL,
    downloaded_at   TIMESTAMPTZ
);
CREATE INDEX idx_export_requests_status ON data_export_requests(workspace_id, status);

CREATE TABLE subprocessor_list (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    processor_name  TEXT NOT NULL,             -- 'OpenAI', 'Anthropic', 'Stripe', 'Datadog'
    processor_type  TEXT NOT NULL,             -- 'llm_provider', 'billing', 'observability', 'communication'
    processor_url   TEXT,
    data_processed  TEXT[],                    -- ['conversation_content', 'metadata', 'logs']
    jurisdiction    TEXT,                      -- 'US', 'EU', 'SG', etc.
    dpa_signed_at   TIMESTAMPTZ,
    is_approved     BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(workspace_id, processor_name)
);
```

### 2.3 Tools / MCP & KB registration

```sql
CREATE TABLE mcp_servers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    source_url      TEXT NOT NULL,                -- pkg://, github://, https://, oci://
    version         TEXT NOT NULL,
    install_status  TEXT NOT NULL DEFAULT 'pending'
                      CHECK (install_status IN ('pending','installed','failed','disabled')),
    manifest_json   JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(workspace_id, name)
);

CREATE TABLE agent_tool_grants (
    agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    mcp_server_id   UUID NOT NULL REFERENCES mcp_servers(id) ON DELETE CASCADE,
    allowed_tools   TEXT[] NOT NULL,              -- subset of manifest tools
    PRIMARY KEY (agent_id, mcp_server_id)
);

CREATE TABLE knowledge_bases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    embedding_model TEXT NOT NULL DEFAULT 'openai:text-embedding-3-large',
    vector_dim      INTEGER NOT NULL DEFAULT 3072,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE agent_kb_grants (
    agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    kb_id           UUID NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    scope           TEXT NOT NULL DEFAULT 'read',
    PRIMARY KEY (agent_id, kb_id)
);

CREATE TABLE kb_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kb_id           UUID NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    source_uri      TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    title           TEXT,
    metadata_json   JSONB NOT NULL DEFAULT '{}',
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    status          TEXT NOT NULL DEFAULT 'indexed'
                      CHECK (status IN ('queued','indexing','indexed','failed'))
);
CREATE INDEX idx_kb_docs_kb ON kb_documents(kb_id);
```

### 2.4 Evals

```sql
CREATE TABLE eval_suites (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    repo_path       TEXT,                         -- e.g. tests/evals/support
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(workspace_id, name)
);

CREATE TABLE eval_cases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_id        UUID NOT NULL REFERENCES eval_suites(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    input_json      JSONB NOT NULL,
    expected_json   JSONB NOT NULL,
    scorers_json    JSONB NOT NULL,               -- list of scorer configs
    tags            TEXT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE eval_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_id        UUID NOT NULL REFERENCES eval_suites(id) ON DELETE CASCADE,
    agent_version_id UUID NOT NULL REFERENCES agent_versions(id) ON DELETE CASCADE,
    baseline_version_id UUID REFERENCES agent_versions(id),
    status          TEXT NOT NULL DEFAULT 'queued'
                      CHECK (status IN ('queued','running','passed','failed','cancelled')),
    started_at      TIMESTAMPTZ,
    ended_at        TIMESTAMPTZ,
    summary_json    JSONB
);

CREATE TABLE eval_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
    case_id         UUID NOT NULL REFERENCES eval_cases(id) ON DELETE CASCADE,
    score           DOUBLE PRECISION,
    passed          BOOLEAN,
    regressed_from_baseline BOOLEAN,
    traces_url      TEXT,
    diagnostics_json JSONB
);
CREATE INDEX idx_eval_results_run ON eval_results(run_id);
```

### 2.5 Billing & budgets

```sql
CREATE TABLE costs_daily (
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    llm_input_tokens     BIGINT NOT NULL DEFAULT 0,
    llm_output_tokens    BIGINT NOT NULL DEFAULT 0,
    llm_usd              NUMERIC(12,4) NOT NULL DEFAULT 0,
    agent_seconds        BIGINT NOT NULL DEFAULT 0,
    compute_usd          NUMERIC(12,4) NOT NULL DEFAULT 0,
    tool_calls           BIGINT NOT NULL DEFAULT 0,
    tool_usd             NUMERIC(12,4) NOT NULL DEFAULT 0,
    PRIMARY KEY (workspace_id, date)
);

CREATE TABLE budgets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    scope           TEXT NOT NULL CHECK (scope IN ('workspace','agent','conversation','day')),
    scope_id        UUID,                         -- agent_id when scope='agent'
    soft_usd        NUMERIC(10,2),
    hard_usd        NUMERIC(10,2),
    degrade_model   TEXT,                         -- model alias to fall back to
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE budget_ledger (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    budget_id       UUID NOT NULL REFERENCES budgets(id) ON DELETE CASCADE,
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    scope_id        UUID,
    spent_usd       NUMERIC(10,4) NOT NULL DEFAULT 0,
    remaining_usd   NUMERIC(10,4),
    alert_sent_at   TIMESTAMPTZ,
    hard_limit_hit_at TIMESTAMPTZ,
    PRIMARY KEY (budget_id, date)
);
CREATE INDEX idx_budget_ledger_workspace_date ON budget_ledger(workspace_id, date);

CREATE TABLE billing_line_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    category        TEXT NOT NULL CHECK (category IN ('llm_tokens','compute','platform','tools')),
    unit_count      BIGINT NOT NULL,
    unit_price_usd  NUMERIC(12,6) NOT NULL,
    total_usd       NUMERIC(12,4) NOT NULL,
    metadata_json   JSONB NOT NULL DEFAULT '{}',  -- {model, agent_id, channel_type, ...}
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_line_items_workspace_date ON billing_line_items(workspace_id, date);
```

---

## 3. Postgres — data plane

### 3.1 Conversations & turns

```sql
CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL,
    agent_id        UUID NOT NULL,
    channel_type    TEXT NOT NULL,
    user_id         TEXT NOT NULL,                -- channel-scoped end-user ID
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    status          TEXT NOT NULL DEFAULT 'active'
                      CHECK (status IN ('active','idle','closed','escalated')),
    operator_user_id UUID,                        -- set when HITL takeover happens
    metadata_json   JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_conv_workspace_last ON conversations (workspace_id, last_at DESC);
CREATE INDEX idx_conv_agent_user ON conversations (agent_id, user_id);

CREATE TABLE turns (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    seq             INTEGER NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('user','agent','tool','system','operator')),
    content_json    JSONB NOT NULL,
    token_in        INTEGER,
    token_out       INTEGER,
    cost_usd        NUMERIC(8,5),
    latency_ms      INTEGER,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at        TIMESTAMPTZ,
    UNIQUE(conversation_id, seq)
);
CREATE INDEX idx_turns_conv_seq ON turns (conversation_id, seq);
```

### 3.2 Memory tiers

```sql
CREATE TABLE memory_user (
    workspace_id    UUID NOT NULL,
    agent_id        UUID NOT NULL,
    user_id         TEXT NOT NULL,
    key             TEXT NOT NULL,
    value_json      JSONB NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, agent_id, user_id, key)
);

CREATE TABLE memory_bot (
    workspace_id    UUID NOT NULL,
    agent_id        UUID NOT NULL,
    key             TEXT NOT NULL,
    value_json      JSONB NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, agent_id, key)
);

-- session memory lives in Redis (see §5)
-- scratch memory is in-process only
-- episodic memory lives in Qdrant + Postgres (text + embedding)

CREATE TABLE episodic_memory (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL,
    agent_id        UUID NOT NULL,
    user_id         TEXT NOT NULL,
    summary         TEXT NOT NULL,
    raw_turn_ids    UUID[] NOT NULL,
    qdrant_point_id UUID NOT NULL,                -- pointer into Qdrant collection
    ts              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_episodic_user ON episodic_memory (workspace_id, agent_id, user_id, ts DESC);
```

### 3.3 Tool calls

```sql
CREATE TABLE tool_calls (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    turn_id         UUID NOT NULL REFERENCES turns(id) ON DELETE CASCADE,
    mcp_server_id   UUID NOT NULL,
    tool_name       TEXT NOT NULL,
    args_json       JSONB NOT NULL,
    result_json     JSONB,
    error           TEXT,
    latency_ms      INTEGER,
    cost_usd        NUMERIC(8,5),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_tool_calls_turn ON tool_calls (turn_id);

CREATE TABLE inbound_webhooks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    channel_type    TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,             -- customer-supplied or hashed signature
    payload_json    JSONB NOT NULL,
    signature_algo  TEXT NOT NULL,             -- 'hmac-sha256', 'ed25519', etc.
    signature_valid BOOLEAN NOT NULL DEFAULT true,
    processed_at    TIMESTAMPTZ,
    retry_count     INTEGER NOT NULL DEFAULT 0,
    next_retry_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(workspace_id, agent_id, channel_type, idempotency_key)
);
CREATE INDEX idx_webhooks_workspace_channel ON inbound_webhooks(workspace_id, channel_type) WHERE processed_at IS NULL;
```

### 3.4 HITL & escalation

```sql
CREATE TABLE hitl_queue (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    reason          TEXT NOT NULL,             -- 'budget_hit', 'escalation_trigger', 'manual_takeover'
    priority        INTEGER NOT NULL DEFAULT 0, -- 0=normal, 1=high, 2=critical
    assigned_operator_id UUID REFERENCES users(id),
    status          TEXT NOT NULL DEFAULT 'open'
                      CHECK (status IN ('open','assigned','resolved','reassigned')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at     TIMESTAMPTZ
);
CREATE INDEX idx_hitl_workspace_status ON hitl_queue(workspace_id, status) WHERE status IN ('open','assigned');
CREATE INDEX idx_hitl_priority ON hitl_queue(workspace_id, priority DESC) WHERE status = 'open';

CREATE TABLE notification_subscriptions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,             -- 'hitl_escalation', 'budget_alert', 'deploy_complete'
    channel         TEXT NOT NULL,             -- 'email', 'slack', 'in_app'
    is_enabled      BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(workspace_id, user_id, event_type, channel)
);
```

### 3.5 Row-level security

Every data-plane table includes `workspace_id`. RLS policy on every table:

```sql
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON conversations
  USING (workspace_id = current_setting('loop.workspace_id')::uuid);
-- repeat for every other tenanted table
```

The runtime sets `loop.workspace_id` per-connection via `SET LOCAL` so accidental cross-tenant queries are physically impossible.

---

## 4. Qdrant collections

### 4.1 KB chunks

- **Name pattern:** `kb_<workspace_id_short>_<kb_id_short>` (e.g. `kb_ab12_de34`).
- **Vector:** `vector_dim` from `knowledge_bases.vector_dim` (default 3072).
- **Distance:** Cosine.
- **Quantization:** binary if collection size > 5M points.
- **Payload:**
  ```json
  {
    "doc_id": "uuid",
    "chunk_id": "uuid",
    "position": 0,
    "source_uri": "s3://...",
    "title": "...",
    "byte_start": 0,
    "byte_end": 512,
    "metadata": { "section": "...", "tags": ["..."] }
  }
  ```

### 4.2 Episodic memory

- **Name pattern:** `episodic_<workspace_id_short>`.
- **Vector dim:** workspace-default embedding dimension.
- **Filtering:** `user_id`, `agent_id`, `ts`.
- **Payload:**
  ```json
  {
    "user_id": "...",
    "agent_id": "uuid",
    "summary": "Last week the user asked about refunds...",
    "ts": "2026-04-29T14:00:00Z",
    "raw_turn_ids": ["uuid", "uuid"]
  }
  ```

---

## 5. Redis keyspace

All keys are prefixed `loop:`. TTL conventions:

| Key pattern | TTL | Purpose |
|-------------|-----|---------|
| `loop:session:{conv_id}:{key}` | 24h (configurable) | Session memory |
| `loop:cache:llm:{prompt_hash}` | 7d | Semantic LLM cache |
| `loop:rl:{scope}:{id}:{window}` | window length | Sliding-window rate limit counters |
| `loop:locks:deploy:{agent_id}` | 5m | Deploy serialization |
| `loop:budget:{scope}:{id}:{day}` | 48h | Spend rolling counter |
| `loop:warmpool:{region}` | n/a | Set of warm runtime pod IDs |

**Cluster sharding:** Redis cluster mode in cloud, hash tag on `{conv_id}` for session keys to keep all of one conversation on one shard.

---

## 6. ClickHouse — analytics & traces

### 6.1 Traces

```sql
CREATE TABLE otel_traces ON CLUSTER loop_ch (
    workspace_id    UUID,
    conversation_id UUID,
    turn_id         UUID,
    span_id         UUID,
    parent_span_id  UUID,
    span_kind       LowCardinality(String),       -- 'llm','tool','retrieval','memory','channel'
    name            LowCardinality(String),
    started_at      DateTime64(3),
    ended_at        DateTime64(3),
    latency_ms      UInt32,
    cost_usd        Decimal(10, 6),
    status          LowCardinality(String),       -- 'ok','error','timeout'
    attrs           Map(String, String)
)
ENGINE = ReplicatedMergeTree
PARTITION BY (workspace_id, toDate(started_at))
ORDER BY (workspace_id, conversation_id, turn_id, started_at)
TTL toDateTime(started_at) + INTERVAL 90 DAY;
```

### 6.2 Cost rollups

```sql
CREATE MATERIALIZED VIEW costs_per_agent
ENGINE = SummingMergeTree
PARTITION BY toYYYYMM(date)
ORDER BY (workspace_id, agent_id, date)
AS SELECT
    workspace_id,
    JSONExtractString(attrs['agent_id']) AS agent_id,
    toDate(started_at) AS date,
    sum(cost_usd) AS total_usd,
    count() AS span_count
FROM otel_traces
GROUP BY workspace_id, agent_id, date;
```

### 6.3 Eval results (denormalized for dashboards)

```sql
CREATE TABLE eval_results_ch ON CLUSTER loop_ch (
    workspace_id    UUID,
    suite_name      LowCardinality(String),
    case_name       String,
    agent_version   UInt32,
    score           Float32,
    passed          UInt8,
    regressed       UInt8,
    ts              DateTime
)
ENGINE = ReplicatedMergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (workspace_id, suite_name, ts);
```

---

## 7. S3 layout

```
s3://loop-{region}-prod/
├── code/                   # versioned agent code artifacts
│   └── {workspace_id}/{agent_id}/{version}.tar.zst
├── recordings/             # voice call recordings (opt-in, encrypted)
│   └── {workspace_id}/{conversation_id}.opus
├── kb-originals/           # original uploaded docs (PDF, DOCX, etc.)
│   └── {workspace_id}/{kb_id}/{doc_id}.{ext}
├── eval-traces/            # full trace bundles for failed eval cases
│   └── {workspace_id}/{eval_run_id}/{case_id}.json.zst
└── exports/                # one-off data exports (GDPR DSARs, customer dumps)
    └── {workspace_id}/{export_id}.tar.zst
```

Encryption: SSE-KMS with per-workspace data keys (envelope encryption). Lifecycle: code & recordings live forever (until customer deletes); eval-traces 180 days; exports 30 days then deleted.

---

## 8. NATS subjects

```
EVENTS.inbound.{workspace_id}.{agent_id}.{channel}
TOOLS.dispatch.{workspace_id}.{agent_id}
TOOLS.result.{workspace_id}.{agent_id}.{turn_id}
TRACE.{workspace_id}
EVAL.run.{workspace_id}.{suite_id}
HITL.escalate.{workspace_id}.{agent_id}
DEPLOY.event.{workspace_id}.{agent_id}
```

Stream retention: 7 days for `EVENTS.*`, 24h for `TOOLS.*`, 30 min for `TRACE.*` (already persisted to ClickHouse), 24h for `EVAL.*`.

---

## 9. End-user identity deduplication

```sql
CREATE TABLE end_users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    primary_user_id TEXT NOT NULL,                -- canonical channel-agnostic identifier
    channel_mappings JSONB NOT NULL DEFAULT '{}', -- {web: 'user123', whatsapp: '5551234567', ...}
    pii_json        JSONB NOT NULL DEFAULT '{}',  -- {name, email, phone} — encrypted at rest
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(workspace_id, primary_user_id)
);
CREATE INDEX idx_end_users_workspace ON end_users(workspace_id);

CREATE TABLE pii_detection_rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    pattern_name    TEXT NOT NULL,               -- 'email', 'phone', 'ssn', 'credit_card'
    regex_pattern   TEXT NOT NULL,
    replacement_text TEXT NOT NULL DEFAULT '[REDACTED]',
    is_enabled      BOOLEAN NOT NULL DEFAULT true,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(workspace_id, pattern_name)
);
```

## 10. Pydantic models (canonical)

These are the public Python types that appear in the SDK. Every breaking change requires an SDK major bump.

```python
from datetime import datetime
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field
from uuid import UUID

class ChannelType(str, Enum):
    WEB = "web"
    WHATSAPP = "whatsapp"
    SLACK = "slack"
    TEAMS = "teams"
    TELEGRAM = "telegram"
    SMS = "sms"
    EMAIL = "email"
    DISCORD = "discord"
    VOICE = "voice"
    WEBHOOK = "webhook"

class ContentPart(BaseModel):
    type: Literal["text", "image", "audio", "file"]
    text: str | None = None
    url: str | None = None
    mime_type: str | None = None
    bytes_b64: str | None = None

class AgentEvent(BaseModel):
    workspace_id: UUID
    conversation_id: UUID
    user_id: str
    channel: ChannelType
    content: list[ContentPart]
    metadata: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime

class AgentResponse(BaseModel):
    conversation_id: UUID
    content: list[ContentPart]
    streaming: bool = True
    suggested_actions: list[dict] = Field(default_factory=list)
    end_turn: bool = True

class ToolCall(BaseModel):
    name: str
    server: str
    args: dict[str, Any]
    result: Any | None = None
    error: str | None = None
    latency_ms: int = 0
    cost_usd: float = 0.0

class TurnEvent(BaseModel):
    type: Literal["token", "tool_call", "retrieval", "trace", "degrade", "complete"]
    payload: dict[str, Any]
    ts: datetime

class AuditLogEntry(BaseModel):
    id: UUID
    workspace_id: UUID
    actor_user_id: UUID | None
    action: str
    resource_type: str
    resource_id: UUID | None
    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None
    created_at: datetime

class DataExportRequest(BaseModel):
    id: UUID
    workspace_id: UUID
    requester_user_id: UUID
    request_type: Literal["dsar", "backup", "full_export"]
    status: Literal["pending", "processing", "ready", "expired", "cancelled"]
    output_s3_path: str | None = None
    size_bytes: int | None = None
    created_at: datetime
    expires_at: datetime
    downloaded_at: datetime | None = None

class BudgetAlert(BaseModel):
    budget_id: UUID
    workspace_id: UUID
    scope: Literal["workspace", "agent", "conversation", "day"]
    spent_usd: float
    remaining_usd: float
    hard_limit_usd: float | None = None
    alerted_at: datetime
```

---

## 11. Constraints & invariants

**RLS enforcement:**
- Every row in a tenant-scoped table MUST have `workspace_id NOT NULL`.
- `SET LOCAL loop.workspace_id` must be called before any query on a tenanted table.
- RLS policies must use `=` (not `IN`), so a single `workspace_id` value is enforced per connection.

**Audit log immutability:**
- `audit_log.entry_hash` is SHA-256(id + actor_user_id + action + created_at + previous_hash).
- Auditors verify the chain by computing SHA-256 of each entry and comparing to the next entry's `previous_hash`.
- No UPDATE or DELETE on `audit_log`, ever.

**Idempotency:**
- `inbound_webhooks.idempotency_key` deduplication window is 24h. After 24h, the same key is allowed again (for eventual timeout of webhook retries).
- `api_keys.key_prefix` is always 8 characters for consistent audit log filtering.

**Optimistic locking:**
- `agent_versions.version_tag` is incremented on every update. Clients include the tag in PATCH and retry with backoff if the tag changes.

**PII handling:**
- `end_users.pii_json` is encrypted with the workspace KMS data key at the Postgres storage layer.
- `conversations.metadata_json` must never store raw PII; the runtime redacts before persisting.

**Budget enforcement:**
- `budgets.hard_usd` is a hard cap; any turn exceeding it is rejected at the gateway layer before LLM invocation.
- `budgets.soft_usd` triggers an alert when reached; the agent continues (no hard stop).

---

## 12. Migration policy

- **Tool:** Alembic for control-plane Postgres. Custom Python migrator for data-plane Postgres (per-tenant DDL). Qdrant uses its own collection migration helper.
- **Backwards compatibility:** all migrations must be backwards-compatible across one major version. Breaking changes require a deprecation flag for ≥30 days.
- **Process:** every PR with a migration must include (1) the up migration, (2) the down migration, (3) a unit test, (4) an entry in `data/CHANGELOG.md`.
- **Production deploys:** migrations apply via the deploy controller, single-leader, with row-counts logged and a 5-min rollback window.
- **Versioning:** control-plane schema version stored in `schema_version` table; data-plane migrations tracked per-tenant in `_migrations` table.

---

## 13. Data classification

| Class | Examples | Storage rules |
|-------|----------|---------------|
| **Public** | Docs, marketing | Any storage |
| **Customer-confidential** | Agent code, KB docs, conversation content | Tenant-scoped, encrypted at rest |
| **PII** | End-user names, emails, phone numbers in conversation | Same as confidential + redaction tools available |
| **Sensitive PII** | Health, financial details, gov IDs | Same as PII + dedicated encryption key + auto-redaction in traces |
| **Secrets** | API keys, OAuth tokens, customer credentials | Vault/Secrets-Manager only, never Postgres |

---

## 14. References

- `architecture/ARCHITECTURE.md` — how the data flows
- `api/openapi.yaml` — REST shapes match Pydantic models
- `engineering/SECURITY.md` — encryption, RLS, threat model
- `data/CHANGELOG.md` — migration and schema change history
