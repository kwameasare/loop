#!/usr/bin/env bash
# S914 demo 2/5: tool-calling against the G7 support agent.
#
# The "where is order ..." question forces the model to call the
# ``lookup_order`` tool, observe its result, and produce a grounded
# response. This is the canonical "tools" demo.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

demo::header "Demo 2/5 — tool calling (lookup_order)"

QUESTION="where is order 4172?"
RECORDED="${DEMO_ROOT}/expected/2_tool.txt"

if demo::require_provider_or_dry_run "${RECORDED}"; then
  demo::run_support_agent "${QUESTION}"
else
  rc=$?
  if [[ "${rc}" == "100" ]]; then exit 0; fi
  exit "${rc}"
fi
