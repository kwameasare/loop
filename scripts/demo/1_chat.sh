#!/usr/bin/env bash
# S914 demo 1/5: plain chat against the G7 support agent.
#
# Demonstrates the shortest path through the runtime: a single user
# question, no tool calls, streamed token-by-token from the configured
# provider.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

demo::header "Demo 1/5 — chat (G7 support agent)"

QUESTION="What is the typical turn-around time for a refund?"
RECORDED="${DEMO_ROOT}/expected/1_chat.txt"

if demo::require_provider_or_dry_run "${RECORDED}"; then
  demo::run_support_agent "${QUESTION}"
else
  rc=$?
  if [[ "${rc}" == "100" ]]; then exit 0; fi
  exit "${rc}"
fi
