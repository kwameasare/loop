#!/usr/bin/env bash
# DR drill driver — ClickHouse snapshot restore (RB-022).
#
# Provisions a drill ClickHouse cluster, downloads a daily snapshot
# from S3 via clickhouse-backup, restores schema+data, replays the
# NATS gap stream, runs smoke checks, and tears the cluster back
# down. Emits one JSON line per step on stdout so the report
# archival job can upload a verbatim audit trail.
#
# Usage:
#   scripts/dr_clickhouse_restore_drill.sh \
#     --region=us-east-1 \
#     --snapshot=2026-05-01-daily \
#     --bucket=s3://loop-clickhouse-backup-us-east-1
#
# In --dry-run mode the orchestration logic is exercised without
# touching cloud resources, which is what the CI test in
# tests/test_dr_clickhouse_restore_drill.py relies on.
set -euo pipefail

REGION=""
SNAPSHOT=""
BUCKET=""
DRY_RUN="false"
DRILL_NAMESPACE_PREFIX="clickhouse-drill-"

usage() {
  sed -n '2,18p' "$0" >&2
  exit 2
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --region=*)   REGION="${1#*=}"   ;;
    --snapshot=*) SNAPSHOT="${1#*=}" ;;
    --bucket=*)   BUCKET="${1#*=}"   ;;
    --dry-run)    DRY_RUN="true"     ;;
    --help|-h)    usage              ;;
    *) echo "unknown arg: $1" >&2; usage ;;
  esac
  shift
done

[ -n "$REGION" ]   || { echo "missing --region" >&2; exit 2; }
[ -n "$SNAPSHOT" ] || { echo "missing --snapshot" >&2; exit 2; }
[ -n "$BUCKET" ]   || { echo "missing --bucket" >&2; exit 2; }

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
    if "$@" >/tmp/dr-ch-step.$$ 2>&1; then ok="true"; else ok="false"; fi
    ended="$(date -u +%FT%TZ)"
    duration=$(( $(date -u -d "$ended" +%s 2>/dev/null || date -u -j -f %FT%TZ "$ended" +%s) \
              - $(date -u -d "$started" +%s 2>/dev/null || date -u -j -f %FT%TZ "$started" +%s) ))
    detail="$(tail -1 /tmp/dr-ch-step.$$ | tr -d '"' | head -c 120)"
    rm -f /tmp/dr-ch-step.$$
  fi
  emit_step "$step" "$name" "$started" "$ended" "$duration" "$ok" "$detail"
  if [ "$ok" != "true" ]; then return 1; fi
}

if ! [[ "$DRILL_NAMESPACE" == ${DRILL_NAMESPACE_PREFIX}* ]]; then
  echo "fatal: refusing non-drill namespace: $DRILL_NAMESPACE" >&2
  exit 3
fi

run_step 1 ack             true
run_step 2 select-snapshot true
run_step 3 provision-drill helm install -n "$DRILL_NAMESPACE" --create-namespace \
                              -f infra/helm/loop/values-clickhouse-drill.yaml \
                              drill-ch infra/helm/loop
run_step 4 backup-download clickhouse-backup download \
                              --remote "$BUCKET" "$SNAPSHOT"
run_step 5 backup-restore  clickhouse-backup restore --schema --data "$SNAPSHOT"
run_step 6 nats-gap-replay  loop admin trace-replay \
                              --since "@snapshot.created_at" \
                              --target-namespace "$DRILL_NAMESPACE"
run_step 7 smoke           clickhouse-client -q "select count() from traces.spans"
run_step 8 validation      clickhouse-client -q \
                              "select quantile(0.95)(duration_ms) from traces.spans"
run_step 9 teardown        helm uninstall -n "$DRILL_NAMESPACE" drill-ch
run_step 10 report         true

echo "drill complete: namespace=$DRILL_NAMESPACE snapshot=$SNAPSHOT" >&2
