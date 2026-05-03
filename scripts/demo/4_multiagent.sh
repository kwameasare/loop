#!/usr/bin/env bash
# S914 demo 4/5: multi-agent handoff.
#
# Walks two G7 support-agent invocations in sequence to illustrate
# the supervisor → worker pattern: the first agent receives the
# customer question, decides which specialist to route to, and the
# second agent answers using its tool. With a real provider key the
# script makes two real LLM calls; in dry-run mode it prints the
# recorded transcript.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

demo::header "Demo 4/5 — multi-agent handoff"

RECORDED="${DEMO_ROOT}/expected/4_multiagent.txt"

if demo::require_provider_or_dry_run "${RECORDED}"; then
  demo::run_support_agent \
    "I need a refund AND I want to know when my last order will arrive. Order 4172."
  printf '\n--- handing off to specialist ---\n\n'
  demo::run_support_agent "where is order 4172?"
else
  rc=$?
  if [[ "${rc}" == "100" ]]; then exit 0; fi
  exit "${rc}"
fi
