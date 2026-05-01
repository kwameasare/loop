#!/usr/bin/env bash
# S181: published demo web-channel smoke. Posts a visitor question to
# the demo chat endpoint and asserts the configured golden answer.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if command -v uv >/dev/null 2>&1; then
    exec uv run python scripts/e2e_web_smoke.py "$@"
else
    exec python scripts/e2e_web_smoke.py "$@"
fi
