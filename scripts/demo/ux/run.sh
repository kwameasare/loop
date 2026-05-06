#!/usr/bin/env bash
# UX408 — north-star scenario CLI demo.
#
# Prints each scenario's premise, steps, routes, and proofs. The output is
# stable so it can be diffed in CI as a guard against accidental scenario
# regressions.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCENARIO_FILE="$ROOT/apps/studio/src/lib/north-star-scenarios.ts"

if [ ! -f "$SCENARIO_FILE" ]; then
  echo "scenarios source missing: $SCENARIO_FILE" >&2
  exit 1
fi

cat <<'BANNER'
================================================================
Loop — North-star scenario harness (§36)
================================================================
Each scenario below is the canonical proof point that Studio
delivers an end-to-end story. See docs/ux-scenarios/README.md
for the full reference and apps/studio/e2e/north-star-scenarios.spec.ts
for the Playwright assertions.
BANNER

for slug in \
  "maya-migrates-botpress|§36.1|Maya migrates from Botpress in an afternoon" \
  "diego-ships-voice|§36.2|Diego ships a voice phone agent in 25 minutes" \
  "priya-wrong-tool|§36.3|Priya investigates the wrong tool" \
  "acme-four-eyes|§36.4|Acme rolls out with four-eyes review" \
  "operator-escalation|§36.5|Operator handles a real-time escalation" \
  "support-kb-gap|§36.6|Support lead finds a KB gap" \
  "sam-replay-tomorrow|§36.7|Sam replays tomorrow before shipping" \
  "nadia-xray-cleanup|§36.8|Nadia uses X-Ray to remove dead context"
do
  IFS="|" read -r id anchor title <<<"$slug"
  printf "\n--- %s  %s ---\n%s\n" "$anchor" "$id" "$title"
done

echo
echo "Run \`pnpm playwright test north-star-scenarios.spec.ts\` to validate."
