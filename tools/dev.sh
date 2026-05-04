#!/usr/bin/env bash
# Local-dev runner — opens a tmux session with cp / dp / studio in
# separate panes, each sourcing .env so port overrides + provider keys
# are picked up.
#
# Why this exists
# ===============
# The Makefile target ``make dev`` referenced ``tools/dev.sh`` but the
# file didn't exist (P0.6c in the prod-readiness audit). Instead of
# manually opening three terminals, sourcing .env in each, and running
# uvicorn / next dev by hand, this script wires it up reproducibly.
#
# Usage
# =====
#   make dev
# or directly:
#   ./tools/dev.sh
#
# Once attached:
#   - Pane 0 (top-left):  cp uvicorn at $LOOP_CP_API_PORT (default 8080)
#   - Pane 1 (top-right): dp uvicorn at $LOOP_RUNTIME_BIND_PORT (default 8081)
#   - Pane 2 (bottom):    studio next dev at $LOOP_STUDIO_PORT (default 3001)
#
# Detach with ``Ctrl-b d``. Re-attach with ``tmux attach -t loop-dev``.
# Kill with ``tmux kill-session -t loop-dev``.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION="loop-dev"
ENV_FILE="$ROOT_DIR/.env"

CP_PORT="${LOOP_CP_API_PORT:-8080}"
DP_PORT="${LOOP_RUNTIME_BIND_PORT:-8081}"
STUDIO_PORT="${LOOP_STUDIO_PORT:-3001}"

if ! command -v tmux >/dev/null 2>&1; then
  echo "error: tmux is required. Install with: brew install tmux" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "error: $ENV_FILE not found." >&2
  echo "       Copy .env.example to .env and fill in your provider keys." >&2
  exit 1
fi

# If a session is already attached, just re-attach so we don't trample
# already-running processes.
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "→ session $SESSION already exists; attaching"
  exec tmux attach -t "$SESSION"
fi

# Each pane prefixes with `set -a; . ./.env; set +a` so child processes
# inherit the env. We also `cd` to the repo root so relative paths in
# imports / configs work.
ENV_PREAMBLE="cd $ROOT_DIR && set -a && . ./.env && set +a"

CP_CMD="$ENV_PREAMBLE && exec uv run uvicorn loop_control_plane.app:app --host 127.0.0.1 --port $CP_PORT --reload --log-level info"
DP_CMD="$ENV_PREAMBLE && exec uv run uvicorn loop_data_plane.runtime_app:app --host 127.0.0.1 --port $DP_PORT --reload --log-level info"
STUDIO_CMD="cd $ROOT_DIR/apps/studio && exec pnpm exec next dev -p $STUDIO_PORT"

echo "→ starting tmux session $SESSION"
tmux new-session -d -s "$SESSION" -n services -x 220 -y 60 "$CP_CMD"
tmux split-window -h -t "$SESSION:services" "$DP_CMD"
tmux split-window -v -t "$SESSION:services.0" "$STUDIO_CMD"
tmux select-layout -t "$SESSION:services" tiled

cat <<EOF

✓ session $SESSION started:
  - cp:     http://localhost:$CP_PORT/healthz
  - dp:     http://localhost:$DP_PORT/healthz
  - studio: http://localhost:$STUDIO_PORT

Attaching now. Detach with Ctrl-b d. Kill with: tmux kill-session -t $SESSION

EOF

exec tmux attach -t "$SESSION"
