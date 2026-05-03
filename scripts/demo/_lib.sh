#!/usr/bin/env bash
# S914: shared helpers for the scripts/demo/* runners.
#
# - ``demo::header`` — print a banner so the operator can tell the
#   demos apart in a screen recording.
# - ``demo::require_provider_or_dry_run`` — when ``LOOP_DEMO_DRY_RUN=1``
#   we short-circuit by printing the recorded "expected" transcript
#   (so the demo tests stay hermetic in CI). Otherwise we require
#   ``OPENAI_API_KEY`` or ``ANTHROPIC_API_KEY`` so the live LLM round
#   trip can run end-to-end.

set -euo pipefail

DEMO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${DEMO_ROOT}/../.." && pwd)"

demo::header() {
  local title="${1:?title is required}"
  printf '\n\033[1;35m=== %s ===\033[0m\n' "${title}"
}

demo::require_provider_or_dry_run() {
  local recorded="${1:?recorded transcript path is required}"
  if [[ "${LOOP_DEMO_DRY_RUN:-0}" == "1" ]]; then
    if [[ ! -f "${recorded}" ]]; then
      printf 'demo: missing recorded transcript at %s\n' "${recorded}" >&2
      return 1
    fi
    cat "${recorded}"
    return 100
  fi
  if [[ -z "${OPENAI_API_KEY:-}" && -z "${ANTHROPIC_API_KEY:-}" ]]; then
    cat >&2 <<EOF
demo: no provider key configured.

Set OPENAI_API_KEY or ANTHROPIC_API_KEY before running this demo, or
re-run with LOOP_DEMO_DRY_RUN=1 to print the recorded transcript at
${recorded}.
EOF
    return 2
  fi
  return 0
}

demo::run_support_agent() {
  local question="${1:?question is required}"
  (
    cd "${REPO_ROOT}"
    uv run python examples/support_agent/run_local.py "${question}"
  )
}
