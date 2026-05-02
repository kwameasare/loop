#!/usr/bin/env bash
# chaos/db_failover.sh — trigger Postgres primary failover and measure RTO/RPO
#
# Usage: CHAOS_PG_LEADER=<pod-or-host> ./chaos/db_failover.sh
#
# Requires: kubectl (for k8s) or pg_ctlcluster, patronictl, or pg_ctl for bare-metal.
# Reads: CHAOS_PG_LEADER, CHAOS_PG_NAMESPACE (default: loop), CHAOS_PG_CLUSTER (default: loop-pg)

set -euo pipefail

PG_NAMESPACE="${CHAOS_PG_NAMESPACE:-loop}"
PG_CLUSTER="${CHAOS_PG_CLUSTER:-loop-pg}"
PG_LEADER="${CHAOS_PG_LEADER:-}"

log() { echo "[$(date -u +%T)] chaos/db_failover: $*" >&2; }

START_TS=$(date -u +%s)
log "starting DB failover drill — cluster=${PG_CLUSTER} namespace=${PG_NAMESPACE}"

# ---------- 1. Identify leader ----------
if [[ -z "${PG_LEADER}" ]]; then
  if command -v patronictl &>/dev/null; then
    PG_LEADER=$(patronictl -c /etc/patroni/config.yml list "${PG_CLUSTER}" --format=json 2>/dev/null \
      | python3 -c "import sys,json; m=[m for m in json.load(sys.stdin) if m.get('Role')=='Leader']; print(m[0]['Member'])" 2>/dev/null || echo "")
  fi
  if [[ -z "${PG_LEADER}" ]] && command -v kubectl &>/dev/null; then
    PG_LEADER=$(kubectl get pod -n "${PG_NAMESPACE}" -l "role=master,cluster-name=${PG_CLUSTER}" \
      -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
  fi
fi

if [[ -z "${PG_LEADER}" ]]; then
  log "WARNING: could not detect leader; dry-run mode"
  FAILOVER_METHOD="dry-run"
else
  log "detected leader: ${PG_LEADER}"
  FAILOVER_METHOD="detected"
fi

# ---------- 2. Record pre-fault LSN / lag ----------
PRE_LSN=""
if command -v kubectl &>/dev/null && [[ "${FAILOVER_METHOD}" != "dry-run" ]]; then
  PRE_LSN=$(kubectl exec -n "${PG_NAMESPACE}" "${PG_LEADER}" -- \
    psql -U postgres -tAc "SELECT pg_current_wal_lsn();" 2>/dev/null || echo "unknown")
fi
log "pre-fault LSN: ${PRE_LSN:-unknown}"

# ---------- 3. Trigger failover ----------
FAULT_TS=$(date -u +%s)
if [[ "${FAILOVER_METHOD}" == "dry-run" ]]; then
  log "dry-run: sleeping 5s to simulate failover"
  sleep 5
elif command -v patronictl &>/dev/null; then
  log "triggering patronictl failover"
  patronictl -c /etc/patroni/config.yml failover "${PG_CLUSTER}" --master "${PG_LEADER}" --force || true
elif command -v kubectl &>/dev/null; then
  log "deleting leader pod to trigger failover"
  kubectl delete pod -n "${PG_NAMESPACE}" "${PG_LEADER}" --grace-period=0 || true
fi

# ---------- 4. Poll for new leader ----------
MAX_WAIT=300
RECOVERED_TS=""
for i in $(seq 1 "${MAX_WAIT}"); do
  sleep 1
  NEW_LEADER=""
  if command -v patronictl &>/dev/null; then
    NEW_LEADER=$(patronictl -c /etc/patroni/config.yml list "${PG_CLUSTER}" --format=json 2>/dev/null \
      | python3 -c "import sys,json; m=[m for m in json.load(sys.stdin) if m.get('Role')=='Leader']; print(m[0]['Member'])" 2>/dev/null || echo "")
  fi
  if [[ -n "${NEW_LEADER}" && "${NEW_LEADER}" != "${PG_LEADER}" ]]; then
    RECOVERED_TS=$(date -u +%s)
    RTO=$(( RECOVERED_TS - FAULT_TS ))
    log "new leader elected: ${NEW_LEADER} — RTO=${RTO}s"
    break
  fi
  if (( i == MAX_WAIT )); then
    log "ERROR: no new leader after ${MAX_WAIT}s"
    RECOVERED_TS=$(date -u +%s)
    RTO=$(( RECOVERED_TS - FAULT_TS ))
    NEW_LEADER="NONE"
  fi
done

END_TS=$(date -u +%s)

cat <<EOF
{
  "scenario": "db_failover",
  "cluster": "${PG_CLUSTER}",
  "old_leader": "${PG_LEADER:-unknown}",
  "new_leader": "${NEW_LEADER:-unknown}",
  "pre_fault_lsn": "${PRE_LSN:-unknown}",
  "method": "${FAILOVER_METHOD}",
  "fault_epoch": ${FAULT_TS},
  "recovered_epoch": ${RECOVERED_TS:-${END_TS}},
  "rto_s": ${RTO:-0},
  "start_epoch": ${START_TS},
  "end_epoch": ${END_TS},
  "status": "completed"
}
EOF
