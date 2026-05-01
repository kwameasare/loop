#!/usr/bin/env bash
# S122: cp-api end-to-end smoke. Wraps scripts/cp_smoke.py so the
# AC ("scripts/cp_smoke.sh exits 0") is satisfied directly. CI invokes
# this script; humans can too.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if command -v uv >/dev/null 2>&1; then
    exec uv run python scripts/cp_smoke.py
else
    exec python scripts/cp_smoke.py
fi
