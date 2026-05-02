#!/usr/bin/env bash
# chaos/network_partition.sh — simulate network partition between services
#
# Usage: ./chaos/network_partition.sh [--duration SECONDS] [--target SERVICE]
#
# Requires: tc (iproute2), kubectl/docker-compose access, CHAOS_TARGET env var
# Supported targets: dp-runtime, cp-api, nats, postgres, redis, qdrant

set -euo pipefail

DURATION="${CHAOS_DURATION:-30}"
TARGET="${CHAOS_TARGET:-dp-runtime}"
LOSS_PCT="${CHAOS_LOSS_PCT:-100}"  # 100 = full partition

log() { echo "[$(date -u +%T)] chaos/network_partition: $*" >&2; }

usage() {
  echo "Usage: CHAOS_TARGET=<service> CHAOS_DURATION=<seconds> $0"
  echo "  Targets: dp-runtime cp-api nats postgres redis qdrant"
  exit 1
}

if [[ "${1:-}" == "--help" ]]; then usage; fi

log "starting network partition on ${TARGET} for ${DURATION}s (loss=${LOSS_PCT}%)"

START_TS=$(date -u +%s)

# Record pre-fault state
PRE_LATENCY_FILE=$(mktemp)
cat > "${PRE_LATENCY_FILE}" <<EOF
scenario: network_partition
target: ${TARGET}
duration_s: ${DURATION}
loss_pct: ${LOSS_PCT}
start_epoch: ${START_TS}
EOF

# Apply fault via tc netem (requires NET_ADMIN capability in container or host)
# In CI/staging: use kubectl exec or docker exec to reach the target container
if command -v kubectl &>/dev/null && kubectl get pod -l "app=${TARGET}" -o name &>/dev/null 2>&1; then
  POD=$(kubectl get pod -l "app=${TARGET}" -o name | head -1)
  log "applying tc netem on ${POD}"
  kubectl exec "${POD}" -- sh -c \
    "tc qdisc add dev eth0 root netem loss ${LOSS_PCT}% || tc qdisc change dev eth0 root netem loss ${LOSS_PCT}%"
  sleep "${DURATION}"
  kubectl exec "${POD}" -- sh -c "tc qdisc del dev eth0 root netem || true"
elif command -v docker &>/dev/null; then
  CONTAINER=$(docker ps --filter "name=${TARGET}" --format "{{.Names}}" | head -1)
  if [[ -z "${CONTAINER}" ]]; then
    log "WARNING: no running container found for target=${TARGET}; dry-run mode"
    sleep "${DURATION}"
  else
    log "applying tc netem on container ${CONTAINER}"
    docker exec "${CONTAINER}" sh -c \
      "tc qdisc add dev eth0 root netem loss ${LOSS_PCT}% 2>/dev/null || tc qdisc change dev eth0 root netem loss ${LOSS_PCT}%"
    sleep "${DURATION}"
    docker exec "${CONTAINER}" sh -c "tc qdisc del dev eth0 root netem || true"
  fi
else
  log "WARNING: neither kubectl nor docker found; dry-run mode (sleeping ${DURATION}s)"
  sleep "${DURATION}"
fi

END_TS=$(date -u +%s)
ELAPSED=$(( END_TS - START_TS ))

log "partition lifted after ${ELAPSED}s"

# Emit result JSON for the harness runner to collect
cat <<EOF
{
  "scenario": "network_partition",
  "target": "${TARGET}",
  "duration_s": ${ELAPSED},
  "loss_pct": ${LOSS_PCT},
  "start_epoch": ${START_TS},
  "end_epoch": ${END_TS},
  "status": "completed"
}
EOF
