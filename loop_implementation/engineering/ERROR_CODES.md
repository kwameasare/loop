# Loop — Error Code Registry

**Status:** v0.1  •  **Owner:** Founding Eng #1 (Runtime)
**Companion:** `engineering/HANDBOOK.md`, `api/openapi.yaml` (every error response carries a code).

Every error in Loop has a stable code. Codes never change meaning. They are part of the public contract — customers grep for them in logs, file support tickets with them, build automation against them.

---

## 0. As-shipped — codes actually emitted by the codebase today

> This is the live truth as of the Sprint-0 cut-off (S001–S014). The
> `docs-with-code` CI gate (`tools/check_docs_with_code.py`) requires this
> file to be updated in any PR that touches `packages/**/errors.py`.

| Code | Class | Where defined | Story |
|------|-------|---------------|-------|
| `LOOP-TH-000` | `ToolHostError` (base) | `packages/tool-host/loop_tool_host/errors.py` | S014 |
| `LOOP-TH-001` | `SandboxStartupError` (image pull failure / kata-runtime unavailable / image hash mismatch) | `packages/tool-host/loop_tool_host/errors.py` | S014 |
| `LOOP-TH-002` | `SandboxBusyError` (warm-pool exhausted within wait budget) | `packages/tool-host/loop_tool_host/errors.py` | S014 |

### 0.1 Known drift — pending renumber

The S014 implementation of `loop-tool-host` claimed `LOOP-TH-001` /
`LOOP-TH-002` for sandbox-lifecycle failures, but §3 below has those numbers
reserved for input-validation errors (`Unknown tool` / `Args schema
mismatch`). Per §1, the number bands are:

- `001-099` input validation
- `300-399` rate limit / budget
- `500-599` internal / bug

So `SandboxStartupError` belongs in `5xx` and `SandboxBusyError` belongs in
`3xx`. **Tracking item:** before any of these codes are exposed in a
public-facing API response (no S0 endpoint emits them yet — they are
internal-only), renumber to:

| Now | Renumber to | Reason |
|-----|-------------|--------|
| `LOOP-TH-001` `SandboxStartupError` | `LOOP-TH-502` | Internal infra failure |
| `LOOP-TH-002` `SandboxBusyError` | `LOOP-TH-302` | Capacity / budget |
| `LOOP-TH-000` `ToolHostError` (base) | (leave as `000`) | Base class is conventionally `xxx-000` |

Filed as **follow-up FU-014-A** (see tracker). Until that PR lands, do not
add `LOOP-TH-001` / `LOOP-TH-002` to any user-facing error response.

### 0.2 Adding a new error code

1. Add the class with a `code` class-var to the appropriate `packages/<svc>/<pkg>/errors.py`.
2. Add the code to either §0 (as-shipped) or §3 (canonical reference) — both is fine.
3. The `docs-with-code` CI gate fails the PR otherwise.

---

## 1. Format

`LOOP-<SERVICE>-<NUMBER>` — fixed-width, all caps, three sections.

- `<SERVICE>` is a 2-letter service prefix (table below).
- `<NUMBER>` is 3 digits, zero-padded. Within a service the number space is segmented:
  - `001-099` — input validation
  - `100-199` — auth & authorization
  - `200-299` — resource not found / conflict
  - `300-399` — rate limit / budget
  - `400-499` — upstream / dependency failure
  - `500-599` — internal / bug
  - `600-699` — security / abuse
  - `700-799` — cloud-portability adapter errors

Examples: `LOOP-RT-001`, `LOOP-GW-303`, `LOOP-API-401`.

---

## 2. Service prefixes

| Prefix | Service |
|--------|---------|
| `RT` | Runtime (`dp-runtime`) |
| `GW` | LLM Gateway (`dp-gateway`) |
| `TH` | Tool Host / MCP (`dp-tool-host`) |
| `KB` | Knowledge Base / RAG (`dp-kb-engine`) |
| `CH` | Channel adapters (any) |
| `EV` | Eval harness / runner |
| `API` | Control-plane API (`cp-api`) |
| `DEP` | Deploy controller |
| `BIL` | Billing |
| `STU` | Studio backend |
| `INF` | Infra adapters (cloud-portability layer) |
| `SEC` | Security / auth pipeline |
| `OBS` | Observability backend |

---

## 3. Common error codes (canonical reference)

### Runtime (`RT`)

| Code | Meaning | HTTP | Recovery |
|------|---------|------|----------|
| `LOOP-RT-001` | Invalid `AgentEvent` schema | 400 | Fix request body |
| `LOOP-RT-002` | Unknown channel type | 400 | Use a registered channel |
| `LOOP-RT-003` | Message exceeds 16 MB | 413 | Truncate |
| `LOOP-RT-101` | Workspace token mismatch | 401 | Re-auth |
| `LOOP-RT-201` | Agent not found | 404 | Check agent_id |
| `LOOP-RT-202` | Agent archived | 410 | Use a non-archived agent |
| `LOOP-RT-301` | Hard budget cap hit (workspace) | 429 | Raise cap or wait |
| `LOOP-RT-302` | Hard budget cap hit (agent) | 429 | Raise cap |
| `LOOP-RT-303` | Hard budget cap hit (conversation) | 429 | New conversation |
| `LOOP-RT-304` | Max iterations exceeded | 429 | Investigate looping; raise cap |
| `LOOP-RT-305` | Max runtime seconds exceeded | 408 | Optimise tool calls |
| `LOOP-RT-401` | LLM gateway upstream failure | 502 | Retry; fallback model |
| `LOOP-RT-402` | KB engine timeout | 504 | Retry |
| `LOOP-RT-403` | Tool call timeout | 504 | Tool author to investigate |
| `LOOP-RT-501` | Internal — unexpected runtime state | 500 | Bug; auto-pages on-call |
| `LOOP-RT-601` | Suspected prompt injection rejected | 400 | Surface to operator |
| `LOOP-RT-602` | Output filter PII leak detected | 500 | Logs to security; surface generic msg |

### LLM Gateway (`GW`)

| Code | Meaning | HTTP |
|------|---------|------|
| `LOOP-GW-001` | Unknown model alias | 400 |
| `LOOP-GW-002` | Invalid prompt structure | 400 |
| `LOOP-GW-101` | Provider key missing | 401 |
| `LOOP-GW-301` | Provider rate limit hit (back-off) | 429 |
| `LOOP-GW-302` | Per-workspace cost cap hit | 429 |
| `LOOP-GW-303` | Per-workspace token cap hit | 429 |
| `LOOP-GW-401` | Provider 5xx (OpenAI/Anthropic/etc.) | 502 |
| `LOOP-GW-402` | Streaming connection dropped | 504 |
| `LOOP-GW-501` | Internal cache poisoned | 500 |

### Tool Host / MCP (`TH`)

| Code | Meaning | HTTP |
|------|---------|------|
| `LOOP-TH-001` | Unknown tool | 400 |
| `LOOP-TH-002` | Args schema mismatch | 400 |
| `LOOP-TH-101` | Tool not granted to this agent | 403 |
| `LOOP-TH-301` | Per-turn tool-call cap hit | 429 |
| `LOOP-TH-401` | Sandbox cold-start timeout | 504 |
| `LOOP-TH-402` | Tool process OOM-killed | 502 |
| `LOOP-TH-403` | Egress to disallowed host | 403 |
| `LOOP-TH-501` | Sandbox supervisor failure | 500 |

### KB engine (`KB`)

| Code | Meaning | HTTP |
|------|---------|------|
| `LOOP-KB-001` | Unsupported source type | 400 |
| `LOOP-KB-002` | Embedding model mismatch | 400 |
| `LOOP-KB-201` | KB not found | 404 |
| `LOOP-KB-401` | Qdrant unavailable | 503 |
| `LOOP-KB-402` | Embedding provider down | 502 |
| `LOOP-KB-501` | Internal chunking failure | 500 |

### Channels (`CH`)

| Code | Meaning | HTTP |
|------|---------|------|
| `LOOP-CH-001` | Webhook signature invalid | 401 |
| `LOOP-CH-002` | Replay outside 24h dedupe window | 409 |
| `LOOP-CH-101` | Channel credentials revoked upstream | 401 |
| `LOOP-CH-301` | Channel-specific rate limit (Meta/Twilio) | 429 |
| `LOOP-CH-401` | Provider 5xx | 502 |

### Eval (`EV`)

| Code | Meaning | HTTP |
|------|---------|------|
| `LOOP-EV-001` | Suite YAML invalid | 400 |
| `LOOP-EV-201` | Suite not found | 404 |
| `LOOP-EV-301` | Eval run blocked: cost cap hit | 429 |
| `LOOP-EV-401` | Cassette stale > 90 days | 503 (warning at 30) |
| `LOOP-EV-501` | Internal scorer crash | 500 |

### Control-plane API (`API`)

| Code | Meaning | HTTP |
|------|---------|------|
| `LOOP-API-001` | Required field missing | 400 |
| `LOOP-API-002` | Idempotency-Key replayed with different body | 409 |
| `LOOP-API-101` | Token expired | 401 |
| `LOOP-API-102` | Token scope insufficient | 403 |
| `LOOP-API-103` | MFA required | 401 |
| `LOOP-API-201` | Resource not found | 404 |
| `LOOP-API-202` | Resource archived | 410 |
| `LOOP-API-203` | Soft-delete conflict (use `?force=true`) | 409 |
| `LOOP-API-301` | Per-IP rate limit hit | 429 |
| `LOOP-API-302` | Per-key rate limit hit | 429 |
| `LOOP-API-501` | Internal — unhandled | 500 |

### Deploy (`DEP`)

| Code | Meaning | HTTP |
|------|---------|------|
| `LOOP-DEP-001` | Code artifact malformed | 400 |
| `LOOP-DEP-002` | Image build failed | 422 |
| `LOOP-DEP-201` | Agent version not found | 404 |
| `LOOP-DEP-301` | Eval gate blocked promotion | 412 |
| `LOOP-DEP-401` | k8s API unreachable | 503 |
| `LOOP-DEP-501` | Internal | 500 |

### Billing (`BIL`)

| Code | Meaning | HTTP |
|------|---------|------|
| `LOOP-BIL-001` | Plan downgrade refused (active resources) | 409 |
| `LOOP-BIL-101` | Stripe webhook signature invalid | 401 |
| `LOOP-BIL-301` | Plan exceeded; upgrade required | 402 |
| `LOOP-BIL-401` | Stripe outage | 503 |

### Cloud-portability infra adapter (`INF`)

| Code | Meaning | HTTP |
|------|---------|------|
| `LOOP-INF-701` | Object-store backend unavailable | 503 |
| `LOOP-INF-702` | KMS unavailable | 503 |
| `LOOP-INF-703` | Secrets backend unavailable | 503 |
| `LOOP-INF-704` | Email sender failed | 502 |
| `LOOP-INF-705` | DNS / cert mismatch | 503 |

---

## 4. Error envelope (RFC 9457 Problem Details)

Every error response has the shape:

```json
{
  "type": "https://errors.loop.example/LOOP-RT-301",
  "title": "Workspace budget cap reached",
  "status": 429,
  "detail": "Hard cap of $50.00 USD/day was reached at 14:37 UTC.",
  "instance": "/v1/agents/abc.../invoke",
  "code": "LOOP-RT-301",
  "request_id": "req_018f...",
  "trace_id": "01HW...",
  "retry_after_seconds": 3600,
  "documentation_url": "https://docs.loop.example/errors/LOOP-RT-301"
}
```

Required fields: `type`, `title`, `status`, `code`, `request_id`, `trace_id`. The `documentation_url` resolves to a docs page per code.

---

## 5. Adding a new error code

1. Pick the right `<SERVICE>` prefix and the right `100`-block.
2. Take the next free number — never reuse a retired code.
3. Add it to this file with HTTP status, meaning, and recommended recovery.
4. Define a Python exception subclassing `LoopError` with the code as a class attr.
5. Add a docs page at `docs/errors/LOOP-XX-NNN.md` if the recovery is non-trivial.
6. Add a test that asserts the code in the response envelope.

```python
# packages/runtime/loop/runtime/errors.py
class BudgetCapHit(LoopError):
    code = "LOOP-RT-301"
    http_status = 429
    title = "Workspace budget cap reached"
```

---

## 6. Forbidden practices

- Reusing a retired code for a different meaning.
- Returning `500` with no `code`.
- Leaking stack traces to the customer (always sanitize).
- Codes outside the `LOOP-XX-NNN` shape.
- "Generic" codes like `LOOP-RT-999` — every error has a specific reason or it goes to `-501` (internal).

---

## 7. Observability mapping

Every error code emits an OTel attribute `loop.error.code` so dashboards can group by code. Sentry tags every event with `loop.error.code` for easy triage.
