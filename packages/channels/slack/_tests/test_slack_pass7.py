"""Slack pass7: ephemeral error format."""

from __future__ import annotations

from loop_channels_slack.ephemeral_errors import (
    EPHEMERAL_BUDGET_EXCEEDED,
    EPHEMERAL_INTERNAL,
    EPHEMERAL_RATE_LIMITED,
    format_ephemeral_error,
)


def test_ephemeral_payload_is_private() -> None:
    p = format_ephemeral_error(EPHEMERAL_INTERNAL)
    assert p["response_type"] == "ephemeral"
    assert "[LOOP-CH-001]" in p["text"]


def test_ephemeral_with_detail_truncates() -> None:
    long = "x" * 200
    p = format_ephemeral_error(EPHEMERAL_INTERNAL, detail=long)
    # truncated to 80 chars in body
    assert "x" * 80 in p["text"]
    assert "x" * 81 not in p["text"]


def test_distinct_codes() -> None:
    codes = {
        EPHEMERAL_INTERNAL.code,
        EPHEMERAL_BUDGET_EXCEEDED.code,
        EPHEMERAL_RATE_LIMITED.code,
    }
    assert len(codes) == 3


def test_blocks_contain_text() -> None:
    p = format_ephemeral_error(EPHEMERAL_BUDGET_EXCEEDED, detail="cap=$5/day")
    assert p["blocks"][0]["text"]["type"] == "mrkdwn"
    assert "LOOP-CH-005" in p["blocks"][0]["text"]["text"]
