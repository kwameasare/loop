#!/usr/bin/env bash
# infra_smoke.sh — bring the dev stack up, verify health, tear it down.
#
# Used by S003 closing checks and as a manual sanity probe whenever
# infra/docker-compose.yml or infra/otel-collector.yaml change. Not run in CI
# by default — Docker-in-Docker integration tests are gated separately
# (see .github/workflows/ci.yml integration job).

set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE="docker compose -f infra/docker-compose.yml"

echo "==> validating compose syntax"
$COMPOSE config --quiet

echo "==> bringing stack up (--wait blocks until healthchecks pass)"
$COMPOSE up -d --wait --wait-timeout 120

echo "==> service status"
$COMPOSE ps

echo "==> probing endpoints"
fail=0
probe() {
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then
    printf "  ok   %s\n" "$name"
  else
    printf "  FAIL %s\n" "$name"
    fail=$((fail + 1))
  fi
}

probe "postgres"        $COMPOSE exec -T postgres pg_isready -U loop -d loop
probe "redis"           $COMPOSE exec -T redis redis-cli ping
probe "qdrant /readyz"  curl -fsS http://127.0.0.1:6333/readyz
probe "nats /healthz"   curl -fsS http://127.0.0.1:8222/healthz
probe "minio ready"     curl -fsS http://127.0.0.1:9000/minio/health/ready
probe "clickhouse ping" curl -fsS http://127.0.0.1:8123/ping
probe "otel healthz"    curl -fsS http://127.0.0.1:13133/

if [[ "${KEEP_UP:-0}" != "1" ]]; then
  echo "==> tearing down (set KEEP_UP=1 to leave running)"
  $COMPOSE down
fi

if (( fail > 0 )); then
  echo "smoke: $fail probe(s) failed" >&2
  exit 1
fi

echo "smoke: all good"
