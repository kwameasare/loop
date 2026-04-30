"""Twilio SIP gateway TwiML emitter (S380).

Twilio Programmable Voice routes incoming PSTN calls to a Loop-hosted
HTTP endpoint that returns TwiML XML. The TwiML tells Twilio to
``<Connect><Stream>`` the call's bidirectional audio to a websocket
that Loop's voice runtime owns. We *generate* TwiML from a strict
config object — no string interpolation in handlers.

This module is the spec; the FastAPI handler imports ``build_twiml``
and returns its output verbatim.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit
from xml.etree.ElementTree import Element, SubElement, tostring


class TwilioTwimlError(ValueError):
    """TwiML config rejected (bad URL scheme, missing required fields)."""


@dataclass(frozen=True, slots=True)
class StreamConfig:
    """A ``<Stream>`` directive nested under ``<Connect>``."""

    websocket_url: str
    track: str = "inbound_track"  # inbound_track | outbound_track | both_tracks
    name: str = "loop-stream"

    def __post_init__(self) -> None:
        if not self.websocket_url:
            raise TwilioTwimlError("websocket_url required")
        scheme = urlsplit(self.websocket_url).scheme
        if scheme not in ("ws", "wss"):
            raise TwilioTwimlError(f"websocket_url must be ws/wss, got {scheme!r}")
        if self.track not in ("inbound_track", "outbound_track", "both_tracks"):
            raise TwilioTwimlError(f"unsupported track {self.track!r}")


@dataclass(frozen=True, slots=True)
class TwimlConfig:
    """Top-level Twilio handler config."""

    stream: StreamConfig
    say_before: str | None = None  # optional <Say> before <Connect>
    voice: str = "Polly.Joanna"  # used only when say_before is set
    language: str = "en-US"
    hangup_on_star: bool = False  # operator escape

    def __post_init__(self) -> None:
        if self.say_before is not None and not self.say_before.strip():
            raise TwilioTwimlError("say_before is empty (set None to skip)")


def build_twiml(config: TwimlConfig) -> bytes:
    """Render TwiML XML bytes for the configured response."""
    response = Element("Response")
    if config.say_before:
        say = SubElement(
            response, "Say", {"voice": config.voice, "language": config.language}
        )
        say.text = config.say_before
    connect = SubElement(response, "Connect")
    stream_attrs = {
        "url": config.stream.websocket_url,
        "track": config.stream.track,
        "name": config.stream.name,
    }
    SubElement(connect, "Stream", stream_attrs)
    if config.hangup_on_star:
        # In Twilio's call-flow, this hint is exposed via Gather/Hangup
        # nodes. We add a minimal Hangup so the handler stays idempotent.
        SubElement(response, "Hangup")
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(response, encoding="utf-8")


def parse_twilio_form(form: dict[str, str]) -> dict[str, str]:
    """Pluck the TwiML-relevant fields from a Twilio webhook POST body.

    Twilio posts form-encoded bodies; runtime maps to a dict before
    reaching this layer. We extract the small subset used downstream
    (CallSid, From, To, AccountSid) and reject required-field gaps.
    """
    required = ("CallSid", "From", "To", "AccountSid")
    missing = [f for f in required if not form.get(f)]
    if missing:
        raise TwilioTwimlError(f"missing required fields: {missing}")
    return {f: form[f] for f in required}


__all__ = [
    "StreamConfig",
    "TwilioTwimlError",
    "TwimlConfig",
    "build_twiml",
    "parse_twilio_form",
]
