# Agent: copilot-titan — infra, observability stack, compliance, runbooks

**Theme**: helm CI gates, deployable observability, dependency hygiene,
DR drills, runbooks, Falco rules, threat-model auto-gating, license
check.

**Branch convention**: `agent/copilot-titan/<slug>`.

---

## Item 1 — Wire `tools/check_helm_chart.py` into CI

**Audit finding** (infra audit P1):
> `tools/check_helm_chart.py` exists but is not wired into any
> workflow — a chart structural validator that never runs.

**Acceptance**:
1. New `.github/workflows/helm-chart-validation.yml` that runs on PR
   if any path under `infra/helm/` changed. Calls the existing tool +
   `helm template` (must `helm` binary install in the runner) +
   `helm lint`.
2. Fails on lint errors. Caches the helm binary install.
3. Add to `branch-protection-required.yml` (or whatever the merge
   gate is on `main`).

**Effort**: ~0.5 day, 1 PR.

---

## Item 2 — Wire `scripts/k6_runtime_baseline_100rpm.js` into CI

**Audit finding**:
> The script + `bench/results/runtime_baseline_100rpm.json` artefact
> exist but no workflow runs it. Dead perf gate.

**Acceptance**:
1. New `.github/workflows/perf-baseline-100rpm.yml` triggered nightly
   + on `workflow_dispatch`. Spins up kind, deploys cp+dp via helm,
   runs the k6 script, asserts the budget from the artefact JSON.
2. Posts results to a Slack/PagerDuty webhook on regression (gated
   on `LOOP_ONCALL_WEBHOOK_URL` like `runtime-sse-1000.yml`).

**Effort**: ~1 day, 1 PR.

---

## Item 3 — `promote-regional-images.yml` environment gate

**File**: `.github/workflows/promote-regional-images.yml`.

**Audit finding**:
> `workflow_dispatch` + a 04:17 cron, no environment approval.
> Auto-promotes nightly to all regions. A bad commit gets to prod
> overnight.

**Acceptance**:
1. Add `environment: production-image-promotion` to every job.
2. Configure the GitHub Environment with required reviewers (the
   PR description mentions which team).
3. Test: trigger via `workflow_dispatch`, assert it pauses on the
   approval gate.

**Effort**: ~0.25 day, 1 PR.

---

## Item 4 — Bitnami subchart mirroring

**Audit finding**:
> Bitnami images now require auth (deprecation as of mid-2025);
> pinned tags `15.5.38`, `20.3.0`, `14.10.5`, `6.2.18` will silently
> start failing pulls when Bitnami flips the registry.

**Acceptance**:
1. New `.github/workflows/mirror-bitnami-subcharts.yml` that pulls
   each pinned subchart + image and re-pushes to GHCR under
   `ghcr.io/loop-ai/mirrored/bitnami/*`.
2. Update `infra/helm/loop/Chart.yaml` to reference the mirror.
3. Document the rotation process in
   `loop_implementation/engineering/HOWTO_BITNAMI_MIRROR.md`.

**Effort**: ~1 day, 1 PR.

---

## Item 5 — `NOTES.txt` preflight

**File**: `infra/helm/loop/templates/NOTES.txt`.

**Audit finding**:
> `values-eu-west.yaml:107-112` claims "the chart fails its NOTES.txt
> preflight if these are unset" — `templates/NOTES.txt` only prints
> the gateway URL. Lie in the docs.

**Acceptance**:
1. Update `NOTES.txt` to actually `{{ fail "..." }}` if the regional
   pinning vars are unset.
2. Add a CI check that asserts the values-EU/US/APAC overlays render
   successfully and the default values fail loudly when EU residency
   is required.

**Effort**: ~0.5 day, 1 PR.

---

## Item 6 — Helm rollback testing

**Audit finding**:
> `helm-e2e.yml` runs install but never tests `helm upgrade --atomic`
> or rollback.

**Acceptance**:
1. Extend `helm-e2e.yml` to do: install v1 ➜ upgrade to broken-v2 ➜
   assert helm rolls back automatically (`--atomic`) ➜ confirm
   pods are at v1.
2. The "broken-v2" mutation: bump an image tag to a non-existent
   one so the deploy fails the readiness probe.

**Effort**: ~0.5 day, 1 PR.

---

## Item 7 — DR backup + restore drills in CI

**Files**:
- `scripts/dr_postgres_pitr_drill.sh`
- `scripts/dr_clickhouse_restore_drill.sh`

**Audit finding**:
> Both exist but aren't scheduled in any workflow — DR is exercised
> manually.

**Acceptance**:
1. New `.github/workflows/dr-drill-postgres.yml` runs weekly, calls
   the existing PITR script in a kind cluster, asserts data round-trip.
2. Same for ClickHouse.
3. Updates the corresponding RUNBOOKS.md entries with the latest
   drill date stamped from the workflow run.

**Effort**: ~1 day, 1 PR.

---

## Item 8 — Deployable observability stack chart

**Audit finding**:
> The chart deploys nothing for Prometheus/Grafana/Loki/Tempo/Jaeger.
> Customers running `helm install loop` get no metrics, no traces, no
> logs UI.

**Acceptance**:
1. New `infra/helm/loop-observability/` chart that bundles
   kube-prometheus-stack + Grafana + Loki + Tempo, all pinned.
2. Pre-loaded Grafana dashboards (extract from the existing Loop
   dashboards JSON in `infra/grafana/`).
3. Pre-wired alertmanager config matches `slo-burn.yaml` (which now
   has data thanks to PRs #180/#181).
4. Document the install path in
   `loop_implementation/engineering/OBS_STACK_INSTALL.md`.

**Effort**: ~2 days, 1 PR.

---

## Item 9 — `cp-api` Dockerfile workers env-driven

**File**: `packages/control-plane/Dockerfile:72`.

**Audit finding**:
> Exposes `--workers 4` hard-coded. Should be env-driven so resource
> sizing matters.

**Acceptance**:
1. Replace with `CMD ["sh", "-c", "uvicorn loop_control_plane.app:app
   --host 0.0.0.0 --port 8080 --workers ${UVICORN_WORKERS:-4}"]`.
2. Helm chart's `controlPlane.env.UVICORN_WORKERS` driven from the
   replicaCount + resource limits.
3. Same change for `packages/data-plane/Dockerfile`.

**Effort**: ~0.25 day, 1 PR.

---

## Item 10 — Falco workflow

**File**: `infra/falco/loop_rules.yaml` (already exists).

**Audit finding**:
> Falco rules ship at `infra/falco/loop_rules.yaml` but no workflow
> installs Falco; no chart hook either. Detection-only doc.

**Acceptance**:
1. Add `falco` as a sub-chart in `infra/helm/loop-observability/`
   (Item 8). Mount the existing rules file as a ConfigMap.
2. Sink alerts to alertmanager via `falco-falcosidekick`.
3. CI smoke: install the obs stack, trigger one of the rules
   (`shell-spawned-in-pod`), assert an alert appears.

**Effort**: ~1 day, 1 PR.

---

## Item 11 — Dependabot + Renovate

**Audit finding**:
> No `.github/dependabot.yml`, no `renovate.json`. No automated
> upstream CVE patching.

**Acceptance**:
1. New `.github/dependabot.yml` covering `pip`, `npm`, `gomod`,
   `docker`, `github-actions`. Schedule weekly. Group minor + patch
   updates.
2. Allowlist (or pin) major-version bumps so they don't auto-merge.
3. Document the policy in `loop_implementation/engineering/DEPENDENCY_POLICY.md`.

**Effort**: ~0.5 day, 1 PR.

---

## Item 12 — License compliance check

**Audit finding**:
> No FOSSA, no `pip-licenses` in CI, no `license_check.py`. SBOM is
> generated but never queried for GPL/AGPL contamination.

**Acceptance**:
1. New `tools/license_check.py` that reads the existing CycloneDX
   SBOM (`anchore/sbom-action` already runs in `ci.yml`) and asserts
   no GPL / AGPL / LGPL-3 is in the dependency tree of any
   distributable wheel.
2. Allowlist file `tools/license_allowlist.json` for the few
   dual-licensed deps that are LGPL-or-MIT etc.
3. Wire into `ci.yml` as a required job.
4. Test cases for both pass and fail conditions.

**Effort**: ~1 day, 1 PR.

---

## Item 13 — Block-on-CVE for `pip-audit` + `npm audit`

**Audit finding**:
> `pip-audit` runs in CI but is non-blocking. Snyk silently skipped
> if `SNYK_TOKEN` unset.

**Acceptance**:
1. Flip `pip-audit` to blocking. Allowlist file `pip_audit_allow.txt`
   for documented unfixable CVEs (with a 90-day expiry).
2. Same for `npm audit --audit-level=high` on `apps/studio`.
3. New `tools/check_audit_allowlist_expiry.py` that fails the build
   if any allowlist entry is past its expiry.

**Effort**: ~0.5 day, 1 PR.

---

## Item 14 — Runbooks: close the 18 TBD entries

**File**: `RUNBOOKS.md`.

**Audit finding** (security audit):
> 18 of 24 runbooks marked "TBD M2-M11" — not drilled. RB-014 (audit
> chain integrity), RB-015 (cross-tenant leak), RB-018 (mass deploy
> rollback), RB-020 (compromised API key) all SEV1 with no drill.

**Acceptance**: Write each missing runbook section. Each must include:
- Symptom / how the alert fires
- First-5-minute triage steps (concrete commands)
- Mitigation (e.g. "rotate the affected workspace's KMS key")
- Recovery validation
- Drill cadence + last-drilled date

Suggest splitting into 4-6 PRs by SEV level. Group SEV1 first
(RB-014, RB-015, RB-018, RB-020).

**Effort**: ~3 days across 6 PRs.

---

## Item 15 — On-call schedule file

**Audit finding**:
> No on-call schedule file (PagerDuty escalation policy) committed.
> Only `pagerduty_receiver` reference in alertmanager.

**Acceptance**:
1. New `infra/oncall/schedule.yaml` describing rotations + escalation
   tiers.
2. Terraform module that applies it to PagerDuty (using the
   `pagerduty/pagerduty` provider).
3. CI smoke that validates the schedule YAML against PagerDuty's
   schema.

**Effort**: ~0.5 day, 1 PR.

---

## Item 16 — Threat-model gate on every new mutating route

**File**: `tools/check_threat_model.py`.

**Audit finding**:
> The threat-model gate covers protected file globs but does not
> gate on `_routes_*.py` mutations — adding a new mutating route
> never triggers the STRIDE checklist.

**Acceptance**:
1. Extend the script to detect new `@router.post|put|patch|delete`
   decorators in any `_routes_*.py` and require a STRIDE entry in
   `THREAT_MODEL.md` referencing the route's audit-action namespace.
2. Migration: backfill STRIDE entries for the routes shipped in
   #182, #185-195 so the new gate doesn't fail on existing code.

**Effort**: ~1 day, 1 PR.

---

## Item 17 — KMS integration tests in CI

**Audit finding** (security audit):
> Cloud KMS / S3 backends added in S905, S918 but no integration
> test of `vault_transit` or `aws_kms` in CI — only the
> `InMemoryKMS` is exercised. Production posture is unverified.

**Acceptance**:
1. New `.github/workflows/kms-integration.yml` that spins up a
   `vault` container in service-mode, runs the `vault_transit`
   round-trip tests against it.
2. Same for `localstack` + `aws_kms` (via the moto S3+KMS image
   already used in fixtures).
3. Both run on PR if any path under
   `packages/control-plane/loop_control_plane/{kms,vault_transit,aws_backends}.py`
   changed.

**Effort**: ~1.5 days, 1 PR.

---

## Item 18 — `perf-regression-budget` no longer `continue-on-error`

**File**: `.github/workflows/perf-regression-budget.yml`.

**Audit finding** (P2):
> Uses `continue-on-error: true` then asserts `outcome != 'success'`
> — clever but fragile.

**Acceptance**:
1. Restructure as: an explicit `bash` step that captures k6 exit
   code, runs the budget assertion, fails on regression. No
   `continue-on-error`.

**Effort**: ~0.25 day, 1 PR.

---

## Item 19 — DRY workflow Dockerfile heredocs

**Audit finding** (P2):
> 5 workflows rebuild the same Python smoke image inline via heredoc
> Dockerfile.

**Acceptance**:
1. Extract to `scripts/Dockerfile.smoke` and update each workflow to
   build from it. Use a buildx-managed cache key on the file content
   so reuse is real.

**Effort**: ~0.5 day, 1 PR.

---

## Acceptance summary for copilot-titan

19 items, ~14-16 PRs, ~12-14 days. After your work:

- [x] Helm chart structurally validated on every PR.
- [x] k6 baseline runs nightly + alerts on regression.
- [x] No prod image promotes without reviewer approval.
- [x] Bitnami subcharts mirrored to GHCR — no surprise pull failures.
- [x] NOTES.txt actually fails on misconfigured EU/US/APAC values.
- [x] Helm rollback verified in CI on every release.
- [x] DR drills run weekly in CI; runbooks track last-drilled dates.
- [x] Customers can deploy a one-click observability stack.
- [x] uvicorn worker count is env-driven across cp + dp.
- [x] Falco runs in the bundled obs stack.
- [x] Dependabot covers every package manager.
- [x] License check is a required CI job.
- [x] CVE allowlist enforced + expiring.
- [x] Every SEV1 runbook is written + drilled.
- [x] On-call schedule under version control.
- [x] New mutating routes auto-gate on STRIDE.
- [x] KMS backends integration-tested.
- [x] perf-regression-budget is honest about success/failure.
- [x] No more heredoc Dockerfile drift across workflows.
