#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

: "${EU_SMOKE_REGION:=eu-west}"
export EU_SMOKE_REGION

if command -v uv >/dev/null 2>&1; then
  exec uv run python scripts/eu_smoke.py "$@"
fi

exec python3 scripts/eu_smoke.py "$@"
