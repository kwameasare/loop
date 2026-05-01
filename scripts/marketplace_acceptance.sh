#!/usr/bin/env bash
set -euo pipefail

uv run pytest packages/control-plane/_tests/test_mcp_marketplace_pass13.py \
  -q -k "first_party_catalog_covers_mvp_servers_and_acceptance_gate"
