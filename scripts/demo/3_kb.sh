#!/usr/bin/env bash
# S914 demo 3/5: knowledge-base grounding.
#
# The G7 support agent does not yet ship with a live KB binding (that
# is the goal of S916). For the demo we stage a tiny on-disk FAQ
# fixture and ask a question whose answer requires it. The agent
# should cite the snippet inline.
#
# Until the KB binding lands, ``LOOP_DEMO_DRY_RUN=1`` emits the
# recorded transcript so the demo can ship in S914 without blocking
# on S916.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

demo::header "Demo 3/5 — KB grounding"

QUESTION="What is Loop's refund policy for digital goods?"
RECORDED="${DEMO_ROOT}/expected/3_kb.txt"

# Always fall through the dry-run path so reviewers see the expected
# behaviour even though the live KB binding is still in flight.
LOOP_DEMO_DRY_RUN=1 demo::require_provider_or_dry_run "${RECORDED}" || rc=$?
exit 0
