#!/usr/bin/env bash
# DR drill driver — Postgres point-in-time recovery (RB-021).
#
# Provisions a drill cluster, fetches the latest base backup, replays WAL
# up to a target recovery time, runs smoke checks, and tears the cluster
# back down. Emits one JSON line per step on stdout so the report
# archival job can upload a verbatim audit trail.
#
# Usage:
#   scripts/dr_postgres_pitr_drill.sh \
#     --region=us-east-1 \
#     --workspace-id=ws_drill_synthetic \
#     --rt=2026-04-30T12:00:00Z \
#     --bucket=s3://loop-wal-archive-us-east-1
#
# This script is intentionally hermetic: every call to an external
# binary is gated behind ``run_step``; in --dry-run mode the binaries
# are stubbed so the drill harness can exercise the orchestration logic
# in CI without an S3 bucket or a Kubernetes cluster.
set -euo pipefail

REGION=""
WORKSPACE_ID=""
RECOVERY_TARGET=""
BUCKET=""
DRY_RUN="false"
DRILL_NAMESPACE_PREFIX="postgres-drill-"

usage() {
  sed -n '2,18p' "$0" >&2
  exit 2
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --region=*)        REGION="${1#*=}"        ;;
    --workspace-id=*)  WORKSPACE_ID="${1#*=}"  ;;
    --rt=*)            RECOVERY_TARGET="${1#*=}" ;;
    --bucket=*)        BUCKET="${1#*=}"        ;;
    --dry-run)         DRY_RUN="true"          ;;
    --help|-h)         usage                   ;;
    *) echo "unknown arg: $1" >&2; usage      ;;
  esac
  shift
done

[ -n "$REGION" ]          || { echo "missing --region" >&2; exit 2; }
[ -n "$WORKSPACE_ID" ]    || { echo "missing --workspace-id" >&2; exit 2; }
[ -n "$RECOVERY_TARGET" ] || { echo "missing --rt" >&2; exit 2; }
[ -n "$BUCKET" ]          || { echo "missing --bucket" >&2; exit 2; }

DRILL_NAMESPACE="${DRILL_NAMESPACE_PREFIX}$(date -u +%Y%m%d-%H%M%S)"

emit_step() {
  local step="$1" name="$2" started="$3" ended="$4" duration="$5" ok="$6" detail="$7"
  printf '{"step":%s,"name":"%s","started_at":"%s","ended_at":"%s","duration_s":%s,"ok":%s,"detail":"%s"}\n' \
    "$step" "$name" "$started" "$ended" "$duration" "$ok" "$detail"
}

run_step() {
  local step="$1" name="$2"; shift 2
  local started ended duration ok detail
  started="$(date -u +%FT%TZ)"
  if [ "$DRY_RUN" = "true" ]; then
    detail="dry-run"
    ok="true"
    duration="0"
    ended="$started"
  else
    if "$@" >/tmp/dr-step.$$ 2>&1; then
      ok="true"
    else
      ok="false"
    fi
    ended="$(date -u +%FT%TZ)"
    duration=$(( $(date -u -d "$ended" +%s 2>/dev/null || date -u -j -f %FT%TZ "$ended" +%s) \
              - $(date -u -d "$started" +%s 2>/dev/null || date -u -j -f %FT%TZ "$started" +%s) ))
    detail="$(tail -1 /tmp/dr-step.$$ | tr -d '"' | head -c 120)"
    rm -f /tmp/dr-step.$$
  fi
  emit_step "$step" "$name" "$started" "$ended" "$duration" "$ok" "$detail"
  if [ "$ok" != "true" ]; then return 1; fi
}

# Refuse to run against any namespace that doesn't carry the drill prefix.
if ! [[ "$DRILL_NAMESPACE" == ${DRILL_NAMESPACE_PREFIX}* ]]; then
  echo "fatal: refusing non-drill namespace: $DRILL_NAMESPACE" >&2
  exit 3
fi

run_step 1 ack             true
run_step 2 select-target   true
run_step 3 provision-drill helm install -n "$DRILL_NAMESPACE" --create-namespace \
                              -f infra/helm/loop/values-drill.yaml drill-pg infra/helm/loop
run_step 4 backup-fetch    wal-g backup-fetch \
                              --target-path "$BUCKET/$WORKSPACE_ID" \
                              /var/lib/postgresql/data LATEST
run_step 5 wal-replay      wal-g wal-fetch \
                              --target-time "$RECOVERY_TARGET" \
                              --target-path "$BUCKET/$WORKSPACE_ID"
run_step 6 read-only-up    kubectl -n "$DRILL_NAMESPACE" exec drill-pg-0 -- \
                              psql -tAc "select pg_is_in_recovery();"
run_step 7 smoke           psql -tAc "select count(*) from workspaces;"
run_step 8 promote         kubectl -n "$DRILL_NAMESPACE" exec drill-pg-0 -- pg_ctl promote
run_step 9 teardown        helm uninstall -n "$DRILL_NAMESPACE" drill-pg
run_step 10 report         true

echo "drill complete: namespace=$DRILL_NAMESPACE rt=$RECOVERY_TARGET" >&2
