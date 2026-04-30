"""WhatsApp interactive message rendering (S347).

WhatsApp Cloud API supports two "interactive" surfaces:

* ``button``: 1-3 quick-reply buttons.
* ``list``:   header + body + a list of sections x rows (max 10 rows).

Loop's agent emits a structured ``Interactive*`` model; this module
renders it to the JSON shape WhatsApp expects on
``POST /v18.0/<phone_id>/messages``.

We validate strictly: WhatsApp will silently drop messages that
exceed the documented per-field limits, which is much harder to
debug than a clear pre-flight error.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Per WhatsApp Cloud API v18 limits as of 2024-09:
MAX_BUTTONS = 3
MAX_BUTTON_TITLE = 20
MAX_LIST_ROWS = 10
MAX_LIST_SECTIONS = 10
MAX_LIST_BUTTON_LABEL = 20
MAX_HEADER_TEXT = 60
MAX_BODY_TEXT = 1024
MAX_FOOTER_TEXT = 60
MAX_ROW_TITLE = 24
MAX_ROW_DESCRIPTION = 72
MAX_ID = 256


class InteractiveError(ValueError):
    """Interactive payload violates a WhatsApp constraint."""


def _check_len(field: str, value: str, max_len: int) -> None:
    if not value:
        raise InteractiveError(f"{field} must be non-empty")
    if len(value) > max_len:
        raise InteractiveError(
            f"{field} length {len(value)} exceeds {max_len}"
        )


@dataclass(frozen=True, slots=True)
class Button:
    id: str
    title: str

    def __post_init__(self) -> None:
        _check_len("button.id", self.id, MAX_ID)
        _check_len("button.title", self.title, MAX_BUTTON_TITLE)


@dataclass(frozen=True, slots=True)
class ButtonReplyMessage:
    body: str
    buttons: tuple[Button, ...]
    header: str | None = None
    footer: str | None = None

    def __post_init__(self) -> None:
        _check_len("body", self.body, MAX_BODY_TEXT)
        if not self.buttons:
            raise InteractiveError("at least one button required")
        if len(self.buttons) > MAX_BUTTONS:
            raise InteractiveError(f"max {MAX_BUTTONS} buttons (got {len(self.buttons)})")
        seen_ids = {b.id for b in self.buttons}
        if len(seen_ids) != len(self.buttons):
            raise InteractiveError("button ids must be unique")
        if self.header is not None:
            _check_len("header", self.header, MAX_HEADER_TEXT)
        if self.footer is not None:
            _check_len("footer", self.footer, MAX_FOOTER_TEXT)


@dataclass(frozen=True, slots=True)
class Row:
    id: str
    title: str
    description: str | None = None

    def __post_init__(self) -> None:
        _check_len("row.id", self.id, MAX_ID)
        _check_len("row.title", self.title, MAX_ROW_TITLE)
        if self.description is not None:
            _check_len("row.description", self.description, MAX_ROW_DESCRIPTION)


@dataclass(frozen=True, slots=True)
class Section:
    title: str
    rows: tuple[Row, ...]

    def __post_init__(self) -> None:
        _check_len("section.title", self.title, MAX_HEADER_TEXT)
        if not self.rows:
            raise InteractiveError("section must have at least one row")


@dataclass(frozen=True, slots=True)
class ListMessage:
    body: str
    button_label: str
    sections: tuple[Section, ...]
    header: str | None = None
    footer: str | None = None

    def __post_init__(self) -> None:
        _check_len("body", self.body, MAX_BODY_TEXT)
        _check_len("button_label", self.button_label, MAX_LIST_BUTTON_LABEL)
        if not self.sections:
            raise InteractiveError("at least one section required")
        if len(self.sections) > MAX_LIST_SECTIONS:
            raise InteractiveError(f"max {MAX_LIST_SECTIONS} sections")
        total_rows = sum(len(s.rows) for s in self.sections)
        if total_rows > MAX_LIST_ROWS:
            raise InteractiveError(
                f"max {MAX_LIST_ROWS} total rows (got {total_rows})"
            )
        # row ids must be unique across sections
        all_ids = [r.id for s in self.sections for r in s.rows]
        if len(set(all_ids)) != len(all_ids):
            raise InteractiveError("row ids must be globally unique")
        if self.header is not None:
            _check_len("header", self.header, MAX_HEADER_TEXT)
        if self.footer is not None:
            _check_len("footer", self.footer, MAX_FOOTER_TEXT)


def render_button_reply(*, to: str, msg: ButtonReplyMessage) -> dict[str, Any]:
    body: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": msg.body},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": b.id, "title": b.title}}
                    for b in msg.buttons
                ],
            },
        },
    }
    if msg.header:
        body["interactive"]["header"] = {"type": "text", "text": msg.header}
    if msg.footer:
        body["interactive"]["footer"] = {"text": msg.footer}
    return body


def render_list(*, to: str, msg: ListMessage) -> dict[str, Any]:
    sections_json = [
        {
            "title": s.title,
            "rows": [
                {
                    "id": r.id,
                    "title": r.title,
                    **({"description": r.description} if r.description else {}),
                }
                for r in s.rows
            ],
        }
        for s in msg.sections
    ]
    body: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": msg.body},
            "action": {
                "button": msg.button_label,
                "sections": sections_json,
            },
        },
    }
    if msg.header:
        body["interactive"]["header"] = {"type": "text", "text": msg.header}
    if msg.footer:
        body["interactive"]["footer"] = {"text": msg.footer}
    return body


__all__ = [
    "Button",
    "ButtonReplyMessage",
    "InteractiveError",
    "ListMessage",
    "Row",
    "Section",
    "render_button_reply",
    "render_list",
]
