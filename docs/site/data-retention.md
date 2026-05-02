# Data Retention Policy

Loop retains customer data for different periods depending on data class and
region.  All retention jobs run nightly; deletion events are written to the
audit log.  Customers on the **Enterprise** plan may configure custom windows
within the bounds shown below.

## Retention windows

| Data class | Default | Min (Enterprise) | Max (Enterprise) | Notes |
|---|---|---|---|---|
| Conversation history | **365 days** | 1 day | 7 years | Includes bot + human turns |
| Trace & span data | **90 days** | 7 days | 1 year | OTel traces; see [Performance docs](../perf/gateway_provider_eval.md) |
| Voice recordings | **30 days** | 1 day | 90 days | Opt-in; disabled by default |
| Knowledge-base documents | **No expiry** | — | — | Deleted explicitly by customer |
| Audit logs | **7 years** | 7 years | 7 years | Not customer-configurable (SOC 2 / HIPAA) |
| Backups | **14 days** (Standard) / **90 days** (Enterprise) | 14 days | 90 days | Encrypted; verified weekly |

## How it works

1. **Nightly scheduler** — the `RetentionJob` class (in
   `packages/control-plane/loop_control_plane/retention.py`) runs once per
   day per region.
2. **Per-region sweep** — records older than the configured window are
   collected region-by-region to respect data-residency requirements.
3. **Audit trail** — every deletion batch is recorded in the audit log with
   `data_class`, `region`, `deleted_count`, `oldest_deleted_at`, and
   `job_run_at`.  Audit records themselves are retained for 7 years.
4. **No-expiry classes** — `KB_DOCUMENT` records are exempt from scheduled
   deletion; customers remove them via the API or Studio UI.

## Configuring custom windows (Enterprise)

Workspace administrators can override default windows via the API:

```
PATCH /workspaces/{workspace_id}/retention-policy
Content-Type: application/json

{
  "windows": {
    "conversation": 90,
    "trace": 30,
    "voice_recording": 7
  }
}
```

Retention windows are validated server-side; values outside the allowed range
return `422 Unprocessable Entity`.

## Data residency

Retention jobs run independently per region.  Data stored in `eu-west-1` is
never moved to `us-east-1` for deletion processing.  Audit records for EU
data are also stored in `eu-west-1`.

## Opt-out and right to erasure (GDPR Art. 17)

Customers can request immediate deletion of all conversation and voice data
for a workspace via the API:

```
DELETE /workspaces/{workspace_id}/data
```

This bypasses the nightly scheduler and triggers an immediate deletion job.
A confirmation is sent to the workspace owner email within 24 hours.
