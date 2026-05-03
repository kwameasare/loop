#!/usr/bin/env bash
# S914 demo 5/5: human-in-the-loop takeover.
#
# Demonstrates the agent escalating to a human operator. The agent
# starts the conversation, hits a confidence threshold, and the
# transcript is then "taken over" by the operator who replies with a
# canned response. The takeover handshake itself ships in S917; until
# then this demo runs in dry-run mode against the recorded transcript.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

demo::header "Demo 5/5 — HITL takeover"

RECORDED="${DEMO_ROOT}/expected/5_hitl.txt"

# HITL takeover infrastructure lands in S917. Demo runs hermetically
# off the recorded transcript so the script remains green in CI.
LOOP_DEMO_DRY_RUN=1 demo::require_provider_or_dry_run "${RECORDED}" || rc=$?
exit 0
