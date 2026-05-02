#!/usr/bin/env bash
# S780: wrapper for the cross-cloud deploy + first-turn smoke.
set -euo pipefail

if command -v uv >/dev/null 2>&1; then
  exec uv run python scripts/cross_cloud_smoke.py "$@"
fi

exec python3 scripts/cross_cloud_smoke.py "$@"
