"""Project ``OutboundFrame`` -> WhatsApp Cloud API request body.

Cloud API messages are POSTed to::

    POST https://graph.facebook.com/v18.0/{phone_number_id}/messages

with a JSON body shaped like::

    {"messaging_product": "whatsapp", "to": "<msisdn>", "type": "text", "text": {"body": "..."}}

We return the JSON body. The HTTP transport (httpx, retries, auth)
lives in the runtime so this module stays sync + dependency-free.

Two entry points (S343):

* :func:`to_messages` — frame-driven path used by the streaming
  channel; covers text + handoff + error.
* :func:`render_interactive` — structured-output path the runtime
  calls when an agent emits a ``list`` / ``button`` / ``media`` /
  ``template`` directive. Works directly with typed payloads so the
  OutboundFrame ``dict[str, str]`` contract is not abused.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from loop_channels_core import OutboundFrame, OutboundFrameKind

MESSAGING_PRODUCT: str = "whatsapp"

# Cloud API hard limits we surface as constants so studio validators
# can show inline errors at design-time rather than at send-time.
MAX_REPLY_BUTTONS: int = 3
MAX_LIST_SECTIONS: int = 10
MAX_LIST_ROWS_PER_SECTION: int = 10
MAX_TEXT_BODY_LEN: int = 4096
MAX_BUTTON_TITLE_LEN: int = 20
MAX_LIST_ROW_TITLE_LEN: int = 24
MAX_LIST_ROW_DESCRIPTION_LEN: int = 72


class WhatsAppRenderError(ValueError):
    """Raised when an interactive payload violates a Cloud API hard limit."""


# ---------------- frame path (text/handoff/error) ----------------


def to_messages(frame: OutboundFrame, *, to: str) -> dict[str, Any]:
    """Serialise a single ``OutboundFrame`` to a Cloud API body.

    Returns an empty ``{}`` for frame kinds that have no surface
    representation (e.g. ``AGENT_TOKEN`` deltas, ``DONE`` markers,
    or ``TOOL_CALL_*`` brackets that should remain server-internal).
    """
    if frame.kind is OutboundFrameKind.AGENT_MESSAGE:
        return _wrap_text(to=to, body=frame.text)
    if frame.kind is OutboundFrameKind.HANDOFF:
        target = frame.payload.get("target", "")
        body = f"Handing off to {target}." if target else "Handing off."
        return _wrap_text(to=to, body=body)
    if frame.kind is OutboundFrameKind.ERROR:
        code = frame.payload.get("code", "error")
        return _wrap_text(to=to, body=f"[{code}] {frame.text}".strip())
    return {}


def _wrap_text(*, to: str, body: str) -> dict[str, Any]:
    return {
        "messaging_product": MESSAGING_PRODUCT,
        "to": to,
        "type": "text",
        "text": {"body": body},
    }


# ---------------- interactive path (list/button/media/template) ----------------


class InteractiveKind(StrEnum):
    LIST = "list"
    BUTTON = "button"
    MEDIA = "media"
    TEMPLATE = "template"


@dataclass(frozen=True)
class ReplyButton:
    id: str
    title: str


@dataclass(frozen=True)
class ListRow:
    id: str
    title: str
    description: str = ""


@dataclass(frozen=True)
class ListSection:
    title: str
    rows: tuple[ListRow, ...]


def render_interactive(kind: InteractiveKind, *, to: str, **kwargs: Any) -> dict[str, Any]:
    """Render a structured outbound message body.

    ``kwargs`` differ by kind:

    * LIST: ``body`` (str), ``button`` (str), ``sections``
      (``Sequence[ListSection]``)
    * BUTTON: ``body`` (str), ``buttons`` (``Sequence[ReplyButton]``)
    * MEDIA: ``media_type`` (image/audio/video/document), ``url``
      (str), optional ``caption``
    * TEMPLATE: ``name`` (str), optional ``language`` (default
      ``en_US``), optional ``components`` (list[dict])
    """
    if kind is InteractiveKind.LIST:
        return _render_list(
            to=to,
            body=str(kwargs.get("body", "")),
            button=str(kwargs.get("button", "Choose")),
            sections=kwargs.get("sections") or (),
        )
    if kind is InteractiveKind.BUTTON:
        return _render_buttons(
            to=to,
            body=str(kwargs.get("body", "")),
            buttons=kwargs.get("buttons") or (),
        )
    if kind is InteractiveKind.MEDIA:
        return _render_media(
            to=to,
            media_type=str(kwargs.get("media_type", "")),
            url=str(kwargs.get("url", "")),
            caption=kwargs.get("caption"),
        )
    if kind is InteractiveKind.TEMPLATE:
        return _render_template(
            to=to,
            name=str(kwargs.get("name", "")),
            language=str(kwargs.get("language", "en_US")),
            components=kwargs.get("components") or (),
        )
    raise WhatsAppRenderError(f"unknown interactive kind: {kind!r}")


def _render_buttons(*, to: str, body: str, buttons: Sequence[ReplyButton]) -> dict[str, Any]:
    if not buttons:
        raise WhatsAppRenderError("button payload requires at least one button")
    if len(buttons) > MAX_REPLY_BUTTONS:
        raise WhatsAppRenderError(
            f"button payload has {len(buttons)} buttons; max {MAX_REPLY_BUTTONS}"
        )
    actions: list[dict[str, Any]] = []
    for b in buttons:
        if not b.id or not b.title:
            raise WhatsAppRenderError("each button needs non-empty id + title")
        actions.append(
            {
                "type": "reply",
                "reply": {"id": b.id, "title": b.title[:MAX_BUTTON_TITLE_LEN]},
            }
        )
    return {
        "messaging_product": MESSAGING_PRODUCT,
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {"buttons": actions},
        },
    }


def _render_list(
    *,
    to: str,
    body: str,
    button: str,
    sections: Sequence[ListSection],
) -> dict[str, Any]:
    if not sections:
        raise WhatsAppRenderError("list payload requires at least one section")
    if len(sections) > MAX_LIST_SECTIONS:
        raise WhatsAppRenderError(
            f"list payload has {len(sections)} sections; max {MAX_LIST_SECTIONS}"
        )
    sections_out: list[dict[str, Any]] = []
    for s in sections:
        if not s.rows:
            raise WhatsAppRenderError(f"section {s.title!r} must have at least one row")
        if len(s.rows) > MAX_LIST_ROWS_PER_SECTION:
            raise WhatsAppRenderError(
                f"section {s.title!r} has {len(s.rows)} rows; "
                f"max {MAX_LIST_ROWS_PER_SECTION}"
            )
        rows_out: list[dict[str, Any]] = []
        for r in s.rows:
            if not r.id or not r.title:
                raise WhatsAppRenderError("each list row needs non-empty id + title")
            row: dict[str, Any] = {"id": r.id, "title": r.title[:MAX_LIST_ROW_TITLE_LEN]}
            if r.description:
                row["description"] = r.description[:MAX_LIST_ROW_DESCRIPTION_LEN]
            rows_out.append(row)
        sections_out.append(
            {"title": (s.title or "Items")[:MAX_LIST_ROW_TITLE_LEN], "rows": rows_out}
        )
    return {
        "messaging_product": MESSAGING_PRODUCT,
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body},
            "action": {
                "button": button[:MAX_BUTTON_TITLE_LEN],
                "sections": sections_out,
            },
        },
    }


_MEDIA_TYPES: frozenset[str] = frozenset({"image", "audio", "video", "document"})


def _render_media(
    *,
    to: str,
    media_type: str,
    url: str,
    caption: object | None,
) -> dict[str, Any]:
    if media_type not in _MEDIA_TYPES:
        raise WhatsAppRenderError(
            f"media_type {media_type!r} not in {sorted(_MEDIA_TYPES)!r}"
        )
    if not url:
        raise WhatsAppRenderError("media payload requires non-empty 'url'")
    body: dict[str, Any] = {"link": url}
    if caption:
        body["caption"] = str(caption)
    return {
        "messaging_product": MESSAGING_PRODUCT,
        "to": to,
        "type": media_type,
        media_type: body,
    }


def _render_template(
    *,
    to: str,
    name: str,
    language: str,
    components: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    if not name:
        raise WhatsAppRenderError("template payload requires 'name'")
    template: dict[str, Any] = {"name": name, "language": {"code": language}}
    if components:
        template["components"] = list(components)
    return {
        "messaging_product": MESSAGING_PRODUCT,
        "to": to,
        "type": "template",
        "template": template,
    }


__all__ = [
    "MAX_BUTTON_TITLE_LEN",
    "MAX_LIST_ROWS_PER_SECTION",
    "MAX_LIST_ROW_DESCRIPTION_LEN",
    "MAX_LIST_ROW_TITLE_LEN",
    "MAX_LIST_SECTIONS",
    "MAX_REPLY_BUTTONS",
    "MAX_TEXT_BODY_LEN",
    "MESSAGING_PRODUCT",
    "InteractiveKind",
    "ListRow",
    "ListSection",
    "ReplyButton",
    "WhatsAppRenderError",
    "render_interactive",
    "to_messages",
]
