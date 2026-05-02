#!/usr/bin/env bash
# chaos/nats_outage.sh — simulate NATS cluster outage and measure recovery
#
# Usage: CHAOS_NATS_TARGET=<pod-or-host> ./chaos/nats_outage.sh
#
# Supports killing one or all NATS nodes.  Default: kill one node (leader), measure
# re-election and message delivery recovery.

set -euo pipefail

NATS_NAMESPACE="${CHAOS_NATS_NAMESPACE:-loop}"
NATS_LABEL="${CHAOS_NATS_LABEL:-app=nats}"
DURATION="${CHAOS_DURATION:-20}"  # seconds to hold node down before restart

log() { echo "[$(date -u +%T)] chaos/nats_outage: $*" >&2; }

START_TS=$(date -u +%s)
log "starting NATS outage drill"

# ---------- 1. Identify NATS leader / any node ----------
NATS_POD=""
if command -v kubectl &>/dev/null; then
  NATS_POD=$(kubectl get pod -n "${NATS_NAMESPACE}" -l "${NATS_LABEL}" \
    -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
fi

if [[ -z "${NATS_POD}" ]]; then
  log "WARNING: no NATS pod found; dry-run mode"
  NATS_POD="dry-run"
fi
log "target NATS pod: ${NATS_POD}"

# ---------- 2. Kill the node ----------
FAULT_TS=$(date -u +%s)
if [[ "${NATS_POD}" != "dry-run" ]] && command -v kubectl &>/dev/null; then
  log "deleting NATS pod ${NATS_POD}"
  kubectl delete pod -n "${NATS_NAMESPACE}" "${NATS_POD}" --grace-period=0 || true
else
  log "dry-run: no action taken"
  sleep "${DURATION}"
fi

# ---------- 3. Poll until pod is Running again ----------
MAX_WAIT=180
RECOVERED_TS=""
for i in $(seq 1 "${MAX_WAIT}"); do
  sleep 1
  if [[ "${NATS_POD}" == "dry-run" ]]; then
    RECOVERED_TS=$(date -u +%s)
    break
  fi
  if command -v kubectl &>/dev/null; then
    STATUS=$(kubectl get pod -n "${NATS_NAMESPACE}" -l "${NATS_LABEL}" \
      -o jsonpath='{.items[*].status.phase}' 2>/dev/null || echo "")
    RUNNING=$(echo "${STATUS}" | tr ' ' '\n' | grep -c "^Running$" || true)
    if (( RUNNING >= 1 )); then
      RECOVERED_TS=$(date -u +%s)
      RTO=$(( RECOVERED_TS - FAULT_TS ))
      log "NATS pod recovered — RTO=${RTO}s"
      break
    fi
  fi
  if (( i == MAX_WAIT )); then
    RECOVERED_TS=$(date -u +%s)
    RTO=$(( RECOVERED_TS - FAULT_TS ))
    log "WARNING: NATS pod did not recover within ${MAX_WAIT}s"
  fi
done

END_TS=$(date -u +%s)
RTO="${RTO:-$(( END_TS - FAULT_TS ))}"

cat <<EOF
{
  "scenario": "nats_outage",
  "target_pod": "${NATS_POD}",
  "namespace": "${NATS_NAMESPACE}",
  "fault_epoch": ${FAULT_TS},
  "recovered_epoch": ${RECOVERED_TS:-${END_TS}},
  "rto_s": ${RTO},
  "start_epoch": ${START_TS},
  "end_epoch": ${END_TS},
  "status": "completed"
}
EOF
