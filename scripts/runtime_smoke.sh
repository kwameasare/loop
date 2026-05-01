#!/usr/bin/env bash
# S143: dp-runtime end-to-end smoke. Wraps scripts/runtime_smoke.py so the
# AC ("smoke script exits 0; CI runs it after deploy") is satisfied
# directly. CI invokes this script after a successful deploy step;
# operators can run it locally too.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if command -v uv >/dev/null 2>&1; then
    exec uv run python scripts/runtime_smoke.py
else
    exec python scripts/runtime_smoke.py
fi
