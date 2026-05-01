"""Loop Slack channel adapter.

Surface APIs:

* `verify_request(signing_secret, headers, body)` -- HMAC verifier for
  Slack's `v0:` signature scheme (rejects stale timestamps > 5min).
* `parse_event(payload, ...)` / `parse_command(payload, ...)` -- lift
  Slack JSON into `InboundEvent`s with conversation routing.
* `to_blocks(frame)` -- render an `OutboundFrame` as a Slack message
  payload (Block Kit when text is structured, plain ``text`` otherwise).
* `SlackChannel` -- thin adapter that owns the thread_ts <->
  conversation_id mapping and exposes ``handle_event`` / ``handle_command``.
"""

from loop_channels_slack.blocks import to_blocks
from loop_channels_slack.channel import SlackChannel, ThreadIndex
from loop_channels_slack.connect import (
    SlackConnectFlow,
    SlackConnectRequest,
    SlackConnectResult,
    SlackInstallResult,
)
from loop_channels_slack.parser import parse_command, parse_event
from loop_channels_slack.verify import (
    REPLAY_WINDOW_SECONDS,
    SignatureError,
    verify_request,
)

__all__ = [
    "REPLAY_WINDOW_SECONDS",
    "SignatureError",
    "SlackChannel",
    "SlackConnectFlow",
    "SlackConnectRequest",
    "SlackConnectResult",
    "SlackInstallResult",
    "ThreadIndex",
    "parse_command",
    "parse_event",
    "to_blocks",
    "verify_request",
]
