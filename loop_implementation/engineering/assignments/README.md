# Post-P0 P1/P2 assignments

After PRs #166–#195 closed every P0 audit finding except P0.2 and P0.3
(both in flight as spawned tasks), the remaining work is P1 (must
land before public-prod claim) and P2 (quality / hygiene). This file
is the master index; one file per agent under
`assignments/agent-<name>.md` carries the line-item detail.

## Status snapshot

| Tier | Items shipped this run | Items remaining |
|---|---|---|
| **P0** | 8/10 categories closed | P0.2 (Postgres-backed cp services), P0.3 (studio fixtures) — both **in flight** |
| **P1** | 18/~60 closed in P0 sweeps | ~42 items, 4 agents |
| **P2** | 0/~20 closed | ~20 items, distributed |

## Agent roster + theme

| Agent | Theme | Why this fits |
|---|---|---|
| `codex-orion` | **Persistence + GDPR cascade** | Owns all the Postgres-store work (memory, KB BM25, channel ConversationIndex, voice room state) plus right-to-erasure cascades. Pairs with the in-flight P0.2 task. |
| `codex-vega` | **Provider routing, billing accuracy, gateway hardening** | Owns the gateway + dp critical path: idempotency Redis, ProviderFailoverRunner, Decimal billing, retry jitter, SSE cancellation, error-code distinction. |
| `copilot-thor` | **Frontend completeness + studio polish** | Owns 401 interceptor, AuthProvider hard-fail, loading/error states, eval-suite create form, security headers, a11y, bundle. Pairs with the in-flight P0.3 task. |
| `copilot-titan` | **Infra, observability, compliance** | Owns helm CI gates (check_helm_chart, k6 baseline), DR drills, Falco, Dependabot, license check, runbooks, threat-model auto-gating, KMS integration tests. |

## Coordination notes

1. **P0.2 (in flight)** must land before `codex-orion`'s "transactional
   audit emission" item can complete (P1.9 from the core-backend
   audit). Until then, the audit-event insert stays out-of-txn but
   the new Postgres adapters should expose a transaction-context
   helper so the wiring is one rebase away.
2. **P0.3 (in flight)** owns the studio `/inbox` fixture replacement.
   `copilot-thor` should NOT also rewrite `/inbox`; their list focuses
   on the cross-cutting concerns (interceptor, headers, loading
   states for everything-except-inbox).
3. **`copilot-titan`'s observability stack work** depends on the
   prometheus + otel middleware (#180/#181) which already shipped.
4. Every agent's PR pattern: branch `agent/<name>/<slug>` ➜ commit
   ➜ push ➜ `gh pr create --base main` ➜ tests-pass ➜
   `gh pr merge --merge`. Each PR includes regression tests that pin
   the contract.
5. **Audit emission is non-negotiable** on every new mutating route
   or service-method. Use `record_audit_event` from
   `loop_control_plane.audit_events` (the pattern is well-trod
   across PRs #182, #185–#195). Audit row schema stores `payload_hash`
   only; never put plaintext / PII in the audit payload.
6. **Conventional commits + co-author trailer**: every PR ends with
   the `Co-Authored-By: Claude …` trailer line so the audit log
   distinguishes Claude-authored from human-authored work.

## Per-agent files

- [`agent-codex-orion.md`](agent-codex-orion.md) — persistence, GDPR cascades, memory + KB Postgres-backing.
- [`agent-codex-vega.md`](agent-codex-vega.md) — gateway / dp critical path, billing accuracy.
- [`agent-copilot-thor.md`](agent-copilot-thor.md) — studio cross-cutting + a11y + bundle.
- [`agent-copilot-titan.md`](agent-copilot-titan.md) — infra, CI gates, observability stack, runbooks.

## Acceptance — when is the platform "fully prod-ready"?

When every item below is checked and CI is green on `main`:

- [ ] P0.2 — every cp service has a Postgres-backed implementation
      AND the integration tests (`_tests_integration/`) cover them.
- [ ] P0.3 — no studio page returns fixture data; `/inbox`,
      `/billing`, `/costs`, `/traces`, `/voice`, `/enterprise`,
      `/agents/[id]/tools`, `/agents/[id]/inspector` all wire to
      cp-api.
- [ ] All P1 items in the four agent files have shipping PRs merged.
- [ ] `tests/test_audit_completeness.py` (new — see
      `agent-codex-vega.md`) asserts every mutating cp/dp route emits
      `record_audit_event`.
- [ ] `infra/prometheus/alerts/slo-burn.yaml` series have
      30-day backfill of real metrics from prometheus.
- [ ] `RUNBOOKS.md` has 0 entries marked `TBD M2-M11`.
- [ ] `.github/workflows/perf-regression-budget.yml` has no
      `continue-on-error: true`.
- [ ] `pip-audit` + `npm audit` are blocking in CI; both clean.
- [ ] `helm template infra/helm/loop --debug` renders cleanly with
      defaults; `helm install` against a kind cluster passes the
      runtime-sse-1000 budget.
