"""Slack ephemeral error responses (S226).

When a Slack handler raises, we must respond with an *ephemeral*
message visible only to the invoking user — never a public
``chat.postMessage`` that spams the channel. Slack's Web API
distinguishes these via ``response_type="ephemeral"`` on the
response payload of slash commands and interactive responses.

Public-facing error codes follow the ``LOOP-CH-NNN`` scheme so
support can correlate without leaking internals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "EPHEMERAL_BUDGET_EXCEEDED",
    "EPHEMERAL_INTERNAL",
    "EPHEMERAL_NOT_INSTALLED",
    "EPHEMERAL_PERMISSION",
    "EPHEMERAL_RATE_LIMITED",
    "SlackErrorCode",
    "format_ephemeral_error",
]


@dataclass(frozen=True)
class SlackErrorCode:
    code: str
    public_message: str


EPHEMERAL_INTERNAL = SlackErrorCode(
    "LOOP-CH-001", "Sorry, something went wrong on our side."
)
EPHEMERAL_NOT_INSTALLED = SlackErrorCode(
    "LOOP-CH-002", "This Slack workspace is not connected to a Loop agent yet."
)
EPHEMERAL_PERMISSION = SlackErrorCode(
    "LOOP-CH-003", "You do not have permission to use this command."
)
EPHEMERAL_RATE_LIMITED = SlackErrorCode(
    "LOOP-CH-004", "You are sending messages too quickly. Try again in a few seconds."
)
EPHEMERAL_BUDGET_EXCEEDED = SlackErrorCode(
    "LOOP-CH-005", "This workspace has reached its daily spend cap."
)


def format_ephemeral_error(
    err: SlackErrorCode, *, detail: str | None = None
) -> dict[str, Any]:
    """Return the JSON payload Slack expects in a 200 OK response.

    The ``response_type=ephemeral`` keeps the error invisible to
    other channel members. The visible text always contains the
    machine-readable ``[code]`` so users can paste it into a
    support ticket.
    """
    text = f"[{err.code}] {err.public_message}"
    if detail:
        # Keep the trailing detail short — Slack mobile truncates
        # past about 100 chars for ephemerals.
        text = f"{text} ({detail[:80]})"
    return {
        "response_type": "ephemeral",
        "text": text,
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            }
        ],
    }
